from django.contrib import admin
from .models import Category, Document
from django.utils.html import format_html
from django.urls import reverse

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'owner', 'uploaded_at', 'is_private')
    list_filter = ('category', 'is_private', 'uploaded_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('owner', 'uploaded_at')
    actions = ('make_private', 'make_public')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set owner when creating new document
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    def document_link(self, obj):
        return format_html('<a href="{}">{}</a>', 
            reverse('document_detail', args=[obj.pk]), 
            obj.title
        )
    document_link.short_description = 'Document Title'
    
    list_display = ('document_link', 'category', 'owner', 'uploaded_at', 'is_private')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(owner=request.user)
        return qs
    
    def make_private(self, request, queryset):
        queryset.update(is_private=True)
    make_private.short_description = "Mark selected documents as private"
    
    def make_public(self, request, queryset):
        queryset.update(is_private=False)
    make_public.short_description = "Mark selected documents as public"