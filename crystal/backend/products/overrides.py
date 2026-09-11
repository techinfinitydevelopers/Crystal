"""Which parts of a product the dashboard owns, once someone edits them there.

The site reads `product-data/products.json` out of git, and the deploy-time
`sync_catalogue` fills the database *from* that file — so by default the file
wins and every dashboard edit is reverted on the next deploy. These tables are
what let a specific edit outrank the file:

  * `Product.overridden_fields` holds **catalogue keys** (the key names used in
    products.json — "name", "hero", "mrp", …), not model field names. That is
    deliberate: the same list drives both the sync guard and the override feed,
    and the feed publishes whole catalogue entries.
  * `FORM_FIELD_KEYS` maps what a person actually touched in the admin to the
    catalogue keys it can change.
  * `SYNC_FIELDS_FOR_KEY` maps a catalogue key back to the model fields
    `sync_catalogue` would write, so those can be dropped from its payload.

Keys with no entry in `SYNC_FIELDS_FOR_KEY` (features, video, gst_pct, filters)
are ones the sync never writes anyway — they need publishing but no guard.
"""

# "is_active" is not a products.json key; it rides in this list so the sync
# knows to leave the flag alone, and the feed turns it into the hidden list.
IS_ACTIVE = 'is_active'

FORM_FIELD_KEYS = {
    'name': ('name',),
    'brand': ('brand',),
    'category': ('category', 'subcategory'),
    'collection_name': ('collection',),
    'tags': ('tags',),
    'highlight': ('highlight',),
    'overview': ('description',),
    'features': ('features',),
    'main_image': ('hero', 'gallery'),
    'image_url': ('hero',),
    'video': ('video',),
    'video_url': ('video',),
    'price': ('mrp',),
    'show_price': ('mrp',),
    'gst_pct': ('gst_pct',),
    'amazon_link': ('amazon_link',),
    'meta_title': ('meta_title',),
    'meta_description': ('meta_description',),
    'is_active': (IS_ACTIVE,),
}

# Inline formsets, by model name, and the keys a change in them can affect.
INLINE_KEYS = {
    'ProductImage': ('hero', 'gallery'),
    'ProductSpecification': ('filters',),
    'ProductMarketplaceLink': ('amazon_link', 'marketplaces'),
}

SYNC_FIELDS_FOR_KEY = {
    'name': ('name',),
    'brand': ('brand',),
    'category': ('category',),
    'subcategory': ('category',),
    'collection': ('collection_name',),
    'tags': ('tags',),
    'highlight': ('short_description', 'highlight'),
    'description': ('overview',),
    'hero': ('image_url',),
    'mrp': ('price', 'show_price'),
    IS_ACTIVE: ('is_active',),
}

# Keys the feed publishes verbatim from the catalogue entry. "is_active" is
# excluded — it becomes the hidden list instead of an entry field.
PUBLISHABLE = frozenset(
    key for keys in FORM_FIELD_KEYS.values() for key in keys if key != IS_ACTIVE
) | {'filters', 'marketplaces'}


def keys_for_form_fields(field_names):
    """Catalogue keys a set of changed admin form fields can affect."""
    keys = set()
    for name in field_names:
        keys.update(FORM_FIELD_KEYS.get(name, ()))
    return keys


def keys_for_inline(model_name):
    return set(INLINE_KEYS.get(model_name, ()))


def sync_fields_to_skip(overridden_keys):
    """Model fields `sync_catalogue` must leave alone for this product."""
    fields = set()
    for key in overridden_keys or ():
        fields.update(SYNC_FIELDS_FOR_KEY.get(key, ()))
    return fields


# ── Brands and categories ──────────────────────────────────────────────────
# The site ships its own copy of both (a BRANDS array and a CATEGORIES array in
# every listing page), and those copies are not always word-for-word what the
# database holds — "Wood Range" here is "Wooden Range" there, for one. So the
# same rule applies: only a field somebody actually edited may replace what the
# page ships. Everything else stays exactly as it is.

BRAND_FIELD_KEYS = {
    'name': ('name',),
    'tagline': ('tagline',),
    'description': ('blurb',),
}

CATEGORY_FIELD_KEYS = {
    'name': ('label',),
}

BRAND_PUBLISHABLE = frozenset(k for ks in BRAND_FIELD_KEYS.values() for k in ks)
CATEGORY_PUBLISHABLE = frozenset(k for ks in CATEGORY_FIELD_KEYS.values() for k in ks)


def keys_for(mapping, field_names):
    keys = set()
    for name in field_names:
        keys.update(mapping.get(name, ()))
    return keys
