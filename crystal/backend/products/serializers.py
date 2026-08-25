import re

from rest_framework import serializers
from .models import Brand, Category, Product, ProductImage, ProductSpecification, Marketplace, ProductMarketplaceLink, ProductVariant


class BrandSerializer(serializers.ModelSerializer):
    catalogue_url = serializers.SerializerMethodField()

    def get_catalogue_url(self, obj):
        request = self.context.get('request')
        if obj.catalogue:
            return request.build_absolute_uri(obj.catalogue.url) if request else obj.catalogue.url
        return None

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'tagline', 'logo', 'catalogue_url', 'description', 'is_active']


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    parent_slug = serializers.CharField(source='parent.slug', read_only=True, default=None)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'parent_name', 'parent_slug', 'order']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order']


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['id', 'key', 'value', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku_suffix', 'is_default', 'order']


MARKETPLACE_DEFAULT_LOGOS = {
    'amazon':   '/static/marketplace-logos/amazon.svg',
    'flipkart': '/static/marketplace-logos/flipkart.svg',
    'jiomart':  '/static/marketplace-logos/jiomart.svg',
    'meesho':   '/static/marketplace-logos/meesho.svg',
}


def _marketplace_logo_url(obj, request):
    """Return uploaded logo URL, falling back to bundled default by slug."""
    if obj.logo:
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url
    default = MARKETPLACE_DEFAULT_LOGOS.get(obj.slug)
    if default and request:
        return request.build_absolute_uri(default)
    return default


class MarketplaceSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        return _marketplace_logo_url(obj, self.context.get('request'))

    class Meta:
        model = Marketplace
        fields = ['id', 'name', 'slug', 'logo', 'logo_url', 'is_active']


class ProductMarketplaceLinkSerializer(serializers.ModelSerializer):
    marketplace_name = serializers.CharField(source='marketplace.name', read_only=True)
    marketplace_slug = serializers.CharField(source='marketplace.slug', read_only=True)
    marketplace_logo = serializers.SerializerMethodField()

    def get_marketplace_logo(self, obj):
        return _marketplace_logo_url(obj.marketplace, self.context.get('request'))

    class Meta:
        model = ProductMarketplaceLink
        fields = ['id', 'marketplace_name', 'marketplace_slug', 'marketplace_logo', 'url']


class ProductListSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'short_description', 'highlight', 'collection_name', 'tags',
            'image_url', 'is_active', 'is_featured', 'is_new',
            'show_price', 'price', 'thumbnail', 'created_at',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    marketplace_links = ProductMarketplaceLinkSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'short_description', 'overview', 'highlight', 'collection_name', 'tags',
            'image_url', 'is_active', 'is_featured', 'is_new',
            'show_price', 'price', 'featured_image', 'thumbnail',
            'images', 'specifications', 'marketplace_links', 'variants', 'created_at',
        ]


# ---------------------------------------------------------------------------
# Site catalogue shape
#
# product-data/products.json is what the static site (index.html /
# All-Products.html / Product.html) reads today. SiteProductSerializer maps a
# Product row back onto exactly those keys so the site can point at
# /api/products/site.json/ instead of the file, with no frontend changes.
# See products/management/commands/export_products_json.py for the same mapping
# applied in file-writing form, and sync_products.py for the original import.
# ---------------------------------------------------------------------------

SITE_DEFAULT_GST = 0.18


def site_subcategory(category):
    """JSON stores the bare sub-slug ("lighters"); the DB slug is parent-prefixed
    ("kitchenware-lighters") to keep Category.slug globally unique. Top-level
    products carry null, not "", in products.json."""
    if not category or not category.parent:
        return None
    slug, prefix = category.slug, f"{category.parent.slug}-"
    return slug[len(prefix):] if slug.startswith(prefix) else slug


def _spec_value(value):
    """ProductSpecification.value is a CharField, but products.json carries a few
    numeric filter values (e.g. "size": 2.0). Restore the number so filter
    comparisons on the site behave the same either way."""
    if re.fullmatch(r"\d+\.\d+", value or ""):
        return float(value)
    return value


def site_filters(product, variant=None):
    """The facet map. A variant's own spec rows REPLACE the general ones rather
    than merging - the same all-or-nothing rule site_image_set uses for photos,
    so there is one mental model for both.

    Partitioned in Python off the already-prefetched rows; calling
    variant.specifications.all() would issue a query per variant and undo the
    prefetch the exporter sets up."""
    specs = list(product.specifications.all())
    if variant is not None:
        own = [sp for sp in specs if sp.variant_id == variant.id]
        specs = own or [sp for sp in specs if sp.variant_id is None]
    else:
        specs = [sp for sp in specs if sp.variant_id is None]
    return {
        spec.key.strip().lower().replace(" ", "_"): _spec_value(spec.value)
        for spec in specs
        if spec.value
    }


def site_amazon_link(product, variant=None):
    """The site's Buy Now target.

    Product.amazon_link is the authority. The marketplace-link fallback exists
    for products created in the dashboard, where the Amazon URL is entered as a
    ProductMarketplaceLink row - but it must NOT apply to rows imported from the
    site catalogue: a handful of those carry a stale Amazon link the live site
    deliberately does not show, and surfacing it here would put a Buy Now button
    on a product that has none today.

    A variant's own link wins outright: 19 of the 29 size-groups in the
    catalogue list each size separately on Amazon."""
    if variant is not None and variant.amazon_link:
        return variant.amazon_link
    if product.amazon_link:
        return product.amazon_link
    if product.is_dashboard_managed:
        for link in product.marketplace_links.all():
            if link.marketplace.slug == "amazon":
                return link.url
    return None


def site_video(product, variant=None):
    """7 of the 29 size-groups have a video on some sizes but not others, so a
    variant's own video has to win before the product's."""
    if variant is not None:
        if variant.video_url:
            return variant.video_url
        if variant.video:
            return variant.video.url
    if product.video_url:
        return product.video_url
    if product.video:
        return product.video.url
    return None


def _image_url(image_field):
    """products.json holds site-root-relative paths ("product-photos/<SKU>/hero.webp"),
    which is exactly ImageField.name here - .url would prepend MEDIA_URL and give
    the site a path it can't resolve."""
    return image_field.name or None


def site_image_set(images, fallback_hero=""):
    """Ordered ProductImage list -> (hero, gallery). is_hero picks the hero,
    the rest keep `order`. A product with no photo gets hero=None, as in
    products.json - the site tests for a falsy hero."""
    images = list(images)
    if not images:
        return fallback_hero or None, []
    hero_obj = next((im for im in images if im.is_hero), images[0])
    hero = _image_url(hero_obj.image) or fallback_hero or None
    gallery = [
        url for im in images if im.pk != hero_obj.pk
        for url in [_image_url(im.image)] if url
    ]
    return hero, gallery


# Unit spellings that mean the same size. "18 LTR" and "18-LITERS" are one
# measurement written two ways, so a name reading "...18-LITERS WATER FILTER"
# already carries the "18 LTR" variant and must not get it appended again.
_UNIT_ALIASES = [
    {"l", "lt", "lts", "ltr", "ltrs", "liter", "liters", "litre", "litres"},
    {"ml"},
    {"cm", "cms", "centimeter", "centimeters", "centimetre", "centimetres"},
    {"mm"},
    {"in", "inch", "inches", '"', "''"},
    {"g", "gm", "gms", "gram", "grams"},
    {"kg", "kgs"},
    {"pc", "pcs", "piece", "pieces"},
    {"w", "watt", "watts"},
]


def _unit_key(unit):
    unit = (unit or "").strip().casefold()
    for index, group in enumerate(_UNIT_ALIASES):
        if unit in group:
            return index
    return unit or None


def _name_carries_size(product_name, variant_name):
    """True when product_name already states the measurement variant_name gives."""
    match = re.match(r'\s*(\d+(?:\.\d+)?)\s*(.*)$', variant_name or "")
    if not match:
        return False
    number, unit = match.group(1), _unit_key(match.group(2))
    for found in re.finditer(
            r'(?<![\d.])' + re.escape(number) + r'(?![\d.])\s*-?\s*([a-z"\']*)',
            product_name or "", flags=re.IGNORECASE):
        if unit is None or _unit_key(found.group(1)) == unit:
            return True
    return False


def _variant_name(product_name, variant_name):
    """Append the size only when the product name doesn't already carry it -
    catalogue rows imported from products.json were flattened per variant, so
    their names already read "... 28CM" (or "...18-LITERS", for a "18 LTR"
    variant)."""
    squash = lambda t: "".join((t or "").split()).casefold()
    if squash(variant_name) and squash(variant_name) in squash(product_name):
        return product_name
    if _name_carries_size(product_name, variant_name):
        return product_name
    return f"{product_name} {variant_name}".strip()


def site_product_entries(product):
    """One Product -> one entry, or one entry per ProductVariant (matching the
    way products.json flattens sizes into sibling entries sharing variant_group)."""
    from django.utils.text import slugify

    base_sku = product.sku or product.slug
    cat = product.category
    common = {
        "brand": product.brand.slug if product.brand else "",
        "category": cat.parent.slug if (cat and cat.parent) else (cat.slug if cat else ""),
        "subcategory": site_subcategory(cat),
        "collection": product.collection_name or "",
        "gst_pct": float(product.gst_pct) if product.gst_pct is not None else None,
    }
    # Everything below varies per size, so it is resolved per entry rather than
    # shared. Putting any of it in `common` would let dict(common, ...) quietly
    # stamp the parent's value onto all eight sizes of a kadai - which is
    # exactly how the distinct Amazon links of 19 groups would have been lost.
    def _resolve(variant=None):
        return {
            "highlight": (
                (variant.highlight if variant is not None and variant.highlight else None)
                or product.highlight or product.short_description or ""
            )[:300],
            "description": (
                (variant.description if variant is not None and variant.description else None)
                or product.overview or product.short_description or ""
            ),
            "tags": (
                variant.tags if variant is not None and variant.tags is not None
                else (product.tags or [])
            ),
            "mrp": (
                float(variant.price) if variant is not None and variant.price is not None
                else (float(product.price) if product.price is not None else None)
            ),
            "amazon_link": site_amazon_link(product, variant),
            "filters": site_filters(product, variant),
            # Provenance only - nothing on the website reads it. Imported rows
            # keep the tier the catalogue recorded; anything created here is
            # tagged as such.
            "match_tier": (
                (variant.match_tier if variant is not None and variant.match_tier else None)
                or product.match_tier
                or ("dashboard_admin" if product.is_dashboard_managed else "imported")
            ),
        }
    if product.specs:
        common["specs"] = product.specs
    video = site_video(product)
    features = product.features or []

    all_images = list(product.images.all())
    general_images = [im for im in all_images if im.variant_id is None]
    variants = [v for v in product.variants.all() if v.is_active]

    entries = []
    if not variants:
        hero, gallery = site_image_set(general_images, product.image_url)
        entry = dict(common, **_resolve(), sku=base_sku, name=product.name,
                     hero=hero, gallery=gallery, id=slugify(base_sku))
        if product.variant_group:
            entry["variant_group"] = product.variant_group
        if video:
            entry["video"] = video
        if features:
            entry["features"] = features
        entries.append(entry)
        return entries

    # Size-swapping on the site keys off this shared id, so the stored value
    # (imported from products.json) wins; only dashboard-born products need a
    # synthesised one.
    group = product.variant_group or f"vg-dash-{product.id}"
    for variant in variants:
        own = [im for im in all_images if im.variant_id == variant.id]
        hero, gallery = site_image_set(own or general_images, product.image_url)
        # A stored full SKU wins; base+suffix is the dashboard-born fallback.
        # The imported SKUs are unrelated strings (LI007/LI008/LI009), so
        # concatenation cannot reproduce them.
        sku = variant.sku or f"{base_sku}{variant.sku_suffix}"
        entry = dict(
            common,
            **_resolve(variant),
            sku=sku,
            # The real names are irregular ('... (LONG SERIES)15"'), so a stored
            # one is emitted verbatim rather than rebuilt from parts.
            name=variant.display_name or _variant_name(product.name, variant.name),
            hero=hero,
            gallery=gallery,
            id=slugify(sku),
            variant_group=group,
            variant_label=variant.name,
            variant_order=variant.order,
        )
        v_video = site_video(product, variant)
        if v_video:
            entry["video"] = v_video
        v_features = variant.features if variant.features is not None else features
        if v_features:
            entry["features"] = v_features
        entries.append(entry)
    return entries
