from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, F
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models.functions import TruncDay
from django.urls import reverse
from datetime import timedelta, datetime
import os
import json
import zipfile
import io
from .models import (
    Document, Category, DocumentVersion, UserProfile, 
    DocumentShare, Comment, Notification
)
from .forms import DocumentForm, UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    if not has_permission(request.user, 'view'):
        return HttpResponseForbidden("You don't have permission to view documents.")
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    # Filter out archived documents from the main dashboard
    documents = Document.objects.filter(
        Q(owner=request.user) | Q(is_private=False)
    ).filter(is_archived=False)
    
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category:
        documents = documents.filter(category__name=category)
    
    # Get all categories
    categories = Category.objects.all()
    
    # Get only categories that have active documents
    active_categories_count = Category.objects.filter(
        document__is_archived=False
    ).distinct().count()
    
    # Analytics data - Document statistics (excluding archived documents)
    total_documents = Document.objects.filter(is_archived=False).count()
    user_documents = Document.objects.filter(owner=request.user, is_archived=False).count()
    
    # Category distribution for pie chart (excluding archived documents)
    category_stats = Document.objects.filter(is_archived=False).values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Format category data for JSON
    category_data = []
    for cat in category_stats:
        category_data.append({
            'label': cat['category__name'] or 'Uncategorized',
            'count': cat['count']
        })
    
    # Recent activity - last 7 days of uploads (excluding archived documents)
    last_week = timezone.now() - timedelta(days=7)
    daily_uploads = Document.objects.filter(
        uploaded_at__gte=last_week,
        is_archived=False
    ).annotate(
        day=TruncDay('uploaded_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Format for the chart
    activity_labels = []
    activity_data = []
    
    # Create a complete date range for the last 7 days
    current_date = last_week
    end_date = timezone.now()
    
    while current_date.date() <= end_date.date():
        day_str = current_date.strftime('%Y-%m-%d')
        activity_labels.append(current_date.strftime('%d %b'))
        
        # Find if there are uploads for this day
        day_data = next((item for item in daily_uploads if item['day'].strftime('%Y-%m-%d') == day_str), None)
        activity_data.append(day_data['count'] if day_data else 0)
        
        current_date += timedelta(days=1)
    
    # File type distribution (excluding archived documents)
    file_types = {}
    for doc in Document.objects.filter(is_archived=False):
        ext = os.path.splitext(doc.file.name)[1].lower()
        if ext:
            file_types[ext] = file_types.get(ext, 0) + 1
    
    # Storage usage calculation (excluding archived documents)
    storage_usage = {
        'user': 0,
        'total': 0,
        'by_category': {}
    }
    
    for doc in Document.objects.filter(is_archived=False):
        try:
            size = doc.file.size
            storage_usage['total'] += size
            if doc.owner == request.user:
                storage_usage['user'] += size
                
            # Also track by category
            cat_name = doc.category.name if doc.category else 'Uncategorized'
            if cat_name not in storage_usage['by_category']:
                storage_usage['by_category'][cat_name] = 0
            storage_usage['by_category'][cat_name] += size
        except:
            # File might not exist
            pass
    
    # Convert bytes to MB
    for key in ['user', 'total']:
        storage_usage[key] = round(storage_usage[key] / (1024 * 1024), 2)
    
    for category in storage_usage['by_category']:
        storage_usage['by_category'][category] = round(storage_usage['by_category'][category] / (1024 * 1024), 2)
    
    # Get recent uploads - last 5 non-archived docs
    recent_uploads = Document.objects.filter(is_archived=False).order_by('-uploaded_at')[:5]
    
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'categories': categories,
        'query': query,
        'selected_category': category,
        # Analytics data
        'analytics': {
            'total_documents': total_documents,
            'user_documents': user_documents,
            'active_categories_count': active_categories_count,  # Add this
            'category_stats': category_data,
            'category_stats_json': json.dumps(category_data),
            'file_types': file_types,
            'file_types_json': json.dumps(file_types),
            'storage_usage': storage_usage,
            'storage_usage_json': json.dumps(storage_usage['by_category']),
            'activity_labels': activity_labels,
            'activity_data': activity_data,
            'activity_labels_json': json.dumps(activity_labels),
            'activity_data_json': json.dumps(activity_data),
            'recent_uploads': recent_uploads
        }
    })

@login_required
def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.owner = request.user
            document.save()
            DocumentVersion.objects.create(
                document=document,
                file=document.file,
                version_number=1,
                created_by=request.user,
                comment="Initial version"
            )
            messages.success(request, 'Document uploaded successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DocumentForm()
    
    context = {
        'form': form,
        'title': 'Upload Document'  # Add this for the template
    }
    return render(request, 'documents/document_upload.html', context)

@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.is_private and document.owner != request.user:
        return HttpResponseForbidden()
    return render(request, 'documents/document_detail.html', {'document': document})

def has_permission(user, action, obj=None):
    """
    Check if user has permission to perform action.
    Actions: 'view', 'create', 'edit', 'delete', 'manage_categories', 'manage_users'
    """
    if not hasattr(user, 'profile'):
        if action in ['view', 'create']:
            return True
        if action in ['edit', 'delete'] and obj and obj.owner == user:
            return True
        return False
    
    role = user.profile.role
    
    # Admins can do everything
    if role == 'admin':
        return True
    
    # Managers can do everything except manage users
    if role == 'manager':
        if action == 'manage_users':
            return False
        return True
    
    # Team members can create, view, and edit/delete their own documents
    if role == 'member':
        if action in ['view', 'create']:
            return True
        if action in ['edit', 'delete'] and obj and obj.owner == user:
            return True
        return False
    
    # Viewers can only view
    if role == 'viewer':
        return action == 'view'
    
    return False

@login_required
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to delete the document
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('dashboard')
    
    return render(request, 'documents/document_delete.html', {'document': document})

@login_required
def edit_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to edit the document
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            new_file = request.FILES.get('file')
            comment = request.POST.get('version_comment', '')
            
            if new_file:
                # Increment version
                document.current_version += 1
                document.save()
                
                # Create new version
                DocumentVersion.objects.create(
                    document=document,
                    file=new_file,
                    version_number=document.current_version,
                    created_by=request.user,
                    comment=comment
                )
                form.save(commit=False)  # Don't save the file to the document
                form.save()
            else:
                form.save()
            messages.success(request, 'Document updated successfully!')
            return redirect('document_detail', pk=document.pk)
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'documents/document_edit.html', {'form': form, 'document': document})

@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'documents/category_list.html', {'categories': categories})

@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, 'Category added successfully!')
            return redirect('category_list')
    return render(request, 'documents/category_form.html')

@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            category.name = name
            category.description = description
            category.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('category_list')
    return render(request, 'documents/category_form.html', {'category': category})

@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        # Optional: Move documents to uncategorized or another category
        documents = Document.objects.filter(category=category)
        uncategorized = Category.objects.get_or_create(name="Uncategorized")[0]
        documents.update(category=uncategorized)
        
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('category_list')
    return render(request, 'documents/category_delete.html', {'category': category})

# Archive-related view functions
@login_required
def archive_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to archive the document
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        document.is_archived = True
        document.archived_at = timezone.now()
        document.save()
        messages.success(request, 'Document archived successfully!')
        return redirect('dashboard')
    
    return render(request, 'documents/document_archive.html', {'document': document})

@login_required
def archived_documents(request):
    if not has_permission(request.user, 'view'):
        return HttpResponseForbidden("You don't have permission to view documents.")
    
    # Get archived documents that the user can access
    documents = Document.objects.filter(
        Q(owner=request.user) | Q(is_private=False)
    ).filter(is_archived=True)
    
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category:
        documents = documents.filter(category__name=category)
    
    categories = Category.objects.all()
    
    return render(request, 'documents/archived_documents.html', {
        'documents': documents,
        'categories': categories,
        'query': query,
        'selected_category': category
    })

@login_required
def restore_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to restore the document
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        document.is_archived = False
        document.archived_at = None
        document.save()
        messages.success(request, 'Document restored successfully!')
        return redirect('archived_documents')
    
    return render(request, 'documents/document_restore.html', {'document': document})

# Document Sharing views
@login_required
def share_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to share the document
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        # Get expiry date if set
        expiry_days = request.POST.get('expiry_days')
        expiry_date = None
        
        if expiry_days and expiry_days.isdigit():
            expiry_days = int(expiry_days)
            if expiry_days > 0:
                expiry_date = timezone.now() + timedelta(days=expiry_days)
        
        # Create share link
        share = DocumentShare.objects.create(
            document=document,
            shared_by=request.user,
            expire_at=expiry_date
        )
        
        # Create notification for document owner
        Notification.objects.create(
            user=request.user,
            document=document,
            notification_type='share',
            message=f"You shared '{document.title}' with a link."
        )
        
        # Generate share URL to display to user
        share_url = request.build_absolute_uri(reverse('shared_document', args=[share.token]))
        return render(request, 'documents/document_share_success.html', {
            'document': document,
            'share': share,
            'share_url': share_url
        })
    
    # Get all active shares for this document
    active_shares = DocumentShare.objects.filter(
        document=document,
        shared_by=request.user,
        is_active=True
    )
    
    return render(request, 'documents/document_share.html', {
        'document': document,
        'active_shares': active_shares
    })

@login_required
def manage_shares(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Only allow the owner to manage shares
    if document.owner != request.user:
        return HttpResponseForbidden()
    
    shares = DocumentShare.objects.filter(document=document, shared_by=request.user)
    
    if request.method == 'POST' and 'delete_share' in request.POST:
        share_id = request.POST.get('share_id')
        if share_id:
            try:
                share = DocumentShare.objects.get(id=share_id, document=document, shared_by=request.user)
                share.is_active = False
                share.save()
                messages.success(request, 'Share link has been deactivated.')
            except DocumentShare.DoesNotExist:
                messages.error(request, 'Share link not found.')
    
    return render(request, 'documents/manage_shares.html', {
        'document': document,
        'shares': shares
    })

def shared_document(request, token):
    share = DocumentShare.get_valid_share(token)
    
    if not share:
        return render(request, 'documents/shared_document_error.html', {
            'error': 'This share link is invalid or has expired.'
        })
    
    document = share.document
    
    # Don't allow viewing archived documents through share links
    if document.is_archived:
        return render(request, 'documents/shared_document_error.html', {
            'error': 'This document has been archived and is no longer available.'
        })
    
    # Track view count
    share.view_count += 1
    share.save()
    
    # Get comments
    comments = Comment.objects.filter(document=document)
    
    return render(request, 'documents/shared_document.html', {
        'document': document,
        'share': share,
        'comments': comments
    })

def download_shared_document(request, token):
    share = DocumentShare.get_valid_share(token)
    
    if not share or share.document.is_archived:
        return render(request, 'documents/shared_document_error.html', {
            'error': 'This share link is invalid or has expired.'
        })
    
    document = share.document
    
    # Track download count
    share.download_count += 1
    share.save()
    
    response = HttpResponse(document.file, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
    return response

# Comment views
@login_required
def add_comment(request, pk):
    document = get_object_or_404(Document, pk=pk)
    
    # Check if user can access this document
    if document.is_private and document.owner != request.user:
        # Check if this is a shared document via token
        token = request.POST.get('token')
        if not token or not DocumentShare.get_valid_share(token):
            return HttpResponseForbidden()
    
    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            comment = Comment.objects.create(
                document=document,
                user=request.user,
                text=comment_text
            )
            
            # Create notification for document owner if commenter is not owner
            if document.owner != request.user:
                Notification.objects.create(
                    user=document.owner,
                    document=document,
                    notification_type='comment',
                    message=f"{request.user.username} commented on your document '{document.title}'."
                )
            
            # If this is an AJAX request, return the comment as JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'id': comment.id,
                    'text': comment.text,
                    'user': comment.user.username,
                    'created_at': comment.created_at.strftime('%b %d, %Y, %I:%M %p')
                })
            
            messages.success(request, 'Comment added successfully!')
            
            # Redirect back to document with token if it exists
            token = request.POST.get('token')
            if token:
                return redirect(f'{reverse("shared_document", args=[token])}#comments')
            return redirect(f'{reverse("document_detail", args=[pk])}#comments')
    
    messages.error(request, 'Failed to add comment.')
    return redirect('document_detail', pk=pk)

@login_required
def delete_comment(request, document_pk, comment_pk):
    document = get_object_or_404(Document, pk=document_pk)
    comment = get_object_or_404(Comment, pk=comment_pk, document=document)
    
    # Only allow comment owner or document owner to delete the comment
    if comment.user != request.user and document.owner != request.user:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
    
    return redirect(f'{reverse("document_detail", args=[document_pk])}#comments')

# Notification views
@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'documents/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications')

@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications')

# Bulk Export/Import views
@login_required
def export_documents(request):
    if request.method == 'POST':
        document_ids = request.POST.getlist('document_ids')
        
        if not document_ids:
            messages.error(request, 'No documents selected for export.')
            return redirect('dashboard')
        
        # Create in-memory ZIP file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for doc_id in document_ids:
                try:
                    document = Document.objects.get(pk=doc_id)
                    
                    # Check permissions
                    if document.owner != request.user and document.is_private:
                        continue
                    
                    # Add file to zip
                    file_name = document.file.name.split('/')[-1]
                    zipf.writestr(file_name, document.file.read())
                except Document.DoesNotExist:
                    continue
        
        # Prepare response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="exported_documents_{timezone.now().strftime("%Y%m%d")}.zip"'
        return response
    
    # Get documents user can access
    documents = Document.objects.filter(
        Q(owner=request.user) | Q(is_private=False)
    ).filter(is_archived=False)
    
    return render(request, 'documents/export_documents.html', {
        'documents': documents
    })

@login_required
def import_documents(request):
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        category_id = request.POST.get('category')
        is_private = request.POST.get('is_private') == 'on'
        
        if not files:
            messages.error(request, 'No files selected for import.')
            return redirect('import_documents')
        
        try:
            category = Category.objects.get(pk=category_id) if category_id else None
        except Category.DoesNotExist:
            category = None
        
        success_count = 0
        error_count = 0
        
        for file in files:
            try:
                # Create document
                document = Document.objects.create(
                    title=os.path.splitext(file.name)[0],  # Use filename as title
                    description='Imported document',
                    file=file,
                    category=category,
                    owner=request.user,
                    is_private=is_private
                )
                
                # Create initial version
                DocumentVersion.objects.create(
                    document=document,
                    file=file,
                    version_number=1,
                    created_by=request.user,
                    comment="Initial version (imported)"
                )
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    document=document,
                    notification_type='upload',
                    message=f"You uploaded a new document: '{document.title}'"
                )
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
        
        if success_count > 0:
            messages.success(request, f'Successfully imported {success_count} document(s).')
        if error_count > 0:
            messages.error(request, f'Failed to import {error_count} file(s). Please check the file types.')
        
        return redirect('dashboard')
    
    categories = Category.objects.all()
    return render(request, 'documents/import_documents.html', {
        'categories': categories
    })