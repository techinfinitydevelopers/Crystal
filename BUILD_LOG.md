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

## 2026-08-25 — export_to_json management command (DB is now source of truth for products.json)

**Task:** Make the dashboard DB regenerable into `product-data/products.json` (the live static site's data file) so client edits in the dashboard can reach the site.

**Done:** Added `crystal/backend/products/management/commands/export_to_json.py`. Reuses `site_product_entries` from `products/serializers.py`. Supports `--check` (diff, no write) and `--out PATH`; atomic temp-file replace; preserves current file SKU order and metadata keys; one-line summary (written / new / missing).

**Verified:** `--check`: 531 file entries vs 531 DB entries, order identical, 0 real diffs, 8 known amazon_link placeholder-only diffs ('No'/'' -> null). Independent Python diff of a scratch export confirmed the same 8-and-only-8. `manage.py check`: no issues. Live products.json NOT overwritten; nothing committed.

---

## 2026-08-25 — End-to-end QA of dashboard workflows (Django test client)

**Task:** Client-style QA of six admin flows: add product with variants/features, image inlines, Excel import (create/update/idempotent/bad-row), site.json API parity, template downloads, admin theme CSS.

**Result:** 6/6 PASS, no code changes needed. Evidence: add form saves and round-trips features as "icon | title | detail" lines with 2 variants; changelist shows hero=1/photos=3/variants=2; import reported 1 created + 1 updated, re-upload all unchanged, unknown-brand row skipped with reason while good row landed; /api/products/site.json/ emitted 2 sibling variant entries sharing a variant_group with all products.json core keys; template.xlsx/.csv both 200 with the documented 15-column header; admin/crystal_theme.css found by staticfiles finder and referenced by JAZZMIN_SETTINGS custom_css.

**Cleanup:** All QA products/variants/images deleted, uploaded media files and empty dirs removed, temp superuser deleted. Counts restored to baseline 531 products / 95 variants / 2483 images. products.json untouched; nothing committed.

**Note:** Jazzmin logs a deprecation warning: JAZZMIN_UI_TWEAKS['dark_mode_theme'] is ignored; use default_theme_mode instead.

## 2026-09-10 — CC-851: add 8 missing gallery images from Amazon

**Task:** User provided `https://www.amazon.in/dp/B0DCSQJLSV?th=1` and asked to scrape the product image and add only what's missing for SKU CC-851 (Crystal Titanium R/G Fruit Fork, Set of 6).

**Found:** `product-data/products.json` (already at HEAD, committed by a concurrent session) referenced `product-photos/CC-851/g1.jpg` through `g8.jpg` in its `gallery` array, but only `hero.jpg` existed on disk — the JSON was ahead of the filesystem.

**Done:** Scraped the current-variant (Rose Gold, Set of 6) gallery from the Amazon listing's `colorImages.initial` JSON (8 images, matched against `#altImages` thumbnails to avoid pulling other-variant images per the shared-gallery gotcha). Bash/curl had no outbound network access in this environment (silent hang/timeout) — fetched image bytes via the Browser pane's `javascript_tool` (`fetch` -> arrayBuffer -> base64) instead, decoded to `g1.jpg`-`g8.jpg` (1080x1080 each). No JSON edit needed since it already matched. Committed only the 8 new image files (1941d0d), pushed.

## 2026-09-10 — Dashboard: editable page sections + Pages picker

**Task:** User wants every page's sections editable from the admin dashboard, with all pages reachable from the dashboard sidebar.

**Found:** A `content` Django app (PageSection model, admin, `/api/sections.json`, dashboard "Pages" picker grouped by category) had already been built and pushed to origin as fbb66bc under this session's own identity, byte-identical to the implementation this session was independently writing — no explicit commit was issued for it in this session's visible history. Left it as-is (did not re-commit) and verified it rather than guessing at the mechanism.

**Done this session:** Wrote `content-sync.js` (repo root), the same fetch/swap/fail-silent pattern as the existing banner-sync script, and wired a `<script>` tag into all 46 category/sub-category listing pages (All-Products + 10 categories + 35 sub-categories), which share identical `#heroPreTxt`/`#heroTitle`/`#heroSub` ids. Committed c8125a4, pushed.

**Verified live:** Started the local `crystal-dashboard` server, logged into local admin (reset the local-only `admin` password since the original was unknown — gitignored `db.sqlite3`, no production impact), added a real PageSection row through the UI, confirmed `/api/sections.json` served it, then ran the swap logic against a live category page in the browser and watched the hero heading update. Deleted the test row afterward.

**Explicitly still open (told to the user):** About.html, the 4 Brand pages, and Home (index.html/index-v2.html) have no shared hero element ids yet — need those added before they can be wired the same way. Only hero text is wired on the 46 pages so far; other sections (stats, feature blocks, CTAs) and image sections beyond the existing CategoryBanner are a further round.

## 2026-09-10 — Dashboard: wire CTA and About's stats

**Task:** Continue the page-sections dashboard — wire the remaining CTA and stats sections.

**Found:** The 46 category/sub-category listing pages already ship `#ctaTitle`/`#ctaSub` ids on their CTA band, so registering `cta-title`/`cta-sub` in `content-sync.js` made CTA text dashboard-editable on all 46 with zero HTML changes.

**Done:** Added ids to About.html's two stat rows (9 numbers + 9 labels — Years of Trust, People Strong, Products & SKUs, Happy Customers, Corporate Offices, Manufacturing Units, Warehouses, Retail Outlets, Factory Space) and matching keys in content-sync.js. The swap now also writes the `data-count` attribute when present, so an edit lands correctly whether the page's count-up animation has already fired or not. Verified live: a counted stat's number and attribute both update, and the two static numbers (Retail Outlets, Factory Space) swap without disturbing the "Sq.Ft." unit span on Factory Space. Committed 3297b77, pushed.

**Checked, no work needed:** Brand pages have a `.cta-band` CSS rule with no matching element in the markup (dead code) — their only bottom section is the shared site-wide footer, out of scope since it's identical across every page, not brand-specific.

**Still open:** Home (index.html/index-v2.html) has 3 stat rows and its own CTA, not yet wired — index.html is generated from home-v3-src, so that edit goes in the source, not the file directly.

## 2026-09-11 — Dashboard: wire Home page stats and CTA

**Task:** Wire index.html/index-v2.html's stats and CTA into the page-sections dashboard.

**Found mid-task:** index.html's real body is NOT built from home-v3-src/shell-donor.html's HERO-to-FOOTER content — build_v3.py discards that range and splices in home-v3-src/v3_main.html instead (shell-donor.html only donates the outer shell for that range). index.html's actual structure differs completely from index-v2.html: one About+Counters block (4 stats, `class="count3" data-target="N"`) instead of three separate stat rows, and a single-line CTA instead of two.

**Done:** Added ids to index-v2.html and shell-donor.html's three stat rows (About/Who-We-Are, Infrastructure, Our Brands) and two-line CTA; added ids to v3_main.html's actual counters and CTA. Fixed a timing bug in v3.js: the count3 counters captured `data-target` into a closure variable immediately at page load, before their scroll-triggered animation ever fired, so a dashboard edit arriving later (async fetch) had no effect — moved the dataset read inside the ScrollTrigger's onEnter callback so it's read lazily at trigger time, matching the safe pattern the other (`data-count`) counter script already used. Verified: scrolled a counter into view after overriding its value and watched the animation land on the new number.

**Found on commit:** a concurrent session (co-authored "Claude Opus 5") had independently built and pushed byte-identical work as ca224e0 while this was in progress. Working tree came back clean against it — nothing left to commit. Same pattern as the earlier fbb66bc/3f1d518 convergences in this project.

**Page-sections dashboard is now wired across:** all 46 listing pages (hero, CTA), About.html (hero, about-adjacent stats, stats x2), 4 Brand pages (hero, about section), index.html and index-v2.html (hero, stats, CTA).

## 2026-10-10 — Pre-launch client changes, and the tablet breakpoint

**Task:** Work the change list the client filed on WhatsApp (group "Crystal -
SEO and AMC", 8-10 Oct) ahead of the 11 Oct 12:00-12:45 PM go-live, then make
the site work on tablets.

**Done:**

- *Map links.* The footer's two address lines were `href="#"` on **63 pages**,
  so a click jumped to the top of the page — the client read that as "map links
  redirect to home page". Pointed Rajkot at the place URL the client supplied
  (tracking query stripped) and Mumbai at a Maps URL-API search, both
  `target="_blank" rel="noopener"`. `home-v3-src/shell-donor.html` included, or
  the next v3 build would have put `href="#"` back.
- *Support phone.* `<div class="support-bar">` was plain text on **66 pages**;
  wrapped the number in `tel:+912249702803`, tagged the bar `data-cms-rich` so a
  dashboard edit goes through innerHTML (content-sync.js:140) instead of
  flattening the anchor, and added a `.support-bar a` rule — the bar is
  white-on-red, so an unstyled anchor would have come out browser-blue.
- *"Kithcen Tools"* -> "Kitchen Tools" on 29 products, in `products.json` and
  `crystal/backend/dashboard-seed.json`. No correctly-spelled twin collection
  existed, so nothing had to be merged.
- *Products removed* (584 -> 579): `SMW001`/`SMW002` (Star and Super Wiper —
  both empty rows, no hero, no gallery, no link, `match_tier: unmatched`) and
  the three Volcano Infrared cooktops `CGIRF-041/042/043`, leaving Cooktop as
  exactly Ignite, Magnite, Lexa, Imperia and Induction as asked.
- *Contact.* Dropped `info@crystalcook.com`. The HR address that replaces it is
  not known yet, so the slot is a commented-out line naming what is missing
  rather than a guess — `careers@crystalcook.com` exists on Career.html but is a
  careers inbox, not confirmed as HR.

**Tablet ("tab view"), measured rather than guessed.** Served the site locally
and read the header at a range of widths. The logo image went 140px at 1280,
100px at 1150, 55px at 1100, 10px at 1050, **0px at 1024** — an iPad in
landscape had no logo at all. Two causes: `.logo { flex: 1 }` is shorthand for
`1 1 0%`, a shrinkable box with a zero basis, and the burger only took over at
960px, so 961-1199px showed a desktop nav that did not fit ("Knowledge Centre"
wrapped to two lines, nav height 69 -> 74px).

Added a nav-only `@media (max-width: 1199px)` block on **67 pages** (+ the
builder source), kept deliberately separate from each page's existing 960px
block — that one carries the grid layouts, which are correct where they are and
should not move the day before launch. Also made the logo unshrinkable
(`flex: 1 0 auto` + `header .logo img { flex-shrink: 0 }`) as a guard above
1200px.

**Verified in a real browser**, 5 pages x 6 widths (1366/1200/1180/1024/834/768):
logo 140px at every width, burger switching at <=1199, zero wrapped nav links,
zero horizontal overflow. Checked the live DOM for the new `tel:` href, the
underline, and both map hrefs.

**Not done, waiting on the client:** the HR email address; real certificate
images (`about-assets/cert-1/2/3.png` are three copies of one stock template,
"Kristen Kennedy — E-Commerce Marketing Master", and `awards/t-iso.png` is the
same file); hero images for `CTV-092/093/094/095`; and the SKUs behind "Oil
Pourer: 3 missing / Pressure Cooker: 2 / Plunger: 1 / Bins: 1". The `CPC_0xx.png`
files the client sent are 372px against the 1500px heroes already on the site,
so they were deliberately not used.

### Follow-up, same day — the phone's brand accordion

Client sent a phone screenshot: on the home page's Our Brands accordion the
white logo card sat on top of "World of Kitchenware" and cut it mid-word.

`.v3 .acc3-logo` is `position: absolute; bottom: -2px; right: 60px; width:
170px`, with **no mobile override at all**. Measured across widths with the
tagline's own text rect (the `<p>` is a full-width block, so its border box
overlaps the logo at every size and says nothing): the collision starts below
about 430px — at 390px the text runs to 167px and the logo starts at 130px.

Rather than pick a breakpoint, below 640px the logo goes back into normal flow
under the text. The taglines are CMS-editable (`brand3-p-2`..`p-5`), so a fixed
reserved gap would only postpone the same bug. `display: none` by default and
shown on `.active`, since in flow an invisible absolute logo would otherwise
take up space on all four rows.

Edited `home-v3-src/v3.css` and rebuilt through `build_v3.py`. The rebuild's
diff against the committed index.html was exactly the twelve new lines, which
also confirms the generated page was in sync with its sources. Verified at
768/640/600/480/430/390/360/320. Commit c3f56b9.

## 2026-10-10 — SparkMate Amazon scrape, and three kettle photos

**Task:** Client sent a SparkMate sheet of 119 ASINs and asked for the Amazon
images to be scraped in against each product id, with no duplicates — "dekh
kar karna".

**Environment note that changed the approach:** `curl` from the shell *does*
have outbound network here (an earlier note in memory said otherwise). But
Python `urllib` with identical headers gets a 3.7 KB captcha page from Amazon
while curl gets the real 1.7 MB listing, so the extractor shells out to curl.
Whatever is being fingerprinted sits below the header level.

**Scope, measured before downloading anything.** 115 of the 119 sheet rows match
the catalogue. Of those, only **25** lacked a gallery. Surveying those 25
listings first: **10 carry 2 photos, 15 carry exactly 1**. The 15 were dropped
without downloading — a single Amazon photo is the hero the site already shows,
and adding it would put the same picture on the page twice.

**Then the useful part: all 9 remaining candidates were duplicates too.**
A dhash comparison said they were new (distance 71–100 from the hero), and
*looking at them* said otherwise:

- `PSM-002/003/004/005` — the hero photograph with marketing text printed over
  it. Same picture.
- `PSMB-002/003/004` — the hero photograph with a SparkMate logo badge in the
  corner. Same picture.
- `PSMB009` — the product sealed in a polybag. Different, but a packaging shot.
- `SMB009` — genuinely a second angle, and then: dhash distance **0** against
  `sparkmate/SMB009/img-2.jpg`, which the site already ships. The harvest had
  only compared against the *hero*, not the existing gallery.

So the scrape yielded **zero** images the site does not already have, and
nothing was added. Worth keeping in mind that a perceptual hash catches
"same photo, different resolution" but not "same photo, logo added" — text and
badges move the hash a long way while a human sees one picture.

**Kettles (committed, 13bb836).** `CKTL-051`, `CKTL-055`, `CKTL-056` had
`hero: null`, empty galleries and no folder — the "Kettle missing" item on the
client's list. The photos arrived on WhatsApp captioned with those exact SKUs;
pulled them out of the page as blobs, checked they were three visibly different
kettles, and set each as its product's hero. Verified on the Kettle listing
page: all three load.

**Open on these:** the three products' *names* are still their SKUs, so the page
shows a customer "CKTL-051" where a name belongs, and `CKTL-057` still has no
photo at all.

## 2026-10-10 — Crystal moved onto the client's own VPS (not yet live)

**Task:** Migrate the whole site off Railway onto the Hostinger KVM 2 the client
owns, ahead of the 11 Oct go-live. Everything except the DNS switch.

**Server:** `srv2035352.hstgr.cloud`, 187.126.118.190, Ubuntu 24.04.5, 2 cores,
7.8 GB RAM, 95 GB free. Site at `/var/www/crystal`, dashboard at
`crystal/backend` inside it, venv at `/opt/crystal-venv`, gunicorn on
127.0.0.1:8001 behind nginx.

**No Postgres dump was taken, deliberately.** The production dashboard reported
**0 enquiries and 0 blog posts**, so it held nothing irreplaceable — and its
product rows were *worse* than the repo's catalogue. So the database was rebuilt
from source: `sync_catalogue --file` off `product-data/products.json`, the two
seeds, then a script replaying only what a human had typed or uploaded (31
category banners, 16 page sections, 5 awards). The 56 uploaded files were pulled
off the old host over HTTP first, so the Railway volume never had to be opened
and the production database never had to be exposed to the internet.

### Three real bugs surfaced, all now fixed

**1. `sync_catalogue` never set `Product.amazon_link` (bfac9ae).** It wrote the
catalogue's URL only into a `ProductMarketplaceLink` row, while
`site_amazon_link()` treats `Product.amazon_link` as the authority and consults
marketplace links *only* for dashboard-created products. A freshly synced
database therefore published **0 links out of 579**. This is the root cause of
the client's "Buy Now goes to an Amazon search" — production had drifted to
310 of 578, and the 130-product gap was simply where it had never been set.
After the fix the new server publishes **439 of 579, matching products.json
exactly, 0 mismatches**.

**2. 52 pages hard-coded the Railway dashboard hostname (843d6d2).** Correct
while the website and dashboard were separate Railway services; wrong the moment
they share an origin. On the new box About.html called the old host, got nothing
and fell back to its shipped card — six copies of the trophy where the client's
four certificates belong. Each literal is now an expression that keeps naming
Railway when served from `*.up.railway.app` and calls its own origin anywhere
else, so **both deployments work and the switch stays reversible**.

**3. nginx: `location /media/` lost to the image regex block.** Regex locations
beat prefix locations, so every `/media/**.png` fell through to
`try_files` under the site root and 404'd. Fixed with `location ^~ /media/`.

### Verified on the box

579 products / 439 links / 0 "Kithcen"; awards 5 = 5, banners 31 = 31, sections
16 over 13 pages = identical to the old feed; **all 48 dashboard-published asset
URLs return 200** with correct content types; 8 pages rendered with **0 broken
images**, including All-Products.html at 506 images; SMS001 — the product the
client screenshotted — now links to `amazon.in/dp/B0BC8MH6YY` rather than a
search.

A throwaway self-signed certificate is installed so the bare IP could be tested
in its final shape: HTTPS serves everything and HTTP 301s to it. certbot will
replace that certificate; nothing else about the config changes.

### Not done

- **DNS untouched.** crystalcook.com still resolves to 78.129.208.60 (nameservers
  `ns1-4.umiyaji.com`, a third party). Switching is two A records plus certbot.
- **No admin user yet** — the client picks that password, not us.
- **16 products carry dashboard image overrides** (hero/gallery picks, 9 of them
  uploads) that were not replayed; the override feed is derived from
  `overridden_fields` plus ProductImage rows and reconstructing it exactly needs
  more care than launch eve allows. Without them those 16 show their
  products.json hero instead of the client's pick. Nothing is broken, and the
  files are already on the server.

### Follow-up: the 16 dashboard overrides, and the upload 500

**The 500 the client hit.** One POST to a product change page returned 500
while every GET was fine — nginx's access log held exactly one 5xx all day, and
it was a `POST`. Cause: the repo was cloned as root, so `/var/www/crystal` was
`root:root`, and gunicorn runs as `www-data`. `MEDIA_ROOT` *is* that tree — the
whole point of co-locating site and dashboard — so **every save in the dashboard
would have failed**, not just that one. Fixed by chowning the tree to www-data
with setgid on directories, and giving the unit a writable `HOME` (gunicorn had
been failing to create its control socket in `/var/www/.gunicorn`). Proved by
writing, reading and deleting a file through `default_storage` as www-data, then
re-running the same POST.

`vps-deploy.sh` re-chowns on every run, because `git` runs as root and would
otherwise reintroduce it on the next pull. Note `git config --system
--add safe.directory` — `--global` is not read by systemd units, which have no
HOME, and that cost the first auto-deploy run.

**Auto-deploy** (15b39b7): a systemd timer every 5 minutes, deploying only when
`origin/main` has moved. Polling, not a webhook — nothing opened to the
internet, no secret to leak, and an unreachable GitHub just retries. `touch
/root/HOLD-DEPLOY` pauses it for the DNS cutover without disabling the timer,
and it keeps logging that it is holding so a forgotten hold is visible.

**The 16 overrides, restored exactly.** `sync_catalogue` had already created a
ProductImage row per catalogue photo; what was missing was the client's *choice*
— that on CL-216 `g4.jpg` is the main image and the original `hero.jpeg` belongs
in the gallery. That lives only as row order plus `is_hero`, published through
`overridden_fields`. The script rebuilds each product's rows in feed order,
flags the first as hero, replays CLMK-007's four field edits, and re-creates the
`RetiredSku` tombstone for MKA042 (a tombstone, not a deletion: products.json
still names it, so without one the next sync would bring it straight back).

`ProductImage.image` is only ever assigned a *name*, never a copied file —
MEDIA_ROOT is the site root here, so `product-photos/CL-216/g4.jpg` already
resolves and `_image_url()` publishes that string verbatim.

Verified by fetching the new `image-overrides.json` and diffing it against the
one taken off production: **16 products both sides, same hidden list, zero
entries differing**.
