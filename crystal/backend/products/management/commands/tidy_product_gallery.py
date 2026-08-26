"""Clean up the two gallery faults the client listed against 42 product pages.

    python manage.py tidy_product_gallery --dry-run
    python manage.py tidy_product_gallery --ids mka914,cl-459 --i-have-a-backup
    python manage.py tidy_product_gallery --all --i-have-a-backup

WHAT THE CLIENT REPORTED, AND WHAT IS ACTUALLY WRONG
----------------------------------------------------
"Double product" / "Double Images". The gallery shows the same photograph more
than once. It is not the same file listed twice -- an md5 over every frame finds
nothing -- it is the same picture ingested repeatedly at different sizes, so
each copy is a different file. MKA914 carries five such repeats in thirteen
frames; CC-848 has the same shot at 1080px and again at 500px. A difference
hash finds them, and a live pixel comparison confirmed it: the pairs flagged
here differ by 2-6 out of 255 per channel, while two genuinely different frames
of the same product differ by 37.

"Please put the product white product first". The frame on show is a lifestyle
shot or a printed infographic, and the plain white studio photograph -- the one
a customer wants to see -- is buried further down the strip. MKA-413 opens on a
frame whose border reads 21 out of 255, nearly black, with the white shot lying
ninth.

Falling out of the first fault: the hero is sometimes the SMALLEST copy of a
picture that also exists at full size. MKA914 opened on a 569px frame while the
identical photograph sat in the gallery at 1500px. That is why some product
pages looked soft.

WHAT THIS DOES
--------------
Per product: group the frames that look alike, keep the largest of each group
and drop the rest, then make sure the frame on show is the plain white studio
one -- preferring the largest when several qualify.

Only ProductImage rows are removed. The photographs themselves are the
website's own files under product-photos/ and are never touched, so a frame
dropped here can be put back by pointing a row at the same path again. Run with
--dry-run first; it prints exactly what would go.
"""
import json
import os
import statistics
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product, ProductImage

try:
    from PIL import Image, ImageFilter
except ImportError:                                   # pragma: no cover
    Image = ImageFilter = None

# Out of 256 bits. Chosen against this catalogue: the pairs the client called
# duplicates score 0-12, two genuinely different frames of one product score 30+.
LOOKALIKE = 12
# A white studio frame has a bright, even border. Lifestyle shots and printed
# infographics do not. Score = mean brightness - 2 x spread.
WHITE_MARGIN = 60


def _abs(name):
    """Where a ProductImage actually lives.

    These names are the website's own relative paths, so they resolve against
    MEDIA_ROOT, which is pointed at the site root.
    """
    if not name:
        return None
    p = os.path.join(str(settings.MEDIA_ROOT), name.replace('/', os.sep))
    return p if os.path.exists(p) else None


def dhash(path, size=16):
    im = Image.open(path)
    im.draft('L', (size * 4, size * 4))
    im = im.convert('L').resize((size + 1, size), Image.LANCZOS)
    px = im.load()
    bits = 0
    for y in range(size):
        for x in range(size):
            bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
    return bits


def whiteness(path):
    """How much this frame looks like the PRODUCT on a plain white sweep.

    A bright even border is not enough on its own, and getting that wrong makes
    the fix worse than the fault: a printed infographic is also shot on white,
    so scoring the border alone promoted MKA914's spec panel over the actual
    juicer. What separates them is the middle of the frame -- a panel is full of
    text, a product shot is mostly empty sweep around one object.

    Measured on this catalogue: plain product frames score 8-13 of interior
    edge energy, infographics 22-30, with both sitting on a 255 border.
    """
    im = Image.open(path)
    im.draft('L', (400, 400))
    im = im.convert('L')
    im.thumbnail((400, 400))
    w, h = im.size
    px = im.load()
    b = max(2, min(w, h) // 20)
    edge = [px[x, y] for x in range(0, w, 3) for y in list(range(b)) + list(range(h - b, h))]
    edge += [px[x, y] for y in range(0, h, 3) for x in list(range(b)) + list(range(w - b, w))]

    ep = im.filter(ImageFilter.FIND_EDGES).load()
    interior = statistics.fmean(
        ep[x, y] for x in range(w // 8, w * 7 // 8, 2) for y in range(h // 8, h * 7 // 8, 2))

    return statistics.fmean(edge) - 2 * statistics.pstdev(edge) - 3 * interior


def pixels(path):
    try:
        with Image.open(path) as im:
            return im.size[0] * im.size[1], im.size
    except Exception:
        return 0, (0, 0)


class Command(BaseCommand):
    help = 'Drop repeated gallery frames and show the plain white studio shot first.'

    def add_arguments(self, p):
        p.add_argument('--ids', default='',
                       help='Comma-separated product ids or SKUs. Default: the 42 the client listed.')
        p.add_argument('--all', action='store_true',
                       help='Every active product, not just the reported ones.')
        p.add_argument('--dry-run', action='store_true')
        p.add_argument('--i-have-a-backup', action='store_true',
                       help='Required to write. Rows are deleted; the image files are not.')
        p.add_argument('--no-dedupe', action='store_true')
        p.add_argument('--no-hero', action='store_true')
        p.add_argument('--report', default='', help='Write a JSON record of every change here.')

    # -- the 42 pages on the client's sheet -------------------------------
    REPORTED = """cns794 cns989 cl-459n cl-215 cl-216 cl-024 cl-459 mka-010 mka-258 mka083
        mka011 mka-012 mka023 mka075 clmk-011 clmk-012 mka-094n mka-095 mka902a mka914
        mka916a mka930 mka933 mka942 mka943 clmk-018 clmk-019 clmk-021 clmk-022 mka-231
        mka-411 mka-412 mka-413 mka-414 mka-415 mka-416 cc-841 cc-847 cc-848 cc-982
        ccs-001 wf001""".split()

    def handle(self, *a, **o):
        if Image is None:
            raise CommandError('Pillow is required.')
        if not o['dry_run'] and not o['i_have_a_backup']:
            raise CommandError('This deletes ProductImage rows. Re-run with --dry-run, '
                               'or with --i-have-a-backup once you have one.')

        if o['all']:
            qs = Product.objects.filter(is_active=True)
        else:
            wanted = [s.strip() for s in (o['ids'] or ','.join(self.REPORTED)).split(',') if s.strip()]
            qs = Product.objects.filter(is_active=True)
            found, missing = [], []
            for w in wanted:
                p = (qs.filter(sku__iexact=w).first()
                     or qs.filter(slug__iexact=w).first()
                     or qs.filter(sku__iexact=w.replace('-', '')).first()
                     or qs.filter(sku__iexact=w.replace('-', '', 1)).first())
                if p:
                    found.append(p.pk)
                else:
                    missing.append(w)
            if missing:
                self.stdout.write(self.style.WARNING(
                    f'  not in the catalogue, skipped: {", ".join(missing)}'))
            qs = Product.objects.filter(pk__in=found)

        report = []
        dropped_total = hero_moved = 0
        for product in qs.prefetch_related('images').order_by('sku'):
            # Variants own their own strips; treat each scope separately or a
            # 16 cm frame can be judged against the 22 cm one.
            scopes = defaultdict(list)
            for im in product.images.all():
                scopes[im.variant_id].append(im)

            for variant_id, images in scopes.items():
                if len(images) < 2:
                    continue
                usable = [(im, _abs(im.image.name)) for im in images]
                usable = [(im, p) for im, p in usable if p]
                if len(usable) < 2:
                    continue

                vlabel = ''
                if variant_id:
                    v = next((x for x in product.variants.all() if x.pk == variant_id), None)
                    vlabel = v.name if v else str(variant_id)
                entry = {'sku': product.sku, 'name': product.name,
                         'variant': variant_id, 'variant_label': vlabel,
                         'dropped': [], 'hero': None}

                keep = list(usable)
                if not o['no_dedupe']:
                    hashes = {}
                    for im, path in usable:
                        try:
                            hashes[im.pk] = dhash(path)
                        except Exception:
                            pass
                    groups, seen = [], set()
                    for i, (im, path) in enumerate(usable):
                        if im.pk in seen or im.pk not in hashes:
                            continue
                        grp = [(im, path)]
                        for jm, jpath in usable[i + 1:]:
                            if jm.pk in seen or jm.pk not in hashes:
                                continue
                            if bin(hashes[im.pk] ^ hashes[jm.pk]).count('1') <= LOOKALIKE:
                                grp.append((jm, jpath))
                                seen.add(jm.pk)
                        if len(grp) > 1:
                            groups.append(grp)
                    for grp in groups:
                        # Keep the biggest copy; it is the one worth showing.
                        grp.sort(key=lambda t: pixels(t[1])[0], reverse=True)
                        winner = grp[0]
                        for loser, lpath in grp[1:]:
                            entry['dropped'].append({
                                'file': loser.image.name,
                                'kept_instead': winner[0].image.name,
                                'was': f'{pixels(lpath)[1][0]}x{pixels(lpath)[1][1]}',
                                'kept_is': f'{pixels(winner[1])[1][0]}x{pixels(winner[1])[1][1]}',
                                'was_hero': loser.is_hero,
                            })
                            keep = [k for k in keep if k[0].pk != loser.pk]

                if not o['no_hero'] and keep:
                    scores = []
                    for im, path in keep:
                        try:
                            scores.append((whiteness(path), pixels(path)[0], im, path))
                        except Exception:
                            pass
                    if scores:
                        best = max(scores, key=lambda t: (t[0], t[1]))
                        current = next((s for s in scores if s[2].is_hero), None)
                        # Only move it when the difference is decisive, so a
                        # deliberate hero is not overruled by a hairline.
                        if current is None or (best[0] - current[0]) > WHITE_MARGIN:
                            if current is None or best[2].pk != current[2].pk:
                                entry['hero'] = {
                                    'from': current[2].image.name if current else None,
                                    'to': best[2].image.name,
                                    'border_score_from': round(current[0], 1) if current else None,
                                    'border_score_to': round(best[0], 1),
                                }

                if entry['dropped'] or entry['hero']:
                    report.append(entry)
                    dropped_total += len(entry['dropped'])
                    hero_moved += 1 if entry['hero'] else 0

                    if not o['dry_run']:
                        with transaction.atomic():
                            names = [d['file'] for d in entry['dropped']]
                            if names:
                                ProductImage.objects.filter(
                                    pk__in=[im.pk for im, _ in usable
                                            if im.image.name in names]).delete()
                            if entry['hero']:
                                ProductImage.objects.filter(
                                    product=product, variant_id=variant_id
                                ).update(is_hero=False)
                                ProductImage.objects.filter(
                                    product=product, variant_id=variant_id,
                                    image=entry['hero']['to']).update(is_hero=True)

        for e in report:
            self.stdout.write(f"\n{e['sku']}  {e['name'][:48]}")
            for d in e['dropped']:
                flag = '  (was the one on show)' if d['was_hero'] else ''
                self.stdout.write(
                    f"   drop {os.path.basename(d['file']):12} {d['was']:>11}  "
                    f"same picture as {os.path.basename(d['kept_instead'])} {d['kept_is']}{flag}")
            if e['hero']:
                h = e['hero']
                self.stdout.write(
                    f"   show {os.path.basename(h['to'])} instead of "
                    f"{os.path.basename(h['from'] or '-')}  "
                    f"(border {h['border_score_from']} -> {h['border_score_to']})")

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(report)} product/variant strips changed: "
            f"{dropped_total} repeated frames dropped, {hero_moved} heroes moved."))
        if o['dry_run']:
            self.stdout.write('Dry run - nothing written.')
        if o['report']:
            json.dump(report, open(o['report'], 'w', encoding='utf-8'), indent=1)
            self.stdout.write(f"Wrote {o['report']}")
