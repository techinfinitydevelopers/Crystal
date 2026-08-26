"""Assemble CRYSTAL-Home-v3.html from the existing home page's shell.

Only the page body between the first section and the footer is swapped, so the
support bar, header, mega menu, search overlay, mobile menu, footer, enquiry
wiring and tweaks panel stay byte-identical to the rest of the site. The old
home page's own section-rendering script is dropped with them - it builds
markup for sections this page no longer has.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
# index.html now IS the v3 page, so it can no longer donate its own shell -
# the pre-v3 home page is kept here purely as the shell source.
SRC = os.path.join(HERE, "shell-donor.html")
OUT = os.path.join(ROOT, "index.html")
MAP_SVG = os.path.join(HERE, "india-map-inline.svg")

html = io.open(SRC, encoding="utf-8").read()

def cut(text, start_marker, end_marker, label):
    a = text.find(start_marker)
    b = text.find(end_marker)
    if a < 0 or b < 0 or b < a:
        raise SystemExit("could not locate %s (%s / %s)" % (label, a, b))
    return a, b

# --- body: replace the section stack -------------------------------------
a, b = cut(html, "<!-- ===== 01 HERO ===== -->", "<!-- ===== FOOTER ===== -->", "sections")

main = io.open(os.path.join(HERE, "v3_main.html"), encoding="utf-8").read()
svg = io.open(MAP_SVG, encoding="utf-8").read()
# the reference animates each state's fill; give them the class this page's JS uses
svg = svg.replace('class="map-state"', 'class="map3-state"')
if "map3-state" not in svg:
    svg = re.sub(r"<path ", '<path class="map3-state" ', svg)
main = main.replace("__INDIA_MAP__", svg)

html = html[:a] + main + "\n\n" + html[b:]

# --- script: drop the old home page's section renderer + its animations ---
a, b = cut(html,
           "  /* ---------- DATA + RENDER ---------- */",
           "  /* ---------- HEADER + MENU + COUNTERS + DRAG",
           "home script")
html = html[:a] + html[b:]

# Two leftovers in the kept half still reach for the sections that just left:
# the testimonial rail's drag handler, and the call into the renderer above.
a, b = cut(html,
           "  /* testimonials drag-to-scroll */",
           "  /* ---------- INIT + FAILSAFE ---------- */",
           "testimonial drag")
html = html[:a] + html[b:]

html = html.replace(
    '  if (!RM) { try { initGSAP(); } catch (e) { console.warn("GSAP init issue", e); } }\n',
    "")

# --- head: Swiper stylesheet + our section styles -------------------------
SWIPER_CSS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@8/swiper-bundle.min.css">\n'
html = html.replace("<style>", SWIPER_CSS + "<style>", 1)

v3css = io.open(os.path.join(HERE, "v3.css"), encoding="utf-8").read()
i = html.find("</style>")
html = html[:i] + v3css + "\n" + html[i:]

# --- head: the libraries the choreography needs ---------------------------
GSAP_ST = '<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>'
LIBS = (GSAP_ST +
        '\n<script src="https://cdn.jsdelivr.net/npm/swiper@8/swiper-bundle.min.js"></script>')
html = html.replace(GSAP_ST, LIBS, 1)

# --- title ----------------------------------------------------------------
html = re.sub(r"<title>.*?</title>",
              "<title>Crystal Cook N Serve Products - Home</title>",
              html, count=1, flags=re.S)

# --- body: our section script, right before the enquiry bundle ------------
v3js = io.open(os.path.join(HERE, "v3.js"), encoding="utf-8").read()
anchor = '<script src="enquiry.js"></script>'
if anchor not in html:
    raise SystemExit("enquiry.js anchor missing")
html = html.replace(anchor, "<script>\n" + v3js + "</script>\n" + anchor, 1)

# every h1/h2 on the site is pinned to 37px by a block appended to each
# page's stylesheet; a rebuild must not drop it from the home page
HEAD_BLOCK = io.open(os.path.join(HERE, "heading-size.css"), encoding="utf-8").read()
i = html.rfind("</style>")
html = html[:i] + HEAD_BLOCK + html[i:]

io.open(OUT, "w", encoding="utf-8").write(html)
print("wrote %s  (%.0f KB)" % (OUT, os.path.getsize(OUT) / 1024))
