from django.contrib import admin
from .models import BlogCategory, Blog


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'author', 'category', 'is_published', 'published_at']
    search_fields = ['title', 'slug', 'author', 'excerpt']
    list_filter = ['is_published', 'category', 'published_at']
    prepopulated_fields = {'slug': ('title',)}
