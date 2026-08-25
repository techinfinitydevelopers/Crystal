import io
from contextlib import redirect_stderr, redirect_stdout

from django.conf import settings
from django.contrib import admin, messages
from django.core.management import call_command
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django.templatetags.static import static
from . import importer
from .forms import ProductAdminForm
from .models import (
    Brand, Category, Product, ProductImage,
    ProductSpecification, Marketplace, ProductMarketplaceLink, ProductVariant,
)


# ── Helpers ────────────────────────────────────────────────────────────────

MARKETPLACE_DEFAULT_LOGOS = {
    'amazon':   'marketplace-logos/amazon.svg',
    'flipkart': 'marketplace-logos/flipkart.svg',
    'jiomart':  'marketplace-logos/jiomart.svg',
    'meesho':   'marketplace-logos/meesho.svg',
}


def _marketplace_logo(obj):
    """Uploaded logo URL, or bundled default static file."""
    if obj.logo:
        return obj.logo.url
    key = MARKETPLACE_DEFAULT_LOGOS.get(obj.slug)
    return static(key) if key else None


def _img(url, h=40):
    return format_html(
        '<img src="{}" style="height:{}px;width:auto;border-radius:6px;'
        'box-shadow:0 2px 8px rgba(0,0,0,.15);">',
        url, h,
    )


# ── Brand ──────────────────────────────────────────────────────────────────

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['logo_preview', 'name', 'tagline', 'slug', 'is_active']
    search_fields = ['name', 'slug']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Brand Identity', {'fields': ('name', 'slug', 'tagline', 'logo', 'logo_preview_readonly')}),
        ('Catalogue PDF', {'fields': ('catalogue',), 'description': 'Upload a PDF catalogue for this brand. It will appear as a download link on the Catalogue page.'}),
        ('Content', {'fields': ('description', 'is_active')}),
    )
    readonly_fields = ['logo_preview_readonly']

    @admin.display(description='Logo')
    def logo_preview(self, obj):
        return _img(obj.logo.url) if obj.logo else '—'

    @admin.display(description='Logo Preview')
    def logo_preview_readonly(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:80px;width:auto;border-radius:8px;'
                'box-shadow:0 2px 12px rgba(0,0,0,.15);">',
                obj.logo.url,
            )
        return mark_safe('<span style="color:#aaa;font-style:italic;">No logo uploaded</span>')


# ── Category ───────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_name', 'slug', 'order', 'product_count']
    search_fields = ['name', 'slug']
    list_filter = ['parent']
    prepopulated_fields = {'slug': ('name',)}
    list_display_links = ['name']
    list_select_related = ['parent']

    @admin.display(description='# Products')
    def product_count(self, obj):
        # count direct + via children
        from django.db.models import Q
        count = Product.objects.filter(
            Q(category=obj) | Q(category__parent=obj)
        ).count()
        if not count:
            return '—'
        return format_html(
            '<span style="background:#ed3338;color:#fff;padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;">{}</span>', count
        )

    @admin.display(description='Parent Category')
    def parent_name(self, obj):
        if obj.parent:
            return format_html(
                '<span style="background:#475569;padding:2px 10px;border-radius:100px;'
                'font-size:12px;font-weight:600;color:#fff;">{}</span>',
                obj.parent.name,
            )
        return mark_safe(
            '<span style="background:#dcfce7;padding:2px 10px;border-radius:100px;'
            'font-size:12px;font-weight:700;color:#166534;">Main</span>'
        )


# ── "What's missing?" list filters ─────────────────────────────────────────

# Top-level folders the static website serves; anything else is dashboard media.
SITE_CONTENT_DIRS = frozenset({
    'product-photos', 'about-assets', 'brand-assets', 'home-v3-assets',
    'uploads', 'brand-logos', 'product-data',
})


def _public_url(value):
    """Resolve a stored image/video reference to something a browser can fetch.

    Every imported product stores a *site-root-relative* path such as
    "product-photos/CL-414/hero.jpg" - that is the form the static website
    wants, and MEDIA_ROOT is rooted at the site tree so /media/<path> serves it.

    Emitted raw into an <img src> the browser resolves it against the current
    admin URL and requests
    /admin/products/product/product-photos/CL-414/hero.jpg. Django's legacy
    catch-all route reads that as an object id, the lookup fails, and the
    resulting "Product with ID ... doesn't exist" message is queued into the
    session and shown as a banner on whatever page loads next - which is why it
    looks unrelated to whatever the admin was doing. 491 products carry such a
    path, so one changelist page can fire a hundred of these.
    """
    if not value:
        return None
    if value.startswith(('http://', 'https://', '/', 'data:')):
        return value
    # Site content lives on the website service, not here. Locally MEDIA_ROOT
    # happens to be the site tree so /media/ would also work, but on Railway
    # MEDIA_ROOT is the dashboard's own volume and these files are not in it.
    # Resolving against the website is the answer that is right in both places.
    if value.split('/', 1)[0] in SITE_CONTENT_DIRS:
        return '%s/%s' % (settings.PUBLIC_SITE_URL.rstrip('/'), value.lstrip('/'))
    return '%s%s' % (settings.MEDIA_URL, value.lstrip('/'))


class _YesNoFilter(admin.SimpleListFilter):
    """Base for the yes/no completeness filters on the product changelist."""

    yes_label = 'Yes'
    no_label = 'No'
    yes_q = Q()

    def lookups(self, request, model_admin):
        return [('yes', self.yes_label), ('no', self.no_label)]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(self.yes_q)
        if self.value() == 'no':
            return queryset.exclude(self.yes_q)
        return queryset


class HasHeroImageFilter(_YesNoFilter):
    title = 'has a hero image'
    parameter_name = 'has_hero'
    yes_label = 'Has a hero image'
    no_label = 'Missing a hero image'
    yes_q = Q(images__is_hero=True)

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(self.yes_q).distinct()
        if self.value() == 'no':
            return queryset.exclude(id__in=ProductImage.objects.filter(
                is_hero=True).values('product_id'))
        return queryset


class HasVideoFilter(_YesNoFilter):
    title = 'has a video'
    parameter_name = 'has_video'
    yes_label = 'Has a video'
    no_label = 'No video'
    yes_q = ~Q(video='') & Q(video__isnull=False) | ~Q(video_url='')


class HasAmazonLinkFilter(_YesNoFilter):
    title = 'has an Amazon link'
    parameter_name = 'has_amazon'
    yes_label = 'Has an Amazon link'
    no_label = 'No Amazon link'
    yes_q = ~Q(amazon_link='')


class HasVariantsFilter(_YesNoFilter):
    title = 'has sizes / variants'
    parameter_name = 'has_variants'
    yes_label = 'Has sizes / variants'
    no_label = 'Single size only'
    yes_q = Q(variants__isnull=False)

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(variants__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(variants__isnull=True)
        return queryset


# ── Inlines ────────────────────────────────────────────────────────────────

class ProductVariantInline(admin.StackedInline):
    """The sizes of a product, as cards rather than table rows.

    Must stay Stacked: Django's inlines.js binds "Add another" by
    data-inline-type, and the card template declares "stacked".
    """
    model = ProductVariant
    template = 'admin/products/product/edit_inline/size_cards.html'
    extra = 1
    fields = [
        'name', 'sku', 'display_name', 'highlight', 'description',
        'amazon_link', 'price', 'video', 'video_url', 'image_url',
        'is_active', 'is_default', 'order',
    ]
    ordering = ['order', 'id']
    verbose_name = 'Size'
    verbose_name_plural = 'Sizes — each with its own photos, video and Amazon link'

    def get_queryset(self, request):
        # The card shows each size's photo strip; without this the strip costs
        # one query per size (eight on a kadai) on top of the count.
        return super().get_queryset(request).prefetch_related('images')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'image_preview', 'variant', 'is_hero', 'order']
    readonly_fields = ['image_preview']
    ordering = ['order', 'id']
    verbose_name = 'Gallery Image'
    verbose_name_plural = 'Step 2 — Gallery Images'

    def get_formset(self, request, obj=None, **kwargs):
        # Only offer this product's own sizes/variants in the dropdown — leave the
        # field blank to attach a photo to the product in general (shown for every
        # size), or pick a variant to give that one size its own dedicated photos.
        formset = super().get_formset(request, obj, **kwargs)
        variant_field = formset.form.base_fields['variant']
        variant_field.queryset = obj.variants.all() if obj is not None else ProductVariant.objects.none()
        variant_field.label = 'Applies to size'
        variant_field.empty_label = '— all sizes —'
        variant_field.help_text = (
            'Leave as “all sizes” for a general product photo, or pick one of the '
            'sizes above to give that size its own photo.'
        )
        return formset

    @admin.display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:cover;'
                'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.15);">',
                obj.image.url,
            )
        return mark_safe('<span style="color:#94a3b8;font-style:italic;">—</span>')


class ProductSpecificationInline(admin.StackedInline):
    model = ProductSpecification
    extra = 1
    fields = ['key', 'value', 'order']
    verbose_name = 'Specification'
    verbose_name_plural = 'Specifications'


class ProductMarketplaceLinkInline(admin.TabularInline):
    model = ProductMarketplaceLink
    extra = 1
    fields = ['marketplace', 'url']
    verbose_name = 'Marketplace Link'
    verbose_name_plural = 'Buy Now — Marketplace Links'


# ── Product ────────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm

    class Media:
        # Product-form-only assets. jazzmin allows a single `custom_css`, which
        # crystal_theme.css already occupies, so anything scoped to this screen
        # loads here instead.
        css = {'all': ('admin/crystal_product_form.css',
                       'admin/crystal_variants.css')}
        js = ('admin/crystal_tags.js', 'admin/crystal_variants.js')

    list_display = [
        'image_preview', 'name_cell', 'brand_badge', 'category_badge',
        'hero_status', 'image_count', 'variant_count',
        'video_status', 'amazon_status', 'is_active',
    ]
    list_display_links = ['image_preview', 'name_cell']
    search_fields = [
        'name', 'slug', 'sku', 'collection_name', 'short_description',
        'highlight', 'overview', 'amazon_link',
    ]
    list_filter = [
        'brand', 'category', 'is_active', 'is_featured', 'is_new',
        'show_price', 'is_dashboard_managed', HasHeroImageFilter,
        HasVideoFilter, HasAmazonLinkFilter, HasVariantsFilter,
    ]
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['brand', 'category']
    save_on_top = True

    fieldsets = (
        ('Basics — what the product is', {
            'description': (
                'Fill this in first. The web address (slug) fills itself in from the '
                'name; the SKU is the code used to match the product’s photo folder.'
            ),
            'fields': (
                ('name', 'slug'),
                ('brand', 'category'),
                ('sku', 'collection_name'),
                'tags',
            ),
        }),
        ('Description & features — what the customer reads', {
            'description': (
                'The short description is the one-liner in listings. The highlight is '
                'the bold line on the product page. Feature cards are the small '
                'icon + title + detail boxes further down that page.'
            ),
            'fields': (
                'short_description',
                'highlight',
                'overview',
                'features',
            ),
        }),
        ('Media — pictures and video', {
            'description': (
                'The main image is what shows in listings. Extra photos (and photos '
                'for a particular size) go in “Gallery Images” at the bottom of this '
                'page. For the video either upload a file or paste a link — not both.'
            ),
            'fields': (
                ('featured_image', 'main_image_preview'),
                ('thumbnail', 'thumbnail_preview_field'),
                'image_url',
                'video',
                'video_url',
                'video_status_field',
            ),
        }),
        ('Marketplace — price and where to buy', {
            'description': (
                'Tick “show price” only if the price should be visible on the site. '
                'The Amazon link powers the Buy Now button; other marketplaces go in '
                'the “Buy Now — Marketplace Links” section at the bottom.'
            ),
            'fields': (
                ('show_price', 'price'),
                'gst_pct',
                'amazon_link',
            ),
        }),
        ('Visibility — where it appears on the site', {
            'fields': (
                ('is_active', 'is_featured', 'is_new'),
                'is_dashboard_managed',
            ),
        }),
    )

    readonly_fields = [
        'main_image_preview', 'thumbnail_preview_field', 'video_status_field',
    ]

    change_list_template = 'admin/products/product/change_list.html'

    # ── Bulk import (Excel / CSV) ───────────────────────────────────────

    def get_urls(self):
        custom = [
            path('import/', self.admin_site.admin_view(self.import_view),
                 name='products_product_import'),
            path('import/template.<str:extension>',
                 self.admin_site.admin_view(self.import_template_view),
                 name='products_product_import_template'),
        ]
        return custom + super().get_urls()

    def import_view(self, request):
        """Upload an .xlsx/.csv and report what happened, row by row."""
        context = {
            **self.admin_site.each_context(request),
            'title': 'Import products from Excel / CSV',
            'opts': self.model._meta,
            'columns': importer.COLUMNS,
            'changelist_url': reverse('admin:products_product_changelist'),
            'template_xlsx_url': reverse(
                'admin:products_product_import_template', args=['xlsx']),
            'template_csv_url': reverse(
                'admin:products_product_import_template', args=['csv']),
        }

        if request.method == 'POST':
            upload = request.FILES.get('file')
            if upload is None:
                self.message_user(request, 'Choose a .xlsx or .csv file first.',
                                  level=messages.ERROR)
                return render(request, 'admin/products/product/import.html', context)
            try:
                rows = importer.read_rows(upload)
                results, summary = importer.import_rows(rows)
            except ValueError as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
                return render(request, 'admin/products/product/import.html', context)
            except Exception as exc:                      # unreadable/corrupt file
                self.message_user(request, f'Could not read that file: {exc}',
                                  level=messages.ERROR)
                return render(request, 'admin/products/product/import.html', context)

            context.update(results=results, summary=summary, filename=upload.name)
            level = messages.WARNING if summary['skipped'] else messages.SUCCESS
            self.message_user(
                request,
                f"{summary['created']} created, {summary['updated']} updated, "
                f"{summary['unchanged']} unchanged, {summary['skipped']} skipped.",
                level=level,
            )

        return render(request, 'admin/products/product/import.html', context)

    def import_template_view(self, request, extension):
        """Serve the fill-in template — same columns the importer reads."""
        if extension == 'csv':
            return HttpResponse(
                importer.template_csv_bytes(),
                content_type='text/csv',
                headers={'Content-Disposition':
                         'attachment; filename="product-import-template.csv"'},
            )
        return HttpResponse(
            importer.template_xlsx_bytes(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition':
                     'attachment; filename="product-import-template.xlsx"'},
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'brand', 'category__parent',
        ).annotate(
            _image_count=Count('images', distinct=True),
            _variant_count=Count('variants', distinct=True),
            _hero_count=Count('images', filter=Q(images__is_hero=True), distinct=True),
        )

    inlines = [
        ProductVariantInline,
        ProductImageInline,
        ProductSpecificationInline,
        ProductMarketplaceLinkInline,
    ]

    actions = ['export_to_website']

    @admin.action(description='🚀 Export to website (pushes every dashboard product\'s photos to the live site)')
    def export_to_website(self, request, queryset):
        # This exports ALL dashboard-managed products (not just the selected rows) —
        # export_products_json always rebuilds the full dashboard slice in one go so
        # sizes sharing a variant_group stay together. Selecting rows just triggers it.
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                call_command('export_products_json')
        except Exception as exc:
            self.message_user(request, f"Export failed: {exc}", level=messages.ERROR)
            return
        self.message_user(request, out.getvalue().strip() or "Export finished.", level=messages.SUCCESS)

    # ── List display helpers ────────────────────────────────────────────

    @admin.display(description='Product', ordering='name')
    def name_cell(self, obj):
        """Name with the product code beneath it.

        The site prints the code as "Code: MKA940" on the product page, so the
        dashboard shows the same string rather than a column headed "Sku" that
        the client has to translate.
        """
        code = (obj.sku or '').upper()
        return format_html(
            '<div style="font-weight:600;line-height:1.25;">{}</div>'
            '<div style="font-size:11.5px;color:var(--s-ink-soft,#616161);'
            'margin-top:2px;letter-spacing:.02em;">{}</div>',
            obj.name,
            'Code: %s' % code if code else 'No code',
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Django titles this "Sku"; the site calls it the product code, and the
        # two need to read as the same thing.
        if 'sku' in form.base_fields:
            f = form.base_fields['sku']
            f.label = 'Product code'
            f.help_text = (
                'Shown on the product page as "Code: %s". Also the name of the '
                'folder its photos live in.' % ((obj.sku or 'MKA940').upper() if obj else 'MKA940')
            )
        return form

    @admin.display(description='Image')
    def image_preview(self, obj):
        url = obj.featured_image.url if obj.featured_image else _public_url(obj.image_url)
        if url:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;'
                'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12);">',
                url,
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'height:48px;width:48px;background:#f1f5f9;border-radius:8px;'
            'color:#94a3b8;font-size:20px;">📦</span>'
        )

    @admin.display(description='Brand')
    def brand_badge(self, obj):
        colors = {
            'crystal': ('#ED3338', '#fff'),
            'crystalina': ('#7c3aed', '#fff'),
            'sparkmate': ('#0ea5e9', '#fff'),
            'valmate': ('#059669', '#fff'),
        }
        bg, fg = colors.get(obj.brand.slug, ('#64748b', '#fff'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;">{}</span>',
            bg, fg, obj.brand.name,
        )

    @admin.display(description='Category')
    def category_badge(self, obj):
        parent = obj.category.parent
        if parent:
            return format_html(
                '<span style="color:#64748b;font-size:11px;">{} /</span> '
                '<span style="font-weight:600;font-size:13px;">{}</span>',
                parent.name, obj.category.name,
            )
        return format_html(
            '<span style="font-weight:600;font-size:13px;">{}</span>',
            obj.category.name,
        )

    @staticmethod
    def _pill(text, ok):
        bg, fg = ('#dcfce7', '#166534') if ok else ('#fee2e2', '#b91c1c')
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;white-space:nowrap;">{}</span>',
            bg, fg, text,
        )

    @staticmethod
    def _count_pill(count):
        bg, fg = ('#f1f5f9', '#0f172a') if count else ('#fee2e2', '#b91c1c')
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;">{}</span>',
            bg, fg, count,
        )

    @admin.display(description='Hero?', ordering='_hero_count')
    def hero_status(self, obj):
        has = bool(getattr(obj, '_hero_count', 0))
        return self._pill('✓ Hero' if has else 'No hero', has)

    @admin.display(description='Photos', ordering='_image_count')
    def image_count(self, obj):
        return self._count_pill(getattr(obj, '_image_count', 0) or obj.images.count())

    @admin.display(description='Variants', ordering='_variant_count')
    def variant_count(self, obj):
        count = getattr(obj, '_variant_count', None)
        if count is None:
            count = obj.variants.count()
        return format_html(
            '<span style="background:#f1f5f9;padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;">{}</span>',
            count,
        )

    @admin.display(description='Video?')
    def video_status(self, obj):
        if obj.video:
            return self._pill('✓ File', True)
        if obj.video_url:
            return self._pill('✓ Link', True)
        return self._pill('No video', False)

    @admin.display(description='Amazon?', ordering='amazon_link')
    def amazon_status(self, obj):
        if obj.amazon_link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener" style="background:#dcfce7;'
                'color:#166534;padding:2px 9px;border-radius:100px;font-weight:700;'
                'font-size:12px;text-decoration:none;">✓ Link</a>',
                obj.amazon_link,
            )
        return self._pill('No link', False)

    # ── Form field helpers ──────────────────────────────────────────────

    @admin.display(description='Main Image Preview')
    def main_image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-height:120px;width:auto;border-radius:10px;'
                'box-shadow:0 4px 16px rgba(0,0,0,.15);">',
                obj.featured_image.url,
            )
        url = _public_url(obj.image_url)
        if url:
            # No onerror-hide: silently vanishing is what made the previous
            # breakage invisible and undiagnosable.
            return format_html(
                '<img src="{}" alt="" style="max-height:120px;width:auto;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.15);">',
                url,
            )
        return mark_safe('<span style="color:#aaa;font-style:italic;">No image yet</span>')

    @admin.display(description='Current video')
    def video_status_field(self, obj):
        url = obj.video.url if obj.video else _public_url(obj.video_url)
        if not url:
            return mark_safe(
                '<span style="color:#aaa;font-style:italic;">No video yet — upload a '
                'file above, or paste a link to one that is already online.</span>'
            )
        return format_html(
            '<video src="{}" controls preload="metadata" style="max-height:160px;'
            'border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.15);"></video>'
            '<br><span style="font-size:11px;color:#64748b;">{}</span>',
            url, url,
        )

    @admin.display(description='Thumbnail Preview')
    def thumbnail_preview_field(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height:80px;width:auto;border-radius:8px;'
                'box-shadow:0 2px 8px rgba(0,0,0,.12);">',
                obj.thumbnail.url,
            )
        return mark_safe('<span style="color:#aaa;font-style:italic;">No thumbnail yet</span>')


# ── Marketplace ────────────────────────────────────────────────────────────

@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ['logo_preview', 'name', 'slug', 'product_link_count', 'is_active']
    search_fields = ['name', 'slug']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['logo_preview_readonly']
    fieldsets = (
        ('Marketplace', {'fields': ('name', 'slug', 'logo', 'logo_preview_readonly', 'is_active')}),
    )

    @admin.display(description='Logo')
    def logo_preview(self, obj):
        url = _marketplace_logo(obj)
        if url:
            return format_html(
                '<img src="{}" style="height:28px;width:auto;max-width:90px;'
                'object-fit:contain;border-radius:4px;">',
                url,
            )
        return format_html(
            '<span style="background:#f1f5f9;padding:3px 10px;border-radius:6px;'
            'font-size:12px;color:#64748b;">{}</span>',
            obj.name,
        )

    @admin.display(description='Logo Preview')
    def logo_preview_readonly(self, obj):
        url = _marketplace_logo(obj)
        is_default = not obj.logo and url
        if url:
            note = (
                format_html(
                    '<br><span style="font-size:11px;color:#94a3b8;font-style:italic;">'
                    '✓ Default logo — upload above to replace</span>'
                ) if is_default else ''
            )
            return format_html(
                '<img src="{}" style="max-height:52px;width:auto;max-width:180px;'
                'object-fit:contain;border-radius:6px;padding:8px;background:#f8f9fa;'
                'border:1px solid #e2e8f0;">{}',
                url, note,
            )
        return mark_safe('<span style="color:#aaa;font-style:italic;">Upload a logo above</span>')

    @admin.display(description='Products')
    def product_link_count(self, obj):
        count = obj.product_links.count()
        return format_html(
            '<span style="background:#f1f5f9;padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;">{} product{}</span>',
            count, 's' if count != 1 else '',
        )
