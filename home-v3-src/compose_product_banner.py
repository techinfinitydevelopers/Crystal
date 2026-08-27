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
# The client asked that no product be sliced by the frame, and that governs
# the whole layout. The hero shows a cover-crop of this canvas: 987 of 1980px
# on a computer, and only 780px -- 39% -- on a phone. Anything wider than the
# SMALLER window gets cut on a phone no matter where the crop sits.
#
# So the group is held inside a band of about a third of the canvas, placed
# where both crops can contain it with room to spare. The earlier version let
# the principal bleed off the right edge on purpose, which read as a deliberate
# composition to me and as a cut-off product to them. They are right: it is
# their product, and it should be whole.
GROUP_L, GROUP_R = 0.555, 0.890      # the band the whole group must live in
CENTRE_X = (GROUP_L + GROUP_R) / 2
PRODUCT_H = 0.94          # of canvas height
FLOOR_Y = 0.90            # where the contact shadow sits
# The crops that contain that band, with margin at both ends. Passed to
# apply_category_banner rather than letting it score a crop of its own.
FOCUS_DESKTOP, FOCUS_PHONE = 88, 87

# One small object on a wide pale field reads as a picture that failed to load,
# which is exactly how the first pass looked beside the client's own banners:
# theirs fill the frame edge to edge, mine had a lone spoon rack adrift in
# cream. A category is shown by a group of its products instead -- a principal
# piece with one or two behind it, set back and lightened so they read as depth
# rather than clutter, and the principal allowed to bleed off the right edge
# the way the shot banners do.
SUPPORT = (
    # (scale vs principal, x offset in principal-widths, how far back)
    (0.74, -0.78, 0.42),
    (0.62,  0.72, 0.55),
)


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


def compose(src, tint='warm', support=()):
    """src is the principal product; support is up to two more from the category."""
    canvas = ground(TINTS[tint])
    principal = trim(lift(Image.open(src)))

    band_l, band_r = int(W * GROUP_L), int(W * GROUP_R)
    band_w = band_r - band_l

    target_h = int(H * PRODUCT_H)
    scale = target_h / principal.height
    # The principal keeps most of the band; the supports tuck in beside it.
    if principal.width * scale > band_w * 0.72:
        scale = (band_w * 0.72) / principal.width
    pw, ph = max(1, int(principal.width * scale)), max(1, int(principal.height * scale))
    principal = principal.resize((pw, ph), Image.LANCZOS)

    floor = int(H * FLOOR_Y)
    left = int(W * CENTRE_X) - pw // 2
    # Wholly inside the band, both ends. Nothing bleeds.
    left = min(left, band_r - pw)
    left = max(left, band_l)

    def shadow(x, w, h, strength):
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).ellipse([x + w * 0.06, floor - h * 0.03,
                                   x + w * 0.94, floor + h * 0.07], fill=strength)
        return m.filter(ImageFilter.GaussianBlur(max(4, w * 0.05)))

    # Behind first, so the principal overlaps them.
    for (sc, dx, back), path in zip(SUPPORT, support):
        try:
            piece = trim(lift(Image.open(path)))
        except Exception:
            continue
        sh_h = int(ph * sc)
        sh_w = max(1, int(piece.width * sh_h / piece.height))
        if sh_w > W * 0.34:
            sh_w = int(W * 0.34)
            sh_h = max(1, int(piece.height * sh_w / piece.width))
        piece = piece.resize((sh_w, sh_h), Image.LANCZOS)
        # Set back: lift toward the ground colour and soften, so it recedes
        # instead of competing with the principal.
        veil = Image.new('RGB', piece.size, TINTS[tint]['low'])
        body = Image.blend(piece.convert('RGB'), veil, back * 0.55)
        piece = Image.merge('RGBA', body.split() + (piece.getchannel('A').point(
            lambda v, b=back: int(v * (1 - b * 0.30))),))
        piece = piece.filter(ImageFilter.GaussianBlur(0.4 + back))
        px_ = int(left + pw * dx)
        # supports stay inside the band too, or a phone crop clips them
        px_ = max(band_l, min(px_, band_r - sh_w))
        canvas = Image.composite(Image.new('RGB', (W, H), (120, 112, 104)), canvas,
                                 shadow(px_, sh_w, sh_h, int(70 * (1 - back))))
        canvas.paste(piece, (px_, floor - sh_h), piece)

    canvas = Image.composite(Image.new('RGB', (W, H), (118, 110, 102)), canvas,
                             shadow(left, pw, ph, 112))
    canvas.paste(principal, (left, floor - ph), principal)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('photo')
    ap.add_argument('out')
    ap.add_argument('--tint', default='warm', choices=sorted(TINTS))
    ap.add_argument('--support', nargs='*', default=[],
                    help='up to two more products from the category, set behind')
    a = ap.parse_args()
    if not os.path.exists(a.photo):
        raise SystemExit(f'no such photo: {a.photo}')
    compose(a.photo, a.tint, a.support).save(a.out)
    print(f'{a.out}  {W}x{H}  from {os.path.basename(a.photo)}')


if __name__ == '__main__':
    sys.exit(main())
