"""
Export dashboard-created products into product-data/products.json — the flat
JSON file the live static site actually reads (index.html / All-Products.html /
Product.html never talk to this Django app; see sync_products.py for the
reverse, one-time JSON→DB import).

Each Product with Size/Variant rows becomes MULTIPLE entries in the JSON
(one per variant), linked by a shared `variant_group` — mirroring the existing
hand-curated dataset's pattern, so Product.html's existing variant-swap code
(applySizeVariant) picks them up with no frontend changes needed. A variant
gets its own hero/gallery photos if you attached ProductImage rows to it in
the admin; otherwise it falls back to the product's general photos.

Safe to re-run any time (e.g. after editing products in the dashboard): it
only ever touches entries it previously wrote (tagged match_tier="dashboard_admin"),
replacing them wholesale from the current database state, and never modifies
the hand-curated entries that were already in products.json.

Usage:
    python manage.py export_products_json
"""
import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from products.models import Product, ProductImage

SITE_ROOT = Path(settings.BASE_DIR).resolve().parent.parent
JSON_PATH = SITE_ROOT / "product-data" / "products.json"
PHOTOS_ROOT = SITE_ROOT / "product-photos"
DASHBOARD_TIER = "dashboard_admin"
DEFAULT_GST = 0.18


def _copy_image(field_file, dest_dir: Path, base_name: str) -> str | None:
    """Copy an uploaded ImageField's file to product-photos/<sku>/<base_name>.<ext>
    and return the path relative to the site root, or None if the file is missing."""
    if not field_file:
        return None
    src = Path(field_file.path)
    if not src.is_file():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{base_name}{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return f"product-photos/{dest_dir.name}/{dest.name}"


def _image_set(images, sku_dir: Path):
    """Given an ordered ProductImage queryset, copy files and split into hero + gallery."""
    images = list(images)
    if not images:
        return None, []
    hero_obj = next((im for im in images if im.is_hero), images[0])
    hero = _copy_image(hero_obj.image, sku_dir, "hero")
    gallery = []
    gi = 0
    for im in images:
        if im.pk == hero_obj.pk:
            continue
        gi += 1
        path = _copy_image(im.image, sku_dir, f"g{gi}")
        if path:
            gallery.append(path)
    return hero, gallery


def _category_fields(category):
    if category.parent:
        return category.parent.slug, category.slug
    return category.slug, ""


def _filters(product):
    return {
        spec.key.strip().lower().replace(" ", "_"): spec.value
        for spec in product.specifications.all()
        if spec.value
    }


def _amazon_link(product):
    link = product.marketplace_links.filter(marketplace__slug="amazon").first()
    return link.url if link else "No"


def _mrp(product):
    if product.show_price and product.price is not None:
        return float(product.price)
    return None


def _build_entry(product, sku, name, variant_label=None, variant_group=None, variant_order=None,
                  hero=None, gallery=None):
    cat, sub = _category_fields(product.category)
    entry = {
        "sku": sku,
        "name": name,
        "brand": product.brand.slug,
        "category": cat,
        "subcategory": sub,
        "collection": product.collection_name or "",
        "highlight": (product.highlight or product.short_description or "")[:300],
        "description": product.overview or product.short_description or "",
        "tags": product.tags or [],
        "gst_pct": DEFAULT_GST,
        "mrp": _mrp(product),
        "amazon_link": _amazon_link(product),
        "filters": _filters(product),
        "hero": hero or product.image_url or "",
        "gallery": gallery or [],
        "match_tier": DASHBOARD_TIER,
        "id": slugify(sku),
    }
    if variant_group:
        entry["variant_group"] = variant_group
        entry["variant_label"] = variant_label
        entry["variant_order"] = variant_order
    return entry


class Command(BaseCommand):
    help = "Export dashboard products (with their size/variant photos) into product-data/products.json"

    def handle(self, *args, **options):
        if not JSON_PATH.is_file():
            self.stderr.write(self.style.ERROR(f"products.json not found at {JSON_PATH}"))
            return

        with open(JSON_PATH, encoding="utf-8") as f:
            raw = json.load(f)

        # drop everything we exported last time; the fresh DB state below replaces it
        kept = [p for p in raw.get("products", []) if p.get("match_tier") != DASHBOARD_TIER]

        new_entries = []
        products = Product.objects.filter(
            is_active=True, is_dashboard_managed=True,
        ).select_related("brand", "category__parent")

        for product in products:
            base_sku = product.sku or product.slug
            variants = list(product.variants.all())

            if not variants:
                sku_dir = PHOTOS_ROOT / base_sku
                images = ProductImage.objects.filter(product=product, variant__isnull=True).order_by("order")
                hero, gallery = _image_set(images, sku_dir)
                if hero is None and product.featured_image:
                    hero = _copy_image(product.featured_image, sku_dir, "hero")
                new_entries.append(_build_entry(product, base_sku, product.name, hero=hero, gallery=gallery))
                continue

            group = f"vg-dash-{product.id}"
            general_images = ProductImage.objects.filter(product=product, variant__isnull=True).order_by("order")

            for variant in variants:
                sku = f"{base_sku}{variant.sku_suffix}"
                sku_dir = PHOTOS_ROOT / sku
                own_images = ProductImage.objects.filter(product=product, variant=variant).order_by("order")
                hero, gallery = _image_set(own_images if own_images.exists() else general_images, sku_dir)
                if hero is None and product.featured_image:
                    hero = _copy_image(product.featured_image, sku_dir, "hero")
                name = f"{product.name} {variant.name}".strip()
                new_entries.append(_build_entry(
                    product, sku, name,
                    variant_label=variant.name, variant_group=group, variant_order=variant.order,
                    hero=hero, gallery=gallery,
                ))

        raw["products"] = kept + new_entries
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(new_entries)} dashboard product/variant entries "
            f"({len(kept)} hand-curated entries left untouched). Wrote {JSON_PATH}"
        ))
