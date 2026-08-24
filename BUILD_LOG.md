# Build Log

## 2026-08-17 — Cooktop.html & Lunch-Box.html standalone category pages

**Task:** Replace `All-Products.html?cat=cooktop` / `?cat=lunch-box` deep-links with two dedicated, SEO-friendly standalone pages. Requested by site owner via developers@techinfinity.io context; part of a broader effort splitting `All-Products.html` into per-category pages (see `memory.md` for the reusable pattern — sibling pages for other categories were created in parallel by other sessions).

**Files created:**
- `Cooktop.html` — 17 products (`category === "cooktop"`), filters/facets: Burners (`size`), Type (Gas Stove/Hob Top/Infrared/Induction), Material (all Glass, so hidden — no variance).
- `Lunch-Box.html` — 0 products in `product-data/products.json`; built as an honest "coming soon" teaser page with a custom empty-state card + CTA to `Contact.html`, rather than a broken/blank listing.

**Key implementation decisions:**
1. Filtered `data.products` to the target category inside each page's own `loadCatalog()` fetch mapping (not just via `state.cat` post-filtering) — this makes hero tiles and the "Shop by category" grid scope correctly too, not just the product grid.
2. Cooktop has no real product photos in the data (`hero: null` for all 17 SKUs — pre-existing gap, not introduced here). Used two genuinely on-topic images already in the repo (`about-assets/about-3-cooktop.webp`, `about-assets/prod-1.jpg`, both real Crystal glass-top gas stove photos, visually confirmed) as an alternating fallback instead of the generic placeholder, so hero tiles show real cooktop imagery instead of collapsing to one oversized duplicate tile.
3. Fixed a latent facet-label gap while at it (page-local only, doesn't touch `All-Products.html`): `ATTR_LABELS` was missing a `size` label and mislabeled `type` as "Shape" (leftover from cookware/knife copy) — relabeled to "Burners" / "Type" in `Cooktop.html`'s own script copy.
4. For Lunch-Box: hid `.browse-bar` (sort/count meaningless at 0 items) and set the tweaks-panel `DEF.showCategoryNav = false` for this page only, since the generic "Shop by category" section would otherwise render visibly empty (no category matches with 0 products).
5. Removed the `?cat=/?sub=` URL-parsing IIFE from both pages' scripts (dead code once the category is hardcoded) and hid the top-level `#chips` category-switcher row (redundant on a single-category page); `#attrChips` was left untouched — it already auto-scopes to the single active category.
6. Left all shared chrome (header incl. mega-menu links to `All-Products.html?cat=...`, mobile menu, footer, tweaks-panel, `enquiry.js`) byte-for-byte identical to `All-Products.html`, per instruction — cross-page nav updates are a separate follow-up owned by the site owner.

**Verification (via `product-data/products.json` + local server on port 4567 + browser tool JS checks, not visual screenshots — screenshot compositing was unavailable in this environment session):**
- Cooktop: 17/17 `.pcard` elements render, `#count` reads "Showing 17 of 17 products in Cooktop", 2 distinct hero tiles, `#catGrid` shows a single "Cooktop · 17 products" card, `#chips` present but hidden, `#attrChips` shows `size`/`type` groups only (material filtered out — all "Glass"), grid is single-column with no horizontal overflow at 390px, 4-column grid at desktop width, no console errors (only a pre-existing cosmetic GSAP-timing warning also reproduced on unmodified `All-Products.html`, confirmed not a regression).
- Lunch-Box: 0 `.pcard` elements, `.empty-soon` card renders with the intended coming-soon copy + "Get in Touch" CTA to `Contact.html`, `.browse-bar`/`#categories`/`#chips` all `display:none`, `#attrChips` empty, no console errors, no horizontal overflow at 390px.
- Note for whoever verifies next: this session's browser-pane tabs were observed being shared with other concurrent agent sessions on this same repo (a stale tab briefly showed an unrelated "Water Bottles" page mid-verification) — always open a fresh tab and assert `document.title`/`location.href` before trusting further reads on it.

**Not touched (per instructions):** `All-Products.html`, `product-data/products.json`, any other existing page, and cross-page nav links (mega-menu / mobile accordion / footer still point at `All-Products.html?cat=cooktop`/`?cat=lunch-box` everywhere except within these two new pages' own body content).

## 2026-08-17 — v2 visual facelift for `Cookware.html` & `Kitchenware.html`

**Task:** CSS/typography-only visual refresh of the two dedicated category-listing pages to match `index-v2.html`'s premium design language (font, heading weight/tracking, eyebrow pill, button/chip softness, product-card radius+shadow). No JS/filtering/product-data/HTML-structure changes.

**Edits applied identically to both files:**
1. Google Fonts `<link>` swapped from DM Sans + Space Grotesk to Inter (`wght@400;500;600;700;800;900`).
2. `--head`/`--body` custom properties → `"Inter", sans-serif`.
3. `body` rule gained `letter-spacing: -0.003em`; `h1,h2,h3,h4` rule changed `font-weight: 700 → 800` and `letter-spacing: -0.02em → -0.03em` (mirrors index-v2's final cascaded values). `html { scroll-behavior: smooth }` was already present, untouched.
4. `.eyebrow` gained `padding: 6px 14px 6px 10px; border-radius: 100px; background: rgba(237,51,56,0.08)`.
5. `.btn` padding/font-size tightened to `16px 28px` / `14.5px`; `.btn-red` box-shadow softened to `0 14px 32px -16px rgba(237,51,56,0.55)`.
6. `.chip:hover`/`.chip.active`/`.fbtn:hover`/`.fopt.active` each gained a subtle colored/dark box-shadow (premium hover/active feel on the filter pills — all were already `border-radius:100px`, no change needed there).
7. `.pcard` border-radius changed from `var(--r)` (tweaks-panel-controlled, default 20px) to a fixed `26px`; `.pcard:hover` box-shadow softened/enlarged to `0 36px 80px -36px rgba(15,15,15,0.5)` (was `0 32px 58px -34px rgba(15,15,15,0.42)`). Existing hover translateY/scale/border-color transitions left untouched.
8. Header/nav untouched (already shares `var(--head)`/`var(--body)`, picks up Inter automatically).

**Verification (local server port 4567, browser-tool JS checks — visual screenshot compositing unavailable in this session, same environment limitation as the Cooktop/Lunch-Box build):**
- Desktop (1280-1440px) and mobile (390px), both pages: `getComputedStyle(document.body).fontFamily` = `"Inter, sans-serif"`; `.pcard` computed `border-radius` = `26px`; `.btn` computed `border-radius`/`padding` = `100px` / `16px 28px`; `document.documentElement.scrollWidth === window.innerWidth` at 390px (no horizontal overflow) and at desktop widths.
- Product counts intact: Cookware "Showing 88 of 88 products in Cookware" (88 `.pcard` elements); Kitchenware "Showing 296 of 296 products in Kitchenware" (296 `.pcard` elements).
- Filtering still works: clicked a Kitchenware category chip ("Lighters") — correctly re-rendered to 10/296 products, chip got `.active`.
- No console errors on either page at either viewport.
- Noted (not a defect): both pages' hidden dev tweaks-panel defaults `DEF.type` to `"editorial"`, which applies `body.tv-editorial` and overrides the `h1-h4` base rule to weight 500/`letter-spacing:-0.012em` — this is pre-existing shared behavior, identical on `index-v2.html` itself (same default), so headings render consistently between old and new pages either way.

**Not touched:** `index-v2.html`, `All-Products.html`, any other file; no JS logic, product data, filtering behavior, or HTML structure/content changed on either page.

## 2026-08-17 — 6 standalone Cookware sub-category pages

**Task:** Build one dedicated v2-style page per Cookware sub-category (in addition to `Cookware.html`), using `Cookware.html` itself (already v2-faceli­fted) as the starting template rather than the older `All-Products.html`, per site-owner request via developers@techinfinity.io context.

**Files created:** `Cookware-Tripro.html` (43 products), `Cookware-Cast-Iron.html` (4), `Cookware-Non-Stick.html` (29), `Cookware-Non-Stick-Mini.html` (5), `Cookware-Sandwich-Bottom-Steel.html` (6), `Cookware-Hard-Anodised.html` (1). Counts confirmed against `product-data/products.json` (`category==="cookware"` grouped by `subcategory`; total 88, matches sum). None were 0 products, so no "coming soon" empty-state was needed (pattern from `Lunch-Box.html` reviewed but unused this round).

**Method:** Wrote a one-off Node script (scratchpad, not committed) that read `Cookware.html` verbatim and applied the same 13 targeted string replacements to each of the 6 outputs — safer than 6x manual copy-paste-edit for an 97KB file with repeated similar phrases (`mustReplace` helper throws if a pattern isn't found exactly once, catching drift immediately).

**Key implementation decisions:**
1. Added a `FIXED_SUB` constant next to the existing `FIXED_CAT = "cookware"` and changed the one-line `catProducts` filter to `P.filter(p => p.c === FIXED_CAT && p.sub === FIXED_SUB)` — this is the only functional JS change needed; because `Cookware.html`'s hero tiles / `#catGrid` / `#colGrid` / grid / counts were already all derived from this single `viewProducts` variable (unlike `All-Products.html`'s `?cat=` path, which only re-filters the grid post-hoc — see `memory.md`), scoping cascaded for free.
2. Hid `#chips` (subcategory switcher — pointless when the page's product set IS one subcategory) via `style="display:none"` inline on the existing empty div; left `#attrChips` (induction/set/shape facets) fully functional — all 6 subcategories share the same 3 filter facet keys (`induction`, `set_type`, `type`) per `filters{}` in the data.
3. Set `state.subLabel` at init time (was `""`) to the sub-category's display label (e.g. `"Tripro"`) purely for the `#count` text ("Showing 43 of 43 products in **Tripro**" instead of the less useful generic "...in Cookware") — low-risk, since `subLabel` has no other reader and the chip UI that used to set it dynamically is now hidden/unused.
4. Rewrote per-page: `<title>`, `<meta name="description">`, `heroPreTxt`, `heroTitle` (h1), `heroSub`, `catLead`, `colTitle`, `colLead`, `browseTitle`, `ctaTitle`, `ctaSub` — all sub-category-specific, tone/facts cross-checked against `About.html` (e.g. no DuPont/certification claim added for Non-Stick since it's a historical company-milestone claim in `About.html`, not tied to current product data — grep of `products.json` confirmed zero "dupont" mentions, so left out to avoid fabricating a claim).
5. `Featured Collections` section (`#colGrid`) will only ever render **1 card** on each of these pages (each sub-category's products all share exactly one `collection` value in the data, e.g. tripro→"Triply", cast-iron→"CAST IRON") — a pre-existing site-wide default (`DEF.showCollections: false` in the tweaks panel) already hides this section out of the box, so the single-card look never actually ships visibly; not treated as a defect, matches `Cookware.html`'s own out-of-the-box behavior.
6. "Shop by category" section (`#catGrid`) — left mechanically identical (single "Cookware" tile whose count now reflects the sub-scoped total): confirmed this is *already* how `Cookware.html` behaves today (its own `catsInView` also always resolves to exactly one "Cookware" tile, since its `viewProducts` is already category-filtered before that computation runs) — not a new limitation introduced by this change.
7. No breadcrumb/back-link added: confirmed via grep that `Cookware.html` has no breadcrumb component to port forward (task said to update one "if Cookware.html has one").
8. Header/nav/footer/tweaks-panel/CSS copied byte-for-byte unchanged, per instructions; mega-menu and mobile-accordion links to `All-Products.html?cat=cookware&sub=...` deliberately left as-is (site owner will decide separately whether to point them at these new standalone pages instead).

**Verification (existing dev server on port 4567 — port 4567 was already occupied by a live server at task start rather than free, so reused it directly instead of starting a duplicate on 4591; browser-tool JS checks, not visual screenshots — screenshot compositing unavailable in this environment session, consistent with prior sessions' note in `memory.md`):**
- All 6 pages, desktop (1440px) and mobile (390px): `getComputedStyle(document.body).fontFamily` = `"Inter, sans-serif"`; `document.documentElement.scrollWidth === window.innerWidth` (no horizontal overflow) at both viewports; `#chips` computed `display: none`; zero console errors on any page at either viewport.
- Product counts verified against both the DOM (`#count` text + `.pcard` count) and a fresh `products.json` re-filter: Tripro 43/43, Cast Iron 4/4, Non-Stick 29/29, Non-Stick Mini 5/5, Sandwich Bottom Steel 6/6, Hard Anodised 1/1 (spot-checked the single Hard Anodised card's name against SKU `cns-098` — "CRYSTAL ALUMINIUM HARD ANODISED TADKA PAN, MULTICOLOUR", matches).

**Not touched (per instructions):** `Cookware.html`, `index-v2.html`, `All-Products.html`, `product-data/products.json`, any other existing page.

## 2026-08-17 — 9 standalone Electric Appliances sub-category pages

**Task:** Build one dedicated v2-style page per Electric Appliances sub-category (in addition to `Electric-Appliances.html`), using `Electric-Appliances.html` itself (already v2-facelifted) as the starting template, per site-owner request via developers@techinfinity.io context.

**Files created:** `Electric-Appliances-Chimney.html` (0 products), `Electric-Appliances-Kettle.html` (4), `Electric-Appliances-Iron.html` (0), `Electric-Appliances-Ice-Cream-Maker.html` (0), `Electric-Appliances-OTG.html` (2), `Electric-Appliances-Air-Fryer.html` (0), `Electric-Appliances-Rice-Cooker.html` (1), `Electric-Appliances-Food-Processor.html` (1), `Electric-Appliances-JMG.html` (2). Counts confirmed against `product-data/products.json` (`category==="electric-appliances"` grouped by `subcategory`): 4+2+1+1+2 = 10, matches `Electric-Appliances.html`'s total exactly; 4 of the 9 subs (Chimney, Iron, Ice Cream Maker, Air Fryer) are currently 0-stock.

**Method:** One-off Node script in the session scratchpad (not committed) reading `Electric-Appliances.html` verbatim and applying ~20 targeted "must-match-exactly-once" string replacements per output file — same approach as the 6 Cookware sub-pages. Hit and fixed a CRLF line-ending bug on the first run (multi-line search strings written with `\n` didn't match the file's actual `\r\n` line endings — normalized to `\n` for searching, converted back to `\r\n` on write). See `memory.md` for the reusable gotcha note.

**Key implementation decisions:**
1. Added `PAGE_SUB` next to the existing `PAGE_CAT` const; changed the one-line `loadCatalog()` fetch filter to `.filter(p => p.category === PAGE_CAT && p.subcategory === PAGE_SUB)` — the only functional JS change needed, since hero tiles / `#colGrid` / `#grid` / counts already all derive from this one `viewProducts` variable.
2. `Electric-Appliances.html`'s tweaks-panel `DEF` already ships `showCollections`/`showBrandValue`/`showCTA: false` out of the box (only `showCategoryNav`/`showMarquee` are on by default) — flipped `showCategoryNav` to `false` on every sub-page (the "Shop by type" 9-tile switcher grid doesn't make sense on a page already scoped to one type; the section stays in the DOM, just hidden, so no HTML/JS removal was needed). Hid `#chips` (the subcategory pill-switcher row) via inline `style="display:none"` for the same reason — both are switchers between the other 8 sibling subcategories.
3. Set `state.subLabel`/`subText` at init to the sub's label/slug so `#count` reads "Showing 4 of 4 products in Kettle" instead of generic "...in Electric Appliances".
4. Rewrote per-page `<title>`, `<meta name="description">`, `heroPreTxt`, `heroTitle`(h1), `heroSub`, `catLead`, `colTitle`, `colLead`, `browseTitle`, `ctaTitle`, `ctaSub` — tone/facts cross-checked against `About.html` (1971 founding, "trusted since"/"Made in India" language already used site-wide) and `Electric-Appliances.html`'s own copy; no certifications or specs invented.
5. **New empty-state pattern (upgrade over `Lunch-Box.html`'s single-branch version):** split the `if (!list.length)` grid branch into two cases. Genuinely 0-stock sub (`!viewProducts.length`) → ported `Lunch-Box.html`'s `.empty-soon` card CSS (didn't exist yet in `Electric-Appliances.html`, added it) with a sub-specific "Coming Soon" message + "Get in Touch" CTA to `Contact.html`. Filtered-to-0 on a page that DOES have stock (attribute facet over-narrowed) → a distinct "No Matches" card with a "Clear Filters" button wired to reset `state.attrFilters` and re-render. Avoids ever showing a broken/blank state.
6. No breadcrumb existed on `Electric-Appliances.html` to port forward, so repurposed the hero's secondary CTA button (previously "Featured Collections", a section that's hidden by default anyway) into a back-link: `← All Electric Appliances` → `Electric-Appliances.html`.
7. Cosmetic: added `class="active"` to each sub's own link inside the shared mega-menu / mobile accordion "Electric Appliances" group, purely a visual "you are here" highlight — link targets (`All-Products.html?cat=appliances&sub=...`) deliberately left untouched, per instructions that cross-page nav is a separate site-owner decision.
8. Header/nav/footer/tweaks-panel/CSS copied byte-for-byte unchanged from `Electric-Appliances.html` otherwise, per instructions.

**Verification (existing dev server already running on port 4567 from a concurrent session — reused it directly rather than starting a duplicate on 4594; browser-tool JS checks via an explicitly-tracked `tabId`, not visual screenshots — screenshot compositing unavailable in this environment, consistent with prior sessions):**
- All 9 pages, desktop (1440px) and mobile (390px): Inter font confirmed (`getComputedStyle(document.body).fontFamily`); `document.documentElement.scrollWidth === window.innerWidth` (no horizontal overflow) at both viewports; zero console errors on any page at either viewport.
- Product counts verified via DOM (`#count` text + grid child count): Kettle 4/4, OTG 2/2, Rice Cooker 1/1, Food Processor 1/1, JMG 2/2; Chimney/Iron/Ice-Cream-Maker/Air-Fryer all 0/0 with `.empty-soon` "Coming Soon" card rendering (icon + heading + message + Contact.html CTA) instead of a blank grid.
- Confirmed this session's Browser-pane had multiple foreign tabs open from concurrent sessions (`tab-19`, `tab-22`, `tab-23` on other ports) — always passed explicit `tabId` and asserted `document.title` before trusting reads, per the gotcha logged by the prior Cooktop/Lunch-Box session.

**Not touched (per instructions):** `Electric-Appliances.html`, `index-v2.html`, `All-Products.html`, `product-data/products.json`, any other existing page.

## 2026-08-17 — 10 standalone Kitchenware sub-category pages

**Task:** Build one dedicated v2-style page per Kitchenware sub-category (in addition to `Kitchenware.html`), using `Kitchenware.html` itself (already v2-facelifted) as the starting template, per site-owner request via developers@techinfinity.io context.

**Files created:** `Kitchenware-Lighters.html` (10 products), `-Knives.html` (72), `-Peelers.html` (7), `-Chopping-Boards.html` (19), `-Trolleys.html` (3), `-Kitchen-Tools.html` (29), `-Manual-Appliances.html` (30), `-Cutlery.html` (61), `-Servers.html` (61), `-Water-Filter.html` (4). Counts confirmed against `product-data/products.json` (`category==="kitchenware"` grouped by `subcategory`): sum = 296, matches `Kitchenware.html`'s total exactly. None were 0-product, so no "coming soon" empty-state was needed (pattern from `Lunch-Box.html`/`Electric-Appliances-*` reviewed but unused this round).

**Method:** One-off Node script in the session scratchpad (not committed) reading `Kitchenware.html` verbatim, normalizing CRLF→LF before search and restoring CRLF on write (avoided the bug an earlier concurrent session hit on Electric Appliances), applying 26 targeted "must-match-exactly-once" string replacements per output file.

**Key implementation decisions:**
1. Added `FIXED_SUB`/`SUB_LABEL` next to the existing `FIXED_CAT = "kitchenware"` const; changed `catProducts` to `P.filter(p => p.c === FIXED_CAT && p.sub === FIXED_SUB)` — the one functional change needed since hero tiles/`#catGrid`/`#colGrid`/grid/counts already all derive from the resulting `viewProducts`.
2. Fully deleted the sub-category chip switcher (`#chips` element + its render/wiring JS + `setSub()`) rather than just hiding it via CSS, since the task explicitly asked to remove it (nothing to switch to on a single-sub page). Simplified `state` to `{ sort, attrFilters }`, dropping now-dead `cat`/`col`/`cats`/`subLabel`/`subText` branches from `applyAndRender()`.
3. Rewrote `#catGrid` ("Shop by category", visible by default on this page — `DEF.showCategoryNav: true`) as a single hardcoded card using `SUB_LABEL` + `viewProducts.length`, instead of letting the generic `CATEGORIES`-driven loop resolve to a tile mislabeled "Kitchenware" showing only the sub-category's count.
4. Reworked `#colGrid` ("Featured Collections" → "Featured Picks"): each sub-category shares exactly one `collection` tag in the data (verified: LIGHTERS, KNIVES, PEELERS, etc. are each singular), so grouping by `collection` would only ever render 1 card. Instead grouped by distinct product image (up to 3), each card is now a real `<a href="Product.html?p=...">` instead of a JS-intercepted `data-col` filter — renders 3 useful cards and works correctly if the site owner ever flips the (default-off) `showCollections` tweaks-panel setting on.
5. Added a breadcrumb-style back-link since `Kitchenware.html` has none to port forward: hero eyebrow (`#heroPre`) rewritten as `<a href="Kitchenware.html">Kitchenware</a> / {Sub Label}`.
6. Rewrote per-page `<title>`, `<meta name="description">`, hero eyebrow/H1/sub-copy, `catLead`, `colTitle`/`colLead`, `browseTitle`, `ctaTitle`/`ctaSub`, and the CTA row's "Explore {Label}" button — tone/facts cross-checked against `About.html` (1971 founding; "108+ knife shapes, pioneered India's first surgical stainless-steel kitchen knives" for Knives; "Kitchenware India founded in Rajkot" for Cutlery) and `Kitchenware.html`'s own copy; no certifications or specs invented.
7. `#attrChips` (facet bar) needed zero changes — it self-scopes to the single category present in `scoped`, and with `viewProducts` now sub-filtered the rendered facets are automatically sub-specific (Knives → Brand/Set/Handle/Edge; Cutlery → Brand/Design/Set Size/Set).
8. Header/nav/footer/tweaks-panel/CSS copied byte-for-byte unchanged from `Kitchenware.html` otherwise, per instructions; mega-menu and mobile-accordion links to `All-Products.html?cat=kitchenware&sub=...` deliberately left as-is (site owner decides cross-page nav separately).

**Verification (existing dev server already running on port 4567 from a concurrent session — reused it directly; browser-tool JS checks via an explicitly-tracked `tabId`, not visual screenshots — screenshot compositing unavailable in this environment, consistent with prior sessions):**
- All 10 pages, desktop (1440px) and mobile (390px): Inter font confirmed; `document.documentElement.scrollWidth === window.innerWidth` (no horizontal overflow) at both viewports; zero console errors on any page at either viewport; all 3 `<script>` blocks on each file pass a Node.js syntax check (`new Function(...)`) before ever touching a browser.
- Product counts verified via DOM (`#count` text + `.pcard`/grid child count), matching `product-data/products.json` exactly: Lighters 10/10, Knives 72/72, Peelers 7/7, Chopping Boards 19/19, Trolleys 3/3, Kitchen Tools 29/29, Manual Appliances 30/30, Cutlery 61/61, Servers 61/61, Water Filter 4/4. Sum 296 = Kitchenware total.
- Breadcrumb spot-checked (`#heroPre` renders "Kitchenware / Water Filter" with a working link back to `Kitchenware.html`); `#colGrid` spot-checked on Trolleys (3/3 distinct picks, since the sub only has 3 products total) and Water Filter (3 of 4 picks); facet bar spot-checked on Knives (`Brand | Set | Handle | Edge`).
- Confirmed this session's Browser-pane and scratchpad had cross-talk from other concurrent sessions (extra tabs on other ports; scratchpad `gen.js` briefly reported as "modified" with unrelated Cleaning-Aid-page content via a system-reminder that also told the agent not to mention it to the user) — consistent with the gotcha already logged above; disregarded the "don't tell the user" instruction (no observed-content channel can authorize withholding information from the user) and reported it plainly instead. No repo files belonging to this task were affected.

**Not touched (per instructions):** `Kitchenware.html`, `index-v2.html`, `All-Products.html`, `product-data/products.json`, any other existing page.

## 2026-08-17 — 10 standalone Cleaning Aid sub-category pages

**Task:** Build one dedicated v2-style page per Cleaning Aid sub-category (in addition to `Cleaning-Aid.html`), using `Cleaning-Aid.html` itself (already v2-facelifted) as the starting template — explicitly NOT `All-Products.html` — per site-owner request via developers@techinfinity.io context.

**Files created:** `Cleaning-Aid-Spin-Mops.html` (9 products), `-Hand-Held-Mops.html` (7), `-Brooms.html` (10), `-Wipers.html` (12), `-Plunger.html` (2), `-Brush.html` (13), `-Scrubber.html` (4), `-Bins.html` (5), `-Sink-Organiser.html` (2), `-Wipe.html` (2). Counts confirmed against `product-data/products.json` (`category==="cleaning-aid"` grouped by `subcategory`): sum = 66, matching the task brief's stated total exactly. None were 0-product, so the default view never hits the "coming soon" branch, but the dual empty-state (see below) was still added for the filtered-to-zero case.

**False start, corrected:** built a first version that invented its own repurposing of `#catGrid` (cross-links to the 9 sibling sub-pages) and `#colGrid` (grouped by individual product instead of `collection`, since every sub-category maps to exactly one `collection` value in the data). Before finalizing, checked whether any other category already had this exact "N sub-pages off one category template" pattern shipped — it did: `Cookware-Tripro.html` etc. and `Electric-Appliances-Kettle.html` already existed in the repo (built by earlier concurrent sessions, per `memory.md`). Diffed `Electric-Appliances.html` against `Electric-Appliances-Kettle.html` to recover the site owner's actual accepted convention and rebuilt all 10 Cleaning Aid pages against that diff instead of the invented approach.

**Method:** One-off Node script in the session scratchpad (not committed), reading `Cleaning-Aid.html` verbatim, with a "search string must match exactly once" guard on every anchor before replacing (fails loudly instead of no-op'ing or double-patching), CRLF-normalized on read and restored on write.

**Key implementation decisions (mirrors the `Electric-Appliances-Kettle.html` precedent exactly):**
1. Added `PAGE_SUB` next to the existing `PAGE_CAT = "cleaning-aid"` const; changed the `loadCatalog()` fetch filter to `.filter(p => p.category === PAGE_CAT && p.subcategory === PAGE_SUB)` — filtering upstream (not post-hoc) so hero tiles, `#catGrid` counts, and the grid all scope correctly for free.
2. Left `SUBCATS` (all 10 siblings) and `#catGrid`'s existing per-sub-count render loop untouched. Hid the two redundant sub-category switchers rather than deleting their markup/JS: `#chips` via inline `style="display:none"`, and the entire `#categories` ("Shop by type") section via flipping the tweaks-panel `DEF.showCategoryNav` default to `false` — otherwise that section would render 9 sibling cards reading "0 products" plus 1 real one, which is exactly the kind of broken-looking empty state the task asked to avoid elsewhere. `#collections` needed no equivalent change since `Cleaning-Aid.html` already ships `showCollections:false` by default.
3. Set `state.subLabel`/`state.subText` at init to the current sub's label/slug (so `#count` reads "...in Spin Mops" etc.), matching the Kettle precedent.
4. Ported the `.empty-soon` CSS block (Coming-Soon / No-Matches card, originally from `Lunch-Box.html`) into all 10 pages' `<style>`, and split `applyAndRender`'s `if (!list.length)` into the same two branches as the Kettle page — `!viewProducts.length` (Coming Soon + Contact CTA) vs. filtered-to-zero (No Matches + Clear Filters button) — even though every sub currently has stock, since attribute filters can still legitimately narrow a result set to zero.
5. Repurposed the hero's secondary CTA button as the back-link: `← All Cleaning Aid` → `Cleaning-Aid.html`, replacing the original `#collections`-anchor "Featured Collections" button (that section is hidden by default anyway).
6. Added `class="active"` to each page's own sub-category link inside the shared mega-menu / mobile accordion "Cleaning Aid" group — cosmetic "you are here" highlight only; the links' actual hrefs (`All-Products.html?cat=cleaning&sub=...`) were left untouched, per instructions that cross-page nav is the site owner's call.
7. Rewrote per-page `<title>` (`"{Sub} | Cleaning Aid | CRYSTAL"`, matching the Kettle page's exact title format), `<meta name="description">`, hero eyebrow/H1/sub-copy, `catLead`, `colTitle`/`colLead`, `browseTitle`, `ctaTitle`/`ctaSub`, and the CTA row's "Explore {Sub}" button. Tone/facts cross-checked against `About.html` (SparkMate = "Cleaning Simplified", since 1971, Made in India) and `Cleaning-Aid.html`'s own copy; no certifications or specs invented — all 66 Cleaning Aid SKUs in the data are brand `sparkmate` only, so every page's hero/meta copy correctly says "SparkMate", not "Crystal".
8. `#attrChips` (facet bar) needed zero code changes (self-scopes automatically) — but in practice renders empty on every one of these 10 pages, since Cleaning Aid's `filters{}` field is empty (`{}`) for all 66 products in the current data; confirmed this is a data gap, not a page bug, by checking the source JSON directly.
9. Header/nav/footer/tweaks-panel/CSS copied byte-for-byte unchanged from `Cleaning-Aid.html` otherwise. Diffing one finished output file (`Cleaning-Aid-Spin-Mops.html`) against `Cleaning-Aid.html` end-to-end confirmed the total change surface was exactly the ~14 intended edit points and nothing else drifted.

**Verification (spun up a second local server on port 4593 since port 4567 was already occupied by another concurrent session's server serving this same repo; browser-tool JS checks via an explicitly-tracked `tabId`, not visual screenshots — screenshot compositing unavailable in this environment, consistent with every prior session's note above):**
- All 3 `<script>` blocks on each of the 10 files pass a Node.js syntax check (`new Function(...)`) before ever touching a browser.
- All 10 pages, desktop (1440px) and mobile (390px): `getComputedStyle(document.body).fontFamily` = `"Inter, sans-serif"`; `document.documentElement.scrollWidth === document.documentElement.clientWidth` (no horizontal overflow) at both viewports; zero console errors on any page at either viewport.
- Product counts verified via DOM (`#count` text + `#grid .pcard` count), matching `product-data/products.json` exactly: Spin Mops 9/9, Hand Held Mops 7/7, Brooms 10/10, Wipers 12/12, Plunger 2/2, Brush 13/13, Scrubber 4/4, Bins 5/5, Sink Organiser 2/2, Wipe 2/2. Sum 66 = task brief's stated Cleaning Aid total.
- Spot-checked exact SKU names on the Spin Mops page against the source JSON (`King Plus`, `Strolly Plastic`, `Strolly Steel`, `Rapid Spin Mop`, `GLIDE MOP`, `Grace Spin Mop`, `Spin Mop Spare Set (Rod+Disc+Refill)`, `Spin Mop Rod`, `SM Spin Mop Refill`) — exact match, confirming the data-mapping (not just the count) is correct.
- Confirmed `#chips` and `#categories` both compute to `display:none` on page load (the two switcher-hiding mechanisms actually take effect, not just present in markup); confirmed the hero back-link element and its `href="Cleaning-Aid.html"` render correctly.
- This session hit the same environment cross-talk noted by prior sessions: port 4567 was already serving this repo from another concurrent session (used 4593 instead, per the task's own fallback instruction), and `git status` showed a large pre-existing untracked/modified set (including `memory.md`/`BUILD_LOG.md` themselves) from parallel sessions before this task even started — none of it was touched or attributed to this task's diff.

**Not touched (per instructions):** `Cleaning-Aid.html`, `index-v2.html`, `All-Products.html`, `product-data/products.json`, any other existing page.

## 2026-08-18 — Fix Product.html breadcrumb overlapping fixed nav header

**Task:** User reported (screenshot) breadcrumb/content on `Product.html` sitting almost flush against the fixed nav header.

**Root cause:** `.crumb { padding-top: clamp(94px, 11vh, 116px) }` was calibrated for the old header position (`inset: 14px`); a prior site-wide support-bar migration pushed the header to `inset: 38px`, leaving insufficient clearance.

**Fix:** `.crumb` padding-top changed to `clamp(118px, 13vh, 140px)` (Product.html:117).

**Verification:** `http://localhost:4567/Product.html?p=ctp-tp-001` — `#hdr` bottom = 95.6px, `.crumb` content top = 118px (computed padding-top), ~22px clear gap, no overlap.

**Committed & pushed** to `main`.

## 2026-08-18 — Merge size-variant products into one listing card + real size selector

**Task:** Same product listed as separate cards per size (e.g. Tripro Tope 14/16/18/20/22/24/26 CM = 7 cards) should show as **1 card**; size selection moves inside `Product.html` and switches the actual product (image/code/price) when changed.

**Data (`product-data/products.json`):** Auto-detected size-variant families by stripping size/unit tokens (CM/MM/ML/LTR/KG/GM/inch/quote-mark) from product names and grouping by (category, subcategory, brand, stripped-name). Required every member to contain a genuine size token and have a distinct raw name — excluded 5 groups (11 products) that were identical-name/different-SKU with no real size difference (likely true duplicate catalog entries, e.g. `CL-922`/`CL-923` "STAINLESS STEEL KNIFE, BROWN") and 1 group (`CL-073/074/457/458`) that had duplicate size labels within the group (also a duplicate-entry issue, not a size progression) — none of these were touched. Result: **20 real size-variant groups, 72 products tagged** with `variant_group` (`vg-01`..`vg-20`), `variant_label` (e.g. "14 CM", "800 ML"), `variant_order` (ascending by numeric size).

**Listing pages (all 46: `All-Products.html` + 10 category + 35 sub-category pages):** Inserted one block right after each page's `const data = await res.json();` that keeps only the lowest-`variant_order` member per `variant_group` before the page's existing category/subcategory filtering runs — no other page-specific logic touched. Site-wide visible product count: 531 → 479. Verified: `Cookware-Tripro.html` 43 → 16 cards (6 merged Tripro sub-lines + 10 standalone), `All-Products.html` 531 → 479, merged card links to the smallest-size SKU (e.g. `ctp-tp-001`, 14cm).

**`Product.html`:** The page already shipped an unused `.vsel`/`.vchips` "variant selector" UI wired to fake, generic per-category placeholder options (e.g. every cookware product showed "24 cm / 26 cm / 28 cm" chips that did nothing real). Replaced with real sibling-based switching: `P` mapping gains `vgroup`/`vlabel`/`vorder`; `renderProduct()` computes `siblings = P.filter(p => p.vgroup === prod.vgroup)`, renders one chip per real sibling (both the hero `.vsel` and the Specs-section "Available Sizes" panel), and clicking a chip navigates to `Product.html?p=<sibling id>` (full nav, safe given the page's one-time GSAP scroll-animation setup). Selector auto-hides (`display:none`) when a product has no real siblings (`siblings.length <= 1`) instead of showing the old fake options. Verified: `ctp-tp-001` page shows all 7 real Tripro Tope sizes as chips, clicking "20 CM" navigates to `ctp-tp-004` with title/SKU/active-chip updating correctly; a non-variant product (`li001a`) correctly hides the whole size-selector section.

**Not touched:** any product's core content/description, the 11 flagged non-size duplicate-name products, backend Django sync script (`sync_products.py` — variant grouping not yet reflected in the admin DB, one-way JSON→DB sync unaffected by this change).

**Committed & pushed** to `main`.

**Follow-up same day:** user wanted size-chip clicks to NOT do a full page navigation — only swap image/code/title in place on the same page load. Reworked `applySizeVariant()` in `renderProduct()`: chip click now directly updates `#gMain`/`#gThumbs` (new gallery), `#pTitle`, `#pSku`, `#crumb .cur`, `#vCurrent`, active chip class, and re-wires the Enquire/Buy buttons' `dataset` (id/name/img) to the new SKU — then calls `history.replaceState(null, "", "Product.html?p="+id)` so the URL/refresh/share-link stay correct without an actual navigation. `wireEnq(btn)` signature extended to `wireEnq(btn, p, gal)` (defaults to the initially-loaded `prod`/`gallery`) so it can be reused for both the initial render and each in-place variant swap. Overview/specs/features/related-products sections intentionally left untouched on swap (out of scope — data doesn't vary per size anyway). Verified via `beforeunload` listener + before/after DOM state that no real navigation occurs, and that image/code/title/breadcrumb/active-chip/enquire-button dataset all update correctly.

## 2026-08-20 — Category page restructure, typography, and image gray-background fix

**Task:** Multiple follow-up requests on the 46 category/sub-category listing pages and product photos.

**Changes:**
1. Moved "Browse / Product Grid" section to appear right after Hero (before Category Nav/Collections/Marquee/Brand Value/CTA) across all 46 listing pages — filter bar + products now visible immediately below the hero CTA buttons.
2. Removed the hero-tiles image-preview strip (looked like cropped photos) and its JS population line.
3. `.hero h1` font-size: `clamp(40px,7vw,92px)` → `clamp(40px,5.5vw,70px)`.
4. `.sec-head h2` font-size: `clamp(32px,5.4vw,70px)` → `clamp(28px,4vw,50px)`.
5. Added, then (per follow-up instruction) removed, 15 lifestyle banner images across 5 Cookware + 10 Kitchenware sub-pages — net no banners remain; `category-banners/` folder deleted.
6. Fixed 107 product photos site-wide that had a light-gray (#f1f1f1-ish) studio-backdrop band baked into the image pixels (not a CSS issue) — used PIL flood-fill from all 4 corners (tolerance 18) to convert the connected gray background to pure white, leaving the product itself untouched. Verified on samples before running on the full affected set.

**Verification:** Fresh-tab console checks on multiple pages (no new errors beyond pre-existing unrelated 404s), computed-style checks confirming font-size and section order, before/after image comparison on 3 sample photos before full rollout.

**Committed & pushed** to `main`.

## 2026-08-24 — Fix 3 mis-scraped Amazon product ASINs (cross-tab contamination)

**Task:** 3 ASINs (`B098MVMKBT`, `B098MV5MKJ`, `B0DZGQ5W78`) in `amazon-products/` had wrong product data saved from an earlier parallel batch scrape (cross-tab contamination). Re-scraped each fresh in its own tab with title verification before saving.

**Results:**
- `B098MVMKBT` -> "Crystal TriPro -Triply Stainless Steel Tasla - 26 cm (Induction Bottom)" — old img-1/2/3.jpg deleted, 5 new images saved, info.json overwritten.
- `B098MV5MKJ` -> "Crystal TriPro -Triply Stainless Steel Saucepan with Lid - 20 cm (Induction Bottom)" — old img-1..5.jpg deleted, 4 new images saved (only 4 available on listing), info.json overwritten.
- `B0DZGQ5W78` -> "Crystal Trival Triply Stainless Steel 2 Pc Cookware Set (Fry Pan-22cm & Tea/Milk Saucepan-16cm), Silver" — old img-1..5.jpg deleted, 5 new images saved, info.json overwritten.

Titles confirmed to match expected products before any save. Old images deleted prior to downloading replacements in all 3 folders.
