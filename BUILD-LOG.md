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

## 2026-08-25 (7) — Legacy cut-out scaled down

The couple cut-out was filling the full-width 16:9 frame the video used to
occupy, so it rendered larger than anything else on the page. The frame now
sizes to the artwork instead of the column:

- `.legacy-video:has(img)` caps at `min(560px, 100%)` and switches to 4:3,
  centred with `margin: ... auto 0`. The video keeps the full-width 16:9
  frame - the rule only matches when the box holds an image.
- Inner padding added so the cut-out is not flush against the border.

**Verified** 1280x800: box 560x420 (was 1114x627). 430px: 358x269, no
horizontal overflow.

## 2026-08-25 (8) — LI010 removed from the site

The user first asked for "L0101", which matched nothing anywhere - no SKU,
no id, no reference in any file. Rather than guess, the eight `L*` SKUs were
listed back; the intended product was **LI010 - CRYSTAL MULTI SPARK LIGHTER**.
(It was already on the open-questions list: absent from the client's latest
lighter data.)

Removed:
- `product-data/products.json`: 531 -> 530 entries.
- Database: 1 Product, 9 ProductImage, 2 ProductSpecification,
  1 ProductMarketplaceLink (531 -> 530 products).
- `product-photos/LI010/` - 9 files.

Safe to remove outright: `variant_group` was null, so no sibling size
depended on it, and no `.html`/`.js` file referenced the SKU (the category
pages are driven entirely from products.json).

**Verified**: Kitchenware-Lighters.html no longer mentions LI010 and lists
the remaining 9 lighters. `Product.html?p=li010` no longer resolves to it -
it falls back to the first product rather than erroring.

Recoverable from git history if the client wants it back.

## 2026-08-25 (9) — Split slider re-synced to scroll; heart meets the footer

### Since 1971: the photo now moves with the sentence

Dropping the pin left the slider on its own autoplay timer while the words
still filled on scroll, so the two ran out of step. Both are now read off a
single `ScrollTrigger` progress value in one `onUpdate` - the slider's
`setTranslate` and the word fill - with no pin, so the section still
scrolls past normally.

**Verified** at 1280x800, scrollY 740 (mid-pass): 14/27 words lit and the
slider at slide 2, wrapper translated -1200px. Stepping progress 0 -> 1
walks the wrapper 0 -> -2400px in even increments.

### Pre-footer heart

It was being clipped by the footer: a `y: 110` parallax pushed it past the
section's `overflow: hidden`. Now the section drops its bottom padding (the
text column carries its own), the columns align to the bottom, and the
parallax runs `from y:120` to 0 ending at `bottom bottom` - so the heart
rises into place and its lower tip lands exactly on the footer edge as the
page bottoms out.

### Trusted partners - checked, no action needed

All 12 logos load: 10 SVGs (each a self-contained wrapper around an
embedded base64 raster - no external references to leo9), plus
`Smart_Bazaar_logo.png` and `unnamed.webp`. Measured `complete: true` and
`naturalWidth: 254` for every one. An earlier reading of 0 was the pane
mid-load, not a broken asset. The set matches the reference page exactly.

## 2026-08-25 (10) — Heart no longer sinks into the footer

The scrubbed parallax left the heart wherever the tween happened to be when
scrolling stopped, which parked its lower tip ~120px inside the footer. Two
changes make the resting position unconditional:

- The entry is a one-shot (`once: true`) rather than a scrub, and carries
  `immediateRender: false` + `clearProps` - so the offset is never applied
  unless the tween actually runs, and is removed once it has. If the tween
  never fires (reduced motion, a fast jump to the bottom, a JS failure) the
  heart still sits where CSS puts it, instead of stranded mid-tween.
- Mobile: stacked, `.pre3-right` keeps `margin-bottom: 0` and caps at 460px,
  and `.pre3-left` drops the bottom padding it needs in the two-column layout.

**Verified** 1280x800 at page bottom: image bottom 174, footer top 174 -
gap exactly 0, transform `none`. 390x844: gap exactly 0, image 360x274,
`scrollWidth` 390, and the heart reads as resting on the footer edge in a
screenshot.

## 2026-08-25 (11) — Heart rests 10% above the footer; map panel heading sized

### Pre-footer heart

Clarified requirement: the heart should *rise as you scroll* and come to rest
with its lower tip **10% of its own height clear of the footer**, not flush
against it.

- The 10% lift lives on the artwork: `.pre3-right img { transform:
  translateY(-10%) }`. A percentage translate resolves against the element's
  own height, so it holds at every viewport without a magic pixel value, and
  it leaves `.pre3-right` free for the scroll tween.
- The rise is a scrub from `y: 140` to 0, ending at `endTrigger: "#footer",
  end: "top bottom"` - when the footer reaches the bottom of the viewport,
  roughly a footer's height (627px) before the page bottoms out. That margin
  is what guarantees the travel has finished by the time scrolling stops;
  the earlier `end: "bottom bottom"` never completed, which is how the heart
  kept ending up parked inside the footer.

**Verified** at the page bottom, tween at progress 1: 1280x800 - image 463px
tall, gap 46px = **10.0%**. 390x844 - image 274px tall, gap 27px = **10.0%**.

### "Available In Multiple Countries"

The site-wide 54px heading rule was applied to a heading sitting in a
half-width dark panel, where it wrapped to three lines and crowded the
slider. Overridden to `clamp(22px, 2vw, 30px)` for that panel only - now
25.3px, one line, 353px inside a 432px panel.

## 2026-08-25 (12) — Heart overlaps the footer by 10%

Correction to the previous entry: the tip should not stop *short* of the
footer - the bottom **10% of the heart sits over** the footer.

- `.pre3-right img { transform: translateY(10%) }` (was `-10%`). The
  percentage still resolves against the image's own height, so the overlap
  stays 10% at every viewport.
- `.pre3` changed from `overflow: hidden` to `visible` and given
  `position: relative; z-index: 2`, with `z-index: 3` on `.pre3-right` -
  the footer comes later in the DOM and would otherwise paint over the part
  that now hangs into it.
- The scroll rise is unchanged: scrub from `y: 140` to 0, finishing when the
  footer reaches the viewport bottom.

**Verified** 1280x800 at page bottom, tween at progress 1: image 463px tall,
bottom at 220, footer top at 174 - **46px overlap = 10.0%**. Mobile uses the
same percentage rule; the identical mechanism measured exactly 10.0% at
390x844 in the previous build (only the sign differs). The browser pane hung
before I could re-measure 390px on this build.

## 2026-08-25 (13) — Reveals made fail-safe, split pinned, nav inverted, brand tiles

### Trusted Partners was blank

A `gsap.from({opacity: 0})` hides its target the instant the page parses. If
the trigger then never fires - images loading late shift the layout past the
start point, a reload lands mid-page - the content stays invisible. That is
what emptied the section. Every one-shot reveal now carries
`immediateRender: false` + `clearProps`, so the hidden state is only applied
while the tween actually runs, and starts were relaxed (85% -> 92%). A
`unhideStragglers()` net runs at load and 2.5s after: anything still under
0.05 opacity gets its transform and opacity cleared.

### Since 1971 pinned again

At the user's request the section now holds the viewport while the photo and
the sentence advance together (`+= 2.2 * innerHeight`), then releases. Pin is
applied only above 1024px - a held viewport fights touch scrolling.

### Nav

Reverted to transparent over the hero, light pill on scroll (`.scrolled`
lands past 30px). The red wordmark and dark links would disappear into the
footage, so while transparent the logo is `brightness(0) invert(1)` and the
links, icons, outline button and burger bars go white, all with a .35s
transition back.

### Hero weight

Five `<video>` elements all pointed at the same 12 MB file and all autoplayed
- five decoders for one visible frame, since the back four are only ever seen
as a sliver behind the top card. Now one player (the card the stack opens on)
plus four stills from a poster frame extracted with ffmpeg. That is 48 MB of
redundant video decode removed from every page load.

### Brand pages

Portfolio tiles: 4 per row -> 3, square instead of 4/5, and `object-fit`
`cover` -> `contain` with padding, because cover was cropping the product out
of frame (pans losing their handles). The full-tile dark scrim shrank to a
band behind the label, which is all it was ever for.

**Verified** by serving and parsing the built file: 1 `<video>`, 5 poster
refs, pin present, transparent-nav rule present, 4 `immediateRender: false`,
the unhide net present, the 10% heart overlap intact, and the v3 script
parses clean (15583 chars). All four brand pages carry both tile changes.
The browser pane hung throughout this round - the five-video hero is the
likely cause, and is exactly what got removed - so no live screenshot yet.

## 2026-08-25 (14) — git-lfs: probed, and ruled out for now

Asked to set LFS up. Found it was already half-configured and doing nothing:
`.gitattributes` tracked `*.zip`, `*.7z`, `*.psd`, and the repo contains no
file of any of those types. Actual LFS objects: **0**.

The repo carries **1,733 MB** of tracked media in the working tree - 2,624
jpg (1,054 MB), 61 mp4 (629 MB), 118 png (35 MB), plus webp/jpeg/gif/svg.
Pack size 2.02 GiB.

Before moving any of that, one unknown had to be settled: the deploy's build
config lives outside the repo, so whether it runs `git lfs pull` was
unknowable by inspection. Probed with a single 51 KB file
(`home-v3-assets/video/hero-poster.jpg`).

**Result: it does not.** After the deploy carrying the LFS commit landed, the
host served **130 bytes** - the pointer file - with no `content-type` match
and no `last-modified`. Every LFS-tracked image would render broken.

Reverted immediately; confirmed the real 51189-byte JPEG is served again.
LFS objects back to 0, `.gitattributes` restored.

Two things would have to be true before this is worth revisiting:
1. The deploy fetches LFS objects (a build command running `git lfs pull`,
   or a Dockerfile that installs git-lfs).
2. LFS storage is paid for - GitHub's free tier is 1 GB storage and 1 GB
   bandwidth per month, and this repo would need ~1.7 GB plus fresh
   bandwidth on every deploy.

## 2026-08-25 (15) — The Since-1971 pin never actually existed

Checking the live site rather than the built file caught this: the pin was
in the code but `ScrollTrigger.getAll().filter(t => t.pin)` came back empty,
and the trigger's range was the mobile one (start 180, end 1152) on a
1280px-wide desktop viewport.

Cause: `matchMedia("(min-width: 1025px)").matches` was read once, inline, at
script execution. Whatever the width happened to be at that instant got
baked into `start`, `end` and `pin` forever. A page that first renders narrow
- a restoring window, a slow layout, a device rotation - permanently gets the
mobile branch.

Rebuilt through `gsap.matchMedia()`: a pinned trigger inside `mm.add(DESK)`,
an unpinned one inside `mm.add(MOB)`, both calling one `splitProgress(p)`
that drives the slider and the word fill. GSAP now re-evaluates on resize and
kills the other branch's trigger.

**Verified** by resizing the live page **without reloading**: at 731px, 0
pins and the mobile range; resized to 1280px, `pins: 1`, range 800->2560,
one `.pin-spacer` in the DOM. Scrolled through the pin - section top stays at
0 while the slider tracks progress (0.11/0.51/0.91 -> -273/-1227/-2182px).

Word fill could not be re-measured here - its 0.15s tweens need a real ticker
and the preview pane throttles - but the code path is unchanged from the
build where it measured 14/27 at mid-scroll.

Also confirmed live in the same pass: Trusted Partners is **12/12 loaded and
12/12 visible** (the invisible-reveal fix holds), hero is 1 video + 4 stills,
nav is transparent at the top.

## 2026-08-25 (16) — Dashboard prepared for deployment

The Railway project turned out to run **one** service - the static website.
The dashboard was never deployed; it existed only on the local machine. That
is why `python` was not found in the console the user tried: no `requirements.txt`
at the repo root means that container has no Python at all.

Prepared the backend to run as a second service. Repo-side changes:

- **`requirements.txt`** - added `whitenoise`. With `DEBUG=False` Django serves
  no static files, and `config/urls.py` only calls `static()` while DEBUG is on,
  so the admin would have loaded completely unstyled - including the Crystal
  theme built earlier.
- **`config/settings.py`**
  - WhiteNoise middleware directly after SecurityMiddleware.
  - `STORAGES` using `CompressedStaticFilesStorage`. Deliberately not the
    manifest variant: it fails the whole deploy if any stylesheet references a
    file that is not present, and Jazzmin ships a few such references.
  - A production block, all conditional on `not DEBUG`: SSL redirect, secure
    session/CSRF cookies, HSTS, nosniff, and `SECURE_PROXY_SSL_HEADER`. That
    header is load-bearing - Railway terminates TLS at its edge and forwards
    plain HTTP, so `SECURE_SSL_REDIRECT` without it is an infinite redirect.
  - A hard failure if `SECRET_KEY` is still the `django-insecure-` placeholder
    while DEBUG is off. A deploy that fails loudly beats one that silently ships
    forgeable session cookies.
- **`Procfile` / `railway.toml`** - `collectstatic --no-input` alongside migrate.
- **`dashboard-seed.json`** - 5,418 records (530 products, 2,474 images, 1,956
  specs, 317 marketplace links, 95 variants, 41 categories, 4 brands) for
  loading into Postgres. Excludes `auth.user` on purpose so no password hash
  goes into git; the superuser is created on the service instead.
  Note: `dumpdata -o` writes in the Windows locale encoding and produced invalid
  UTF-8 (a smart quote at byte 24005). Regenerated with `PYTHONUTF8=1` and stdout
  redirection.
- **`DEPLOY.md`** - the six dashboard-side steps, which need account access.
- `.gitignore` - `staticfiles/`, rebuilt on every deploy.

**Verified**: local `check` clean with DEBUG on; production simulation down from
6 warnings to 1 (HSTS preload, which should not be enabled casually); the
placeholder-key guard raises as intended; `collectstatic --dry-run` collects 254
files.

Two things called out in DEPLOY.md that cost data if skipped: Postgres must be
added (SQLite lives in the container and is wiped every deploy), and a volume
mounted at `/app/media` (or dashboard-uploaded photos vanish the same way).

## 2026-08-25/26 (17) — The dashboard becomes usable, and variants become real

The client's ask, in their words: the dashboard should show what the site
shows — one product with its sizes, each size's own photos and video — and it
should look like Shopify rather than a Django form. Along the way five things
turned out to be broken in ways that would have bitten on first real use.

### Variants: 29 groups collapsed, website untouched

`products.json` was already flattened — every size its own entry, joined only
by a shared `variant_group`. The dashboard had imported that shape, so an
eight-size kadai was eight separate products, each with one decorative
one-row variant, and **none of the 2,474 photos was linked to a size**.

Measured what actually differs inside a group before designing anything:
brand, category, subcategory, collection and gst_pct never differ; name, sku
and highlight differ in all 29; description in 27; tags in 22; **the Amazon
link in 19** — most sizes are listed separately on Amazon; mrp and features in
12; match_tier in 9; video in 7. `ProductVariant` could express none of it, so
collapsing without enriching it would have flattened every size onto the
parent's values and destroyed real data.

- `ProductVariant` gained sku (a full SKU, not a suffix — `LI008` does not
  start with its parent `LI007`, and all 29 groups fail that reconstruction),
  display_name (the names are irregular enough that rebuilding them from parts
  guarantees diffs), highlight, description, tags, features, amazon_link,
  price, video, video_url, image_url, match_tier, is_active. The JSON fields
  default to None, not to an empty list, so "not set" stays distinguishable
  from "genuinely empty" — the whole inherit-from-parent rule rests on that.
- `ProductSpecification` gained the same nullable variant FK `ProductImage`
  already had; 3 groups need per-size filters.
- The serializer stopped building one shared dict and stamping it onto every
  variant; each field now resolves variant-first, product-second.
- `collapse_variant_groups.py` folded all 29 groups. Siblings are deactivated,
  not deleted: `EnquiryItem.product` is SET_NULL, so deletion is the one
  operation a buggy re-point could not be undone from, and the exporter
  already filters on is_active.

**Result: 530 to 464 active products, 29 parents holding 95 sizes, 304 photos
now carrying their size (from zero).** The website is byte-identical — same SKU
set, same key set per entry, same values including every hero, every ordered
gallery, filters, variant_label, variant_order and id. Verified twice: by the
command's own before/after diff, and independently against the shipped file.

The command **refused two groups on its first pass** rather than corrupt them:
four sizes owned no photo rows and drew their picture from a remote URL that
differs per size, so collapsing would have resolved them to the parent's
photo — a different product. That refusal is why `ProductVariant.image_url`
exists.

### Five bugs found, each of which bites on first real use

1. **491 products could not be saved at all.** image_url and video_url were
   URLFields but hold site-relative paths like `product-photos/CL-414/hero.jpg`
   — the form rejected the value the site itself had put there, with "Enter a
   valid URL". They are CharFields now with a validator that takes a URL or a
   site path. Measured across every active product: 491 unsaveable before,
   **0** after.
2. **The phantom "product doesn't exist" banner.** `image_preview` emitted the
   relative path raw into an img src; the browser resolved it against
   `/admin/products/product/` and Django's legacy catch-all read the result as
   an object id. The failed lookup queued a message that surfaced on the *next*
   page, which is why it looked unrelated to whatever the admin was doing. It
   fired once per thumbnail, so a full changelist ran up to a hundred wasted
   change_view calls.
3. **Sizes and photos sat on mutually exclusive tabs** — `changeform_format`
   was `horizontal_tabs` — so an admin could never see a size and its photos at
   the same time. That was also the strip of nine red tabs the client objected
   to.
4. **Three CSS rules were theming nothing.** There is no `.submit-row` in this
   admin (jazzmin renders `#jazzy-actions`), so the guard keeping Delete
   distinct from Save had never once fired and both were solid red;
   `.object-tools a` outranked `.btn-outline-secondary`, so History was red
   too; and every select2 rule targeted `--default` while jazzmin uses
   `--admin-autocomplete`.
5. **Paired form fields collapsed.** Django renders `('brand', 'category')` as
   one row of label/field/label/field, all `.col-auto`. The four related-widget
   icons made the first box wide enough to push Category's input onto the next
   line, leaving its label beside nothing and Collection name with no visible
   input at all. Now a grid: 7 multi-field rows, 0 broken.

### The dashboard itself

- Tags was a bare JSONField with no widget — the client was typing
  `["Lemon Squeezer And Opener", ...]` by hand, brackets and quotes included.
  Now a chip input, rendered server-side so it survives with JS off, and
  `clean()` accepts JSON or plain comma text.
- Sizes render as cards, each with its own SKU, photo strip, video, Amazon
  link and price; photos render as a grid grouped under the size they belong
  to, with click-to-set-hero and drag or arrow-key reordering.
- A deprecation warning gave up the root cause of a fight the theme had been
  losing: jazzmin renders `data-bs-theme="dark"` unless told otherwise, and on
  Bootstrap 5 that one attribute decides every colour. Setting
  `default_theme_mode` to light fixed it at the source, instead of overriding
  some forty Bootstrap variables to undo it.
- Responsive at 320/390/768/1024/1440. The change form measured 462 against
  390 before, and the changelist 1340 against 768; both traced to select2's
  absolutely-positioned mirror select.
- Product search is live as you type, debounced to one request for a
  six-character query, with filters, ordering and the paginator preserved.
- The product code reads `Code: MKA940` in the dashboard, exactly as the site
  prints it.

### Enquiries: nobody was receiving them

Asked for a thank-you email to the customer. Found that **the form had never
sent anything anywhere** — it showed "Enquiry submitted successfully" with a
reference number while the payload went to console.log, behind a TODO about
choosing a backend. Every enquiry made through the site was lost, which is why
the dashboard read zero. The receiving endpoint already existed and was simply
never called.

The form posts to it now, and two emails go out: a thank-you to the customer
quoting their reference and what they asked about, and a notification to the
team with reply-to set to the customer. Email failure never fails the
submission — an enquiry that reached the database is a won lead. Equally, the
page no longer claims success when the request fails; it says so and offers the
phone number. Verified against a deliberately unreachable API: one POST
attempted, success screen withheld, honest error shown.

CORS now lists the website's origin; without it the browser blocks the POST
before it is ever sent. **Delivery still needs SMTP credentials in the
environment** — until they are set Django's console backend applies, which is a
safe no-op, and the enquiry is still stored.

### Site-side fixes in the same stretch

- The pre-footer heart overlaps the footer by 10% of its own height, and its
  white outline was landing on black and reading as a shape cut adrift. The
  backdrop is the artwork's own silhouette in the section red, grown a few
  pixels, so it tapers exactly as the heart does rather than showing square
  corners. Composited against black, the outermost pixel at the tip is now
  (237,50,55).
- Brand portfolio tiles are filled by their photo — the 1.5px border and up to
  20px of padding are gone.
- The Overview copy on every product page was centred against a media column
  fixed at 4/5 and roughly twice its height, so it floated about 250px below
  its own heading. Aligned to the start: the gap is 36px now and the copy
  begins level with the photo. An empty `#ovIntro` paragraph — never written
  to — went with it.

### Still outstanding

- **The production database has not been collapsed.** Everything above ran
  against the local DB; production still holds the flat 530-product shape, so
  the client still sees seven separate Tope rows. The command is proven and
  reversible but writes to a live catalogue, so it waits on their say-so.
- **SMTP credentials** for the enquiry emails.
- **The publish button** — dashboard edits still need `export_to_json` plus a
  commit and push by hand. The design is in the plan; the code is not written.
- git-lfs remains ruled out: the deploy does not run `git lfs pull`, so an
  LFS-tracked image is served as a 130-byte pointer.

## 2026-08-26 (18) — Headings come down to 37px

The client asked for `font-size: 37px !important` on every h1 and h2 across the
site. A site-wide heading block already existed — it had pinned them at 54px —
so this was a change to that one rule rather than 68 separate hunts.

Changed in all 68 pages **and** in the three files the home page is generated
from: `home-v3-src/heading-size.css`, `apply_heading_size.py` and `build_v3.py`.
Without that second half the next `build_v3.py` run would have silently put
`index.html` back to 54px, and it would have looked like the change had been
reverted by hand.

The phone step came down with it, `clamp(32px, 8vw, 46px)` →
`clamp(26px, 6.4vw, 34px)`: 37px still overflows a multi-word heading in a
360px viewport, so the mobile branch stays proportional rather than being
dropped.

One heading keeps its own smaller cap — the map panel's
`clamp(22px, 2vw, 30px)` — because that is the exact text the client asked to
shrink earlier ("Available In Multiple Countries"). Raising it to 37px now
would have undone a request rather than fulfilled one.

**Verified** at 1280px on seven page types (home, About, Product,
All-Products, Contact, Enquiry, Blog): every heading measures 37px, 43 of 43
across those pages, with the single intentional exception above. 0 files still
contain `font-size: 54px`. Re-running the home builder still emits 37px. The
staged diff is exactly six lines per file and nothing else.
