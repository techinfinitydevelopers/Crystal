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

### Still open
- ~219 scraped products not yet wired into `products.json` — waiting on SKU tables.
- Product-image hover magnifier: awaiting a choice between a lens + side-panel
  (Amazon style) and inline background-position zoom (Flipkart style).
