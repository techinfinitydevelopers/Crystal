"""Sync the database from the local product-data/products.json.

Kept as a standalone script because it predates the management command and is
what the deploy notes reference. The actual work lives in
`products.catalogue_sync`, shared with `manage.py sync_catalogue` — which can
fetch the same file over HTTP, and is the one to use against production, where
the repo root is not in the container.

    python sync_products.py
"""
import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from products.catalogue_sync import sync_catalogue  # noqa: E402  (after django.setup)

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "product-data", "products.json")


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    stats = sync_catalogue(raw["products"])

    print("Created: {created}, Updated: {updated}, Skipped (no sku): {skipped}".format(**stats))
    if stats["retired"]:
        print(
            f"Retired (in DB, no longer in products.json): {len(stats['retired'])} - "
            + ", ".join(stats["retired"])
        )
    print(f"Total products in DB: {stats['total_products']}")
    print(f"Total brands: {stats['total_brands']}, categories: {stats['total_categories']}")


if __name__ == "__main__":
    main()
