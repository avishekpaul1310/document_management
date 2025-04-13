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
    
    # Document Sharing URLs
    path('document/<int:pk>/share/', views.share_document, name='share_document'),
    path('document/<int:pk>/shares/', views.manage_shares, name='manage_shares'),
    path('shared/<uuid:token>/', views.shared_document, name='shared_document'),
    path('shared/<uuid:token>/download/', views.download_shared_document, name='download_shared_document'),
    
    # Comment URLs
    path('document/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('document/<int:document_pk>/comment/<int:comment_pk>/delete/', 
         views.delete_comment, name='delete_comment'),
    
    # Notification URLs
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Export/Import URLs
    path('export/', views.export_documents, name='export_documents'),
    path('import/', views.import_documents, name='import_documents'),
]