from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import ContactSubmission

SUBJECT_COLORS = {
    'general':    ('#3b82f6', '#fff'),
    'support':    ('#f59e0b', '#1a1a1a'),
    'sales':      ('#10b981', '#fff'),
    'complaint':  ('#ef4444', '#fff'),
    'feedback':   ('#8b5cf6', '#fff'),
}


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'email', 'phone', 'subject_badge', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'message']
    list_filter   = ['subject', 'created_at']
    readonly_fields = ['full_name', 'email', 'phone', 'subject', 'message', 'created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Contact Info', {
            'fields': ('full_name', 'email', 'phone'),
        }),
        ('Message', {
            'fields': ('subject', 'message'),
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Subject')
    def subject_badge(self, obj):
        bg, fg = SUBJECT_COLORS.get(obj.subject, ('#64748b', '#fff'))
        label = obj.get_subject_display() if hasattr(obj, 'get_subject_display') else obj.subject
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;">{}</span>',
            bg, fg, label,
        )
