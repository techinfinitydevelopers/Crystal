"""Make each product's photographs and copy match its own Amazon listing.

    python manage.py adopt_amazon_listing --dry-run
    python manage.py adopt_amazon_listing --skus CL-921,MKA011 --i-have-a-backup
    python manage.py adopt_amazon_listing --i-have-a-backup

The client wants the site to show what the listing shows: the same frames, in
the same order, and the same wording. The listings were scraped in an earlier
pass and sit in `amazon-products/<ASIN>/` -- img-N.jpg plus an info.json with
title, bullets, description and the declared variant axes. Every one of the 309
products carrying an amazon_link already has its folder, so nothing is fetched
here and Amazon is never contacted.

WHY THE FILES ARE COPIED RATHER THAN LINKED
-------------------------------------------
The scraped frames are written into `product-photos/<SKU>/amz-N.jpg` and the
database is pointed at those. Referencing m.media-amazon.com directly would
make every product page depend on Amazon's CDN and on the listing staying up,
and the catalogue already had trouble from a handful of products doing exactly
that.

The existing studio shots are left on disk untouched. This command only
repoints ProductImage rows, so undoing it means pointing them back -- nothing
is destroyed.

WHAT IS DELIBERATELY NOT TAKEN
------------------------------
`title`. The listing titles are written for Amazon's search, not for a
catalogue -- "Crystal - CL414 Stainless Steel Utility Knife | 22.8 cm" against
the catalogue's own name -- and some are simply wrong: on variant listings
Amazon renders the parent's title on every child, so three different teak
coasters all read "Cuppo". The names stay as they are.
"""
import html
import json
import os
import re
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product, ProductImage

SCRAPE_DIR = 'amazon-products'


def asin_of(url):
    m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url or '')
    return m.group(1) if m else None


def clean(text):
    """Amazon's copy arrives HTML-escaped and padded with runs of whitespace."""
    if not text:
        return ''
    t = html.unescape(str(text))
    t = re.sub(r'\s*\n\s*', '\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return t.strip()


class Command(BaseCommand):
    help = "Point products at their Amazon listing's photographs and copy."

    def add_arguments(self, p):
        p.add_argument('--skus', default='', help='Comma-separated. Default: every linked product.')
        p.add_argument('--dry-run', action='store_true')
        p.add_argument('--i-have-a-backup', action='store_true')
        p.add_argument('--images-only', action='store_true')
        p.add_argument('--copy-only', action='store_true', help='Only the wording, not the photos.')
        p.add_argument('--limit', type=int, default=0)
        p.add_argument('--report', default='')

    def handle(self, *a, **o):
        if not o['dry_run'] and not o['i_have_a_backup']:
            raise CommandError('This repoints image rows and rewrites copy. '
                               'Use --dry-run, or --i-have-a-backup once you have one.')

        site_root = str(settings.MEDIA_ROOT)
        scrape_root = os.path.join(site_root, SCRAPE_DIR)
        if not os.path.isdir(scrape_root):
            raise CommandError(f'No {SCRAPE_DIR}/ beside the site. Nothing to adopt.')

        qs = Product.objects.filter(is_active=True).exclude(amazon_link='')
        if o['skus']:
            wanted = [s.strip().lower() for s in o['skus'].split(',') if s.strip()]
            qs = [p for p in qs if (p.sku or '').lower() in wanted]
        else:
            qs = list(qs.order_by('sku'))
        if o['limit']:
            qs = qs[:o['limit']]

        report = []
        no_folder = []
        img_written = rows_repointed = copy_changed = 0

        for product in qs:
            asin = asin_of(product.amazon_link)
            folder = os.path.join(scrape_root, asin) if asin else None
            if not asin or not os.path.isdir(folder):
                no_folder.append(product.sku or product.slug)
                continue

            frames = sorted(
                (f for f in os.listdir(folder) if re.match(r'img-\d+\.', f)),
                key=lambda f: int(re.search(r'\d+', f).group()))
            info = {}
            ip = os.path.join(folder, 'info.json')
            if os.path.exists(ip):
                try:
                    info = json.load(open(ip, encoding='utf-8'))
                except Exception:
                    pass

            entry = {'sku': product.sku, 'asin': asin, 'frames': len(frames),
                     'was_frames': product.images.count(), 'copy': {}}

            # ---- photographs ------------------------------------------------
            if frames and not o['copy_only']:
                dest_dir = os.path.join(site_root, 'product-photos', product.sku or product.slug)
                written = []
                for i, f in enumerate(frames, 1):
                    ext = os.path.splitext(f)[1].lower() or '.jpg'
                    name = f'amz-{i}{ext}'
                    rel = f"product-photos/{product.sku or product.slug}/{name}"
                    written.append(rel)
                    if not o['dry_run']:
                        os.makedirs(dest_dir, exist_ok=True)
                        shutil.copy2(os.path.join(folder, f), os.path.join(dest_dir, name))
                        img_written += 1
                entry['images'] = written

                if not o['dry_run']:
                    with transaction.atomic():
                        # Variant-scoped rows are left alone: a size's own strip
                        # is a finer distinction than the one listing can express,
                        # and Amazon shares frames across sizes anyway.
                        product.images.filter(variant__isnull=True).delete()
                        for order, rel in enumerate(written):
                            ProductImage.objects.create(
                                product=product, image=rel,
                                is_hero=(order == 0), order=order)
                            rows_repointed += 1

            # ---- wording ----------------------------------------------------
            if not o['images_only']:
                bullets = [clean(b) for b in (info.get('bullets') or []) if clean(b)]
                desc = clean(info.get('description'))
                if bullets:
                    head = bullets[0][:300]
                    if head and head != product.highlight:
                        entry['copy']['highlight'] = {'from': product.highlight[:60], 'to': head[:60]}
                        if not o['dry_run']:
                            product.highlight = head
                if desc and desc != product.overview:
                    entry['copy']['overview'] = {'chars_from': len(product.overview or ''),
                                                 'chars_to': len(desc)}
                    if not o['dry_run']:
                        product.overview = desc
                if bullets and len(bullets) > 1:
                    # The remaining bullets are the page's feature list. Amazon
                    # gives no icons, so they get the neutral one the template
                    # already falls back to.
                    feats = [['check', b[:80], ''] for b in bullets[1:6]]
                    if feats != (product.features or []):
                        entry['copy']['features'] = {'from': len(product.features or []),
                                                     'to': len(feats)}
                        if not o['dry_run']:
                            product.features = feats
                if entry['copy'] and not o['dry_run']:
                    product.save(update_fields=['highlight', 'overview', 'features'])
                if entry['copy']:
                    copy_changed += 1

            if entry.get('images') or entry['copy']:
                report.append(entry)

        for e in report[:40]:
            bits = []
            if e.get('images'):
                bits.append(f"{e['was_frames']} -> {e['frames']} frames")
            if e['copy']:
                bits.append('copy: ' + ', '.join(e['copy']))
            self.stdout.write(f"  {e['sku']:14} {e['asin']}  " + '; '.join(bits))
        if len(report) > 40:
            self.stdout.write(f"  ... and {len(report) - 40} more")
        if no_folder:
            self.stdout.write(self.style.WARNING(
                f"\n{len(no_folder)} linked products have no scraped folder: "
                f"{', '.join(no_folder[:10])}{' ...' if len(no_folder) > 10 else ''}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(report)} products adopted their listing: "
            f"{img_written} image files written, {rows_repointed} rows repointed, "
            f"{copy_changed} had their wording updated."))
        if o['dry_run']:
            self.stdout.write('Dry run - nothing written.')
        if o['report']:
            json.dump(report, open(o['report'], 'w', encoding='utf-8'), indent=1)
            self.stdout.write(f"Wrote {o['report']}")
