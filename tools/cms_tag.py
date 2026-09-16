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
NOT_A_PAGE = {
    "CRYSTAL Home.html", "CRYSTAL Light.html", "LOUD Agency.html",
    "index-old-v1.html",
}

TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>", re.S)
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
IMAGE_TAGS = {"img"}

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
        if "data-cms" in a:
            report["already"] += 1
            continue

        if name in IMAGE_TAGS and media_depth:
            report["owned_elsewhere"] += 1
            continue

        if name in IMAGE_TAGS:
            src = a.get("src", "")
            if not src or src.startswith("data:"):
                report["skipped_empty"] += 1
                continue
            text = a.get("alt", "")
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
            kind = "text"

        counters.setdefault(section, {}).setdefault(name, 0)
        counters[section][name] += 1
        n = counters[section][name]
        key = LEGACY_KEY_BY_ID.get(a.get("id", ""), "%s-%s-%d" % (section, name, n))

        out.append(html[pos:m.end() - 1])
        out.append(' data-cms="%s"' % key)
        pos = m.end() - 1

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

    manifest, report = [], {"already": 0, "skipped_empty": 0, "owned_elsewhere": 0}
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
          "images owned by Category banners: %d"
          % (report["already"], report["skipped_empty"], report["owned_elsewhere"]))

    if not args.dry_run:
        io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(
            json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
        print("wrote %s and edited %d pages" % (MANIFEST, changed))
        if any(n in GENERATED_FROM for n in names):
            print("NOTE: run  python home-v3-src/build_v3.py  to carry the "
                  "source's tags into index.html")


if __name__ == "__main__":
    sys.exit(main())
