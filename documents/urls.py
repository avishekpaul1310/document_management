from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_document, name='upload_document'),
    path('document/<int:pk>/', views.document_detail, name='document_detail'),
    path('document/<int:pk>/delete/', views.delete_document, name='delete_document'),
    path('document/<int:pk>/edit/', views.edit_document, name='edit_document'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/<int:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
    
    # Archive-related URLs
    path('document/<int:pk>/archive/', views.archive_document, name='archive_document'),
    path('document/<int:pk>/restore/', views.restore_document, name='restore_document'),
    path('archives/', views.archived_documents, name='archived_documents'),
]