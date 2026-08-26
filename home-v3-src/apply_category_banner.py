"""Give a category page a banner hero.

    python home-v3-src/apply_category_banner.py Cookware-Non-Stick.html path/to/photo.png

Does the whole job for one page: encodes the photograph, works out where to
crop it, writes the CSS and the markup, and measures whether the text is still
readable on top of it.

Re-running is safe. A page that already has a banner keeps its markup and just
takes the new picture and the new crop.

WHY THE CROP IS COMPUTED RATHER THAN CENTRED
--------------------------------------------
These banners are around 5:1. The hero is around 2.5:1, so cover-cropping
throws away about half the width -- on a 1980px photograph only ~987px are
ever on screen. Which half you keep decides whether the product is whole or
sliced down the middle, and whether the copy sits on empty counter or on top
of a pan.

So the picture is measured: per-column brightness and edge energy say where
the subject is and where the photographer left space. Candidate crops are
scored on four things and the best one wins:

  * the copy must land somewhere quiet and bright
  * the crop edges must not cut through a busy area (that is what a bisected
    pan looks like numerically)
  * as much of the subject as possible should be inside the window
  * mild preference for keeping the subject off the copy

Pass --focus to overrule it; the automatic value is a starting point, not a
verdict on composition.
"""
import argparse
import io
import os
import re
import statistics
import sys

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, 'category-banners')

# The reference desktop frame the crop is reasoned about. It is the measured
# hero box at a 1280px viewport; every other width is a scale of it.
BOX_W, BOX_H = 1265, 500
COPY_L, COPY_R = 76, 540          # measured copy column inside that box
# The narrow layout crops to 2:1 and carries no text, so it is scored only on
# where the subject is.
M_BOX_W, M_BOX_H = 390, 195

MARK = 'BANNER HERO'


# --------------------------------------------------------------------------
# measuring the photograph
# --------------------------------------------------------------------------

def profile(im, bands=200):
    """Per-column brightness and edge energy, as two lists of `bands` values."""
    g = im.convert('L')
    e = g.filter(ImageFilter.FIND_EDGES)
    gp, ep = g.load(), e.load()
    W, H = im.size
    step_y = max(1, H // 90)
    bright, detail = [], []
    for i in range(bands):
        x0, x1 = W * i // bands, max(W * i // bands + 1, W * (i + 1) // bands)
        step_x = max(1, (x1 - x0) // 4)
        px = [(x, y) for x in range(x0, x1, step_x) for y in range(0, H, step_y)]
        bright.append(statistics.fmean(gp[x, y] for x, y in px))
        detail.append(statistics.fmean(ep[x, y] for x, y in px))
    return bright, detail


def _slice(vals, lo, hi):
    """Mean of a per-column list over a fractional span of the image width."""
    n = len(vals)
    a, b = max(0, int(lo * n)), min(n, max(int(lo * n) + 1, int(hi * n)))
    return statistics.fmean(vals[a:b])


def geometry(nw, nh, box_w, box_h, focus):
    """Where a cover-crop at this focus lands, in source pixels."""
    sc = max(box_w / nw, box_h / nh)
    overflow = nw * sc - box_w
    left = (overflow * focus) / sc
    return sc, left, left + box_w / sc


def pick_focus(bright, detail, nw, nh, box_w, box_h, with_copy):
    """Score candidate crops and return the best focus, plus its report."""
    total = sum(detail)
    hi = max(detail)
    lo = min(bright)
    span = (max(bright) - lo) or 1.0
    best, rows = None, []

    f = 0.00
    while f <= 1.0001:
        sc, x0, x1 = geometry(nw, nh, box_w, box_h, f)
        a, b = x0 / nw, x1 / nw

        # How much of the subject we keep.
        n = len(detail)
        i0, i1 = int(a * n), max(int(a * n) + 1, int(b * n))
        coverage = sum(detail[i0:i1]) / total if total else 0.0

        # Cutting through a busy area is what a sliced pan looks like. Sample a
        # thin strip just inside each edge.
        strip = (b - a) * 0.06
        cut = max(_slice(detail, a, a + strip), _slice(detail, max(0.0, b - strip), b)) / (hi or 1)

        if with_copy:
            ca, cb = a + (COPY_L / sc) / nw, a + (COPY_R / sc) / nw
            quiet = 1.0 - _slice(detail, ca, min(cb, 1.0)) / (hi or 1)
            light = (_slice(bright, ca, min(cb, 1.0)) - lo) / span
            # Coverage dominates on purpose. An early weighting favoured a quiet
            # copy area and picked a crop holding 25% of the subject -- a
            # beautifully readable photograph of an empty worktop. The scrim
            # already guarantees the text, so quietness is a tie-breaker, not a
            # goal; showing the product whole is the goal.
            score = 2.40 * coverage - 1.50 * cut + 0.45 * quiet + 0.20 * light
        else:
            score = 1.60 * coverage - 1.30 * cut

        rows.append((f, score, coverage, cut))
        if best is None or score > best[1]:
            best = (f, score, coverage, cut)
        f += 0.01

    return best, rows


# --------------------------------------------------------------------------
# contrast, measured through the real gradients
# --------------------------------------------------------------------------

HORZ = [(0, 1.0), (.32, .972), (.45, .885), (.63, .34), (.78, 0), (1, 0)]
VERT = [(0, 1.0), (.14, .90), (.23, .46), (.37, 0), (.78, 0), (1, 1.0)]


def _ramp(stops, t):
    for (a, av), (b, bv) in zip(stops, stops[1:]):
        if a <= t <= b:
            return av + (bv - av) * ((t - a) / (b - a) if b > a else 0)
    return stops[-1][1]


def _lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def contrast_report(im, focus):
    """Composite the scrims exactly as the browser will, then find the worst
    pixel under each piece of text. Guessing here is how unreadable heroes ship."""
    nw, nh = im.size
    sc = max(BOX_W / nw, BOX_H / nh)
    sw, sh = nw * sc, nh * sc
    ox, oy = (sw - BOX_W) * focus, (sh - BOX_H) * 0.5
    crop = im.resize((int(round(sw)), int(round(sh))), Image.LANCZOS).crop(
        (int(ox), int(oy), int(ox) + BOX_W, int(oy) + BOX_H))
    px = crop.load()
    for x in range(BOX_W):
        ah = _ramp(HORZ, x / BOX_W)
        for y in range(BOX_H):
            a = 1 - (1 - ah) * (1 - _ramp(VERT, y / BOX_H))
            r, g, b = px[x, y]
            px[x, y] = tuple(int(round(c * (1 - a) + 255 * a)) for c in (r, g, b))

    def worst(x0, x1, y0, y1, fg):
        return min(_ratio(fg, px[x, y])
                   for x in range(x0, x1, 3) for y in range(y0, y1, 2))

    return crop, [
        ('nav links', '#1A1A1A', worst(0, BOX_W, 32, 96, (0x1A, 0x1A, 0x1A)), 3.0),
        ('headline', '#1A1A1A', worst(COPY_L, COPY_R, 150, 250, (0x1A, 0x1A, 0x1A)), 3.0),
        ('body copy', '#5F5F5F', worst(COPY_L, COPY_R, 123, 423, (0x5F, 0x5F, 0x5F)), 4.5),
        ('eyebrow', '#ED3338', worst(COPY_L, 300, 118, 140, (0xED, 0x33, 0x38)), 3.0),
    ]


# --------------------------------------------------------------------------
# the CSS and the markup
# --------------------------------------------------------------------------

def css_block(focus, mobile_focus):
    return '''
  /* ===== BANNER HERO =====
     The category banner is a very wide, short photograph (roughly 5:1). Two
     things follow from that shape.

     It cannot be a full-height hero background: cover-cropping 5:1 into a
     92svh box magnifies it about three and a half times, so you get a blurry
     slab of one pan. So the hero comes down to a band the photo can fill.

     And it cannot be a plain strip under the nav either -- at 5:1 a 1280px
     screen gets ~250px, most of it hidden behind the transparent header, and
     it reads as an advert someone left at the top. So the photo IS the hero,
     with the copy sitting inside it.

     These banners are shot with the product to one side and empty counter to
     the other, which is where the text goes. The scrim does not depend on
     that holding true -- it fades to solid white behind the copy, so the text
     stays readable whatever the photo does at that crop.

     --banner-focus is the one knob per page: it slides the crop window along
     the photograph so the product stays whole while the quiet side lands
     under the copy. apply_category_banner.py measures it; override it here if
     you disagree with what it chose. */
  .hero.hero-banner { --banner-focus: %(focus)d%%; min-height: clamp(430px, 60svh, 600px); justify-content: center; align-items: stretch; text-align: left; padding-top: clamp(120px, 15vh, 156px); padding-bottom: clamp(34px, 5vh, 58px); }
  /* The red glow belongs to the photo-less hero; over a photograph it muddies
     the image without adding anything. */
  .hero.hero-banner::before { display: none; }

  .hero-media { position: absolute; inset: 0; z-index: 0; overflow: hidden; }
  .hero-media picture { display: contents; }
  .hero-media img { width: 100%%; height: 100%%; object-fit: cover; object-position: var(--banner-focus, 74%%) center; display: block; }
  /* Two washes. Left-to-right for the copy; and top-to-bottom because the
     header is fixed, transparent and dark-texted (#1A1A1A), so it now hangs
     over the photograph -- without the top band its links sit on whatever the
     picture happens to put there. The foot fades so the band resolves into
     the page instead of ending on a hard line. */
  .hero-media::after { content: ""; position: absolute; inset: 0; background:
      linear-gradient(94deg, #fff 0%%, rgba(255,255,255,0.972) 32%%, rgba(255,255,255,0.885) 45%%, rgba(255,255,255,0.34) 63%%, rgba(255,255,255,0) 78%%),
      linear-gradient(to bottom, #fff 0%%, rgba(255,255,255,0.90) 14%%, rgba(255,255,255,0.46) 23%%, rgba(255,255,255,0) 37%%, rgba(255,255,255,0) 78%%, #fff 100%%); }

  .hero-banner .wrap { position: relative; z-index: 4; display: flex; align-items: center; }
  .hero-banner .hero-copy { max-width: 46ch; }
  .hero-banner .pre { margin-bottom: clamp(12px, 1.8vw, 20px); }
  .hero-banner h1 { margin: 0; max-width: 14ch; }
  .hero-banner .hero-sub { margin: clamp(16px, 2vw, 22px) 0 clamp(20px, 2.6vw, 28px); max-width: 46ch; }
  .hero-banner .hero-cta { justify-content: flex-start; }
  .hero-banner .scroll-hint { left: auto; right: clamp(20px, 4vw, 54px); transform: none; }

  /* Under about 860px the photo has no empty side left to write on -- the crop
     is too tight for the copy to sit over it without covering the product. So
     it stops being a backdrop and becomes a picture above the words. */
  @media (max-width: 860px) {
    /* The header occupies 32-96px. Stacked, the photo would start under it
       with no wash to keep the links legible, so it starts below it. */
    .hero.hero-banner { display: flex; flex-direction: column; justify-content: flex-start; min-height: 0; padding-top: 104px; padding-bottom: clamp(30px, 6vw, 44px); text-align: center; }
    /* 2:1, not the photo's own 5:1 -- a full-width 5:1 strip is only ~77px tall
       on a phone, too thin to read as a photograph. */
    .hero-media { position: relative; inset: auto; width: 100%%; aspect-ratio: 2/1; max-height: 42svh; }
    .hero-media img { object-position: %(mfocus)d%% center; }
    /* Only a hairline fade at the foot. The generous bottom wash the desktop
       band uses would swallow the subject here, because this band is a third
       of the height and the subject sits in its lower half. */
    .hero-media::after { background: linear-gradient(to bottom, rgba(255,255,255,0) 88%%, #fff 100%%); }
    /* No tucking the copy up under the photo: the foot fade is a hairline
       here, so an overlapping eyebrow lands on bare picture. */
    .hero-banner .wrap { justify-content: center; margin-top: clamp(22px, 5vw, 34px); }
    .hero-banner .hero-copy { max-width: none; }
    .hero-banner h1 { max-width: none; margin-inline: auto; }
    .hero-banner .hero-sub { margin-inline: auto; }
    .hero-banner .hero-cta { justify-content: center; }
    .hero-banner .scroll-hint { display: none; }
  }
''' % {'focus': round(focus * 100), 'mfocus': round(mobile_focus * 100)}


# Matches the page's original hero and one this script has already converted,
# so a re-run recognises its own work instead of reporting the hero missing.
HERO_RE = re.compile(r'<section class="hero(?: hero-banner)?" id="hero">(.*?)</section>', re.S)


def rewrite_hero(page_src, slug):
    """Wrap the existing hero copy in the banner shell, keeping this page's own
    eyebrow, title, subtitle and buttons exactly as they are."""
    m = HERO_RE.search(page_src)
    if not m:
        return None, 'no <section class="hero" id="hero"> on this page'
    body = m.group(1)
    if 'hero-media' in body:
        return None, 'already a banner hero'

    # The scroll hint lives outside .wrap and stays outside it.
    hint = ''
    hm = re.search(r'\s*<div class="scroll-hint">.*?</div>\s*$', body, re.S)
    if hm:
        hint = hm.group(0).rstrip()
        body = body[:hm.start()]

    wm = re.search(r'<div class="wrap">(.*?)</div>\s*$', body, re.S)
    if not wm:
        return None, 'hero has no <div class="wrap"> to lift the copy out of'
    inner = wm.group(1).strip('\n').rstrip()
    inner = '\n'.join(('  ' + ln if ln.strip() else ln) for ln in inner.split('\n'))

    shell = (
        '<section class="hero hero-banner" id="hero">\n'
        '  <!-- Decorative: the copy beside it already says what this page is, so the\n'
        '       photo carries no alt text a screen reader would have to sit through. -->\n'
        '  <div class="hero-media" aria-hidden="true">\n'
        '    <picture>\n'
        f'      <source srcset="category-banners/{slug}.webp" type="image/webp">\n'
        f'      <img src="category-banners/{slug}.jpg" alt="" fetchpriority="high" decoding="async">\n'
        '    </picture>\n'
        '  </div>\n'
        '  <div class="wrap">\n'
        '    <div class="hero-copy">\n'
        f'{inner}\n'
        '    </div>\n'
        '  </div>\n'
        f'{hint}\n'
        '</section>'
    )
    return page_src[:m.start()] + shell + page_src[m.end():], None


def install_css(src, block):
    if MARK in src:                      # refresh the focus values in place
        src = re.sub(r'(\.hero\.hero-banner \{ --banner-focus: )\d+(%)',
                     lambda mm: mm.group(1) + re.search(r'--banner-focus: (\d+)%', block).group(1) + mm.group(2),
                     src, count=1)
        src = re.sub(r'(\.hero-media img \{ object-position: )\d+(% center)',
                     lambda mm: mm.group(1) + re.search(r'object-position: (\d+)% center', block).group(1) + mm.group(2),
                     src, count=1)
        return src, 'refreshed'
    anchor = '  /* ===== CATEGORY NAV ===== */'
    if anchor in src:
        return src.replace(anchor, block.rstrip() + '\n\n' + anchor, 1), 'inserted'
    i = src.rfind('</style>')
    if i == -1:
        raise SystemExit('page has no </style> to insert into')
    return src[:i] + block.rstrip() + '\n' + src[i:], 'appended'


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('page', help='e.g. Cookware-Non-Stick.html')
    ap.add_argument('image', help='the banner photograph')
    ap.add_argument('--focus', type=float, default=None,
                    help='override the computed desktop crop, as a percentage')
    ap.add_argument('--mobile-focus', type=float, default=None)
    ap.add_argument('--slug', default=None, help='asset name; defaults from the page name')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--render', default=None,
                    help='write a PNG of the finished hero band here, to eyeball the crop')
    a = ap.parse_args()

    page = os.path.join(ROOT, a.page)
    if not os.path.exists(page):
        raise SystemExit(f'no such page: {a.page}')
    if not os.path.exists(a.image):
        raise SystemExit(f'no such image: {a.image}')

    slug = a.slug or os.path.splitext(os.path.basename(a.page))[0].lower().replace(' ', '-')
    im = Image.open(a.image).convert('RGB')
    nw, nh = im.size
    print(f'{a.page}  <-  {os.path.basename(a.image)}  {nw}x{nh} ({nw/nh:.2f}:1)')
    if nw / nh < 3.0:
        print(f'  ! this is {nw/nh:.2f}:1, not a ~5:1 banner. The hero will crop it hard.')
    if nh < 380:
        print(f'  ! only {nh}px tall; it will be upscaled ~{BOX_H/nh:.2f}x in the hero.')

    bright, detail = profile(im)

    if a.focus is None:
        best, _ = pick_focus(bright, detail, nw, nh, BOX_W, BOX_H, with_copy=True)
        focus = best[0]
        print(f'  desktop crop {focus:.0%}  (keeps {best[2]:.0%} of the subject, '
              f'edge business {best[3]:.2f})')
        if best[2] < 0.50:
            print('  ! no crop holds even half the subject. This photograph is '
                  'probably too wide, or its subject too spread out, for this hero.')
    else:
        focus = a.focus / 100.0
        print(f'  desktop crop {focus:.0%}  (given)')

    if a.mobile_focus is None:
        mbest, _ = pick_focus(bright, detail, nw, nh, M_BOX_W, M_BOX_H, with_copy=False)
        mfocus = mbest[0]
        print(f'  phone crop   {mfocus:.0%}  (keeps {mbest[2]:.0%} of the subject)')
    else:
        mfocus = a.mobile_focus / 100.0
        print(f'  phone crop   {mfocus:.0%}  (given)')

    _, x0, x1 = geometry(nw, nh, BOX_W, BOX_H, focus)
    print(f'  visible source x {int(x0)}-{int(x1)} of {nw}  ({x0/nw:.0%}-{x1/nw:.0%})')

    crop, rows = contrast_report(im, focus)
    print('  contrast through both scrims (WCAG AA minimum in brackets):')
    bad = []
    for name, hexv, got, need in rows:
        flag = 'ok ' if got >= need else 'FAIL'
        print(f'    {flag} {name:10s} {hexv}  {got:5.2f}:1  [{need}]')
        if got < need:
            bad.append(name)
    if bad:
        print(f'  ! {", ".join(bad)} fails on this photograph. Try a different '
              f'--focus, or a picture with a quieter left side.')

    if a.render:
        crop.save(a.render)
        print(f'  wrote {a.render}')

    if a.dry_run:
        print('  dry run, nothing written')
        return

    os.makedirs(ASSET_DIR, exist_ok=True)
    webp = os.path.join(ASSET_DIR, slug + '.webp')
    jpg = os.path.join(ASSET_DIR, slug + '.jpg')
    im.save(webp, 'WEBP', quality=84, method=6)
    im.save(jpg, 'JPEG', quality=86, optimize=True, progressive=True)
    print(f'  {os.path.getsize(a.image)/1024:.0f} KB in  ->  '
          f'{os.path.getsize(webp)/1024:.0f} KB webp, {os.path.getsize(jpg)/1024:.0f} KB jpg')

    src = io.open(page, encoding='utf-8').read()
    src, how = install_css(src, css_block(focus, mfocus))
    print(f'  css {how}')
    out, err = rewrite_hero(src, slug)
    if err == 'already a banner hero':
        print('  markup already in place, left alone')
        out = src
    elif err:
        raise SystemExit(f'  markup NOT changed: {err}')
    else:
        print('  hero markup wrapped')
    io.open(page, 'w', encoding='utf-8').write(out)
    print('  done')


if __name__ == '__main__':
    sys.exit(main())
