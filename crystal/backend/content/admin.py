from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import PageSection, PageSectionTrash
from .pages_registry import ALL_PAGES, PAGE_LABELS


class PageSectionForm(forms.ModelForm):
    page = forms.ChoiceField(
        choices=[(p, f'{p}  —  {PAGE_LABELS[p]}') for p in ALL_PAGES])

    class Meta:
        model = PageSection
        fields = '__all__'


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    """Deleting here -- the change form's Delete button, or the bulk 'Delete
    selected' action -- goes through Django's normal confirmation page as
    always, but only ever soft-deletes: the row moves to Trash instead of
    being removed. Only Trash can remove it for good."""

    form = PageSectionForm
    list_display = ('page_cell', 'section_key', 'kind', 'preview_cell',
                     'is_active', 'updated_at')
    list_display_links = ('page_cell', 'section_key')
    list_filter = ('page', 'kind', 'is_active')
    search_fields = ('page', 'section_key', 'label', 'text_value')
    fields = ('page', 'section_key', 'label', 'kind', 'text_value', 'image',
              'is_active', 'updated_at')
    readonly_fields = ('updated_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)

    def delete_model(self, request, obj):
        obj.is_deleted = True
        obj.deleted_at = timezone.now()
        obj.save(update_fields=['is_deleted', 'deleted_at'])

    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True, deleted_at=timezone.now())

    @admin.display(description='Page', ordering='page')
    def page_cell(self, obj):
        return format_html('<strong>{}</strong><br><span style="color:#888">{}</span>',
                           PAGE_LABELS.get(obj.page, obj.page), obj.page)

    @admin.display(description='Content')
    def preview_cell(self, obj):
        if obj.kind == PageSection.IMAGE:
            if obj.image:
                return format_html(
                    '<img src="{}" style="height:36px;border-radius:4px">', obj.image.url)
            return '—'
        text = (obj.text_value or '')[:80]
        return text or '—'


@admin.register(PageSectionTrash)
class PageSectionTrashAdmin(admin.ModelAdmin):
    """Only reachable from here: 'Delete selected' is Django's real,
    permanent delete, behind its usual are-you-sure confirmation page.
    Restoring is the one action that needs no confirmation -- it's the
    reversible half of this screen."""

    list_display = ('page_cell', 'section_key', 'kind', 'deleted_at')
    list_display_links = ('page_cell', 'section_key')
    list_filter = ('page', 'kind')
    search_fields = ('page', 'section_key', 'label', 'text_value')
    actions = ['restore_selected']
    ordering = ['-deleted_at']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=True)

    def has_add_permission(self, request):
        return False

    @admin.display(description='Page', ordering='page')
    def page_cell(self, obj):
        return format_html('<strong>{}</strong><br><span style="color:#888">{}</span>',
                           PAGE_LABELS.get(obj.page, obj.page), obj.page)

    @admin.action(description='Restore selected sections')
    def restore_selected(self, request, queryset):
        n = queryset.update(is_deleted=False, deleted_at=None)
        self.message_user(request, f'{n} section(s) restored.')
