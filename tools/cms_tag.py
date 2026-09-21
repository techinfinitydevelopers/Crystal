"""Mark the site's editable text and images with data-cms keys.

The dashboard can already change any piece of a page it has a key for (see
content/models.py PageSection, and content-sync.js). What was missing was the
keys: 54 were wired by hand to element ids and everything else on the site was
uneditable. This walks the pages and marks the rest.

    python tools/cms_tag.py --dry-run          # report, touch nothing
    python tools/cms_tag.py                    # write the attributes
    python tools/cms_tag.py --only About.html  # one page

Keys read as "<section id>-<tag><n>" — "legacy-p2", "value-img1". They are
stable as long as a section's elements keep their order, which is why they are
derived from the section rather than from a running count over the page: an
edit inside one section cannot renumber another.

Deliberately skipped:
  * anything inside <script> or <style> — those are JS templates, not content;
  * anything inside <header>, <footer> or <nav> — shared chrome, identical on
    all 68 pages, so a per-page key there would mean editing it 68 times;
  * elements that already carry data-cms, so re-running is safe;
  * empty elements and ones whose whole text is a ${...} placeholder;
  * data: and blank images.

Writes tools/cms-manifest.json: every key with its page, kind, section and the
text the page ships today. `manage.py seed_page_sections` reads that to fill
the dashboard's list with readable labels.
"""
import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", "cms-manifest.json")

# index.html is BUILT from these by home-v3-src/build_v3.py, so tagging the
# generated file would be undone by the next rebuild. The source is tagged
# instead and reported under the page it becomes; run build_v3.py afterwards.
GENERATED_FROM = {
    os.path.join("home-v3-src", "v3_main.html"): "index.html",
}

# A generated source that carries no <style> of its own -- see process()'s
# `extra_css`. The build step inlines this file into <style> tags that don't
# exist yet when cms_tag.py runs against the source.
GENERATED_CSS = {
    os.path.join("home-v3-src", "v3_main.html"): os.path.join("home-v3-src", "v3.css"),
}

# Design-tool leftovers that live in the site's repo root but are not live
# pages. content/pages_registry.py leaves them out of the dashboard's picker
# for the same reason, so tagging them would only add rows nobody can reach.
# Keys the page's own JavaScript writes after this sync runs, or that would
# break the page if replaced. Found by reading every tagged element in context
# (see BUILD-LOG). A dashboard row for any of these is a row whose edit is
# silently discarded — or, for the Enquiry success message, one that breaks
# submitting the form, because content-sync replaces the element's children and
# the page then looks for a span inside it that no longer exists.
EXCLUDE_KEYS = {
    # wrappers whose children are separately editable — replacing the wrapper
    # destroys the child
    ("index.html", "map3-li-1"), ("index.html", "map3-li-2"),
    ("index.html", "map3-li-3"), ("index.html", "map3-li-4"),
    ("index.html", "map3-li-5"),
    # purely decorative
    ("index.html", "map3-img-1"), ("index.html", "pre3-img-1"),
    # a crossfade pair whose src is rewritten on every scroll
    ("index-v2.html", "about-img-1"), ("index-v2.html", "about-img-2"),
    # "after you submit" messages, written by JS at the only moment they show
    ("Contact.html", "reach-p-2"),
    ("Quote.html", "request-p-2"),
    ("Enquiry.html", "page-p-2"),
    # rendered from the Blog API on every load
    ("Article.html", "page-h1-1"), ("Article.html", "page-p-1"),
    # per-product / per-brand chrome rewritten by Product.html's renderer
    ("Product.html", "related-h2-1"), ("Product.html", "specs-h4-1"),
}

NOT_A_PAGE = {
    "CRYSTAL Home.html", "CRYSTAL Light.html", "LOUD Agency.html",
    "index-old-v1.html",
}

# The hyphen matters: a custom element's name always contains one, so without
# it <image-slot> parsed as a tag called "image" with "-slot" as stray attribute
# text, and never matched IMAGE_TAGS.
TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*)>", re.S)
ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')

SKIP_INSIDE = {"script", "style", "header", "footer", "nav", "svg", "select", "template"}

# Chrome that is not part of the page's content: the mobile menu, the mega
# menu, the search overlay and the enquiry drawer are the same on all 68 pages
# and are built or filtered by script, so a per-page key there would be both
# wrong and unreachable. Matched on the container's id or any of its classes.
# The category/brand hero banner is ALREADY dashboard-editable, through
# banners.CategoryBanner, and its own sync script assigns .hero-media img.src
# after this one runs — so a key here would be both a duplicate control and
# the one that loses. Left out on purpose; edit those under "Category banners".
SKIP_CONTAINERS_MEDIA = {"hero-media"}

SKIP_CONTAINERS = {
    "mobilemenu", "mobile-menu", "mm-panel", "megamenu", "mega", "dd-menu",
    "searchov", "search-ov", "search-results", "search-row", "enqdrawer",
    "enq-drawer", "enq-panel", "cart", "toast", "modal", "overlay",
    "breadcrumb", "crumbs", "wa-float",
    # A hidden developer overlay for live-tweaking a category page's layout
    # (id="twkPanel", "TWEAKS PANEL" in its own HTML comment) shipped on 53
    # pages. Not a visitor ever sees it; its field names ("Mood", "Grid
    # columns", "Accent") are not page content and were showing up as
    # dashboard rows before this.
    "twk",
}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote"}
# span/div/a carry real copy too -- an eyebrow kicker, a stat number and its
# label, a button's own words, the support-bar phone number -- all missed
# until now, because none of them are in TEXT_TAGS. Not safe to tag on sight
# the way a heading is, though: a <div> is just as often a layout wrapper
# around OTHER editable elements, and tagging the wrapper as one text blob
# would both duplicate the child's key and let an edit here delete it. Only
# taken when the element is a genuine leaf -- see the "<" in inner check
# below, which skips (does not tag) anything that contains markup instead of
# marking it rich the way a heading does. A real wrapper always has a child
# tag, so it fails that check on its own; nothing here has to know in advance
# which divs are "layout" and which are "copy".
TEXT_LEAF_TAGS = {"span", "div", "a"}
# A leaf has to look like copy, not decoration, to be worth a dashboard row:
# at least one letter or digit rules out a bare arrow, pipe, or icon glyph
# ("→", "×", "★" alone) while still allowing "54+" or a phone number through.
HAS_ALNUM = re.compile(r"[0-9A-Za-zÀ-ɏ]")
# <image-slot> is a design-tool custom element (image-slot.js) left in place on
# a few pages; on the live site it is read-only and simply renders its `src`.
# It shows a real photograph to a visitor, so it is as much page content as an
# <img> -- and it observes `src`, so setting that attribute re-renders it.
# A <video>'s poster is the still shown before it plays, or if autoplay is
# blocked or the file is slow -- a real picture on the page, so it is offered
# like any other. The video itself is not editable from the dashboard.
IMAGE_TAGS = {"img", "image-slot", "video"}
# Which attribute holds the picture. Doubles as the `data-cms-attr` written
# out: without it content-sync's applyImage assigns el.src, which is the video
# file on a <video> and nothing at all on a custom element with a shadow DOM.
# A plain <img> is absent here -- it is read from src and set directly.
IMAGE_ATTR_TAGS = {"image-slot": "src", "video": "poster"}
# Keys are counted per tag, so an <img> and an <image-slot> in one section would
# otherwise both be "-img-1"/"-image-slot-1". Counting them together keeps the
# numbering unique and the key readable. A video poster counts separately, or
# adding one would renumber every <img> after it in its section.
KEY_TAG_NAME = {"image-slot": "img", "video": "poster"}

# A page's own <section id>; anything outside one is keyed against this.
NO_SECTION = "page"

PLACEHOLDER = re.compile(r"^\s*(\$\{[^}]*\}|\{\{[^}]*\}\})\s*$")

# 54 sections were editable before this, wired by element id in
# content-sync.js. Those elements must keep their original key, or the same
# heading would end up with two keys — the old one someone may already have
# edited, and a freshly minted one — both pointing at it.
with io.open(os.path.join(ROOT, "tools", "legacy-ids.json"), encoding="utf-8") as _fh:
    LEGACY_KEY_BY_ID = json.load(_fh)


# ── Site-wide chrome ────────────────────────────────────────────────────────
# The header and footer are the same on all 64 pages, which is why the walk
# below skips them: a per-page key there would mean editing one phone number
# 64 times. These get ONE key each instead, recorded against the pseudo-page
# below, written into every page's copy, and applied by content-sync on top of
# whatever that page's own keys say.
#
# Matched by a distinctive substring, not by position. Fifteen pages list four
# brand links in the footer that the other forty-nine do not, so the same
# position is "Cookware" on one page and "Crystal" on another -- one key would
# have edited two different things.
#
# Menu items are deliberately absent. "Products" and "Brands" wrap an entire
# dropdown, and content-sync replaces an element's children, so a key there
# would take the menu with it -- the same trap EXCLUDE_KEYS exists for.
SITE_PAGE = "_site.html"
# index.html is spliced together by build_v3.py: its body comes from
# v3_main.html and its header and footer from shell-donor.html. So the chrome
# tags have to go into the donor -- v3_main.html has no header or footer to
# tag, and tagging the built index.html would be undone by the next build.
# Only the site-wide pass runs over it; everything between its HERO and FOOTER
# markers is discarded at build time, so page keys there would be thrown away.
SITE_ONLY_FILES = [os.path.join("home-v3-src", "shell-donor.html")]
# The three contact lines are tagged on the <a> inside the <li>, not the <li>.
# The anchor carries the tel: link and the map jump; tagging the <li> would
# make the value rich text, and then editing the phone number to plain digits
# would take the click-to-call away with it. On the <a> the value is the
# visible text and the link is untouched.
SITE_WIDE = [
    ("site-support-bar",   "div", "Customer Support",                    "Support bar"),
    ("site-foot-cta",      "h3",  "every corner of your home",           "Footer heading"),
    ("site-foot-desc",     "p",   "Complete Kitchen and Home Solutions", "Footer description"),
    ("site-addr-rajkot",   "a",   "G.I.D.C Metoda",                      "Factory address"),
    ("site-addr-mumbai",   "a",   "Sahar Plaza",                         "Office address"),
    ("site-phone",         "a",   "022-49702803 / 06",                   "Phone number"),
]


# The search runs inside these and nowhere else. Contact.html lists the same
# phone number in its own contact block, ahead of the footer, and a document-
# wide search took that one -- so editing the site-wide phone number would have
# rewritten one page's content instead of the footer on all 64.
CHROME_REGIONS = [
    r'<div[^>]*class="[^"]*support-bar[^"]*"[^>]*>.*?</div>',
    r'<header\b.*?</header>',
    r'<footer\b.*?</footer>',
]


def tag_site_wide(html, report):
    """Mark this page's copy of the shared chrome. Returns (html, rows)."""
    rows = []
    spans = []
    for region in CHROME_REGIONS:
        for m in re.finditer(region, html, re.S | re.I):
            spans.append((m.start(), m.end()))

    for key, tag, needle, label in SITE_WIDE:
        pat = re.compile(r"<%s\b([^>]*)>((?:(?!</%s>).)*?%s(?:(?!</%s>).)*?)</%s>"
                         % (tag, tag, re.escape(needle), tag, tag), re.S)
        hit = None
        for start, end in spans:
            m = pat.search(html, start, end)
            if m:
                hit = m
                break
        if not hit:
            report["site_not_found"] += 1
            continue
        if "data-cms" in hit.group(1):
            report["already"] += 1
            rows.append((key, hit.group(2), label))
            continue
        # Nested markup (a <span> highlight, a <br>) would be flattened by a
        # plain text swap, same rule as the main walk.
        rich = ' data-cms-rich' if "<" in hit.group(2) else ""
        cut = hit.start() + len("<%s" % tag) + len(hit.group(1))
        while cut > hit.start() and html[cut - 1] in '/ \t\r\n':
            cut -= 1
        insert = ' data-cms="%s"%s' % (key, rich)
        html = html[:cut] + insert + html[cut:]
        # Everything after the insertion point shifted along with it.
        spans = [(s + len(insert) if s > cut else s,
                  e + len(insert) if e > cut else e) for s, e in spans]
        report["site_tagged"] += 1
        rows.append((key, hit.group(2), label))
    return html, rows


def attrs_of(raw):
    return dict(ATTR.findall(raw))


def strip_tags(html):
    """A <br> is a word boundary. Left as nothing it glued headings together
    ("Built onsolid ground") in both the label AND the shipped reference, and
    the shipped value is what seeds the dashboard — so saving a row unchanged
    would have published the missing space."""
    html = re.sub(r"<br\s*/?>", " ", html, flags=re.I)
    return re.sub(r"<[^>]+>", "", html)


def unescape(text):
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&mdash;", "—"),
                 ("&ndash;", "–"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def label_for(section, tag, n, text):
    """What the dashboard calls this row. The shipped words are the most
    recognisable handle a person has, so they lead; the section is the
    fallback for an image or an empty element."""
    where = section.replace("-", " ").strip().title()
    if tag == "video":
        return "%s — video poster %d" % (where, n)
    if tag in IMAGE_TAGS:
        return "%s — image %d" % (where, n)
    snippet = text[:48] + ("…" if len(text) > 48 else "")
    return "%s — %s" % (where, snippet) if snippet else "%s — %s %d" % (where, tag, n)



# ── Expected upload size, guessed from the page's own CSS ──────────────────
# The point: an editor uploading a photo has no way to know it will be
# cropped to a fixed shape until after they save and look at the live page.
# Every image row gets a plain-English "upload roughly this size" hint,
# resolved from the CSS rule that actually sizes its container -- the same
# rule the browser uses, so the hint can never drift from the real crop.

STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
ASPECT_RATIO = re.compile(r"aspect-ratio\s*:\s*([\d.]+)\s*/\s*([\d.]+)")
ASPECT_RATIO_1 = re.compile(r"aspect-ratio\s*:\s*([\d.]+)\s*;")
PX_PAIR = re.compile(r"width\s*:\s*(\d+)px[^;]*;.*?height\s*:\s*(\d+)px", re.S)
MIN_HEIGHT = re.compile(r"height\s*:\s*min\([^,]+,\s*(\d+)px\)")

# Common ratios get a named, round recommendation instead of the raw CSS
# numbers -- "469 x 334" means nothing to someone choosing a photo; "roughly
# 1400 x 1000px, landscape" does. Matched by the simplified ratio, to 2dp.
_NAMED_RATIOS = [
    (1.0, "Square", "1000 × 1000"),
    (16 / 9, "Widescreen (16:9)", "1600 × 900"),
    (16 / 10, "Widescreen (16:10)", "1600 × 1000"),
    (4 / 3, "Classic (4:3)", "1200 × 900"),
    (5 / 4, "5:4", "1250 × 1000"),
    (0.5, "Tall (1:2)", "800 × 1600"),
]


def _rule_for(css, selector):
    """The declaration block of the first rule whose selector is exactly this,
    matched as one item of a comma-separated list -- ".a, .b img { ... }"
    matches selector ".b img" even though the brace sits after ".a" too, and
    the block that eventually opens belongs to the whole list. `selector` is
    a plain string like ".bp-tile img" -- escaped here, once, correctly,
    rather than by the caller."""
    esc = re.escape(selector)
    pat = re.compile(
        r"(?:^|[{}\s,])" + esc + r"\s*(?:,[^{]*)?\{([^}]*)\}", re.S)
    m = pat.search(css)
    return m.group(1) if m else None


def _box_from_rule(rule):
    m = ASPECT_RATIO.search(rule)
    if m:
        w, h = float(m.group(1)), float(m.group(2))
        return _describe_ratio(w, h)
    m = ASPECT_RATIO_1.search(rule)
    if m:
        return _describe_ratio(float(m.group(1)), 1.0)
    m = PX_PAIR.search(rule)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        return "%d × %d px" % (w, h)
    m = MIN_HEIGHT.search(rule)
    if m:
        h = int(m.group(1))
        return ("Full-width banner — landscape, roughly %d × %d px "
                "or wider. It stretches edge to edge and is capped around "
                "%dpx tall on a computer, so keep the subject centred or it "
                "gets cropped on the sides on a narrow screen." % (h * 2, h, h))
    return None


def _describe_ratio(w, h):
    ratio = w / h if h else 1.0
    for target, name, px in _NAMED_RATIOS:
        if abs(ratio - target) < 0.03:
            return "%s — roughly %spx or larger" % (name, px)
    # An unnamed ratio: show it plainly, at a size close to the CSS's own
    # numbers (design tools often export the crop at literal pixel values,
    # which is exactly what these look like) doubled for a sharp screen.
    scale = 1
    while w * scale < 500 and h * scale < 500:
        scale += 1
    return "Landscape (%d:%d) — roughly %d × %d px or larger" % (
        round(w), round(h), round(w * scale), round(h * scale))


def expected_box(css, tag, own_classes, ancestor_levels):
    """Best-guess upload size for an image/video/image-slot element.

    Three kinds of markup all show up on this site, tried in that order:
      * the element carries its own sizing class (a bare <img class="x">,
        no wrapper) -- ".x" / ".x img";
      * a crop is declared on the immediate parent -- ".parent img" / ".parent"
        (the common case: an <img> with no class of its own inside
        <a class="bp-tile">);
      * a swiper-style carousel, where the box the browser actually renders
        comes from an ANCESTOR two or three levels up (.hero3-swiper-wrap),
        with generic, unstyled wrapper divs (.swiper-slide, .slide-inner) in
        between that carry no size of their own. Walked outward until
        something resolves, or the wrappers run out.
    """
    def tries_for(classes):
        if not classes:
            return []
        combo = "." + ".".join(classes)
        out = [combo + " " + tag, combo]
        for cls in classes:
            out += ["." + cls + " " + tag, "." + cls]
        return out

    for selector in tries_for(own_classes):
        rule = _rule_for(css, selector)
        if rule:
            box = _box_from_rule(rule)
            if box:
                return box

    for classes in ancestor_levels:
        for selector in tries_for(classes):
            rule = _rule_for(css, selector)
            if rule:
                box = _box_from_rule(rule)
                if box:
                    return box
    return None


def process(html, page, report, extra_css=""):
    """Return the page with data-cms added, plus the manifest rows it earned.

    `extra_css` is for a source file with no <style> of its own --
    home-v3-src/v3_main.html carries none; its rules live in the sibling
    v3.css and only get inlined by build_v3.py, well after this runs. Without
    it every image on that page silently resolved no box at all: not "this
    box has no fixed shape", just nothing to search.
    """
    out = []
    rows = []
    pos = 0
    depth = {name: 0 for name in SKIP_INSIDE}
    container_depth = []          # open depths of skipped chrome containers
    media_depth = []              # depths where images are owned elsewhere
    parent_stack = []              # classes of each currently-open element,
                                    # innermost last -- how an <img> finds the
                                    # container that actually sizes it
    section = NO_SECTION
    section_depth = None
    open_depth = 0
    counters = {}
    css = "\n".join(STYLE_BLOCK.findall(html)) + "\n" + extra_css

    for m in TAG.finditer(html):
        closing, name, raw = m.group(1) == "/", m.group(2).lower(), m.group(3)
        self_closing = raw.rstrip().endswith("/") or name in ("img", "br", "hr", "input", "meta", "link", "source")
        # Captured before this tag can push its own entry, so it always names
        # elements ENCLOSING this one -- for a self-closing <img> that push
        # never happens anyway, but a non-self-closing <video> or
        # <image-slot> pushes itself first, and without this snapshot the
        # "container" lookup below would see the element's own (usually
        # empty) classes instead of its ancestors'. Nearest first, several
        # levels deep: a swiper carousel wraps its <img> in two or three
        # generic, unstyled divs (.swiper-slide, .slide-inner) before
        # reaching the one that actually carries a size.
        ancestor_levels = [cls for _, cls in reversed(parent_stack[-6:]) if cls]

        if closing:
            if name in depth and depth[name]:
                depth[name] -= 1
            open_depth -= 1
            while container_depth and open_depth < container_depth[-1]:
                container_depth.pop()
            while media_depth and open_depth < media_depth[-1]:
                media_depth.pop()
            if parent_stack and open_depth < parent_stack[-1][0]:
                parent_stack.pop()
            if section_depth is not None and open_depth < section_depth:
                section, section_depth = NO_SECTION, None
            continue

        if not self_closing:
            open_depth += 1

        if not self_closing:
            a0 = attrs_of(raw)
            names = set()
            if a0.get("id"):
                names.add(a0["id"].lower())
            names.update(c.lower() for c in (a0.get("class", "") or "").split())
            if names & SKIP_CONTAINERS:
                container_depth.append(open_depth)
            elif names & SKIP_CONTAINERS_MEDIA:
                media_depth.append(open_depth)
            classes = [c for c in (a0.get("class", "") or "").split() if c]
            parent_stack.append((open_depth, classes))

        if name == "section" and not closing:
            got = attrs_of(raw).get("id")
            section = got or NO_SECTION
            section_depth = open_depth

        inside_skipped = any(depth[n] for n in SKIP_INSIDE) or bool(container_depth)
        if name in SKIP_INSIDE and not self_closing:
            depth[name] += 1
            continue
        if inside_skipped:
            continue

        if name not in TEXT_TAGS and name not in IMAGE_TAGS and name not in TEXT_LEAF_TAGS:
            continue

        a = attrs_of(raw)
        # An element that already carries a key is not re-tagged, but it must
        # still walk the rest of this loop: it owns a slot in the per-section
        # numbering, and it owns a row in the manifest. Bailing out here -- as
        # this did -- made a second run renumber everything after it, so keys
        # held back by EXCLUDE_KEYS came back into range and got tagged (twice
        # over, in Contact.html's case), and rebuilt the manifest with only the
        # handful of keys that happened to be new: 984 rows down to 7.
        existing_key = a.get("data-cms")

        rich = ""
        box = None

        if name in IMAGE_TAGS and media_depth:
            report["owned_elsewhere"] += 1
            continue

        if name in IMAGE_TAGS:
            # Same map as the attribute written out: a <video>'s picture is its
            # poster, not its src. A video with no poster falls through as
            # empty, which is right -- there is nothing to show or replace.
            src = a.get(IMAGE_ATTR_TAGS.get(name, "src"), "")
            if not src or src.startswith("data:"):
                report["skipped_empty"] += 1
                continue
            # The reference shown in the dashboard has to be the picture the
            # page uses; the alt text is not what the editor is replacing.
            text = src
            kind = "image"
            # What actually sizes this element on the page: its own class
            # first (a bare, unwrapped <img class="x">), then each enclosing
            # element's classes in turn, nearest first. None anywhere
            # resolves to nothing, same as an unmatched selector.
            own_classes = [c for c in (a.get("class", "") or "").split() if c]
            box = expected_box(css, name, own_classes, ancestor_levels)
        else:
            # The element's own text, up to its closing tag. Nested markup is
            # stripped for the label only — the attribute goes on the element
            # either way, and the dashboard replaces its whole text.
            close = re.search(r"</%s\b" % name, html[m.end():], re.I)
            inner = html[m.end():m.end() + close.start()] if close else ""
            if name in TEXT_LEAF_TAGS and "<" in inner:
                # A span/div/a with markup inside it is a wrapper around
                # other elements -- possibly ones that already earned their
                # own key -- not a piece of copy in its own right. Skipped
                # outright rather than marked rich, unlike a heading: tagging
                # the wrapper would duplicate whatever is inside it, and an
                # edit here would delete that child entirely.
                report["skipped_empty"] += 1
                continue
            text = unescape(strip_tags(inner))
            # A counted stat starts at "0" in the markup -- content-sync's
            # own count-up script animates it up to data-count/data-target on
            # load. "0" is not the number this page ships, so it is not what
            # the reference (or the row's starting value) should show.
            counted = a.get("data-count") or a.get("data-target")
            if counted:
                text = counted
            if not text or PLACEHOLDER.match(text):
                report["skipped_empty"] += 1
                continue
            if name in TEXT_LEAF_TAGS and not HAS_ALNUM.search(text):
                # A bare arrow, pipe or icon glyph -- decoration, not copy.
                report["skipped_empty"] += 1
                continue
            if "<" in inner:
                # The element ships with markup inside it — a <br>, a
                # <span class="grad"> highlight, a <b>, a mailto link. Plain
                # textContent would flatten all of it on the first edit, so the
                # element is marked as taking rich text instead.
                rich = ' data-cms-rich'
                report["rich"] += 1
            kind = "text"

        key_name = KEY_TAG_NAME.get(name, name)
        counters.setdefault(section, {}).setdefault(key_name, 0)
        counters[section][key_name] += 1
        n = counters[section][key_name]
        key = existing_key or LEGACY_KEY_BY_ID.get(
            a.get("id", ""), "%s-%s-%d" % (section, key_name, n))
        if (page, key) in EXCLUDE_KEYS:
            report["excluded"] += 1
            continue

        if existing_key:
            report["already"] += 1
        else:
            # Insert before ">" — and before a self-closing "/", or the result
            # is <img ... / data-cms="x">, which browsers tolerate but no
            # serializer should have to.
            cut = m.end() - 1
            while cut > m.start() and html[cut - 1] in '/ \t\r\n':
                cut -= 1
            attr_target = IMAGE_ATTR_TAGS.get(name)
            cms_attr = ' data-cms-attr="%s"' % attr_target if attr_target else ""

            out.append(html[pos:cut])
            out.append(' data-cms="%s"%s%s' % (key, rich, cms_attr))
            pos = cut

        row = {
            "page": page,
            "key": key,
            "kind": kind,
            "section": section,
            "label": label_for(section, name, n, text),
            "shipped": text[:300],
        }
        if box:
            row["box"] = box
        rows.append(row)

    out.append(html[pos:])
    return "".join(out), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", action="append", default=None)
    args = ap.parse_args()

    generated = set(GENERATED_FROM.values())
    names = args.only or (
        sorted(GENERATED_FROM)
        + sorted(f for f in os.listdir(ROOT)
                 if f.endswith(".html") and not f.startswith("_")
                 and f not in generated and f not in NOT_A_PAGE)
    )

    manifest, report = [], {"already": 0, "skipped_empty": 0,
                            "owned_elsewhere": 0, "excluded": 0, "rich": 0,
                            "site_tagged": 0, "site_not_found": 0}
    changed = 0
    site_rows = {}
    for name in names:
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            print("missing: %s" % name)
            continue
        html = io.open(path, encoding="utf-8", newline="").read()
        extra_css = ""
        css_path = GENERATED_CSS.get(name)
        if css_path:
            extra_css = io.open(os.path.join(ROOT, css_path), encoding="utf-8").read()
        new, rows = process(html, GENERATED_FROM.get(name, name), report, extra_css)
        # The shared chrome is tagged in every page but described once: the
        # first page to carry a key contributes its row, the other 63 just get
        # the attribute.
        new, found = tag_site_wide(new, report)
        for key, shipped, label in found:
            site_rows.setdefault(key, (shipped, label))
        manifest.extend(rows)
        if not args.dry_run and new != html:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
            changed += 1
        as_page = GENERATED_FROM.get(name)
        print("%-40s %4d keys%s" % (name, len(rows),
                                    "  -> %s" % as_page if as_page else ""))

    for rel in SITE_ONLY_FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            print("missing: %s" % rel)
            continue
        html = io.open(path, encoding="utf-8", newline="").read()
        new, found = tag_site_wide(html, report)
        for key, shipped, label in found:
            site_rows.setdefault(key, (shipped, label))
        if not args.dry_run and new != html:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
            changed += 1
        print("%-40s %4s      (chrome only)" % (rel, len(found)))

    for key, (shipped, label) in site_rows.items():
        manifest.append({
            "page": SITE_PAGE,
            "key": key,
            "kind": "text",
            "section": "site",
            "label": label,
            "shipped": unescape(strip_tags(shipped)).strip()[:300],
        })

    kinds = {}
    for r in manifest:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("\npages: %d | keys: %d (%s)" % (len(names), len(manifest), kinds))
    print("already tagged: %d | skipped empty/placeholder: %d | "
          "images owned by Category banners: %d" %
          (report["already"], report["skipped_empty"], report["owned_elsewhere"]))
    print("excluded as JS-driven or unsafe: %d | take rich text: %d"
          % (report["excluded"], report["rich"]))
    print("site-wide chrome: %d keys, newly tagged on %d pages, not found %d times"
          % (len(site_rows), report["site_tagged"], report["site_not_found"]))

    if not args.dry_run:
        io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(
            json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        print("wrote %s and edited %d pages" % (MANIFEST, changed))
        if any(n in GENERATED_FROM for n in names):
            print("NOTE: run  python home-v3-src/build_v3.py  to carry the "
                  "source's tags into index.html")


if __name__ == "__main__":
    sys.exit(main())
