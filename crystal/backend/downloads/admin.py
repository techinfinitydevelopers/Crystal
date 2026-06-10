from django.contrib import admin
from django.utils.html import format_html
from .models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ['title', 'brand_badge', 'category', 'file_link', 'thumbnail_preview', 'is_active', 'created_at']
    search_fields = ['title', 'slug']
    list_filter = ['brand', 'category', 'is_active']
    prepopulated_fields = {'slug': ('title',)}
    list_select_related = ['brand']
    fieldsets = (
        ('File Details', {
            'fields': ('title', 'slug', 'brand', 'category', 'description'),
        }),
        ('Upload', {
            'fields': ('file', 'thumbnail'),
        }),
        ('Visibility', {
            'fields': ('is_active',),
        }),
    )

    @admin.display(description='Brand')
    def brand_badge(self, obj):
        if not obj.brand:
            return format_html(
                '<span style="background:#f1f5f9;padding:3px 10px;border-radius:100px;'
                'font-size:11px;font-weight:600;color:#64748b;">All Brands</span>'
            )
        colors = {
            'crystal': '#ED3338', 'crystalina': '#7c3aed',
            'sparkmate': '#0ea5e9', 'valmate': '#059669',
        }
        bg = colors.get(obj.brand.slug, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, obj.brand.name,
        )

    @admin.display(description='File')
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" style="color:#ED3338;font-weight:600;font-size:12px;">'
                '📄 {}</a>',
                obj.file.url,
                obj.file.name.split('/')[-1],
            )
        return '—'

    @admin.display(description='Thumbnail')
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:36px;width:auto;border-radius:6px;">',
                obj.thumbnail.url,
            )
        return '—'
