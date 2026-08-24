import io
from contextlib import redirect_stderr, redirect_stdout

from django.contrib import admin, messages
from django.core.management import call_command
from django.utils.html import format_html, mark_safe
from django.templatetags.static import static
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


# ── Inlines ────────────────────────────────────────────────────────────────

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['name', 'sku_suffix', 'is_default', 'order']
    verbose_name = 'Size / Variant'
    verbose_name_plural = 'Sizes & Variants'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['variant', 'image', 'image_preview', 'is_hero', 'order']
    readonly_fields = ['image_preview']
    verbose_name = 'Gallery Image'
    verbose_name_plural = 'Gallery Images'

    def get_formset(self, request, obj=None, **kwargs):
        # Only offer this product's own sizes/variants in the dropdown — leave the
        # field blank to attach a photo to the product in general (shown for every
        # size), or pick a variant to give that one size its own dedicated photos.
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['variant'].queryset = obj.variants.all() if obj is not None else ProductVariant.objects.none()
        return formset

    @admin.display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:cover;'
                'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.15);">',
                obj.image.url,
            )
        return '—'


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
    list_display = [
        'image_preview', 'name', 'brand_badge', 'category_badge',
        'collection_name', 'variant_count', 'is_active', 'is_featured',
    ]
    search_fields = ['name', 'slug', 'sku', 'collection_name']
    list_filter = ['brand', 'is_active', 'is_featured', 'is_new', 'category']
    prepopulated_fields = {'slug': ('name',)}
    list_display_links = ['image_preview', 'name']

    fieldsets = (
        ('Product Identity', {
            'fields': (
                ('name', 'slug'),
                ('brand', 'category'),
                ('sku', 'collection_name'),
                'tags',
            ),
        }),
        ('Content & Description', {
            'fields': (
                'short_description',
                'highlight',
                'overview',
            ),
        }),
        ('Main Image', {
            'fields': (
                ('featured_image', 'main_image_preview'),
                ('thumbnail', 'thumbnail_preview_field'),
                'image_url',
            ),
        }),
        ('Pricing & Visibility', {
            'fields': (
                ('is_active', 'is_featured', 'is_new'),
                ('show_price', 'price'),
            ),
        }),
    )

    readonly_fields = [
        'main_image_preview', 'thumbnail_preview_field',
    ]

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

    @admin.display(description='Image')
    def image_preview(self, obj):
        url = obj.featured_image.url if obj.featured_image else (obj.image_url or None)
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

    @admin.display(description='Variants')
    def variant_count(self, obj):
        count = obj.variants.count()
        return format_html(
            '<span style="background:#f1f5f9;padding:2px 9px;border-radius:100px;'
            'font-weight:700;font-size:12px;">{}</span>',
            count,
        )

    # ── Form field helpers ──────────────────────────────────────────────

    @admin.display(description='Main Image Preview')
    def main_image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-height:120px;width:auto;border-radius:10px;'
                'box-shadow:0 4px 16px rgba(0,0,0,.15);">',
                obj.featured_image.url,
            )
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height:120px;width:auto;border-radius:10px;'
                'box-shadow:0 4px 16px rgba(0,0,0,.15);" onerror="this.style.display=\'none\'">',
                obj.image_url,
            )
        return mark_safe('<span style="color:#aaa;font-style:italic;">No image yet</span>')

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
