from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, F
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.db.models.functions import TruncDay
from datetime import timedelta
import os
from .models import Document, Category, DocumentVersion, UserProfile
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
    
    documents = Document.objects.filter(
        Q(owner=request.user) | Q(is_private=False)
    )
    
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category:
        documents = documents.filter(category__name=category)
    
    categories = Category.objects.all()
    
    # Analytics data - Document statistics
    total_documents = Document.objects.count()
    user_documents = Document.objects.filter(owner=request.user).count()
    
    # Category distribution for pie chart
    category_stats = Document.objects.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent activity - last 7 days of uploads
    last_week = timezone.now() - timedelta(days=7)
    daily_uploads = Document.objects.filter(
        uploaded_at__gte=last_week
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
    
    # File type distribution
    file_types = {}
    for doc in Document.objects.all():
        ext = os.path.splitext(doc.file.name)[1].lower()
        if ext:
            file_types[ext] = file_types.get(ext, 0) + 1
    
    # Storage usage calculation
    storage_usage = {
        'user': 0,
        'total': 0,
        'by_category': {}
    }
    
    for doc in Document.objects.all():
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
    
    # Get recent uploads - last 5 docs
    recent_uploads = Document.objects.order_by('-uploaded_at')[:5]
    
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'categories': categories,
        'query': query,
        'selected_category': category,
        # Analytics data
        'analytics': {
            'total_documents': total_documents,
            'user_documents': user_documents,
            'category_stats': list(category_stats),
            'file_types': file_types,
            'storage_usage': storage_usage,
            'activity_labels': activity_labels,
            'activity_data': activity_data,
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