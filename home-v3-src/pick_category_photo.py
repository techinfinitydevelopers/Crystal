"""Choose the best product photograph to stand in for a category page.

The client is supplying a shot lifestyle banner per category, but there are
~35 pages and the photographs arrive a few at a time. This picks a product
photo from the catalogue so a page can carry a banner in the meantime;
compose_product_banner.py then turns it into the 5:1 band.

Matching a page to its products is not one rule. The pages filter three
different ways -- FIXED_CAT/FIXED_SUB, LOCK_CAT, and a couple that filter
nothing in the page at all -- so rather than reproduce each, the page name is
resolved against the catalogue's own category and subcategory ids, which the
file names already mirror ("Cleaning-Aid-Spin-Mops" -> cleaning-aid/spin-mops).

Choosing the photo is a measurement, not a guess. A product shot only works as
a banner if its background is a clean, even white that can be lifted away, so
candidates are scored on how uniform and bright their border is, how much of
the frame the product fills, and resolution -- in that order. A page whose best
candidate is still poor says so rather than shipping a grey box.
"""
import argparse
import io
import json
import os
import re
import statistics
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def catalogue():
    p = os.path.join(ROOT, 'product-data', 'products.json')
    return json.load(io.open(p, encoding='utf-8'))['products']


def page_slug(page):
    return os.path.splitext(os.path.basename(page))[0].lower().replace(' ', '-')


def resolve(page, prods):
    """Which products belong to this page. Returns (products, how)."""
    slug = page_slug(page)
    cats = {p.get('category') for p in prods if p.get('category')}
    subs = {p.get('subcategory') for p in prods if p.get('subcategory')}

    # Longest matching subcategory first: "cleaning-aid-spin-mops" must match
    # spin-mops, not the shorter cleaning-aid.
    for sub in sorted(subs, key=len, reverse=True):
        if slug.endswith('-' + sub) or slug == sub:
            hit = [p for p in prods if p.get('subcategory') == sub]
            if hit:
                return hit, f'subcategory={sub}'
    for cat in sorted(cats, key=len, reverse=True):
        if slug == cat or slug.startswith(cat + '-') or slug.endswith('-' + cat):
            hit = [p for p in prods if p.get('category') == cat]
            if hit:
                return hit, f'category={cat}'

    # Last resort: the words in the page name against name and collection.
    words = [w for w in re.split(r'[-_]', slug) if len(w) > 3]
    if words:
        hit = [p for p in prods
               if all(w in ((p.get('name') or '') + ' ' + (p.get('collection') or '')).lower()
                      for w in words)]
        if hit:
            return hit, 'name/collection keywords: ' + ' '.join(words)
    return [], 'no match'


def score_photo(path):
    """How usable this shot is as a banner. Returns (score, report) or None.

    A banner needs the product lifted off its background, so the border has to
    be a clean even white. Everything else is secondary.
    """
    try:
        im = Image.open(path)
        full_w, full_h = im.size
        if full_w < 500 or full_h < 500:
            return None
        # Several of these are 8000px studio masters. Every measure here is a
        # coarse statistic, so decode small: draft() lets the JPEG decoder skip
        # straight to a reduced scale, which is the difference between this
        # scan taking seconds and taking minutes.
        im.draft('RGB', (900, 900))
        im = im.convert('RGB')
        im.thumbnail((900, 900), Image.BILINEAR)
    except Exception:
        return None
    w, h = im.size
    px = im.load()

    # Sample the border: a product shot on white reads ~250 with almost no spread.
    band = max(2, min(w, h) // 60)
    edge = []
    for x in range(0, w, max(1, w // 120)):
        for y in list(range(band)) + list(range(h - band, h)):
            edge.append(sum(px[x, y]) / 3)
    for y in range(0, h, max(1, h // 120)):
        for x in list(range(band)) + list(range(w - band, w)):
            edge.append(sum(px[x, y]) / 3)
    bright = statistics.fmean(edge)
    spread = statistics.pstdev(edge)

    # How much of the frame is not background — a product filling 2% of a huge
    # canvas upscales into mush once it is placed in the band.
    thresh = max(200, bright - 18)
    step = max(1, min(w, h) // 220)
    ink = tot = 0
    for x in range(0, w, step):
        for y in range(0, h, step):
            tot += 1
            if sum(px[x, y]) / 3 < thresh:
                ink += 1
    fill = ink / tot if tot else 0

    # Is this the product, or the box it ships in? Retail packaging is the
    # cleanest white-background shot a category owns, so scoring on background
    # quality alone reliably picks the carton -- the spin-mop category chose a
    # printed box over the mop. A carton fills its own bounding box almost
    # completely; a mop, a pan, a bottle leave large gaps around themselves.
    xs = [x for x in range(0, w, step) for y in range(0, h, step)
          if sum(px[x, y]) / 3 < thresh]
    ys = [y for x in range(0, w, step) for y in range(0, h, step)
          if sum(px[x, y]) / 3 < thresh]
    boxiness = 0.0
    if xs and ys:
        bw, bh = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
        cells = (bw / step + 1) * (bh / step + 1)
        boxiness = min(1.0, ink / cells) if cells else 0.0

    clean = max(0.0, min(1.0, (bright - 214) / 38)) * max(0.0, 1.0 - spread / 26)
    size = min(1.0, (w * h) / (2400 * 2400))
    body = min(1.0, fill / 0.30)
    carton = max(0.0, (boxiness - 0.80) / 0.20)

    score = 3.0 * clean + 1.1 * body + 0.5 * size - 2.2 * carton
    return score, {'px': f'{full_w}x{full_h}', 'border': round(bright, 1),
                   'spread': round(spread, 1), 'fill': f'{fill:.0%}',
                   'clean': round(clean, 2), 'boxy': round(boxiness, 2)}


def best_for(page, prods, tried=60):
    hits, how = resolve(page, prods)
    cands = []
    for p in hits:
        for ref in [p.get('hero')] + list(p.get('gallery') or []):
            if ref and not ref.startswith('http'):
                fp = os.path.join(ROOT, ref)
                if os.path.exists(fp):
                    is_hero = 1 if ref == p.get('hero') else 0
                    cands.append((os.path.getsize(fp), fp, p.get('name', ''), is_hero))
    # Biggest files first - a proxy for the studio shots rather than thumbnails.
    # Scanning deep matters: several categories lead with a lifestyle shot on a
    # coloured set, and the clean white studio frame is a dozen candidates down.
    cands.sort(reverse=True)
    seen, best = set(), None
    for _, fp, name, is_hero in cands:
        if fp in seen:
            continue
        seen.add(fp)
        if len(seen) > tried:
            break
        s = score_photo(fp)
        if not s:
            continue
        sc = s[0] + 0.25 * is_hero      # the hero is likelier to be the product itself
        if best is None or sc > best[0]:
            best = (sc, fp, name, s[1])
    return best, how, len(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages', nargs='+')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    a = ap.parse_args()
    prods = catalogue()
    out = {}
    for page in a.pages:
        best, how, n = best_for(page, prods)
        if not best:
            if not a.json:
                print(f'{page:40} -- {how}, {n} products, NO USABLE PHOTO')
            continue
        score, fp, name, rep = best
        out[page] = fp
        if not a.json:
            mark = 'ok  ' if score >= 2.4 else 'weak'
            print(f'{mark} {page:40} {score:4.2f}  {rep["px"]:>10} '
                  f'border {rep["border"]:>5} +-{rep["spread"]:<4} fill {rep["fill"]:>4} '
                  f'boxy {rep["boxy"]:.2f}')
            print(f'       {how}, {n} products -> {os.path.relpath(fp, ROOT)}')
    if a.json:
        print(json.dumps(out, indent=1))


if __name__ == '__main__':
    sys.exit(main())
