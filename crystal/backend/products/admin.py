import io
from contextlib import redirect_stderr, redirect_stdout

from django.contrib import admin, messages
from django.core.management import call_command
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django.templatetags.static import static
from . import importer
from .forms import KEEP_CURRENT_IMAGE, ProductAdminForm
from .media_urls import _public_url
from . import overrides as ov
from .models import (
    Brand, Category, Product, ProductImage, ProductSpecification, Marketplace,
    ProductMarketplaceLink, ProductVariant, RetiredSku,
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
    template = 'admin/products/product/edit_inline/gallery_grid.html'
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


def _image_public_url(image_field):
    """A browser-usable URL for a stored product photo.

    The imported photos are site-root-relative paths and the files live on the
    website service, so ImageField.url (which prepends MEDIA_URL) 404s in
    production. The gallery template reads this off the instance.
    """
    return _public_url(getattr(image_field, 'name', '') or '')


ProductImage.public_image_url = property(lambda self: _image_public_url(self.image))


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
                       'admin/crystal_variants.css',
                       'admin/crystal_media.css')}
        js = ('admin/crystal_tags.js', 'admin/crystal_variants.js',
              'admin/crystal_media.js')

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
                'Pick the main image straight from this product’s photos. It is the '
                'big picture on the product page and the one every listing card '
                'shows, and the live site picks the change up on its own — there is '
                'nothing to publish afterwards. Photos for one particular size are '
                'chosen in “Gallery Images” at the bottom of this page. For the '
                'video either upload a file or paste a link — not both.'
            ),
            'fields': (
                'main_image',
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
        ('Search engines — how this product shows up on Google', {
            'description': (
                'Leave both blank and the site uses the product name and highlight, '
                'which is what it does today. Fill them in to control the blue '
                'heading and the grey summary of the Google result, and the text '
                'shown when someone shares the link.'
            ),
            'classes': ('collapse',),
            'fields': (
                'meta_title',
                'meta_description',
            ),
        }),
        ('Visibility — where it appears on the site', {
            'fields': (
                ('is_active', 'is_featured', 'is_new'),
                'is_dashboard_managed',
            ),
        }),
    )

    readonly_fields = ['video_status_field']

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

    def save_related(self, request, form, formsets, change):
        """Turn the main-image pick into the thing the website actually reads.

        It has to run *after* the inlines: a photo added in the gallery grid in
        this same save does not exist yet while the main form is being saved,
        and neither does a photo that was just deleted. Everything below works
        off the gallery as it stands once the formsets have committed.
        """
        super().save_related(request, form, formsets, change)
        self._apply_main_image(request, form, formsets)
        self._record_dashboard_edits(request, form, formsets)

    def _record_dashboard_edits(self, request, form, formsets):
        """Remember which parts of the product were edited here.

        products.json is still the source for everything nobody has touched, and
        the deploy-time sync rewrites the database from it. Recording the edited
        catalogue keys is what makes an edit survive that, and what puts it in
        the feed the live pages read — see products/overrides.py.

        Only *changed* fields are recorded. Re-saving a product without touching
        anything must not quietly hand its whole record over to the dashboard.
        """
        product = form.instance
        keys = ov.keys_for_form_fields(form.changed_data)
        for formset in formsets:
            model_name = getattr(formset.model, '__name__', '')
            if any(f.has_changed() for f in formset.forms) or formset.deleted_forms:
                keys.update(ov.keys_for_inline(model_name))

        keys &= (ov.PUBLISHABLE | {ov.IS_ACTIVE})
        if not keys:
            return
        current = set(product.overridden_fields or ())
        merged = current | keys
        if merged == current:
            return
        product.overridden_fields = sorted(merged)
        product.save(update_fields=['overridden_fields'])

        self.message_user(
            request,
            'Saved. The website now takes %s for this product from here rather '
            'than from its catalogue file — reload the product page to see it.'
            % self._describe_keys(sorted(keys)),
            level=messages.SUCCESS,
        )

    @staticmethod
    def _describe_keys(keys):
        labels = {
            'name': 'the name', 'brand': 'the brand', 'category': 'the category',
            'subcategory': 'the category', 'collection': 'the collection',
            'tags': 'the tags', 'highlight': 'the highlight',
            'description': 'the description', 'features': 'the feature cards',
            'hero': 'the main image', 'gallery': 'the photos', 'video': 'the video',
            'mrp': 'the price', 'gst_pct': 'the GST', 'amazon_link': 'the Amazon link',
            'filters': 'the specifications', ov.IS_ACTIVE: 'whether it is shown',
        }
        seen, out = set(), []
        for key in keys:
            label = labels.get(key, key)
            if label not in seen:
                seen.add(label)
                out.append(label)
        if len(out) == 1:
            return out[0]
        return ', '.join(out[:-1]) + ' and ' + out[-1]

    # ── Removing a product ──────────────────────────────────────────────

    def _retire(self, request, products):
        """Tombstone the products being deleted, then let Django delete them.

        Deleting the row alone does not remove a product from anything: the
        website reads products.json, which still lists it, and the next deploy's
        sync would recreate the row from that same file. The tombstone is what
        makes the removal stick, and deleting the tombstone undoes it.
        """
        for product in products:
            if not product.sku:
                continue
            RetiredSku.objects.update_or_create(
                sku=product.sku,
                defaults={'name': product.name,
                          'retired_by': getattr(request.user, 'username', '')},
            )

    def delete_model(self, request, obj):
        self._retire(request, [obj])
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        self._retire(request, list(queryset))
        super().delete_queryset(request, queryset)

    @staticmethod
    def _inline_hero_pick(formsets):
        """The photo whose “Main” star was clicked in the gallery grid, if any.

        The grid can set the hero too, and an edit made there has to count as
        much as one made in the picker — otherwise starring a photo down there
        would change the dashboard and never reach the website.
        """
        for formset in formsets:
            if formset.model is not ProductImage:
                continue
            for image_form in formset.forms:
                data = getattr(image_form, 'cleaned_data', None) or {}
                if 'is_hero' not in getattr(image_form, 'changed_data', ()):
                    continue
                if not data.get('is_hero') or data.get('DELETE') or data.get('variant'):
                    continue
                if image_form.instance.pk:
                    return image_form.instance.pk
        return None

    def _apply_main_image(self, request, form, formsets):
        product = form.instance
        images = list(
            product.images.filter(variant__isnull=True).order_by('order', 'id')
        )
        if not images:
            return

        choice = str(form.cleaned_data.get('main_image') or '')
        picked = 'main_image' in form.changed_data

        if not picked:
            # Nothing moved in the picker, so a star clicked in the gallery grid
            # is what the person meant. (If both moved, the picker wins — it is
            # the control that is actually labelled "Main image".)
            inline_pk = self._inline_hero_pick(formsets)
            if inline_pk is not None:
                choice = str(inline_pk)
                picked = True

        if choice == KEEP_CURRENT_IMAGE:
            # "Leave the path alone" — only meaningful while the product had no
            # gallery rows at all. It has some now, so fall through to whichever
            # of them is already flagged.
            chosen = next((im for im in images if im.is_hero), images[0])
            picked = False
        else:
            chosen = next((im for im in images if str(im.pk) == choice), None)
            if chosen is None:
                # The chosen photo was deleted in this same save, or the picker
                # was never rendered (add form). Keep the flag consistent rather
                # than leaving the product with no main image at all.
                chosen = next((im for im in images if im.is_hero), images[0])
                picked = False

        for image in images:
            wanted = image.pk == chosen.pk
            if image.is_hero != wanted:
                image.is_hero = wanted
                image.save(update_fields=['is_hero'])

        changed_fields = []
        hero_path = getattr(chosen.image, 'name', '') or ''
        if hero_path and product.image_url != hero_path:
            product.image_url = hero_path
            changed_fields.append('image_url')
        if picked:
            # From here on the deploy-time catalogue sync must not put
            # products.json's photo back. See catalogue_sync.sync_catalogue.
            owned = set(product.overridden_fields or ()) | {'hero', 'gallery'}
            if owned != set(product.overridden_fields or ()):
                product.overridden_fields = sorted(owned)
                changed_fields.append('overridden_fields')
        if changed_fields:
            product.save(update_fields=changed_fields)

        if picked:
            self.message_user(
                request,
                'Main image updated — the website shows it from now on '
                '(reload the product page to see it).',
                level=messages.SUCCESS,
            )

    @admin.display(description='Image')
    def image_preview(self, obj):
        url = _public_url(obj.image_url)
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

    @admin.display(description='Amazon', ordering='amazon_link')
    def amazon_status(self, obj):
        """The Amazon mark when the product is listed, a red flag when it is not.

        A green tick said "link present" without saying where to, and said
        nothing useful at a glance across a hundred rows. The logo reads
        instantly, and the red flag matches what the website now shows on a
        product with no link, so the two views agree.
        """
        if obj.amazon_link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener" title="{}" '
                'style="display:inline-flex;align-items:center;gap:6px;'
                'padding:3px 10px;border-radius:100px;background:#fff;'
                'border:1px solid #e1e1e1;text-decoration:none;">'
                '<img src="{}" alt="Amazon" style="height:15px;display:block;">'
                '</a>',
                obj.amazon_link, obj.amazon_link,
                static('marketplace-logos/amazon.svg'),
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;gap:6px;'
            'padding:3px 10px;border-radius:100px;background:rgba(237,51,56,.10);'
            'border:1.5px solid #ED3338;color:#ED3338;font-weight:700;font-size:12px;">'
            '<span style="width:7px;height:7px;border-radius:50%;background:#ED3338;"></span>'
            'No link</span>'
        )

    # ── Form field helpers ──────────────────────────────────────────────

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


@admin.register(RetiredSku)
class RetiredSkuAdmin(admin.ModelAdmin):
    """Products removed in the dashboard.

    A removal has to be recorded somewhere the deploy-time sync can see it:
    products.json still lists the product, so without this row the next deploy
    would recreate it and the website would go on showing it regardless.

    Deleting a row here undoes the removal — the next sync reads the product
    back out of the catalogue file. Nothing on this screen destroys data.
    """

    list_display = ['sku', 'name', 'retired_at', 'retired_by', 'restore_hint']
    search_fields = ['sku', 'name']
    readonly_fields = ['retired_at']
    ordering = ['-retired_at']

    def has_add_permission(self, request):
        # These are created by removing a product, never typed in by hand.
        return False

    @admin.display(description='To bring it back')
    def restore_hint(self, obj):
        return mark_safe(
            '<span style="color:#64748b;font-size:12px;">Delete this row — the '
            'product returns on the next sync.</span>'
        )


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
                mark_safe(
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
