# Build Log

## 2026-08-24 — Wood Range + Oil Pourer verification pass

**Commit:** `4db9f6a` Fix Oil Pourer hero images: carton dielines replaced with product photos

### Scope
Verify, for every SKU that has an Amazon link, that (a) the stored `amazon_link`
points at the right listing and (b) the website images show that exact product.
SKUs with no Amazon link were not touched.

### Wood Range — CPW-001…CPW-030
- 29 linked ASINs re-scraped from amazon.in (the previous `amazon-products/` data
  for these had been lost in a folder-wipe; the zip backup didn't have them either).
- All 29 titles match their sheet descriptions. **No mismatches.**
- CPW-026 has no Amazon link — skipped, untouched.
- Wording-only differences (same product, no action): CPW-010 listed as a
  9-compartment masala dabba vs sheet "9 Bowls"; CPW-020 listed as "Milano Tray
  with 3 Bowls" vs sheet "Store N Serve 3 pcs".
- CPW-014/015/016: amazon.in renders "Cuppo" as the `#productTitle` on all three
  tea-coaster children. Twister data confirms Square/Round/Cuppo respectively, so
  the sheet mapping is correct — Amazon's own title is the bug.

### Oil Pourer & Sprayer — COP-001…005, CLMK-017
- All 6 `amazon_link` values verified correct.
- **Defect found:** COP-001…004 used the packaging carton dieline artwork
  (8404×6004 flat print layout) as `hero.jpg` instead of a product photo.
- Fix: the correct product shot was already in each gallery as `g1.jpg`, so it was
  promoted to `hero.jpg`; the dieline was preserved as `carton.jpg` and moved to
  the last gallery slot. Byte-identical gallery duplicates were dropped
  (COP-001/002/003 each had `g2.jpg` == `g3.jpg`).
- CLMK-017 had `hero` pointing at a remote `m.media-amazon.com` URL with an empty
  gallery; the photo is now stored locally at `product-photos/CLMK-017/hero.jpg`.
  This listing genuinely has only one photo, so the empty gallery is correct.
- COP-005 needed no change.

### Verified
Dev server on :4567, `Product.html?p=cop-001` and `?p=clmk-017` both render the
correct product photo as the main image; `products.json` hero/gallery/link values
re-read from the served file.

### Housekeeping
`amazon-products.zip` refreshed — now 313 ASIN folders (was 284), covering the
newly re-scraped Wood Range and Oil Pourer data. This zip is the only copy;
the working folder is untracked and has been wiped three times.

---

## 2026-08-24 — Full-catalogue Amazon verification and image sync

**Commit:** `a423ae0` Localize 17 hotlinked product images and fix one contaminated gallery

A batch agent reported that concurrent scraping agents shared one browser tab
pool and that tabs were reassigned between `navigate` and extract, so a folder
could hold a different product's data than its name claims. That made every
scraped folder suspect, so all 309 were re-checked.

### Method
Stored `info.json` title vs the live amazon.in title, fetched over **curl with a
browser User-Agent**. curl has no tab-contention failure mode, and unlike
`urllib` it returns the full page (urllib gets a stripped variant with no
`#productDescription`, which had silently produced ~85 empty descriptions).
Diffs were classified by similarity ratio, because Amazon edits its own listing
copy and a strict compare over-reports.

### Results — 309 scraped folders
- 294 clean
- 4 reworded by Amazon, same product (`Haevy`→`Heavy`, `Dishwsher`→`Dishwasher`,
  `Cmand`→`Cm and`) — no action
- **11 genuinely contaminated**, all re-scraped over curl. Every one of the 11
  SKU↔`amazon_link` pairings turned out correct — only the scraped folder data
  was wrong, never the link.
- Of those 11, only **CLCL-002** had a wrong image live on the site; the other 10
  SKUs already had correct studio photos. CLCL-002 is re-synced.

### 13 folders that held only an error.txt
9 of the 13 error reports were **false** — same tab-contamination, reported as
"ASIN redirects to a different product". curl recovered all 9, and each title
matches its SKU name: CL-215, MKA921, MKA075, MKA941, MKA-094N, MKA942, CC-992,
CC-994, CWB-032. The other 4 are genuine 404s (delisted), confirmed as 404 rather
than robot-checks.

### Image sync
17 entries served hero/gallery from `m.media-amazon.com` hotlinks; all are now
local under `product-photos/<SKU>/`. Final audit: **531 products, 0 broken image
paths.** 9 hotlinks remain, every one on a product with no Amazon link, left
untouched per the standing instruction.

### Variants
29 variant groups, 95 products. 28 groups healthy — labels present, orders
unique, per-size heroes distinct.

### Dead links cleared — `ba58557`
`CL-804`, `CLMK-015`, `CWB042` pointed at ASINs returning a genuine 404, so their
`amazon_link` is now empty. Each keeps its page, name and local photos; the
"Available on: Amazon" link falls back to an Amazon search for the product name,
a path Product.html already handled, and Buy Now no longer carries a marketplace
URL. Verified: all three render, every image 200, no other entry references the
dead ASINs.

---

## 2026-08-24 — Gallery cleanup, videos wired, footer wordmark removed

**Commits:** `06e2e88` galleries · `a9a75b5` wordmark · `8b5e3fa` videos

### Galleries — `06e2e88`
- 126 gallery entries repeated a photo the product already showed (usually the
  hero listed again as a thumbnail). References dropped; files left on disk.
- 203 standalone products were showing fewer photos than their ASIN folder holds
  — 908 photos wired in.
- **Variant groups deliberately excluded.** A first pass enriched all products
  (1032 photos) and was reverted: Amazon serves one shared image set per size
  range, so a 20 cm folder also holds 32 cm photos with no reliable way to tell
  them apart. Enriching there would put the wrong size on the page.
- Correction to the earlier entry: the "28/29 variant groups healthy" claim came
  from a check that compared hero *paths* (always distinct, one per SKU folder)
  rather than image content. Several groups — vg-08, vg-09, vg-11, vg-13 — have
  always shared one photo across every size, matching what Amazon itself shows.
  Pre-existing, not introduced here.

### Footer wordmark — `a9a75b5`
The giant CRYSTAL wordmark is gone from all 62 live pages: markup, CSS (rule plus
two responsive overrides), and the three GSAP calls that filled the letters on
scroll and looped the wave layers. Footer now ends at the copyright bar.

Five files (Terms, Career, Privacy, CRYSTAL Light, index-old-v1) carry one extra
`}` in their CSS — verified against HEAD as pre-existing, left alone.

### Videos — `8b5e3fa`
48 products now have a video (was 10). Nine cutlery listings share one brand
video, stored once at `product-photos/_shared/` — copying it per SKU would have
added 145 MB of identical bytes. Playback verified on both a shared and a
per-SKU video; the hover magnifier correctly suppresses while a video shows.

`.git` is now 1.5 GB and GitHub warns about large files. If this keeps growing,
git-lfs or hosting video off-repo is worth considering.

### Not a defect (checked)
The in-app preview browser reports 404s for `proj.leo9studio.in` assets — 128
references across 59 pages, including a 68 MB AV film. The host actually returns
200; the preview browser blocks external origins. Real visitors load them fine.
Still a third-party dependency: if that staging server goes away, those assets
break.

### Needs a decision (not changed)
- **`vg-10`** (Extra Deep Kadai, rose gold handle) — CTP-EDK-002/003/004 have no
  Amazon link, hotlinked heroes, empty galleries, and 003 (26 cm) and 004 (28 cm)
  share one photo, so the size switcher shows the same image for both. Cannot be
  fixed from Amazon without a link.
- **`CTP-EDK-001`** (22 cm, has a link and local images) sits outside `vg-10`, so
  the size switcher on that group omits 22 cm. May be deliberate — 002-004 are the
  rose-gold-handle line and 001 is not.

---

## 2026-08-24 — Product image hover magnifier

**Commit:** `a7387aa` Add hover magnifier to the product image gallery

Inline zoom (Flipkart/Myntra style) rather than Amazon's lens + side panel, since
the PDP's right column holds the product info and a side panel would cover it.

- `.g-zoom` layer inside `#gMainWrap` repaints the current photo at 2.5x, offset so
  the point under the cursor stays under the cursor. The offset math accounts for
  `object-fit: contain` letterboxing, so it stays correct for non-square photos.
- Cursor is `zoom-in` (the native magnifying glass).
- The `zooming` class is set inside the mousemove handler, not on `mouseenter` —
  `mouseenter` does not reliably fire when the pointer is already inside the box.
- Suppressed while a video is playing; disabled entirely under `(hover: none)` so
  touch devices keep the plain image.

**Verified** at 1280x900: zoom engages with correct background-size/position on
COP-004; suppressed on CPW-001 with its video playing; at the 375x812 mobile preset
the layer is `display:none`, nothing is wired, and the cursor stays default. No
console errors, all gallery requests 200.

## 2026-08-25 — Home v3 page + Amazon wordmark on product pages

### CRYSTAL-Home-v3.html

A full re-build of the home page against the reference at
`proj.leo9studio.in/projects/crystal-wp/`, structure, copy and scroll
choreography included.

Built by a script (`scratchpad/home3/build/build_v3.py`) that swaps only the
body between the first section and the footer of `index.html`, so the support
bar, header, mega menu, search overlay, mobile menu, footer, enquiry wiring and
tweaks panel stay byte-identical to the rest of the site. The old home page's
own renderer script is dropped with the sections it built; two leftovers in the
kept half (the testimonial rail's drag handler and the `initGSAP()` call) had to
go with it or the page threw on load.

Sections and what animates:

| Section | Behaviour |
|---|---|
| Hero | Swiper `cards` stack of 5 videos, GSAP opens it to 100vw/100vh, then swaps to a `fade` loop |
| Since 1971 | Pinned; scroll drives a vertical parallax Swiper and fills the sentence word by word |
| About | Halves fly in, image morphs circle to rectangle, four counters, red line drawn |
| Our Brands | Accordion recolours the section + CTA and refilters the gallery per brand |
| Trusted Partners | 12 logos, grayscale until hover |
| Made in India | Pinned; the inline India map zooms out from a close crop as the dark panel slides in; five tabs drive its slider |
| Resources | Three blog cards, one featured spanning two rows |
| Pre-footer | Image parallax |

Notes worth keeping:
- `SplitText` and `DrawSVG` are premium GSAP plugins. Neither is used: the words
  are split by a small local walker, and the red line animates `strokeDashoffset`
  directly (which is all the reference's DrawSVG call did anyway).
- Every pin is desktop-only via `gsap.matchMedia("(min-width: 1025px)")`. Below
  that the sliders autoplay, which is what the reference does and what keeps iOS
  Safari from fighting pinned sections.
- A vertical Swiper sizes its slides from its container, so an auto-height
  container makes the two chase each other. `aspect-ratio` on the mobile wrap
  grew the page to 26,000,000px; an explicit `height` fixed it.
- The nav pill is transparent until scrolled, which was fine over the old light
  hero but hid the red wordmark against dark video. This page floats the light
  pill from the start.

Assets: 66 files pulled into `home-v3-assets/`. The host answers a JS challenge
with an HTML body even for `.jpg` URLs, so downloads are validated by their first
bytes; the session cookie from a browser that solved the challenge is what gets
curl through. The 68 MB hero film was re-encoded to 12 MB (1280px, CRF 26, no
audio, faststart) and the master is gitignored.

**Verified** at 1440x900: pins created at 870-4470 (split) and 7866-10366 (map),
13/27 words filled at scrollY 2600, map panel mid-slide at 9200, accordion switch
to SparkMate repainted the section to `#6E1A8F` and swapped the gallery to its 5
photos with the CTA pointing at `Brand-SparkMate.html`, counters ended at
50/2000/1000/10Cr. At 390x844: no pins, no horizontal overflow
(`scrollWidth === 390`), hero legible. No console errors at either size.

### Amazon wordmark on product pages

`Product.html` and `enquiry.js` now show the Amazon logo where the word "Amazon"
was printed: in the "Available on:" row and in the Buy Now marketplace modal.

- `brand-logos/amazon.svg` — the official wordmark, 5.5 KB. It shipped without a
  `viewBox`, so it would not scale to a CSS height; one was added from its
  width/height.
- The modal inverts its rows on hover, which would swallow a black wordmark, so
  logos there sit on a small white chip.
- `.mk-row img` was `22x22` square; wordmarks are ~3:1, so it is now
  `height:20px; width:auto`.
- If the file is ever missing the `onerror` handler puts the word "Amazon" back,
  so the link never renders empty.

**Verified** on `Product.html?p=CNS-756`: the logo loads (603x182 natural,
renders 63x19), the link still points at `amazon.in/dp/B0FHKWJ46X`, and Buy Now's
`data-mk` carries the logo path.

### About page — hero and legacy media swapped

The film moved into the hero and the couple cut-out moved into the legacy box.
Both containers needed their inner rules adjusted rather than just their `src`:

- `.hero-couple` was styled for a cut-out (`drop-shadow`, `height:auto`). The
  video gets `aspect-ratio: 16/9`, `object-fit: cover`, rounded corners and a
  real box shadow instead.
- `.legacy-video` is a 16/9 frame with `object-fit: cover`, which would crop the
  couple at the shoulders. The image uses `contain` on white.

**Verified** at 1440x900: hero holds `about-vid.mp4` at 820x461 with
`readyState 4`; legacy holds `hero-couple.webp` (810x656 natural) contained in a
1098x617 frame. No stray `<video>` left in `.legacy-video`, no stray `<img>` in
`.hero-couple`.

## 2026-08-25 (2) — Home v3 scroll fixes, About hero cleanup, git-lfs

### Home v3 — scroll and section sizing

The user reported scroll not working properly and sections looking off.
Three causes, all fixed in the build sources and regenerated:

- **Lenis removed.** Its 1.1s eased scroll fought the wheel on the pinned
  sections; nothing else on the site uses it. The page now scrolls natively.
- **Pinned sections were not viewport-sized.** `split3` (704px) and `map3`
  (941px in an 800px viewport) pinned with the next section showing beneath /
  the heading cut off. Both are now exactly `100vh` on desktop; `map3-right`,
  `map3-left` and `brand3-right` are capped with `min(..vh, ..px)` instead of
  `calc(100vh - var(--v-hdr))`, which had assumed a reserved header.
- **Pin distances shortened** - 4 viewports for 4 slides read as a dead
  stretch; now 0.6x (split) and 1600px (map).

Mobile keeps `height:auto` via the ≤1024px block (the pins never run there).
Verified 1280x800: both pins land (770→2690, 5713→7313), doc 12141→9884,
split and map each fill one clean screen. 390x844: no horizontal overflow,
sections stack, sliders autoplay.

### About page

- Hero's three floating product bubbles removed (markup + intro tween).
- `CRAFTING EVERYDAY ESSENTIALS WITH CARE` fixed at 54px on desktop
  (mobile clamps below 760px unchanged).
- Awards & Recognition: the three stock certificates ("Kristen Kennedy",
  an e-commerce course template) removed - fake-looking credentials on a
  live page. The real HomeShop18 STAR Award now sits in a captioned card.
  Real certificates can be dropped in when the user supplies them.

### git-lfs

`git lfs install` run; `*.zip`, `*.7z`, `*.psd` tracked in `.gitattributes`.
The site-served media (`.mp4`, product photos) is deliberately NOT tracked:
the static site deploys straight from this repo and a host that does not
fetch LFS objects would serve pointer files - every video on production
would break. The 2.4 GB history predates LFS and only shrinks with a
history rewrite + force push, which needs its own decision.

## 2026-08-25 (3) — Home v3: pinning removed entirely

Second scroll complaint on desktop. Root call: pinned sections read as
"scroll is stuck" no matter how they were tuned, so both pins are gone.
The page now scrolls natively end to end (document went 12141px -> 6364px,
0 pin spacers):

- Since-1971: slider autoplays with its vertical parallax; the sentence
  still fills word by word, scrubbed to the section scrolling past
  (`top 75%` -> `bottom 45%`), halves fly in on entry.
- Made in India: the map still settles from a zoomed crop and the panel
  slides in, scrubbed to entry (`top 85%` -> `top 15%`) instead of a pin.
- About/Brands: entry animations are one-shot `once:true` timelines now,
  not scrubbed, so nothing feels tied to the wheel.

Testing note for the future: the site CSS has `scroll-behavior: smooth`,
so a plain `scrollTo()` in a background tab never advances (rAF throttled)
and reads back the old scrollY - it looks exactly like broken scrolling.
Use `behavior:"instant"` when driving scroll from the tools.

## 2026-08-25 (4) — v3 goes live as index.html; all h1/h2 at 54px

### v3 is the home page

`CRYSTAL-Home-v3.html` is gone; its content is `index.html`. Since the
builder used to take its shell from the old `index.html` - which no longer
exists - the pre-v3 page is kept as `home-v3-src/shell-donor.html` purely
as the shell source.

The whole build now lives in the repo at `home-v3-src/` instead of a
scratch folder: `v3_main.html`, `v3.css`, `v3.js`, `india-map-inline.svg`,
`shell-donor.html`, `heading-size.css` and `build_v3.py`. Paths are
relative, so `python home-v3-src/build_v3.py` regenerates `index.html`
from anywhere. **Do not hand-edit index.html** - it is generated.

### Heading size

Every `h1`/`h2` across all 68 pages renders at **54px**, from a block
appended to each page's stylesheet (so it beats the per-section `clamp()`
scales without hunting them down). Below 900px it steps to
`clamp(32px, 8vw, 46px)` - 54px in a 360px viewport overflows any
multi-word heading. `home-v3-src/apply_heading_size.py` re-applies it to
every page; the v3 builder folds the same file in so a rebuild keeps it.

Two overflow fixes came out of this:
- `overflow-wrap: break-word` on headings and `min-width: 0` on the v3
  flex columns - a flex child defaults to `min-width:auto` and widens its
  track rather than wrapping, which pushed the map panel past the viewport.
- `.v3 { overflow-x: clip; }` - the red-line SVG is deliberately oversized
  (viewBox runs to x=2006) and the entry animations start elements off to
  the right, which grew a 130px horizontal scrollbar. `clip`, not `hidden`,
  so no scroll container is created.

**Verified** at 1280x800 on index/About/Cookware: every h1/h2 computes to
54px, `scrollWidth` 1265 vs 1280 viewport (no horizontal scroll). At
390x844: 32px headings, `scrollWidth` exactly 390.

## 2026-08-25 (5) — About: The Crystal Story cards halved

Each milestone was a full-width card with a 2:1 photo and a two-column
body, so one card filled the screen. Now two fit per viewport:

- `.ms-row` becomes `grid-template-columns: repeat(2, 1fr)` (single column
  under 860px) instead of a vertical flex stack.
- Photo goes 2:1 -> 16:9 and `object-fit: contain` -> `cover`; contain left
  letterbox bars once the card narrowed.
- `.ms-body` stacks instead of sitting metric-beside-text; icon 52->40px,
  metric 33->22px, heading 20->16px, copy 15->13.5px.
- The red rail is hidden: it ran down the left of a single column and no
  longer threads the dots in a two-column layout. Each card keeps its dot.

**Verified** 1280x800: two 542x483 cards per row, `scrollWidth` 1265.
390x844: single column, 415px cards, `scrollWidth` exactly 390.

### Deploy confirmed

Live `index.html` is now 371754 bytes (`last-modified` 06:55 UTC) - the v3
page. The earlier check that showed 104875 bytes was the pre-push build.

## 2026-08-25 (6) — Awards & Recognition restored and gridded

The three certificates are back at the user's request (I had pulled them
as stock-looking placeholders; that call was theirs to make). The section
also stopped leaving two-thirds of its width empty:

- `.ritems` is a `1.35fr repeat(3, 1fr)` grid instead of a flex row, so
  the award card and the three certificates fill the row - 2-up under
  980px, single column under 560px.
- Certificates get their own card treatment (`.cert-card`) matching the
  award card, each image `width:100%; height:120px; object-fit:contain`
  so the landscape scans fill their card without distortion.
- Trophy fixed at 120px so all four cards share a height; hover lift added
  to match the story cards.

**Verified** 1280x800: four cards at 324/240/240/240px, all 154px tall,
row 1114px wide, `scrollWidth` 1265. 430px: single column, no overflow.
