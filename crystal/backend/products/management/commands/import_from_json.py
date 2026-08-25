"""
Import the live site's catalogue (product-data/products.json) into the dashboard
database, so the admin reflects what the website actually shows.

This is the counterpart of export_products_json (DB -> JSON). It fills in the
fields the original one-time sync (backend/sync_products.py) could not:

  * Product.video_url / features / amazon_link / gst_pct
  * Product.variant_group (the shared id that makes size-swapping work),
    match_tier and specs
  * ProductImage rows for the hero + gallery photos
  * ProductVariant rows for entries that belong to a variant_group

Images are NOT copied or re-uploaded. The JSON holds paths that already exist
on disk relative to the site root (C:\\Website\\crystal), e.g.
"product-photos/CNS-756/hero.jpg". We assign that path straight to
ProductImage.image.name, so the database records where the file lives without
duplicating 300+ MB of photos.

Matching is by SKU and never creates products: a JSON entry with no matching
Product row is reported, not invented.

Usage:
    python manage.py import_from_json --dry-run
    python manage.py import_from_json
"""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, ProductImage, ProductVariant

SITE_ROOT = Path(settings.BASE_DIR).resolve().parent.parent
JSON_PATH = SITE_ROOT / "product-data" / "products.json"

# amazon_link placeholders used in the JSON for "no link yet"
NO_LINK = {"", "no", "none", "n/a", "-"}


def _clean_link(value):
    if not value:
        return ""
    value = str(value).strip()
    if value.lower() in NO_LINK:
        return ""
    return value[:500]


def _local_paths(entry):
    """Ordered, de-duplicated hero+gallery paths, plus the ones we had to skip.

    A handful of entries still point at remote Amazon CDN URLs; those cannot be
    an on-disk ImageField target, so they are skipped and reported.
    """
    raw = []
    hero = (entry.get("hero") or "").strip()
    if hero:
        raw.append(hero)
    for g in entry.get("gallery") or []:
        g = (g or "").strip()
        if g:
            raw.append(g)

    paths, skipped, seen = [], [], set()
    for p in raw:
        if p in seen:
            continue
        seen.add(p)
        if p.startswith("http://") or p.startswith("https://"):
            skipped.append((p, "remote URL, not a local file"))
        elif not (SITE_ROOT / p).is_file():
            skipped.append((p, "file not found on disk"))
        else:
            paths.append(p)
    return paths, skipped


def _gst(entry):
    value = entry.get("gst_pct")
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "Import product-data/products.json (images, variants, video, features) into the dashboard DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would change and write nothing.",
        )
        parser.add_argument(
            "--json", dest="json_path", default=str(JSON_PATH),
            help="Path to products.json (defaults to the site's product-data/products.json).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        json_path = Path(options["json_path"])
        if not json_path.is_file():
            self.stderr.write(self.style.ERROR(f"products.json not found at {json_path}"))
            return

        with open(json_path, encoding="utf-8") as f:
            entries = json.load(f).get("products", [])

        stats = {
            "entries": len(entries),
            "products_updated": 0,
            "products_unchanged": 0,
            "images_created": 0,
            "images_deleted": 0,
            "images_unchanged": 0,
            "variants_created": 0,
            "variants_updated": 0,
            "variants_unchanged": 0,
            "videos_linked": 0,
            "features_set": 0,
            "amazon_links_set": 0,
            "variant_groups_set": 0,
        }
        missing_products = []
        skipped_images = []
        no_sku = 0

        with transaction.atomic():
            for entry in entries:
                sku = (entry.get("sku") or "").strip()
                if not sku:
                    no_sku += 1
                    continue

                product = Product.objects.filter(sku=sku).first()
                if product is None:
                    missing_products.append((sku, entry.get("name") or ""))
                    continue

                self._sync_product(product, entry, stats, dry_run)
                self._sync_images(product, entry, stats, skipped_images, dry_run)
                self._sync_variant(product, entry, stats, dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self._report(stats, missing_products, skipped_images, no_sku, dry_run)

    # ------------------------------------------------------------------ product

    def _sync_product(self, product, entry, stats, dry_run):
        highlight = (entry.get("highlight") or "")[:300]
        video = (entry.get("video") or "").strip()
        features = entry.get("features") or []
        amazon = _clean_link(entry.get("amazon_link"))

        desired = {
            "name": entry.get("name") or product.name,
            "short_description": highlight,
            "overview": entry.get("description") or "",
            "highlight": highlight,
            "collection_name": entry.get("collection") or "",
            "tags": entry.get("tags") or [],
            "image_url": (entry.get("hero") or "")[:500],
            "video_url": video[:500],
            "features": features,
            "amazon_link": amazon,
            "gst_pct": _gst(entry),
            # variant_group is what makes size-swapping work on the site: the
            # JSON gives every size of one pan the same id ("vg-04"), and
            # All-Products.html / the category pages group on it.
            "variant_group": (entry.get("variant_group") or "")[:64],
            "match_tier": (entry.get("match_tier") or "")[:64],
            "specs": entry.get("specs") or {},
        }

        changed = [f for f, v in desired.items() if getattr(product, f) != v]
        if not changed:
            stats["products_unchanged"] += 1
        else:
            stats["products_updated"] += 1
            if not dry_run:
                for field, value in desired.items():
                    setattr(product, field, value)
                product.save(update_fields=list(desired))

        if video:
            stats["videos_linked"] += 1
        if features:
            stats["features_set"] += 1
        if amazon:
            stats["amazon_links_set"] += 1
        if desired["variant_group"]:
            stats["variant_groups_set"] += 1

    # ------------------------------------------------------------------- images

    def _sync_images(self, product, entry, stats, skipped_images, dry_run):
        paths, skipped = _local_paths(entry)
        for path, reason in skipped:
            skipped_images.append((product.sku, path, reason))

        existing = list(ProductImage.objects.filter(product=product).order_by("order", "id"))
        current = [(im.image.name, im.is_hero, im.order) for im in existing]
        desired = [(p, i == 0, i) for i, p in enumerate(paths)]

        if current == desired:
            stats["images_unchanged"] += len(existing)
            return

        stats["images_deleted"] += len(existing)
        stats["images_created"] += len(desired)
        if dry_run:
            return

        for im in existing:
            # delete the row only; the file lives in the site's product-photos
            # tree and is shared with the live site, so it must stay on disk.
            ProductImage.objects.filter(pk=im.pk).delete()
        for path, is_hero, order in desired:
            image = ProductImage(product=product, variant=None, is_hero=is_hero, order=order)
            image.image.name = path
            image.save()

    # ----------------------------------------------------------------- variants

    def _sync_variant(self, product, entry, stats, dry_run):
        """Each JSON entry is its own Product row (the catalogue lists every size
        separately), so a product that belongs to a variant_group gets the single
        ProductVariant describing its own size/label."""
        label = (entry.get("variant_label") or "").strip()
        if not entry.get("variant_group") or not label:
            return

        order = entry.get("variant_order") or 0
        desired = {"sku_suffix": "", "is_default": order == 0, "order": order}

        variant = ProductVariant.objects.filter(product=product, name=label).first()
        if variant is None:
            stats["variants_created"] += 1
            if not dry_run:
                ProductVariant.objects.create(product=product, name=label, **desired)
            return

        if all(getattr(variant, f) == v for f, v in desired.items()):
            stats["variants_unchanged"] += 1
        else:
            stats["variants_updated"] += 1
            if not dry_run:
                for field, value in desired.items():
                    setattr(variant, field, value)
                variant.save(update_fields=list(desired))

    # ------------------------------------------------------------------ summary

    def _report(self, stats, missing_products, skipped_images, no_sku, dry_run):
        head = "DRY RUN - nothing was written" if dry_run else "Import complete"
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{head}"))
        self.stdout.write(f"  JSON entries read      : {stats['entries']}")
        self.stdout.write(f"  Products updated       : {stats['products_updated']}")
        self.stdout.write(f"  Products already in sync: {stats['products_unchanged']}")
        self.stdout.write(f"  Images created         : {stats['images_created']}")
        self.stdout.write(f"  Images replaced/removed: {stats['images_deleted']}")
        self.stdout.write(f"  Images already in sync : {stats['images_unchanged']}")
        self.stdout.write(f"  Variants created       : {stats['variants_created']}")
        self.stdout.write(f"  Variants updated       : {stats['variants_updated']}")
        self.stdout.write(f"  Variants already in sync: {stats['variants_unchanged']}")
        self.stdout.write(f"  Videos linked          : {stats['videos_linked']}")
        self.stdout.write(f"  Feature lists set      : {stats['features_set']}")
        self.stdout.write(f"  Amazon links set       : {stats['amazon_links_set']}")
        self.stdout.write(f"  Variant groups set     : {stats['variant_groups_set']}")

        if no_sku:
            self.stdout.write(self.style.WARNING(f"  Skipped {no_sku} JSON entries with no SKU"))

        if missing_products:
            self.stdout.write(self.style.WARNING(
                f"\n  {len(missing_products)} JSON entries have no matching Product row "
                f"(not created - report only):"))
            for sku, name in missing_products[:50]:
                self.stdout.write(f"    - {sku}: {name}")
            if len(missing_products) > 50:
                self.stdout.write(f"    ... and {len(missing_products) - 50} more")

        if skipped_images:
            self.stdout.write(self.style.WARNING(
                f"\n  {len(skipped_images)} image paths skipped:"))
            for sku, path, reason in skipped_images[:50]:
                self.stdout.write(f"    - {sku}: {path} ({reason})")
            if len(skipped_images) > 50:
                self.stdout.write(f"    ... and {len(skipped_images) - 50} more")
