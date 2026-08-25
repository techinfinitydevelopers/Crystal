"""
Export the WHOLE product catalogue from the dashboard database back into
product-data/products.json - the file the separate static Railway site reads
at runtime (it cannot reach this Django service's database).

This is the true counterpart of import_from_json: after a client edits
products in the dashboard, run this to regenerate the JSON the live site
serves. The per-entry mapping is NOT duplicated here - it calls
products.serializers.site_product_entries, the same "site catalogue shape"
layer /api/products/site.json/ uses, so the API and the file can never drift.

Ordering: existing SKUs keep the current file's order; products not yet in
the file are appended after, in DB order. Top-level metadata keys
(source_xlsx, sheets_included, ...) are carried over from the current file;
generated_at is refreshed on write.

The write is atomic: a temp file in the same directory is written first and
then os.replace()d over the target, so the live file is never half-written.

Usage:
    python manage.py export_to_json --check          # diff against file, write nothing
    python manage.py export_to_json --out PATH       # write elsewhere
    python manage.py export_to_json                  # regenerate product-data/products.json
"""
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import Product
from products.serializers import site_product_entries

SITE_ROOT = Path(settings.BASE_DIR).resolve().parent.parent
JSON_PATH = SITE_ROOT / "product-data" / "products.json"

# Stable key order inside each entry, matching the current hand-curated file,
# so diffs of the written file stay readable. Unknown keys sort after these.
KEY_ORDER = [
    "sku", "name", "brand", "category", "subcategory", "collection",
    "highlight", "description", "tags", "gst_pct", "mrp", "amazon_link",
    "filters", "hero", "gallery", "match_tier", "id",
    "variant_group", "variant_label", "variant_order",
    "video", "features", "specs",
]
_KEY_RANK = {k: i for i, k in enumerate(KEY_ORDER)}

# amazon_link placeholders the JSON historically used for "no link". The DB
# stores "" for all of them (import_from_json cleans them), and the export
# emits null - the value the file itself uses for the other 200+ link-less
# products. These placeholder spellings are a known, acceptable diff: --check
# reports them separately instead of letting them fail the round-trip.
NO_LINK_PLACEHOLDERS = {"", "no", "none", "n/a", "-"}

_MISSING = object()


def _ordered(entry):
    return dict(sorted(entry.items(), key=lambda kv: _KEY_RANK.get(kv[0], len(KEY_ORDER))))


def _is_placeholder_link_diff(old, new):
    """True when the only difference is a "no link" placeholder spelling."""
    old_blank = old is None or (isinstance(old, str) and old.strip().lower() in NO_LINK_PLACEHOLDERS)
    new_blank = new is None or (isinstance(new, str) and new.strip().lower() in NO_LINK_PLACEHOLDERS)
    return old_blank and new_blank


class Command(BaseCommand):
    help = "Regenerate product-data/products.json from the dashboard database (counterpart of import_from_json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check", action="store_true",
            help="Write nothing; diff the would-be export against the current file.",
        )
        parser.add_argument(
            "--out", default=str(JSON_PATH),
            help="Where to write the JSON (default: product-data/products.json).",
        )

    # ------------------------------------------------------------------ build

    def _build_entries(self):
        """DB -> list of site-shape entries, via the shared serializer layer."""
        products = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category__parent")
            .prefetch_related(
                "specifications", "images", "variants",
                "marketplace_links__marketplace",
            )
            .order_by("id")
        )
        entries = []
        for product in products:
            entries.extend(_ordered(e) for e in site_product_entries(product))
        return entries, products.count()

    # ------------------------------------------------------------------ handle

    def handle(self, *args, **options):
        out_path = Path(options["out"])

        current, meta = [], {}
        if JSON_PATH.is_file():
            with open(JSON_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            current = raw.get("products", [])
            meta = {k: v for k, v in raw.items() if k != "products"}

        built, product_count = self._build_entries()
        built_by_sku = {e["sku"]: e for e in built}
        current_by_sku = {e.get("sku"): e for e in current}

        # keep the current file's SKU order; append new SKUs after, in DB order
        file_order = [s for s in current_by_sku if s in built_by_sku]
        new_skus = [e["sku"] for e in built if e["sku"] not in current_by_sku]
        missing_skus = [s for s in current_by_sku if s not in built_by_sku]
        ordered_entries = [built_by_sku[s] for s in file_order + new_skus]

        if options["check"]:
            self._check(current_by_sku, built_by_sku, new_skus, missing_skus)
            return

        payload = dict(meta)
        payload["generated_at"] = timezone.now().isoformat()
        payload["products"] = ordered_entries

        out_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=out_path.parent, prefix=out_path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_name, out_path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(ordered_entries)} entries ({product_count} products) to {out_path} "
            f"| new since file: {len(new_skus)} | in file but missing from DB export: {len(missing_skus)}"
        ))
        if missing_skus:
            self.stdout.write(self.style.WARNING(
                "  Missing SKUs (were in the file, not exported - inactive or deleted in DB): "
                + ", ".join(missing_skus[:20])
                + (" ..." if len(missing_skus) > 20 else "")
            ))

    # ------------------------------------------------------------------- check

    def _check(self, current_by_sku, built_by_sku, new_skus, missing_skus):
        differing = []           # (sku, [keys]) with real diffs
        placeholder_only = []    # (sku, old, new) amazon_link placeholder-only diffs
        key_counter = Counter()

        for sku, old in current_by_sku.items():
            new = built_by_sku.get(sku)
            if new is None:
                continue
            keys = []
            for key in sorted(set(old) | set(new)):
                ov, nv = old.get(key, _MISSING), new.get(key, _MISSING)
                if ov == nv:
                    continue
                if key == "amazon_link" and _is_placeholder_link_diff(
                        None if ov is _MISSING else ov,
                        None if nv is _MISSING else nv):
                    placeholder_only.append((sku, ov, nv))
                    continue
                keys.append(key)
            if keys:
                differing.append((sku, keys))
                key_counter.update(keys)

        self.stdout.write(self.style.MIGRATE_HEADING("\nCHECK - nothing written"))
        self.stdout.write(f"  Entries in file        : {len(current_by_sku)}")
        self.stdout.write(f"  Entries from DB        : {len(built_by_sku)}")
        self.stdout.write(f"  New in DB, not in file : {len(new_skus)}")
        self.stdout.write(f"  In file, missing in DB : {len(missing_skus)}")
        self.stdout.write(f"  Products with real diffs: {len(differing)}")
        self.stdout.write(
            f"  amazon_link placeholder-only diffs (known/acceptable): {len(placeholder_only)}")

        if key_counter:
            self.stdout.write("\n  Differing keys (real diffs):")
            for key, count in key_counter.most_common():
                self.stdout.write(f"    {key}: {count} products")
        if differing:
            self.stdout.write("\n  Products with real diffs:")
            for sku, keys in differing[:50]:
                self.stdout.write(f"    - {sku}: {', '.join(keys)}")
            if len(differing) > 50:
                self.stdout.write(f"    ... and {len(differing) - 50} more")
        if placeholder_only:
            self.stdout.write("\n  amazon_link placeholder-only (file value -> export value):")
            for sku, ov, nv in placeholder_only:
                self.stdout.write(f"    - {sku}: {ov!r} -> {nv!r}")
        if new_skus:
            self.stdout.write("\n  New SKUs: " + ", ".join(new_skus[:20])
                              + (" ..." if len(new_skus) > 20 else ""))
        if missing_skus:
            self.stdout.write("\n  Missing SKUs: " + ", ".join(missing_skus[:20])
                              + (" ..." if len(missing_skus) > 20 else ""))
