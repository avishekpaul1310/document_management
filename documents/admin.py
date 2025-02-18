from django.contrib import admin
from .models import Category, Document

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_by', 'uploaded_at', 'is_private')
    list_filter = ('category', 'is_private', 'uploaded_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_by', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set uploaded_by when creating new document
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)