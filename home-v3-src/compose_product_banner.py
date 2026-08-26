"""Build a 5:1 category banner from a studio product photograph.

The client's own banners are shot in a kitchen: product to one side, empty
counter to the other. There are ~35 category pages and those photographs
arrive a few at a time, so this makes a stand-in in the same shape from a
product shot already in the catalogue -- product to the right, clear ground to
the left for the copy. It is deliberately plain. It is meant to be replaced by
the real photograph, which is one command once it exists.

Lifting the product off its background is a flood fill from the four corners,
not a brightness threshold. That distinction matters: a threshold also erases
every white part of the product -- the white handle of a peeler, the steam in
a pan -- because it cannot tell them from the backdrop. A flood fill only takes
background that is actually connected to the edge of the frame, so enclosed
whites survive.

The alpha is then blurred a little and pulled in by a fraction of a pixel.
Without that you get a bright fringe: the photograph's own anti-aliased edge
pixels are part background, and against a darker canvas they read as a halo
traced around the product.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1980, 390

# Where the product sits, as fractions of the canvas. Chosen to match the
# client's own banners: subject right of centre, the left half clear for the
# headline. The hero only ever shows about half the width, and the scrim
# whitens what is left of ~60%, so a subject centred here survives the crop.
CENTRE_X = 0.755
PRODUCT_H = 0.80          # of canvas height
FLOOR_Y = 0.86            # where the contact shadow sits


def lift(im, thresh=26, feather=1.6, pull=0.9):
    """Return the photo with its connected background made transparent."""
    im = im.convert('RGB')
    # The product ends up about 310px tall, and flood-filling an 8000px studio
    # master to get there costs minutes. Work at a size comfortably above the
    # target so the downscale still has detail to give.
    if max(im.size) > 1500:
        im.thumbnail((1500, 1500), Image.LANCZOS)
    w, h = im.size
    work = im.copy()
    SENTINEL = (255, 0, 255)

    # Flood from all four corners: some shots have a gradient backdrop that is
    # not one flat value, and a single seed leaves the far side behind.
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
               (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)):
        r, g, b = work.getpixel(xy)
        if min(r, g, b) < 150:          # that corner is product, not backdrop
            continue
        ImageDraw.floodfill(work, xy, SENTINEL, thresh=thresh)

    diff = ImageChops.difference(work, im).convert('L')
    # Anything the fill touched became magenta, so it differs from the original.
    alpha = diff.point(lambda v: 0 if v > 12 else 255)

    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    if pull:
        # Erode: MinFilter over a small window, then bias, removes the fringe.
        alpha = alpha.filter(ImageFilter.MinFilter(3))
        alpha = alpha.point(lambda v: max(0, int((v - 255 * (1 - pull) * 0.35) * 1.06)))

    out = im.convert('RGBA')
    out.putalpha(alpha)
    return out


def trim(rgba, pad=0.02):
    box = rgba.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        return rgba
    x0, y0, x1, y1 = box
    px, py = int((x1 - x0) * pad), int((y1 - y0) * pad)
    return rgba.crop((max(0, x0 - px), max(0, y0 - py),
                      min(rgba.width, x1 + px), min(rgba.height, y1 + py)))


def ground(tint):
    """The canvas the product stands on.

    Not flat white. The hero's scrim already whitens the left, so a white
    canvas would leave the right half looking like nothing was ever shot there.
    A soft warm wash plus a floor line reads as a studio set instead.
    """
    base = Image.new('RGB', (W, H), tint['high'])
    grad = Image.new('L', (W, 1))
    gp = grad.load()
    for x in range(W):
        t = x / W
        gp[x, 0] = int(255 * min(1.0, max(0.0, (t - 0.18) / 0.72)) ** 0.85)
    wash = Image.new('RGB', (W, H), tint['low'])
    base = Image.composite(wash, base, grad.resize((W, H)))

    # A soft horizon so the product is standing on something.
    floor = Image.new('L', (1, H))
    fp = floor.load()
    for y in range(H):
        t = y / H
        fp[0, y] = int(210 * max(0.0, (t - FLOOR_Y + 0.16) / 0.30)) if t > FLOOR_Y - 0.16 else 0
    base = Image.composite(Image.new('RGB', (W, H), tint['floor']),
                           base, floor.resize((W, H)))
    return base.filter(ImageFilter.GaussianBlur(0.6))


TINTS = {
    'warm':    {'high': (255, 255, 255), 'low': (241, 236, 230), 'floor': (228, 221, 213)},
    'cool':    {'high': (255, 255, 255), 'low': (235, 238, 241), 'floor': (219, 224, 229)},
    'neutral': {'high': (255, 255, 255), 'low': (240, 240, 240), 'floor': (226, 226, 226)},
}


def compose(src, tint='warm'):
    prod = trim(lift(Image.open(src)))
    canvas = ground(TINTS[tint])

    target_h = int(H * PRODUCT_H)
    scale = target_h / prod.height
    if prod.width * scale > W * 0.46:            # very wide products
        scale = (W * 0.46) / prod.width
    pw, ph = max(1, int(prod.width * scale)), max(1, int(prod.height * scale))
    prod = prod.resize((pw, ph), Image.LANCZOS)

    cx = int(W * CENTRE_X)
    top = int(H * FLOOR_Y) - ph
    left = cx - pw // 2
    # Keep it off the right edge; a subject touching the frame reads as a crop
    # accident rather than a composition.
    left = min(left, W - pw - int(W * 0.035))
    left = max(left, int(W * 0.42))

    # Contact shadow, so it is not floating.
    sh = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sh).ellipse(
        [left + pw * 0.06, int(H * FLOOR_Y) - ph * 0.035,
         left + pw * 0.94, int(H * FLOOR_Y) + ph * 0.075],
        fill=104)
    sh = sh.filter(ImageFilter.GaussianBlur(pw * 0.045))
    canvas = Image.composite(Image.new('RGB', (W, H), (120, 112, 104)), canvas, sh)

    canvas.paste(prod, (left, top), prod)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('photo')
    ap.add_argument('out')
    ap.add_argument('--tint', default='warm', choices=sorted(TINTS))
    a = ap.parse_args()
    if not os.path.exists(a.photo):
        raise SystemExit(f'no such photo: {a.photo}')
    compose(a.photo, a.tint).save(a.out)
    print(f'{a.out}  {W}x{H}  from {os.path.basename(a.photo)}')


if __name__ == '__main__':
    sys.exit(main())
