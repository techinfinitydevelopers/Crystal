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

### Needs a decision (not changed)
- **3 dead `amazon_link`s** — Buy Now sends the customer to a 404:
  `CL-804`, `CLMK-015`, `CWB042`. Their product pages and images are fine.
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
