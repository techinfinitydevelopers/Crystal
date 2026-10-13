"""The SEO team's screens.

Everything here ends in a rebuild, because search engines and social previews
read the *files*, not an API. Saving a row asks for one; it runs in the
background a couple of seconds later and merges with any other edit made in the
meantime, so changing fifty products in a row costs one rebuild, not fifty.
"""
import csv
import io
import re

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from . import pipeline
from .bake import abs_url, site_root
from .models import BlogPostSeo, ProductPage, Redirect, ScriptBlock, SeoMeta, SeoSettings

SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def _badge(text, kind):
    colours = {'ok': ('#dcfce7', '#166534'), 'warn': ('#fef3c7', '#92400e'),
               'bad': ('#fee2e2', '#991b1b'), 'off': ('#f1f5f9', '#64748b')}
    bg, fg = colours[kind]
    return format_html(
        '<span style="background:{};color:{};padding:2px 8px;border-radius:100px;'
        'font-size:11px;font-weight:700;white-space:nowrap;">{}</span>', bg, fg, text)


def length_badge(text, lo, hi):
    n = len((text or '').strip())
    if not n:
        return _badge('missing', 'bad')
    if n > hi:
        return _badge('%d — too long' % n, 'warn')
    if n < lo:
        return _badge('%d — short' % n, 'warn')
    return _badge('%d — good' % n, 'ok')


def _rebuild(request, products=False, blog=False):
    if not site_root():
        messages.warning(request, 'Saved, but the website files are not reachable from this '
                                  'server, so nothing was written into the pages.')
        return
    pipeline.request_bake(products=products, blog=blog)
    messages.info(request, 'Saved. The pages are being rewritten and will be live in a few seconds.')


class RebuildMixin:
    """Adds a "Rebuild everything now" button and the view behind it."""

    def get_urls(self):
        info = (self.model._meta.app_label, self.model._meta.model_name)
        return [
            path('rebuild/', self.admin_site.admin_view(self.rebuild_view),
                 name='%s_%s_rebuild' % info),
        ] + super().get_urls()

    def rebuild_view(self, request):
        if not self.has_change_permission(request):
            messages.error(request, 'You do not have permission to do that.')
            return redirect('..')
        report = pipeline.bake_all()
        text = 'Rebuilt: %s.' % report
        if report.notes:
            text += ' ' + ' '.join(report.notes)
        messages.success(request, text)
        for s in report.skipped[:8]:
            messages.warning(request, 'Skipped — ' + s)
        return redirect('..')


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
class PageHealth(admin.SimpleListFilter):
    title = 'copy'
    parameter_name = 'health'

    def lookups(self, request, model_admin):
        return [('nodesc', 'No description'), ('longtitle', 'Title too long (60+)'),
                ('longdesc', 'Description too long (155+)'), ('edited', 'Edited here')]

    def queryset(self, request, qs):
        v = self.value()
        if v == 'nodesc':
            return qs.filter(description='', shipped_description='')
        if v == 'edited':
            return qs.exclude(title='', description='')
        ids = []
        for row in qs:
            if v == 'longtitle' and len(row.effective_title) > 60:
                ids.append(row.pk)
            if v == 'longdesc' and len(row.effective_description) > 155:
                ids.append(row.pk)
        return qs.filter(pk__in=ids) if v in ('longtitle', 'longdesc') else qs


WIDE = {'style': 'width:100%;max-width:760px;'}


class SeoMetaForm(forms.ModelForm):
    class Meta:
        model = SeoMeta
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs=WIDE),
            'description': forms.Textarea(attrs=dict(WIDE, rows=4)),
            'keywords': forms.TextInput(attrs=WIDE),
            'og_title': forms.TextInput(attrs=WIDE),
            'og_description': forms.Textarea(attrs=dict(WIDE, rows=3)),
            'canonical': forms.URLInput(attrs=WIDE),
        }


@admin.register(SeoMeta)
class SeoMetaAdmin(RebuildMixin, admin.ModelAdmin):
    form = SeoMetaForm
    change_list_template = 'admin/seo/seometa/change_list.html'
    list_display = ('label', 'group', 'title_state', 'description_state', 'search_state', 'in_sitemap', 'priority')
    list_display_links = ('label',)
    list_filter = ('group', 'indexing', 'in_sitemap', PageHealth)
    search_fields = ('page', 'label', 'title', 'description', 'shipped_title', 'shipped_description')
    list_per_page = 80
    readonly_fields = ('page_file', 'live_address', 'google_preview', 'shipped_reference', 'updated_at')

    fieldsets = (
        ('Page', {'fields': ('page_file', 'label', 'live_address')}),
        ('How it looks in Google', {
            'description': 'Leave the title or description empty to keep what the page says '
                           'today. Fill them in to replace it.',
            'fields': ('title', 'description', 'google_preview', 'shipped_reference', 'keywords'),
        }),
        ('When someone shares the link', {
            'description': 'The card WhatsApp, Facebook, LinkedIn and X draw. Empty fields '
                           'use the title, description and default picture above.',
            'fields': ('og_title', 'og_description', 'og_image'),
        }),
        ('Search engines', {
            'fields': ('indexing', 'in_sitemap', 'priority', 'canonical'),
        }),
    )

    class Media:
        js = ('seo/seo-admin.js',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields

    @admin.display(description='Title')
    def title_state(self, obj):
        return length_badge(obj.effective_title, 30, 60)

    @admin.display(description='Description')
    def description_state(self, obj):
        return length_badge(obj.effective_description, 110, 155)

    @admin.display(description='In search')
    def search_state(self, obj):
        return _badge('shown', 'ok') if obj.indexing == SeoMeta.INDEX_YES else _badge('hidden', 'off')

    @admin.display(description='File')
    def page_file(self, obj):
        return obj.page

    @admin.display(description='Address')
    def live_address(self, obj):
        st = SeoSettings.load()
        url = abs_url(st, obj.url_path)
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    @admin.display(description='Preview')
    def google_preview(self, obj):
        st = SeoSettings.load()
        return format_html(
            '<div id="seo-preview" data-url="{}" data-fallback-title="{}" '
            'data-fallback-description="{}" style="max-width:640px;padding:14px 16px;'
            'border:1px solid #e2e8f0;border-radius:10px;background:#fff;"></div>',
            abs_url(st, obj.url_path), obj.shipped_title, obj.shipped_description)

    @admin.display(description='What the page says today')
    def shipped_reference(self, obj):
        if not (obj.shipped_title or obj.shipped_description):
            return '—'
        return format_html('<b>{}</b><br>{}', obj.shipped_title or '(no title)',
                           obj.shipped_description or '(no description)')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _rebuild(request)

    def changelist_view(self, request, extra_context=None):
        rows = list(SeoMeta.objects.all())
        live = [r for r in rows if r.indexing == SeoMeta.INDEX_YES]
        extra = dict(extra_context or {})
        extra['seo_coverage'] = {
            'pages': len(rows),
            'indexed': len(live),
            'no_description': sum(1 for r in live if not r.effective_description),
            'long_title': sum(1 for r in live if len(r.effective_title) > 60),
            'long_description': sum(1 for r in live if len(r.effective_description) > 155),
        }
        return super().changelist_view(request, extra_context=extra)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
class MetaFilter(admin.SimpleListFilter):
    title = 'search copy'
    parameter_name = 'meta'

    def lookups(self, request, model_admin):
        return [('none', 'No title or description'), ('nodesc', 'No description'),
                ('both', 'Has both')]

    def queryset(self, request, qs):
        v = self.value()
        if v == 'none':
            return qs.filter(product__meta_title='', product__meta_description='')
        if v == 'nodesc':
            return qs.filter(product__meta_description='')
        if v == 'both':
            return qs.exclude(product__meta_title='').exclude(product__meta_description='')
        return qs


class SlugCleaning:
    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip().lower()
        if not SLUG_RE.match(slug):
            raise forms.ValidationError('Lower-case letters, numbers and single hyphens only, e.g. "steel-tawa-26-cm".')
        # 'gallery' is the folder dashboard-uploaded product photos live in, in the
        # same /products/ directory these pages are written to.
        if slug in ('index', 'all', 'new', 'gallery'):
            raise forms.ValidationError('That address is reserved.')
        return slug


class ProductPageListForm(SlugCleaning, forms.ModelForm):
    """What the list's inline editing submits. Deliberately has no title or
    description fields: a form that carried them would treat their absence from a
    quick address edit as "emptied", and wipe the product's search copy."""

    class Meta:
        model = ProductPage
        fields = ('slug', 'noindex')


class ProductPageForm(SlugCleaning, forms.ModelForm):
    meta_title = forms.CharField(
        required=False, max_length=120, label='Search title', widget=forms.TextInput(attrs=WIDE),
        help_text='The blue line in Google. Empty builds one from the product name.')
    meta_description = forms.CharField(
        required=False, max_length=320, label='Search description',
        widget=forms.Textarea(attrs=dict(WIDE, rows=3)),
        help_text='The grey paragraph under it. Empty uses the product\'s highlight.')

    class Meta:
        model = ProductPage
        fields = ('slug', 'noindex')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product = getattr(self.instance, 'product', None)
        if product:
            self.fields['meta_title'].initial = product.meta_title
            self.fields['meta_description'].initial = product.meta_description
        else:
            for f in ('meta_title', 'meta_description'):
                self.fields[f].disabled = True
                self.fields[f].help_text = 'This entry is not linked to a dashboard product, so its copy cannot be edited here.'


def apply_product_meta(page, title, description):
    """Write search copy to the dashboard product and mark it as edited here.

    Marking matters: the deploy-time catalogue sync refills the database from
    products.json, and only fields listed in `overridden_fields` survive it.
    """
    product = page.product
    if not product:
        return False
    dirty = []
    if product.meta_title != title:
        product.meta_title = title
        dirty.append('meta_title')
    if product.meta_description != description:
        product.meta_description = description
        dirty.append('meta_description')
    if dirty:
        owned = set(product.overridden_fields or ()) | set(dirty)
        product.overridden_fields = sorted(owned)
        product.save(update_fields=dirty + ['overridden_fields'])
    return bool(dirty)


@admin.register(ProductPage)
class ProductPageAdmin(RebuildMixin, admin.ModelAdmin):
    form = ProductPageForm
    change_list_template = 'admin/seo/productpage/change_list.html'
    list_display = ('name', 'sku', 'slug', 'title_state', 'description_state', 'noindex', 'live_link')
    list_display_links = ('name',)
    list_editable = ('slug', 'noindex')
    list_filter = ('noindex', MetaFilter)
    search_fields = ('name', 'sku', 'slug', 'entry_id')
    list_select_related = ('product',)
    list_per_page = 50
    readonly_fields = ('name', 'sku', 'entry_id', 'live_address', 'google_preview')
    fieldsets = (
        ('Product', {'fields': ('name', 'sku', 'entry_id')}),
        ('Its own page', {
            'description': 'Changing the address is safe: the old one is redirected to the new one '
                           'automatically.',
            'fields': ('slug', 'live_address', 'noindex'),
        }),
        ('How it looks in Google', {'fields': ('meta_title', 'meta_description', 'google_preview')}),
    )

    class Media:
        js = ('seo/seo-admin.js',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Title')
    def title_state(self, obj):
        t = obj.product.meta_title if obj.product else ''
        return length_badge(t, 30, 60) if t else _badge('auto', 'off')

    @admin.display(description='Description')
    def description_state(self, obj):
        t = obj.product.meta_description if obj.product else ''
        return length_badge(t, 110, 155) if t else _badge('auto', 'off')

    @admin.display(description='Page')
    def live_link(self, obj):
        url = abs_url(SeoSettings.load(), obj.path)
        return format_html('<a href="{}" target="_blank">open ↗</a>', url)

    @admin.display(description='Address')
    def live_address(self, obj):
        url = abs_url(SeoSettings.load(), obj.path)
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    @admin.display(description='Preview')
    def google_preview(self, obj):
        return format_html(
            '<div id="seo-preview" data-url="{}" data-fallback-title="{}" data-fallback-description="" '
            'style="max-width:640px;padding:14px 16px;border:1px solid #e2e8f0;border-radius:10px;'
            'background:#fff;"></div>', abs_url(SeoSettings.load(), obj.path), obj.name)

    def get_changelist_form(self, request, **kwargs):
        return ProductPageListForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if isinstance(form, ProductPageForm) and 'meta_title' in form.cleaned_data:
            apply_product_meta(obj, form.cleaned_data.get('meta_title', ''),
                               form.cleaned_data.get('meta_description', ''))
        _rebuild(request, products=True)

    # -- bulk editing by spreadsheet ----------------------------------------
    def get_urls(self):
        extra = [
            path('export/', self.admin_site.admin_view(self.export_view), name='seo_productpage_export'),
            path('import/', self.admin_site.admin_view(self.import_view), name='seo_productpage_import'),
        ]
        return extra + super().get_urls()

    COLUMNS = ['entry_id', 'sku', 'name', 'page_address', 'search_title',
               'search_description', 'hide_from_search']

    def export_view(self, request):
        if not self.has_view_permission(request):
            return redirect('..')
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="product-seo.csv"'
        resp.write('﻿')       # so Excel reads the UTF-8 properly
        w = csv.writer(resp)
        w.writerow(self.COLUMNS)
        for p in ProductPage.objects.select_related('product').order_by('name'):
            prod = p.product
            w.writerow([p.entry_id, p.sku, p.name, p.slug,
                        prod.meta_title if prod else '', prod.meta_description if prod else '',
                        'yes' if p.noindex else 'no'])
        return resp

    def import_view(self, request):
        if not self.has_change_permission(request):
            messages.error(request, 'You do not have permission to do that.')
            return redirect('..')
        ctx = dict(self.admin_site.each_context(request), title='Import product SEO from a spreadsheet',
                   opts=self.model._meta, columns=self.COLUMNS)
        if request.method == 'POST' and request.FILES.get('file'):
            result = self.apply_csv(request.FILES['file'])
            ctx['result'] = result
            if result['updated']:
                pipeline.request_bake(products=True, blog=False)
        return render(request, 'admin/seo/productpage/import.html', ctx)

    def apply_csv(self, upload):
        raw = upload.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(raw))
        result = {'updated': 0, 'unchanged': 0, 'errors': []}
        if not reader.fieldnames or 'entry_id' not in reader.fieldnames:
            result['errors'].append('The first row must be the headings, and must include "entry_id".')
            return result
        pages = {p.entry_id: p for p in ProductPage.objects.select_related('product')}
        taken = {p.slug: p.entry_id for p in pages.values()}
        for n, row in enumerate(reader, start=2):
            eid = (row.get('entry_id') or '').strip()
            page = pages.get(eid)
            if not page:
                if eid:
                    result['errors'].append('Row %d: no product with id "%s".' % (n, eid))
                continue
            changed = False
            slug = (row.get('page_address') or '').strip().lower()
            if slug and slug != page.slug:
                if not SLUG_RE.match(slug) or len(slug) > 90:
                    result['errors'].append('Row %d (%s): "%s" is not a valid address.' % (n, eid, slug))
                    continue
                if taken.get(slug) not in (None, eid):
                    result['errors'].append('Row %d (%s): "%s" is already used by another product.' % (n, eid, slug))
                    continue
                taken.pop(page.slug, None)
                taken[slug] = eid
                page.slug = slug
                changed = True
            hide = (row.get('hide_from_search') or '').strip().lower()
            if hide in ('yes', 'true', '1', 'no', 'false', '0'):
                want = hide in ('yes', 'true', '1')
                if want != page.noindex:
                    page.noindex = want
                    changed = True
            if changed:
                page.save()
            meta_changed = False
            if 'search_title' in row or 'search_description' in row:
                meta_changed = apply_product_meta(
                    page, (row.get('search_title') or '').strip(),
                    (row.get('search_description') or '').strip())
            if changed or meta_changed:
                result['updated'] += 1
            else:
                result['unchanged'] += 1
        return result


# ---------------------------------------------------------------------------
# Tracking code
# ---------------------------------------------------------------------------
class ScriptBlockForm(forms.ModelForm):
    class Meta:
        model = ScriptBlock
        fields = '__all__'
        widgets = {
            'code': forms.Textarea(attrs={'rows': 12, 'style': 'font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;'}),
            'pages': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code') or ''
        st = SeoSettings.load()
        if st.ga4_id and st.ga4_id in code:
            raise forms.ValidationError(
                'This contains your Google Analytics ID (%s), which the site already installs '
                'on every page from SEO settings. Adding it again would count every visit twice. '
                'To change the ID, change it there.' % st.ga4_id)
        if st.search_console_code and st.search_console_code in code:
            raise forms.ValidationError('The Search Console verification is already added by SEO settings.')
        if '<script' not in code.lower() and '<img' not in code.lower() and '<noscript' not in code.lower() and '<meta' not in code.lower() and '<iframe' not in code.lower():
            raise forms.ValidationError('Paste the whole snippet the provider gave you, including its <script> tags.')
        return code


@admin.register(ScriptBlock)
class ScriptBlockAdmin(admin.ModelAdmin):
    form = ScriptBlockForm
    list_display = ('name', 'placement', 'where', 'order', 'is_active', 'updated_at')
    list_editable = ('order', 'is_active')
    list_filter = ('placement', 'is_active')
    search_fields = ('name', 'code')
    fieldsets = (
        (None, {
            'description': mark_safe(
                'Analytics, ads, pixels, chat widgets and verification tags. Each is written '
                'into the pages themselves, so it works for search engines and ad platforms the '
                'same as if it had been typed into the file. <b>Google Analytics</b> and '
                '<b>Search Console</b> are not added here — they have their own boxes in '
                '<a href="../seosettings/">SEO settings</a>.'),
            'fields': ('name', 'placement', 'code', 'pages', 'order', 'is_active'),
        }),
    )

    @admin.display(description='Pages')
    def where(self, obj):
        pages = obj.page_list()
        return ', '.join(pages) if pages else 'every page'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _rebuild(request, products=True, blog=True)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        _rebuild(request, products=True, blog=True)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        _rebuild(request, products=True, blog=True)


# ---------------------------------------------------------------------------
# Site-wide settings
# ---------------------------------------------------------------------------
@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Site', {'fields': ('site_url', 'default_og_image', 'generate_product_pages')}),
        ('Google & Bing', {
            'description': 'The Analytics tag and the verification tags are written onto every '
                           'page from these boxes. Change them here and nowhere else.',
            'fields': ('ga4_id', 'search_console_code', 'bing_verification'),
        }),
        ('About the business', {
            'description': 'Shown to Google as the business details behind the site.',
            'fields': ('organization_name', 'organization_phone', 'organization_email', 'social_profiles'),
        }),
        ('robots.txt', {'fields': ('robots_extra',)}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SeoSettings.load()
        return redirect(reverse('admin:seo_seosettings_change', args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _rebuild(request, products=True, blog=True)


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------
@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ('from_path', 'to_path', 'note', 'automatic', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'automatic')
    search_fields = ('from_path', 'to_path', 'note')
    fieldsets = ((None, {
        'description': 'Send an old address to its new one. Changing a product or blog address '
                       'adds one of these by itself.',
        'fields': ('from_path', 'to_path', 'note', 'is_active'),
    }),)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _rebuild(request)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        _rebuild(request)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        _rebuild(request)


# ---------------------------------------------------------------------------
# Blog posts
# ---------------------------------------------------------------------------
class BlogSeoForm(forms.ModelForm):
    class Meta:
        model = BlogPostSeo
        fields = ('slug', 'meta_title', 'meta_description')
        widgets = {'meta_title': forms.TextInput(attrs=WIDE),
                   'meta_description': forms.Textarea(attrs=dict(WIDE, rows=3))}

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip().lower()
        if not SLUG_RE.match(slug):
            raise forms.ValidationError('Lower-case letters, numbers and single hyphens only, e.g. "why-triply-cookware".')
        return slug


@admin.register(BlogPostSeo)
class BlogPostSeoAdmin(admin.ModelAdmin):
    form = BlogSeoForm
    list_display = ('title', 'slug', 'title_state', 'description_state', 'is_published', 'live_link')
    list_display_links = ('title',)
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'slug', 'meta_title', 'meta_description')
    readonly_fields = ('title', 'live_address', 'google_preview')
    fieldsets = (
        ('Post', {'fields': ('title',)}),
        ('Its own page', {
            'description': 'Changing the address is safe: the old one is redirected to the new one '
                           'automatically.',
            'fields': ('slug', 'live_address'),
        }),
        ('How it looks in Google', {
            'description': 'Empty fields are built from the post\'s title and summary.',
            'fields': ('meta_title', 'meta_description', 'google_preview'),
        }),
    )

    class Media:
        js = ('seo/seo-admin.js',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Title tag')
    def title_state(self, obj):
        return length_badge(obj.meta_title, 30, 60) if obj.meta_title else _badge('auto', 'off')

    @admin.display(description='Description')
    def description_state(self, obj):
        return length_badge(obj.meta_description, 110, 155) if obj.meta_description else _badge('auto', 'off')

    @admin.display(description='Page')
    def live_link(self, obj):
        url = abs_url(SeoSettings.load(), '/blog/%s' % obj.slug)
        return format_html('<a href="{}" target="_blank">open ↗</a>', url)

    @admin.display(description='Address')
    def live_address(self, obj):
        url = abs_url(SeoSettings.load(), '/blog/%s' % obj.slug)
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    @admin.display(description='Preview')
    def google_preview(self, obj):
        return format_html(
            '<div id="seo-preview" data-url="{}" data-fallback-title="{}" data-fallback-description="{}" '
            'style="max-width:640px;padding:14px 16px;border:1px solid #e2e8f0;border-radius:10px;'
            'background:#fff;"></div>', abs_url(SeoSettings.load(), '/blog/%s' % obj.slug),
            obj.title, obj.excerpt)

    # saving the post fires the blog signal, which rebuilds the page and writes the redirect
