from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import os

def validate_file_type(value):
    # Get the file extension
    ext = os.path.splitext(value.name)[1]
    # Define valid file extensions
    valid_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
    
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file type. Allowed types: PDF, Word, Excel, and Images')

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to='documents/',
        validators=[validate_file_type]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=False)
    current_version = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return self.title

    def get_latest_version(self):
        return self.versions.first()
    
    def get_version_file(self):
        latest = self.get_latest_version()
        return latest.file if latest else self.file

    def delete(self, *args, **kwargs):
        # Delete the file from storage when deleting the document
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    file = models.FileField(upload_to='document_versions/', validators=[validate_file_type])
    version_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-version_number']
    
    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"

class UserProfile(models.Model):
    USER_ROLES = (
        ('admin', 'Administrator'),
        ('manager', 'Project Manager'),
        ('member', 'Team Member'),
        ('viewer', 'Viewer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=USER_ROLES, default='member')
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"