import io
from contextlib import redirect_stdout
from itertools import groupby

from django import forms
from django.contrib import admin, messages
from django.core.management import call_command
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django.utils.http import url_has_allowed_host_and_scheme

from banners.models import CategoryBanner

from .models import Page, PageSection, PageSectionTrash
from .pages_registry import ALL_PAGES, PAGE_LABELS

# Groups (from pages_registry) whose pages carry a hero photograph through
# CategoryBanner rather than a data-cms image section — Cookware, Kitchenware
# and the rest are template pages with no standalone <img data-cms> at all,
# so without this the per-page editor would show text only and look like
# there was no way to change the picture, when there is one, just in a
# different table.
CATEGORY_BANNER_GROUPS = {
    'Cookware', 'Kitchenware', 'Cleaning Aid', 'Electric Appliances',
    'Standalone categories',
}


class CategoryBannerInlineForm(forms.ModelForm):
    """The category banner's editable fields, embedded in the page editor
    instead of its own change form. 'page' and 'label' are set from the Page
    object rather than typed here."""

    class Meta:
        model = CategoryBanner
        fields = ('image', 'focus', 'mobile_focus', 'is_active')
        widgets = {
            'focus': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100,
                                              'step': 1, 'class': 'crystal-focus',
                                              'data-preview': 'desktop'}),
            'mobile_focus': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100,
                                                     'step': 1, 'class': 'crystal-focus',
                                                     'data-preview': 'mobile'}),
        }


class PageSectionEditorForm(forms.ModelForm):
    """One row inside the per-page editor. Same fields as the flat admin's
    'Your version' fieldset, just rendered inline instead of on their own
    change form."""

    class Meta:
        model = PageSection
        fields = ('text_value', 'image', 'image_mobile', 'is_active')
        widgets = {
            'text_value': forms.Textarea(attrs={'rows': 3}),
        }


PageSectionEditorFormSet = modelformset_factory(
    PageSection, form=PageSectionEditorForm, extra=0)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    """The sidebar doorway the Page model's docstring describes: a list of
    pages grouped the way the site is, each one opening straight into its own
    section editor instead of Django's generic change form."""

    list_display = ('title', 'group', 'section_count', 'edit_button')
    list_display_links = ('title',)
    list_filter = ('group',)
    search_fields = ('title', 'filename', 'group')
    ordering = ['order', 'group', 'title']

    def get_urls(self):
        return [
            path('<int:pk>/editor/',
                 self.admin_site.admin_view(self.editor_view),
                 name='content_page_editor'),
        ] + super().get_urls()

    def has_add_permission(self, request):
        # Pages come from pages_registry via seed_page_sections, not typed in
        # by hand — a stray row here would have no file behind it to serve.
        return False

    @admin.display(description='Sections')
    def section_count(self, obj):
        live = obj.sections.filter(is_deleted=False)
        total = live.count()
        edited = live.filter(~Q(text_value='') | (~Q(image='') & Q(image__isnull=False))).count()
        return f'{edited} edited of {total}'

    @admin.display(description='')
    def edit_button(self, obj):
        return format_html(
            '<a href="{}" class="btn btn-sm" '
            'style="background:#ED3338;color:#fff;font-weight:600;">'
            'Edit this page &rarr;</a>',
            reverse('admin:content_page_editor', args=[obj.pk]))

    def editor_view(self, request, pk):
        page = get_object_or_404(Page, pk=pk)
        qs = (PageSection.objects.filter(page_ref=page, is_deleted=False)
              .order_by('section', 'section_key'))

        banner_obj = CategoryBanner.objects.filter(page=page.filename).first()
        show_banner = banner_obj is not None or page.group in CATEGORY_BANNER_GROUPS
        banner_instance = banner_obj or CategoryBanner(page=page.filename, label=page.title)

        if request.method == 'POST':
            formset = PageSectionEditorFormSet(
                request.POST, request.FILES, queryset=qs, prefix='sections')
            banner_form = None
            banner_ok = True
            if show_banner:
                banner_form = CategoryBannerInlineForm(
                    request.POST, request.FILES, instance=banner_instance, prefix='banner')
                # A banner that does not exist yet is only worth creating if a
                # photo was actually chosen -- otherwise every unrelated save
                # on this page would fail on the image field being required.
                if banner_instance.pk or request.FILES.get('banner-image'):
                    banner_ok = banner_form.is_valid()
                    if banner_ok:
                        b = banner_form.save(commit=False)
                        b.page = page.filename
                        b.label = b.label or page.title
                else:
                    banner_ok = True

            if formset.is_valid() and banner_ok:
                formset.save()
                if show_banner and (banner_instance.pk or request.FILES.get('banner-image')):
                    b.save()
                messages.success(request, f'Saved “{page.title}”.')
                return redirect(request.path)
            messages.error(request, 'Could not save — check the fields below.')
        else:
            formset = PageSectionEditorFormSet(queryset=qs, prefix='sections')
            banner_form = (CategoryBannerInlineForm(instance=banner_instance, prefix='banner')
                           if show_banner else None)

        forms_by_pk = {f.instance.pk: f for f in formset.forms}
        groups = [
            (section_title, [forms_by_pk[row.pk] for row in rows])
            for section_title, rows in groupby(qs, key=lambda s: s.section_title)
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': f'Edit — {page.title}',
            'opts': self.model._meta,
            'page_obj': page,
            'all_pages': Page.objects.all(),
            'formset': formset,
            'groups': groups,
            'banner_form': banner_form,
            'banner_obj': banner_obj,
        }
        return render(request, 'admin/content/page/editor.html', context)


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
            'fields': ('text_value', 'image', 'current_image', 'image_mobile',
                       'current_image_mobile', 'is_active', 'updated_at'),
        }),
    )
    readonly_fields = ('updated_at', 'shipped_reference', 'current_image',
                       'current_image_mobile', 'section')
    change_list_template = 'admin/content/pagesection/change_list.html'

    def get_urls(self):
        return [
            path('load-from-site/',
                 self.admin_site.admin_view(self.load_from_site),
                 name='content_pagesection_load'),
        ] + super().get_urls()

    def load_from_site(self, request):
        """Pull the site's list of editable sections and add any that are new.

        Reads the manifest the website publishes (tools/cms-manifest.json) and
        creates one empty row per section. Empty rows publish nothing — the feed
        skips a section with no value — so this is safe to press at any time and
        it never touches a value someone typed.
        """
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                call_command('seed_page_sections')
        except Exception as exc:
            self.message_user(
                request,
                'Could not load the sections: %s' % exc,
                level=messages.ERROR,
            )
        else:
            self.message_user(
                request,
                out.getvalue().strip() or 'Sections loaded.',
                level=messages.SUCCESS,
            )
        return redirect(reverse('admin:content_pagesection_changelist'))

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

    @admin.display(description='Phone picture now in use')
    def current_image_mobile(self, obj):
        if not obj or obj.kind != PageSection.IMAGE:
            return mark_safe('<span style="color:#94a3b8;">&mdash;</span>')
        if not obj.image_mobile:
            return mark_safe('<span style="color:#94a3b8;">Nothing uploaded &mdash; '
                               'phones show the picture above.</span>')
        return format_html(
            '<img src="{}" style="max-height:140px;border-radius:10px;'
            'box-shadow:0 4px 16px rgba(0,0,0,.15);">', obj.image_mobile.url)

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
