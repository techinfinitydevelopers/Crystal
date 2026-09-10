from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import PageSection
from .pages_registry import ALL_PAGES, PAGE_LABELS


class PageSectionForm(forms.ModelForm):
    page = forms.ChoiceField(
        choices=[(p, f'{p}  —  {PAGE_LABELS[p]}') for p in ALL_PAGES])

    class Meta:
        model = PageSection
        fields = '__all__'


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    form = PageSectionForm
    list_display = ('page_cell', 'section_key', 'kind', 'preview_cell',
                     'is_active', 'updated_at')
    list_display_links = ('page_cell', 'section_key')
    list_filter = ('page', 'kind', 'is_active')
    search_fields = ('page', 'section_key', 'label', 'text_value')
    fields = ('page', 'section_key', 'label', 'kind', 'text_value', 'image',
              'is_active', 'updated_at')
    readonly_fields = ('updated_at',)

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
