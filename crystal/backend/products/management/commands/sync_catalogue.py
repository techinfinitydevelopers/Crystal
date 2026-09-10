"""Sync the database from the site's products.json — fetched over HTTP.

Production runs this service with Root Directory `crystal/backend`, so the repo
root (and `product-data/products.json` with it) is not in the container. The
file IS however served publicly by the website service, which makes HTTP the
one way production can sync itself — no database credentials have to leave the
Railway project for someone to run it from a laptop.

    python manage.py sync_catalogue                     # fetch from the live site
    python manage.py sync_catalogue --url https://…     # some other deployment
    python manage.py sync_catalogue --file ../../product-data/products.json

Safe to re-run: every product is matched on SKU and updated in place.
"""
import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from products.catalogue_sync import sync_catalogue

DEFAULT_URL = os.environ.get(
    "CATALOGUE_JSON_URL",
    "https://crystal-cook-production.up.railway.app/product-data/products.json",
)

# The sync deactivates anything missing from the payload, so a truncated file or
# an error page served with a 200 could retire the whole catalogue. Refuse
# anything implausibly small unless it is asked for explicitly.
MIN_PRODUCTS = 100


class Command(BaseCommand):
    help = "Update products, categories and specs from the site's products.json."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=DEFAULT_URL, help="Where to fetch products.json from.")
        parser.add_argument("--file", help="Read a local products.json instead of fetching.")
        parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds.")
        parser.add_argument(
            "--allow-small", action="store_true",
            help=f"Proceed even if the catalogue has fewer than {MIN_PRODUCTS} products.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, write nothing.")

    def handle(self, *args, **opts):
        if opts["file"]:
            source = opts["file"]
            try:
                with open(source, encoding="utf-8") as f:
                    raw = json.load(f)
            except OSError as exc:
                raise CommandError(f"could not read {source}: {exc}")
            except json.JSONDecodeError as exc:
                raise CommandError(f"{source} is not valid JSON: {exc}")
        else:
            source = opts["url"]
            self.stdout.write(f"Fetching {source}")
            try:
                with urllib.request.urlopen(source, timeout=opts["timeout"]) as resp:
                    if resp.status != 200:
                        raise CommandError(f"{source} returned HTTP {resp.status}")
                    payload = resp.read()
            except urllib.error.URLError as exc:
                raise CommandError(f"could not fetch {source}: {exc}")
            try:
                raw = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise CommandError(f"{source} did not return valid JSON: {exc}")

        items = raw.get("products") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            raise CommandError("payload has no 'products' list — wrong URL?")
        if len(items) < MIN_PRODUCTS and not opts["allow_small"]:
            raise CommandError(
                f"only {len(items)} products in the payload (expected at least {MIN_PRODUCTS}). "
                "Refusing, because the sync retires anything missing from it. "
                "Pass --allow-small if the catalogue really did shrink."
            )

        self.stdout.write(f"Read {len(items)} products from {source}")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: nothing written"))
            return

        stats = sync_catalogue(items)

        self.stdout.write(
            "Created: {created}, Updated: {updated}, Skipped (no sku): {skipped}".format(**stats)
        )
        if stats["retired"]:
            self.stdout.write(
                f"Retired (in DB, no longer in the catalogue): {len(stats['retired'])} - "
                + ", ".join(stats["retired"])
            )
        self.stdout.write(
            "Total products: {total_products}, brands: {total_brands}, categories: {total_categories}".format(**stats)
        )
        self.stdout.write(self.style.SUCCESS("Catalogue sync complete."))
