"""JSON catalogue -> database.

The site and this dashboard are separate deployables: the live site reads
`product-data/products.json` directly, and that file is the source of truth for
every product that was not created in the dashboard. This module is the one
implementation of "make the database look like that file", used both by
`sync_products.py` (local file, run from a dev machine) and by the
`sync_catalogue` management command (fetches the file over HTTP, so production
can sync itself without the repo root being present in its container).
"""
from django.db import transaction
from django.utils.text import slugify

from products.models import (
    Brand, Category, Product, ProductImage, ProductSpecification, Marketplace,
    ProductMarketplaceLink, ProductVariant, RetiredSku,
)
from products.overrides import sync_fields_to_skip

CAT_LABELS = {
    "cookware": "Cookware", "kitchenware": "Kitchenware", "water-bottle": "Water Bottle",
    "oil-pourer": "Oil Pourer & Sprayer", "wood-range": "Wood Range", "pressure-cooker": "Pressure Cooker",
    "electric-appliances": "Electric Appliances", "cooktop": "Cooktop", "lunch-box": "Lunch Box",
    "cleaning-aid": "Cleaning Aid",
}

BRAND_LABELS = {
    "crystal": ("Crystal", "World of Kitchenware"),
    "crystalina": ("Crystalina", "Splendid Finish"),
    "sparkmate": ("SparkMate", "Cleaning Simplified"),
    "valmate": ("ValMate", "Value for Money"),
}


def slugify_sub(sub):
    return sub.replace(" ", "-").lower()


# Photo rows whose path starts with one of these came from the catalogue and
# are this function's to manage. Anything else — a file someone uploaded in the
# dashboard, which lands under products/gallery/ — is left strictly alone.
from products.media_urls import SITE_CONTENT_DIRS


def _sync_photos(product, variant, wanted, owned_keys):
    """Make this product's (or size's) catalogue photos match the file.

    Returns how many rows changed. Three rules make it safe to run on every
    deploy:

      * a product whose photos were edited in the dashboard is skipped outright
        — that edit is the authority now (see products/overrides.py);
      * only rows pointing into the website's own photo folders are touched, so
        an uploaded file is never deleted or reordered by a sync;
      * it is idempotent — a second run with the same file changes nothing.
    """
    if owned_keys and ({"hero", "gallery"} & set(owned_keys)):
        return 0

    existing = [
        im for im in product.images.all()
        if im.variant_id == (variant.id if variant is not None else None)
    ]
    from_site = {
        im.image.name: im for im in existing
        if (im.image.name or "").split("/", 1)[0] in SITE_CONTENT_DIRS
    }
    # Uploaded photos keep their places at the end; catalogue order comes first.
    uploaded = [im for im in existing if im.image.name not in from_site]

    changed = 0
    for order, path in enumerate(wanted):
        row = from_site.pop(path, None)
        is_hero = order == 0
        if row is None:
            ProductImage.objects.create(
                product=product, variant=variant, image=path,
                order=order, is_hero=is_hero,
            )
            changed += 1
            continue
        if row.order != order or row.is_hero != is_hero:
            row.order, row.is_hero = order, is_hero
            row.save(update_fields=["order", "is_hero"])
            changed += 1

    # Whatever is left pointed at a website photo the catalogue no longer lists.
    # Deleting the row drops a reference, never a file — re-adding the path to
    # the catalogue brings it straight back on the next sync.
    for row in from_site.values():
        row.delete()
        changed += 1

    for offset, row in enumerate(uploaded):
        order = len(wanted) + offset
        if row.order != order or (wanted and row.is_hero):
            row.order = order
            if wanted:
                row.is_hero = False
            row.save(update_fields=["order", "is_hero"])
            changed += 1

    return changed


@transaction.atomic
def sync_catalogue(items):
    """Upsert every catalogue product, and return what changed.

    Atomic on purpose: this now runs against production over the network, and a
    dropped connection halfway through would otherwise leave the catalogue part
    old and part new.
    """
    brand_objs = {}
    for slug, (name, tagline) in BRAND_LABELS.items():
        b, _ = Brand.objects.get_or_create(slug=slug, defaults={"name": name, "tagline": tagline})
        brand_objs[slug] = b

    cat_objs = {}
    for slug, label in CAT_LABELS.items():
        c, _ = Category.objects.get_or_create(slug=slug, defaults={"name": label})
        cat_objs[slug] = c

    marketplace_amazon, _ = Marketplace.objects.get_or_create(slug="amazon", defaults={"name": "Amazon"})

    # Products someone removed in the dashboard. They are still in the file, so
    # without this the next deploy would simply create them again.
    retired_skus = set(RetiredSku.objects.values_list("sku", flat=True))

    # Catalogue keys each product now owns, so an edit made here is not undone.
    owned = dict(
        Product.objects.exclude(overridden_fields=[])
        .values_list("sku", "overridden_fields")
    )

    # A catalogue sku can name a size of a collapsed group rather than a product
    # of its own; its photos then belong to that ProductVariant.
    variant_by_sku = {
        v.sku: v for v in
        ProductVariant.objects.exclude(sku="").select_related("product")
    }

    created, updated, skipped, removed, photo_changes = 0, 0, 0, 0, 0
    for p in items:
        sku = (p.get("sku") or "").strip()
        if not sku:
            skipped += 1
            continue
        if sku in retired_skus:
            removed += 1
            continue
        brand_slug = (p.get("brand") or "crystal").strip().lower()
        brand_obj = brand_objs.get(brand_slug) or brand_objs["crystal"]

        cat_slug = p.get("category")
        sub_slug = p.get("subcategory")
        if sub_slug:
            sub_key = f"{cat_slug}__{sub_slug}"
            cat_obj = cat_objs.get(sub_key)
            if not cat_obj:
                parent = cat_objs.get(cat_slug)
                sub_label = sub_slug.replace("-", " ").title()
                cat_obj, _ = Category.objects.get_or_create(
                    slug=slugify_sub(f"{cat_slug}-{sub_slug}"),
                    defaults={"name": sub_label, "parent": parent},
                )
                cat_objs[sub_key] = cat_obj
        else:
            cat_obj = cat_objs.get(cat_slug)
        if cat_obj is None:
            cat_obj = cat_objs["cookware"]

        name = p.get("name") or sku
        defaults = {
            "name": name,
            "slug": slugify(sku),
            "brand": brand_obj,
            "category": cat_obj,
            "short_description": (p.get("highlight") or "")[:300],
            "overview": p.get("description") or "",
            "highlight": (p.get("highlight") or "")[:300],
            "collection_name": p.get("collection") or "",
            "tags": p.get("tags") or [],
            "image_url": p.get("hero") or "",
            "is_active": True,
            "price": p.get("mrp") if isinstance(p.get("mrp"), (int, float)) else None,
            "show_price": bool(isinstance(p.get("mrp"), (int, float))),
            # bulk-imported from the JSON catalogue, not created in the dashboard —
            # must stay excluded from export_products_json (see that command's docstring)
            "is_dashboard_managed": False,
        }
        # Anything edited in the dashboard outranks what products.json still
        # says — otherwise the next deploy silently undoes the edit, which is
        # exactly the kind of thing nobody thinks to check.
        for field in sync_fields_to_skip(owned.get(sku)):
            defaults.pop(field, None)

        prod, was_created = Product.objects.update_or_create(sku=sku, defaults=defaults)
        if was_created:
            created += 1
        else:
            updated += 1

        # Photos. Every path in the catalogue is site-root-relative
        # ("product-photos/CL-216/g4.jpg", "sparkmate/SHH009/img-1.jpg") and the
        # files live on the website service, so the row only has to carry the
        # path — nothing is downloaded or copied. This used to be skipped
        # entirely, which is why 172 products showed photos on the site and
        # none, or fewer, in the dashboard.
        photos = [x for x in [p.get("hero")] + list(p.get("gallery") or []) if x]
        target = variant_by_sku.get(sku)
        if target is not None:
            # A size of a collapsed group: its photos belong to that size, not
            # to the parent in general, or every size would inherit them.
            photo_changes += _sync_photos(target.product, target, photos, owned.get(target.product.sku))
        else:
            photo_changes += _sync_photos(prod, None, photos, owned.get(sku))

        # specifications from filters{} — rebuilt wholesale, so a product whose
        # specs were edited here has to be left out of it entirely.
        if "filters" not in (owned.get(sku) or ()):
            prod.specifications.all().delete()
            for i, (k, v) in enumerate((p.get("filters") or {}).items()):
                if v:
                    ProductSpecification.objects.create(product=prod, key=k.replace("_", " ").title(), value=str(v), order=i)

        # amazon marketplace link
        link = p.get("amazon_link")
        if link and "amazon_link" not in (owned.get(sku) or ()):
            ProductMarketplaceLink.objects.update_or_create(
                product=prod, marketplace=marketplace_amazon, defaults={"url": link}
            )

    # A product pulled from the catalogue that is no longer in the catalogue was
    # removed from the site on purpose (usually: no genuine product photo). Retire
    # it here too, otherwise the dashboard keeps listing something the site does
    # not sell any more. Deactivated rather than deleted, so re-adding it to the
    # JSON — or attaching a real photo later — brings it straight back.
    #
    # Scoped to is_dashboard_managed=False on purpose: products created in the
    # dashboard are never in products.json, and must not be swept up by this.
    json_skus = {(p.get("sku") or "").strip() for p in items if (p.get("sku") or "").strip()}
    stale = (Product.objects.filter(is_dashboard_managed=False, is_active=True)
             .exclude(sku__in=json_skus)
             .exclude(sku__in=retired_skus))
    retired = sorted(stale.values_list("sku", flat=True))
    if retired:
        stale.update(is_active=False)

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "removed_in_dashboard": removed,
        "photo_rows_changed": photo_changes,
        "retired": retired,
        "total_products": Product.objects.count(),
        "total_brands": Brand.objects.count(),
        "total_categories": Category.objects.count(),
    }
