from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.contrib import messages
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
    
    return render(request, 'documents/dashboard.html', {
        'documents': documents,
        'categories': categories,
        'query': query,
        'selected_category': category
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