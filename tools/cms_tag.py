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
}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote"}
# <image-slot> is a design-tool custom element (image-slot.js) left in place on
# a few pages; on the live site it is read-only and simply renders its `src`.
# It shows a real photograph to a visitor, so it is as much page content as an
# <img> -- and it observes `src`, so setting that attribute re-renders it.
IMAGE_TAGS = {"img", "image-slot"}
# Tags whose value belongs in an attribute rather than in the element. Without
# this content-sync's applyImage falls through to setting a CSS background,
# which a custom element with a shadow DOM never shows.
IMAGE_ATTR_TAGS = {"image-slot": "src"}
# Keys are counted per tag, so an <img> and an <image-slot> in one section would
# otherwise both be "-img-1"/"-image-slot-1". Counting them together keeps the
# numbering unique and the key readable.
KEY_TAG_NAME = {"image-slot": "img"}

# A page's own <section id>; anything outside one is keyed against this.
NO_SECTION = "page"

PLACEHOLDER = re.compile(r"^\s*(\$\{[^}]*\}|\{\{[^}]*\}\})\s*$")

# 54 sections were editable before this, wired by element id in
# content-sync.js. Those elements must keep their original key, or the same
# heading would end up with two keys — the old one someone may already have
# edited, and a freshly minted one — both pointing at it.
with io.open(os.path.join(ROOT, "tools", "legacy-ids.json"), encoding="utf-8") as _fh:
    LEGACY_KEY_BY_ID = json.load(_fh)


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
    if tag in IMAGE_TAGS:
        return "%s — image %d" % (where, n)
    snippet = text[:48] + ("…" if len(text) > 48 else "")
    return "%s — %s" % (where, snippet) if snippet else "%s — %s %d" % (where, tag, n)


def process(html, page, report):
    """Return the page with data-cms added, plus the manifest rows it earned."""
    out = []
    rows = []
    pos = 0
    depth = {name: 0 for name in SKIP_INSIDE}
    container_depth = []          # open depths of skipped chrome containers
    media_depth = []              # depths where images are owned elsewhere
    section = NO_SECTION
    section_depth = None
    open_depth = 0
    counters = {}

    for m in TAG.finditer(html):
        closing, name, raw = m.group(1) == "/", m.group(2).lower(), m.group(3)
        self_closing = raw.rstrip().endswith("/") or name in ("img", "br", "hr", "input", "meta", "link", "source")

        if closing:
            if name in depth and depth[name]:
                depth[name] -= 1
            open_depth -= 1
            while container_depth and open_depth < container_depth[-1]:
                container_depth.pop()
            while media_depth and open_depth < media_depth[-1]:
                media_depth.pop()
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

        if name not in TEXT_TAGS and name not in IMAGE_TAGS:
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

        if name in IMAGE_TAGS and media_depth:
            report["owned_elsewhere"] += 1
            continue

        if name in IMAGE_TAGS:
            src = a.get("src", "")
            if not src or src.startswith("data:"):
                report["skipped_empty"] += 1
                continue
            # The reference shown in the dashboard has to be the picture the
            # page uses; the alt text is not what the editor is replacing.
            text = src
            kind = "image"
        else:
            # The element's own text, up to its closing tag. Nested markup is
            # stripped for the label only — the attribute goes on the element
            # either way, and the dashboard replaces its whole text.
            close = re.search(r"</%s\b" % name, html[m.end():], re.I)
            inner = html[m.end():m.end() + close.start()] if close else ""
            text = unescape(strip_tags(inner))
            if not text or PLACEHOLDER.match(text):
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

        rows.append({
            "page": page,
            "key": key,
            "kind": kind,
            "section": section,
            "label": label_for(section, name, n, text),
            "shipped": text[:300],
        })

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
                            "owned_elsewhere": 0, "excluded": 0, "rich": 0}
    changed = 0
    for name in names:
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            print("missing: %s" % name)
            continue
        html = io.open(path, encoding="utf-8", newline="").read()
        new, rows = process(html, GENERATED_FROM.get(name, name), report)
        manifest.extend(rows)
        if rows and not args.dry_run and new != html:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
            changed += 1
        as_page = GENERATED_FROM.get(name)
        print("%-40s %4d keys%s" % (name, len(rows),
                                    "  -> %s" % as_page if as_page else ""))

    kinds = {}
    for r in manifest:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print("\npages: %d | keys: %d (%s)" % (len(names), len(manifest), kinds))
    print("already tagged: %d | skipped empty/placeholder: %d | "
          "images owned by Category banners: %d" %
          (report["already"], report["skipped_empty"], report["owned_elsewhere"]))
    print("excluded as JS-driven or unsafe: %d | take rich text: %d"
          % (report["excluded"], report["rich"]))

    if not args.dry_run:
        io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(
            json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        print("wrote %s and edited %d pages" % (MANIFEST, changed))
        if any(n in GENERATED_FROM for n in names):
            print("NOTE: run  python home-v3-src/build_v3.py  to carry the "
                  "source's tags into index.html")


if __name__ == "__main__":
    sys.exit(main())
