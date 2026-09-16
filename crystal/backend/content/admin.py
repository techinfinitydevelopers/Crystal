from django import forms
from django.contrib import admin
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import PageSection, PageSectionTrash
from .pages_registry import ALL_PAGES, PAGE_LABELS


class PageSectionForm(forms.ModelForm):
    page = forms.ChoiceField(
        choices=[(p, f'{p}  —  {PAGE_LABELS[p]}') for p in ALL_PAGES])

    class Meta:
        model = PageSection
        fields = '__all__'


class EditedFilter(admin.SimpleListFilter):
    """1,032 sections exist so every part of every page *can* be edited; only
    a handful ever are. Without this the list is a haystack — this is the
    needle."""

    title = 'edited yet'
    parameter_name = 'edited'

    def lookups(self, request, model_admin):
        return [('yes', 'Edited here'), ('no', 'Still as the page ships it')]

    def queryset(self, request, queryset):
        has_value = (~Q(text_value='') | (~Q(image='') & Q(image__isnull=False)))
        if self.value() == 'yes':
            return queryset.filter(has_value)
        if self.value() == 'no':
            return queryset.exclude(has_value)
        return queryset


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    """Deleting here -- the change form's Delete button, or the bulk 'Delete
    selected' action -- goes through Django's normal confirmation page as
    always, but only ever soft-deletes: the row moves to Trash instead of
    being removed. Only Trash can remove it for good."""

    form = PageSectionForm
    list_display = ('page_cell', 'what_cell', 'kind', 'live_cell',
                     'preview_cell', 'is_active', 'updated_at')
    list_display_links = ('page_cell', 'what_cell')
    list_filter = ('page', EditedFilter, 'kind', 'section', 'is_active')
    search_fields = ('page', 'section_key', 'label', 'text_value',
                     'shipped_value')
    list_per_page = 40
    fieldsets = (
        ('Where this is', {
            'description': (
                'Pick the page, then the section. The reference below shows what '
                'the page displays today — leave the boxes under it empty and '
                'that is exactly what visitors keep seeing.'
            ),
            'fields': ('page', 'section_key', 'label', 'section', 'kind',
                       'shipped_reference'),
        }),
        ('Your version', {
            'description': (
                'Fill in only the one that matches the kind above. Clear it '
                'again at any time and the page falls back to what it ships. '
                'The change is live within a minute — nothing to publish.'
            ),
            'fields': ('text_value', 'image', 'current_image', 'is_active',
                       'updated_at'),
        }),
    )
    readonly_fields = ('updated_at', 'shipped_reference', 'current_image',
                       'section')

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

    @admin.display(description='Section', ordering='label')
    def what_cell(self, obj):
        """The label reads as what it is; the key is the thing that has to
        match the page, so it stays visible underneath."""
        return format_html(
            '{}<br><span style="color:#888;font-size:11px">{}</span>',
            obj.label or obj.section_key, obj.section_key)

    @admin.display(description='Showing')
    def live_cell(self, obj):
        edited = bool(obj.text_value) or bool(obj.image)
        if edited and obj.is_active:
            return mark_safe(
                '<span style="display:inline-block;padding:2px 8px;border-radius:100px;'
                'background:rgba(22,101,52,.12);color:#166534;font-weight:700;'
                'font-size:11px;">Your version</span>')
        if edited:
            return mark_safe(
                '<span style="display:inline-block;padding:2px 8px;border-radius:100px;'
                'background:rgba(180,83,9,.12);color:#b45309;font-weight:700;'
                'font-size:11px;">Off &mdash; shipped</span>')
        return mark_safe('<span style="color:#94a3b8;font-size:11px;">As shipped</span>')

    @admin.display(description='What the page shows today')
    def shipped_reference(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span style="color:#94a3b8;">Saved once, this '
                               'will show the page’s own wording.</span>')
        if obj.kind == PageSection.IMAGE:
            return format_html(
                '<span style="color:#64748b;font-size:12px;">{}</span>',
                obj.shipped_value or 'the image the page ships')
        if not obj.shipped_value:
            return mark_safe('<span style="color:#94a3b8;">&mdash;</span>')
        return format_html(
            '<div style="max-width:640px;padding:10px 12px;border-left:3px solid #cbd5e1;'
            'background:#f8fafc;color:#334155;font-size:13px;line-height:1.5;">{}</div>',
            obj.shipped_value)

    @admin.display(description='Image now in use')
    def current_image(self, obj):
        if not obj or obj.kind != PageSection.IMAGE:
            return mark_safe('<span style="color:#94a3b8;">&mdash;</span>')
        if not obj.image:
            return mark_safe('<span style="color:#94a3b8;">Nothing uploaded &mdash; '
                               'the page shows its own picture.</span>')
        return format_html(
            '<img src="{}" style="max-height:140px;border-radius:10px;'
            'box-shadow:0 4px 16px rgba(0,0,0,.15);">', obj.image.url)

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
