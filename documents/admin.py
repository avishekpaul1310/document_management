from django.contrib import admin
from .models import Category, Document

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'owner', 'uploaded_at', 'is_private')
    list_filter = ('category', 'is_private', 'uploaded_at')
    search_fields = ('title', 'description', 'owner__username')
    date_hierarchy = 'uploaded_at'