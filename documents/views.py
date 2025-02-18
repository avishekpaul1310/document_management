from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import Document, Category
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