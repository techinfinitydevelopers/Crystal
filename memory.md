# Crystal Website — Project Memory

## Site structure
- Static multi-page HTML site (no build step). Root files: `About.html`, `All-Products.html`, `Product.html`, `Brands.html`, `Catalogue.html`, `Blog.html`, `Contact.html`, `Enquiry.html`, etc.
- Shared chrome (header/mega-menu/mobile-menu, footer, tweaks-panel, `enquiry.js`) is duplicated verbatim at the top/bottom of every listing-style page rather than templated/included.
- Local dev server: `python3 -m http.server 4567` from repo root (also registered as `.claude/launch.json` config `"crystal"`, port 4567). `crystal-dev` config (`npx serve -l 3456 crystal`) also exists but is unused/stale (no `crystal` subfolder here).

## Product data
- Source of truth: `product-data/products.json` → `{ generated_at, source_xlsx, sheets_included, products: [...] }`. Always read `.products`, not the top-level array.
- Product fields: `sku, name, brand, category, subcategory, collection, highlight, description, tags[], gst_pct, mrp, amazon_link, filters{}, hero, gallery[], match_tier, id`.
- `category` values seen: cookware, kitchenware, cleaning, appliances/electric-appliances, water-bottle, oil-pourer, wood-range, pressure-cooker, cooktop, lunch-box.
- `filters{}` holds category-specific facets (e.g. cooktop: `size` = burner count, `type` = Gas Stove/Hob Top/Infrared/Induction, `material`).
- **Cooktop** category: 17 products (SKU prefixes CGBS-, CGIRF-, CIH-), all brand "crystal", all `hero: null` / `gallery: []` (`match_tier: "unmatched"`) — no real product photos exist yet. Same fallback-image behavior already exists on `All-Products.html` (not a regression).
- **Lunch Box** category: 0 products in the JSON as of 2026-08-17. Listed in nav ("Also explore" in mega-menu / mobile accordion) but has no data yet — any dedicated page must handle the zero-product case explicitly.

## `All-Products.html` catalog engine (shared JS pattern, ~line 711-1180)
- Fetches `product-data/products.json` async in `loadCatalog()`, maps into internal shape `P` (`n,col,b,c,sub,img,hl,tags,id,mrp,attrs`), then calls `renderCatalog()`.
- `renderCatalog()` computes `viewProducts` from `P` (filtered by `?brand=` only, not by category) — hero tiles, "Shop by category" grid (`#catGrid`), and Featured Collections (`#colGrid`) are all driven off `viewProducts`, i.e. off the **full unfiltered catalog**, not the current category filter.
- Category/sub-category filtering via `?cat=&sub=` is applied *after* the above render, in a bottom IIFE (~line 1029-1061) that mutates `state.cat`/`state.cats`/`state.subText` and re-runs `applyAndRender()` — this only re-filters the product `#grid`, not hero tiles/category-nav/collections.
- `#chips` = top-level category-switcher row (auto-built from `viewProducts`). `#attrChips` (`.fbar`) = attribute/facet filter toolbar, auto-scopes to a single category's `filters` keys only when `viewProducts` (as scoped) belongs to exactly one category — safe to reuse as-is on single-category pages.
- Tweaks panel `DEF` config (~line 1209) sets page-wide defaults via `localStorage` key `crystal-products-tweaks`: `showCategoryNav: true` (Shop-by-category section), `showCollections: false` (Featured Collections is **hidden by default site-wide** already — don't need to fight it on dedicated pages), `gridCols: "4"`.
- `ATTR_LABELS` map (~line 845) gives facet keys human labels; it's generic/shared and was written with cookware/knives in mind (`type` → "Shape"). Missing a `size` label entirely. Safe to override per dedicated-category-page copy since each page has its own independent script copy.

## Dedicated per-category page pattern (established 2026-08-17)
Building standalone SEO pages (`Cooktop.html`, `Lunch-Box.html`, and sibling pages `Cookware.html`, `Kitchenware.html`, `Water-Bottle.html`, `Oil-Pourer-Sprayer.html`, `Wood-Range.html`, `Pressure-Cooker.html`, `Cleaning-Aid.html`, `Electric-Appliances.html` were built in the same effort, likely by parallel agents) instead of `All-Products.html?cat=xxx`. Recipe used:
1. Copy `All-Products.html` wholesale; keep header/mega-menu/footer/tweaks-panel/`enquiry.js` byte-for-byte (nav links inside this shared chrome still point at `All-Products.html?cat=...` — intentionally left as-is; site owner updates cross-page nav separately).
2. `<title>` + add `<meta name="description">` (missing site-wide) with real, keyword-relevant, non-fabricated copy.
3. Hardcode hero (`heroPreTxt`, `heroTitle`, `heroSub`) and section headings (`catLead`, `colTitle`, `colLead`, `browseTitle`, `ctaTitle`/`ctaSub`) with category-specific copy instead of generic "All Collections" text.
4. In the bootstrap fetch (`loadCatalog()`), filter `data.products` to the one category **before** mapping into `P` — this is the key change that makes hero tiles / `#catGrid` / counts all scope correctly for free (rather than only filtering `#grid` post-hoc like the `?cat=` query-param path does).
5. Hardcode `state.cat` (and leave `state.cats: null`) to the category slug; delete the `?cat=/?sub=` URL-parsing IIFE entirely (page no longer needs deep-linking into itself).
6. Hide `#chips` (top-level category switcher — redundant, single category) via `style="display:none"`; leave `#attrChips` alone (self-scopes).
7. If a category has zero real product photos (e.g. cooktop), pick 1-2 genuinely on-topic existing images from `about-assets/` (checked visually) as the `img` fallback instead of the generic `about-assets/prod-1.jpg`, alternating by index so hero tiles (deduped by src) get some variety rather than collapsing to a single oversized tile.
8. If a category has **zero products** in the data (e.g. lunch-box): keep hero/header/footer fully built (as a "coming soon" teaser, honest in title/meta about launch status), replace the grid's generic "No products in this category yet" empty state with a custom `.empty-soon` card (icon + heading + message + CTA button to `Contact.html`), hide `.browse-bar` (sort/count is meaningless at 0 items) and set the tweaks `DEF.showCategoryNav = false` for that page only (otherwise "Shop by category" renders a visibly blank section since no category matches).

## Environment gotcha: Browser-pane tabs are shared across concurrent sessions
The `mcp__Claude_Browser__*` tool's browser instance/tabs can be **shared with other concurrent agent sessions** operating on this same repo (e.g. a fleet building the other category pages in parallel). Reusing an existing `tabId` can silently show a stale/foreign page (observed: navigating to `Cooktop.html` returned another session's already-loaded "Water Bottles" page content). Mitigation: close stray tabs and open a fresh one with `tabs_create`, then immediately assert `location.href`/`document.title` via `javascript_tool` before trusting further `get_page_text`/`read_console_messages` calls on that tab. Also, `computer` screenshots were unavailable in this environment ("Browser pane is not displayed") — fall back to `javascript_tool`/`get_page_text`/`read_console_messages` for verification instead of visual screenshots.

## v2 visual facelift (established 2026-08-17, applied to `Cookware.html`/`Kitchenware.html`)
- `index-v2.html` is the "v2" design language reference. Its style block layers two things: base tokens/rules (`:root`, `h1-h4`, etc. near lines 16-45) then a `V2 — MODERN FACELIFT` comment block (~line 422+) that overrides specific selectors with softer/rounder/premium values (font Inter, `h1-h4` `letter-spacing:-0.03em`, `.eyebrow` pill bg, `.btn`/`.btn-red` softer radius+shadow, `.work-card`/`.why-card`/`.tst-card`/`.infra-card` at 24-28px radius with colored shadows like `0 36px 80px -36px rgba(15,15,15,0.5)`).
- To port the v2 look to a cloned page (same pattern as `All-Products.html`-derived pages): swap the Google Fonts `<link>` to Inter only, set `--head`/`--body` to `"Inter", sans-serif`, fold v2's override values directly into the page's *existing* base selectors (`h1,h2,h3,h4`, `.eyebrow`, `.btn`, `.btn-red`, `.chip`/`.fbtn`/`.fopt` hover/active, `.pcard`) rather than duplicating selectors — index-v2 uses a separate override block because it's layering onto an already-shipped v1 page; a fresh clone doesn't need that split.
- `.pcard` has no direct v2 equivalent class; mirrored the `.work-card`/`.infra-card` treatment instead: `border-radius: 26px` (was `var(--r)`, which is the tweaks-panel-controlled 20px default — decoupling it from the radius slider is intentional here, matches the "premium fixed radius" ask) and hover shadow `0 36px 80px -36px rgba(15,15,15,0.5)` (was `0 32px 58px -34px rgba(15,15,15,0.42)`).
- **Gotcha:** every product-listing page (including `index-v2.html` itself) ships a hidden dev "tweaks panel" whose `DEF.type` config defaults to `"editorial"` on page load — this adds a `body.tv-editorial` class that overrides `h1-h4` to `font-weight:500; letter-spacing:-0.012em; text-transform:none`, silently superseding the base `h1,h2,h3,h4` rule (which we set to `font-weight:800; letter-spacing:-0.03em` to mirror index-v2's base value). This is expected/pre-existing and not a bug — `index-v2.html`'s real headings render at weight 500 too because of the same default. Verified via `getComputedStyle` + walking `document.styleSheets` to find which rule won.

## Standalone Cookware sub-category pages (established 2026-08-17)
- `Cookware-Tripro.html` (43), `Cookware-Cast-Iron.html` (4), `Cookware-Non-Stick.html` (29), `Cookware-Non-Stick-Mini.html` (5), `Cookware-Sandwich-Bottom-Steel.html` (6), `Cookware-Hard-Anodised.html` (1) — one page per real `subcategory` value under `category==="cookware"` (sum = 88, matches `Cookware.html`'s total). None are 0-product currently.
- Built by copying `Cookware.html` (not `All-Products.html`) verbatim, then: (1) added `FIXED_SUB` alongside the existing `FIXED_CAT` const and changed the `catProducts` filter to AND both — since `Cookware.html`'s hero tiles/`#catGrid`/`#colGrid`/grid/counts already all derive from one `viewProducts` var, this single line scopes everything; (2) hid `#chips` via inline `style="display:none"` (redundant — page IS one subcategory) while leaving `#attrChips` (induction/set_type/type facets, shared across all 6 subs) untouched; (3) set `state.subLabel` at init to the display label so `#count` reads "...in Tripro" not "...in Cookware"; (4) rewrote title/meta/hero/section copy per page, cross-checked against `About.html` for tone/facts (no unverifiable claims added — e.g. skipped a DuPont/non-stick certification mention since it's an `About.html` company-history claim, not present anywhere in `products.json`).
- Each subcategory's products share exactly **one** `collection` value in the data (tripro→"Triply", cast-iron→"CAST IRON", non-stick→"Nonstick", non-stick-mini→"Nonstick - Mini", sandwich-bottom-steel→"Sandwich Bottom Steel", hard-anodised→"Hard Anodised") — so `#colGrid` (Featured Collections) would only ever render 1 card on these pages; harmless because that section is already hidden by default site-wide (`DEF.showCollections: false`).
- Generated via a one-off Node script (in the session scratchpad, not committed) doing exact-match string replacement with a "must-find-exactly-once" guard — reliable for applying the same ~13 edits to 6 near-identical 97KB files; worth reusing this approach for any future "N variants of one template page" task.

## Standalone Electric Appliances sub-category pages (established 2026-08-17)
- `Electric-Appliances-Kettle.html` (4), `-OTG.html` (2), `-Rice-Cooker.html` (1), `-Food-Processor.html` (1), `-JMG.html` (2), `-Chimney.html` (0), `-Iron.html` (0), `-Ice-Cream-Maker.html` (0), `-Air-Fryer.html` (0) — one page per real `subcategory` under `category==="electric-appliances"` (sum = 10, matches `Electric-Appliances.html`'s total; 4 of the 9 subs are currently 0-stock).
- Built by copying `Electric-Appliances.html` (already v2-facelifted) verbatim via a one-off Node script in the session scratchpad (same `mustReplace`-once-guard approach as the Cookware sub-pages) — **watch out for CRLF**: this repo's HTML files are CRLF line-endings; a plain-JS template-literal search string using `\n` will silently fail to match multi-line blocks unless you normalize (`content.replace(/\r\n/g,'\n')`) before searching and convert back (`.replace(/\n/g,'\r\n')`) before writing.
- Added `PAGE_SUB` const alongside the existing `PAGE_CAT` and changed the `loadCatalog()` fetch filter to `.filter(p => p.category === PAGE_CAT && p.subcategory === PAGE_SUB)` — same "filter upstream, not post-hoc" principle as other dedicated pages, cascades to hero tiles/collections/grid for free.
- `Electric-Appliances.html`'s own `DEF` already ships `showCollections/showBrandValue/showCTA: false` by default (dev-tweaks-panel-only sections, not visible out of the box) — only `showCategoryNav: true` and `showMarquee: true` are on by default. For sub-pages, flipped `showCategoryNav` to `false` (the "Shop by type" 9-tile subcategory-switcher grid is redundant/confusing on a page already scoped to one type) — same one-line DEF change as `Lunch-Box.html` used, no HTML/JS structural removal needed since the section stays in the DOM, just hidden.
- Hid `#chips` (subcategory pill-switcher row) via inline `style="display:none"` — same reasoning as `#catGrid`, both are switchers for the other 8 sibling subcategories which don't apply on a single-sub page.
- Set `state.subLabel` (and `subText`) at init to the sub's label/slug so `#count` reads "...in Kettle" instead of generic "...in Electric Appliances".
- **Empty-state upgrade (new pattern, worth reusing):** split the old single `if (!list.length)` branch into two: `!viewProducts.length` (genuinely 0 stock for this sub — "Coming Soon" copy + Contact.html CTA, mirrors `Lunch-Box.html`'s `.empty-soon` card/CSS which didn't previously exist in `Electric-Appliances.html`, ported over) vs. `list.length===0` but `viewProducts.length>0` (attribute filters over-narrowed on a page that DOES have stock — "No Matches" copy + a "Clear Filters" button wired to reset `state.attrFilters`). Gives a correct, non-broken empty state either way instead of only handling the zero-stock case.
- Hero secondary CTA button repurposed as the breadcrumb/back-link (`Electric-Appliances.html` had none to port forward): `← All Electric Appliances` pointing at the parent category page, replacing the original "Featured Collections" button (that section is hidden by default anyway, see above).
- Cosmetic extra: added `class="active"` to the current sub's own link inside the shared mega-menu / mobile accordion "Electric Appliances" group (harmless — those links still point at `All-Products.html?cat=appliances&sub=...`, per instructions not to touch cross-page nav targets, just a visual highlight of "you are here" within the shared chrome).

## Environment gotcha: scratchpad files can also be overwritten by concurrent sessions
Not just Browser-pane tabs (see above) — the per-session scratchpad temp directory can apparently collide/get overwritten mid-task too (observed: a `gen.js` script for this Electric Appliances task was silently replaced mid-session with an unrelated `Kitchenware-*` generator script from another concurrent session). Mitigation: if a scratchpad file's content doesn't match what you just wrote, don't trust it — write to a fresh, distinctively-named file instead of assuming corruption is your own bug. Similarly `git status` can show large unrelated untracked/modified sets and even show a file you know is already committed (e.g. `Electric-Appliances.html`) as `??` — this repo is being worked on by multiple concurrent agent sessions and its git index can be mutated by any of them; don't run destructive git commands (`add -A`, `reset`, `checkout .`) based on a `git status` snapshot without first confirming the specific files you care about via `git diff <file>` / `git ls-files -- <file>`.

## Standalone Kitchenware sub-category pages (established 2026-08-17)
- `Kitchenware-Lighters.html` (10), `-Knives.html` (72), `-Peelers.html` (7), `-Chopping-Boards.html` (19), `-Trolleys.html` (3), `-Kitchen-Tools.html` (29), `-Manual-Appliances.html` (30), `-Cutlery.html` (61), `-Servers.html` (61), `-Water-Filter.html` (4) — one page per real `subcategory` under `category==="kitchenware"` (sum = 296, matches `Kitchenware.html`'s total exactly). None are 0-product currently, so no "coming soon" empty-state was needed this round.
- Built by copying `Kitchenware.html` (already v2-facelifted) verbatim via the same one-off Node-script "must-match-exactly-once" string-replacement approach as the Cookware/Electric-Appliances sub-pages, with the CRLF normalize-before-search / restore-before-write gotcha applied from the start (avoided the bug the Electric-Appliances session hit).
- Added `FIXED_SUB`/`SUB_LABEL` next to the existing `FIXED_CAT` const; changed `catProducts` to `P.filter(p => p.c === FIXED_CAT && p.sub === FIXED_SUB)` — the one line that cascades correct scoping to hero tiles/`#catGrid`/`#colGrid`/grid/counts for free, same principle as every other dedicated sub-page.
- **Deviation from the Cookware/Electric-Appliances precedent on `#colGrid` ("Featured Collections"):** those sessions left the collection-grouping logic as-is (each sub-category shares one `collection` value in the data, so it degrades to a single card) and relied on `DEF.showCollections: false` hiding the section by default. Since `Kitchenware.html` ships the same `showCollections: false` default, that same fallback applies here too — but rewrote the section anyway (grouping by distinct product image instead of `collection`, up to 3 individual products, each `<a>` now has a real `href` to `Product.html?p=...` instead of a JS `data-col` intercept) so it renders 3 genuinely useful cards and navigates correctly *if* the site owner ever flips `showCollections` on via the tweaks panel. Removed the `#colGrid` click-handler's `e.preventDefault()`/`state.col` filtering entirely since it's now plain anchor navigation.
- Fully removed (not just hidden) the sub-category chip switcher: `#chips` element deleted from HTML, plus its render block, `setSub()`, and the `chipsEl` click listener deleted from JS (Cookware/Electric-Appliances sessions only did `style="display:none"` on `#chips` and left the JS in place — this session went further since the task explicitly asked to "remove/hide"). `state` simplified to `{ sort, attrFilters }` — dropped the now-dead `cat`/`col`/`cats`/`subLabel`/`subText` fields and their branches in `applyAndRender()`; `#count` now always reads "...in `${SUB_LABEL}`" unconditionally instead of a multi-way fallback.
- "Shop by category" (`#catGrid`) is **visible by default** on `Kitchenware.html` (`DEF.showCategoryNav: true`, unlike `showCollections`) — so unlike the collections section, this one had to be actually correct out of the box. The generic `CATEGORIES`-iteration render (which, once scoped to one category, always resolves to exactly one "Kitchenware" tile — same behavior already present on `Kitchenware.html` itself) would have mislabeled the tile "Kitchenware" while showing only the sub-category's count. Replaced with a hardcoded single-card render using `SUB_LABEL` + `viewProducts.length` instead, so e.g. Lighters correctly shows "Lighters · 10 products", not a misleading "Kitchenware · 10 products".
- No breadcrumb existed on `Kitchenware.html` to port forward (confirmed via grep, same finding as the Cookware session). Chose a different treatment than the Electric-Appliances session's repurposed-CTA-button approach: turned the hero eyebrow (`#heroPre`) into a two-part breadcrumb — `<a href="Kitchenware.html">Kitchenware</a> / {Sub Label}` — since the eyebrow is visible by default on every variant and reads naturally as "you are here" without needing a whole extra CTA button.
- Facet bar (`#attrChips`) needed zero code changes — it already self-scopes to whichever single category is present in `scoped`, and since `viewProducts` is now sub-filtered, the facets it renders are automatically sub-specific for free (e.g. Knives → Brand/Set/Handle/Edge; Cutlery → Brand/Design/Set Size/Set; Chopping Boards → Material/Size/Blade).

## Standalone Cleaning Aid sub-category pages (established 2026-08-17)
- `Cleaning-Aid-Spin-Mops.html` (9), `-Hand-Held-Mops.html` (7), `-Brooms.html` (10), `-Wipers.html` (12), `-Plunger.html` (2), `-Brush.html` (13), `-Scrubber.html` (4), `-Bins.html` (5), `-Sink-Organiser.html` (2), `-Wipe.html` (2) — one page per real `subcategory` under `category==="cleaning-aid"` (sum = 66, matches the count `Cleaning-Aid.html`'s own hero copy already advertises). None are 0-product currently, so no "coming soon" empty-state was needed for the default view (the `.empty-soon` CSS/markup was still added for the "no attribute-filter matches" case — see below).
- Built by copying `Cleaning-Aid.html` (already v2-facelifted) verbatim, NOT `All-Products.html` — the site owner was explicit about this since `Cleaning-Aid.html` had just received the v2 pass (Inter, pill eyebrows, 24px-radius `.pcard` with colored hover shadow) and older templates hadn't.
- **Found the real established convention partway through by diffing an existing sibling pair** (`Electric-Appliances.html` vs `Electric-Appliances-Kettle.html`, built by an earlier concurrent session — see the Electric Appliances section above) instead of improvising: this session's first draft invented its own treatment (cross-linking `#catGrid` to sibling sub-pages, repurposing `#colGrid` into a "featured picks" grid of individual products with real `Product.html` links) before noticing `Cookware-*`/`Electric-Appliances-*` already existed in the repo and represented the site owner's actual accepted pattern. Discarded the invented version and rebuilt against the diff instead — worth checking for existing sibling pages of the *same shape* before designing a new one from scratch, not just reading the immediate parent template.
- Confirmed convention (mirrors `Electric-Appliances-Kettle.html` exactly): add `PAGE_SUB` next to `PAGE_CAT`, change `loadCatalog()`'s filter to `.filter(p => p.category === PAGE_CAT && p.subcategory === PAGE_SUB)`; leave `SUBCATS` (all 10 siblings) and `#catGrid`'s per-sub-count render loop completely unchanged; hide (not delete) the redundant switchers — `#chips` via inline `style="display:none"`, and the whole `#categories` ("Shop by type") section via flipping the tweaks-panel `DEF.showCategoryNav` to `false` (cheap, since the section would otherwise render 9 sibling cards reading "0 products" + 1 real one). `#collections` was already `showCollections:false` by default site-wide so its degenerate single-collection-per-sub grouping doesn't need reworking either.
- Set `state.subLabel`/`state.subText` at init to the sub's label/slug (so `#count` reads "...in Spin Mops") — same as the Kettle precedent, technically redundant once `P` is pre-filtered but kept for consistency/robustness.
- Ported the `.empty-soon` CSS block (Coming-Soon / No-Matches card, originally introduced on `Lunch-Box.html`) into every page even though all 10 subs currently have stock — it's the "no attribute-filter matches" fallback (`applyAndRender`'s `if (!list.length)` now branches on `viewProducts.length` too) and the pre-existing generic `<div class="empty">` text was worse UX for that case regardless of stock status.
- Hero secondary CTA repurposed as the back-link, matching the Kettle precedent exactly: `← All Cleaning Aid` → `Cleaning-Aid.html`, replacing the original `#collections`-anchor "Featured Collections" button.
- Added `class="active"` to the current sub's own link inside the shared mega-menu / mobile accordion "Cleaning Aid" group (cosmetic "you are here" highlight; cross-page nav targets themselves — `All-Products.html?cat=cleaning&sub=...` — deliberately left untouched, site owner's call).
- Generator: one-off Node script in the session scratchpad, `raw.split(anchor).length - 1 === 1` guard on every search string before replacing (fails loud instead of silently no-op'ing or double-replacing), CRLF-normalize-then-restore on write (`content.replace(/\r\n/g,'\n')` while slicing anchors, `.replace(/\n/g,'\r\n')` on the final assembled string) — same gotcha logged by the Electric-Appliances session, still worth restating since it's easy to reintroduce by typing replacement blocks with plain `\n`.

## Size-variant products (established 2026-08-18)
- `product-data/products.json` products can carry `variant_group` (e.g. `"vg-08"`), `variant_label` (e.g. `"14 CM"`), `variant_order` (0-based, ascending by size) — present only on the 72 products (20 families) that are genuinely the same product at different sizes (Tripro cookware lines, oil pourer ml, knives cm, etc.). Absent/`null` on all other products.
- **Listing pages** (all 46 category/sub-category pages + `All-Products.html`): each dedupes `data.products` right after the JSON fetch, keeping only the lowest-`variant_order` member per group, before any page-specific category filter runs. When adding a NEW dedicated listing page in future, port this same block (search any existing page for the comment `"Merge same-product size variants"`) — otherwise the new page will show every size as a separate card again.
- **`Product.html`**: real per-product size switching lives in `renderProduct()` — `siblings = P.filter(p => p.vgroup === prod.vgroup)`; chips render into both `#vChips` (hero `.vsel`) and `#vChips2` (Specs-section "Available Sizes"); clicking navigates via `location.href = "Product.html?p="+id` (full nav, not in-place DOM patch — safe against the page's one-time GSAP timeline setup). The whole `.vsel` block + `#vSecHeading`/`#vChips2` auto-hide when a product has ≤1 sibling.
- To regenerate/re-tag variant groups after a future Excel/product-data merge: re-run the same detect-by-stripped-name-and-unit-token approach (script was deleted after use, not committed — rewrite from this description if needed) and re-apply the listing-page dedupe block to any newly added page.

## Amazon product-data scraping (`amazon-products/` folder, batch runs, 2026-08-24)
- Task: for a list of amazon.in `/dp/<ASIN>` URLs, scrape title/bullets/description/variants/images into `amazon-products/<ASIN>/info.json` + up to 5 downloaded `img-N.jpg`, run in parallel batches of ~15 URLs per session.
- **Old-ASIN redirect gotcha (batch 11, discovered 2026-08-24):** many pre-2020 ASINs (`B07M*`, `B07N*`, `B07P*`, `B07Q*`, `B07V*`, `B081T*`) no longer resolve to their own page — Amazon 301s them to an unrelated newer ASIN (different product entirely, e.g. `B07MKJPZY7` → `B0BL6TWBP2` "Square Server", `B07MR8XBGR` → `B00UHEKZOK` "Sleek Plain Edge Knife"). The redirect is **often delayed 2-6s after the `navigate` call returns and after the tab title first shows the *correct* original-product title** — reading `document.location.href`/`#productTitle` immediately after `navigate` can capture stale/about-to-be-replaced content. Mitigation: after `navigate`, `wait` ~3s, re-check `document.title`, and if it changed, wait again until `location.href` stabilizes before extracting. Verified the redirect is real (not a race) by re-navigating fresh and reading `location.href` again — reproducible every time for the same ASIN.
- Confirmed handling: for a genuine redirect-to-different-product, write `error.txt` in the *original* ASIN's folder noting `"redirected to different product (<new-ASIN> - <new-title>); original ASIN <old-ASIN> appears delisted/merged"` — do NOT save the redirected product's data under the old ASIN's folder (would mislabel it).
- Batch 11 of 15 URLs: 2 succeeded (`B07MDBRMVR` Dessert Knife Set, `B07MDBRMVY` Soup Spoon Set, `B07PV27LKF` Apple Cutter — 3 actually succeeded), 1 blocked by captcha (`B07PV2CBZ9`, one retry attempted per instructions then gave up), 11 redirected to unrelated newer ASINs and were logged as errors rather than mis-saved.

## Amazon product-data re-scrape: cross-tab contamination fix (2026-08-24)
- 3 ASINs from an earlier parallel-batch scrape session had saved the WRONG product's data (`B098MVMKBT`, `B098MV5MKJ`, `B0DZGQ5W78`) — likely cross-tab contamination when running multiple scrapes concurrently. Symptom: `info.json` title/images belonged to a different, unrelated product than the ASIN's real Amazon listing.
- Fix pattern used: re-navigate each ASIN in its OWN fresh tab (not reused from a batch), read `#productTitle` immediately, confirm it plausibly matches the expected product before extracting/saving anything, delete the old (wrong) `img-*.jpg` files first, then download fresh images and overwrite `info.json`.
- Confirmed titles after fix: `B098MVMKBT` = "Crystal TriPro -Triply Stainless Steel Tasla - 26 cm (Induction Bottom)"; `B098MV5MKJ` = "Crystal TriPro -Triply Stainless Steel Saucepan with Lid - 20 cm (Induction Bottom)"; `B0DZGQ5W78` = "Crystal Trival Triply Stainless Steel 2 Pc Cookware Set (Fry Pan-22cm & Tea/Milk Saucepan-16cm)".
- Takeaway for future batch scrapes: always open a dedicated fresh tab per ASIN rather than reusing/sharing tabs across parallel scrape tasks — reuse is the likely root cause of the mislabeled saves.

## Contacts / voice reference
- Brand tone reference: `About.html`. Don't invent certifications/claims not already stated elsewhere on the site.
- Footer contact: `sales@crystalcook.com`, `022-49702803/06`, Rajkot (GIDC Metoda) + Mumbai (Andheri E) addresses — already in shared footer, no need to re-derive.

## export_to_json (DB -> products.json), 2026-08-25
- New command: `python manage.py export_to_json` (crystal/backend/products/management/commands/export_to_json.py). Regenerates `product-data/products.json` from the dashboard DB via `products.serializers.site_product_entries` (same layer as `/api/products/site.json/` — no duplicated mapping).
- Flags: `--check` (diff only, writes nothing), `--out PATH`. Writes temp file + `os.replace` (atomic), preserves file's SKU order + top-level metadata, refreshes `generated_at`, appends new SKUs after.
- Round-trip verified 2026-08-25: 531/531 entries, 0 real diffs; only the 8 known amazon_link placeholder products (`"No"`/`""` in file -> `null` in export: LI007, LI008, LI009, VML-002, CL-804, CLCL-003, CLMK-015, CWB042). Note: the file uses `null` (not `""`) for the other 213 link-less products, so export emits `null` for empty links to match.
- Older `export_products_json` command only handled dashboard_admin entries; `export_to_json` is the full-catalogue exporter to use going forward.

## Variants are now parent + sizes, not sibling products (2026-08-26)
- 29 `variant_group`s collapsed: one parent `Product` holds N `ProductVariant`
  rows, each owning its photos via `ProductImage.variant`. Active products
  530 -> 464 (435 standalone + 29 parents holding 95 sizes). 66 siblings are
  **deactivated, not deleted** — that is also the rollback.
- `ProductVariant` carries the fields that differ per size: `sku` (a FULL sku —
  base+suffix cannot rebuild the real ones, `LI008` does not start with
  `LI007`), `display_name`, `highlight`, `description`, `tags`, `features`,
  `amazon_link`, `price`, `video`, `video_url`, `image_url`, `match_tier`,
  `is_active`. **Blank/NULL means "inherit from the parent"**, so the JSON
  fields default to `None`, never `[]`.
- Measured, and the reason the model had to grow: within a group the Amazon
  link differs in **19 of 29** groups and the video in 7. Copying the parent's
  values onto every size would have destroyed both.
- `collapse_variant_groups.py`: `--dry-run`, `--group vg-09`, `--snapshot`,
  refuses without `--i-have-a-backup`, idempotent (re-running is a no-op).
  It **refuses** a group where a size owns no photos and no `image_url` while
  the parent has one — collapsing there would show a different product's photo.
- **Proof of safety, and how to re-prove it after any change:**
  `python manage.py export_to_json --check` must print `Products with real
  diffs: 0` and 530 entries on both sides. Stronger: export to a scratch file
  before and after and diff all 530 entries key-by-key including `hero`, the
  ordered `gallery`, `filters`, `variant_label`, `variant_order` and `id`.
- **Production has NOT been collapsed** as of 2026-08-26 — only the local DB.

## Dashboard gotchas worth not rediscovering (2026-08-26)
- jazzmin 3 is **AdminLTE 4 on Bootstrap 5**. AdminLTE-3 selectors
  (`.content-wrapper`, `.main-sidebar`) match nothing. The real layout is
  `.app-wrapper` / `.app-header` / `.app-sidebar` / `.app-content`, and colour
  comes from Bootstrap CSS **variables**, not classes.
- It renders `<html data-bs-theme="dark">` unless `JAZZMIN_SETTINGS`
  `default_theme_mode` says otherwise. Fix the mode; do not fight it in CSS.
- There is **no `.submit-row`** — jazzmin renders `#jazzy-actions`. Any rule
  targeting `.submit-row` silently does nothing.
- select2 here is `.select2-container--admin-autocomplete`, not `--default`.
- select2's absolutely-positioned mirror `<select>` is the usual cause of
  horizontal page overflow in this admin.
- `image_url` / `video_url` hold **site-relative paths**, so they must not be
  `URLField`s — that made 491 products unsaveable with "Enter a valid URL".
- Emitting such a path raw into an `<img src>` makes the browser request
  `/admin/products/product/<path>`, which Django's legacy catch-all reads as an
  object id; the failed lookup queues a "product doesn't exist" banner that
  appears on the *next* page. Resolve site content against `PUBLIC_SITE_URL`.
- A custom inline template must keep Django's formset contract:
  `data-inline-type`, `<prefix>-group`, `<prefix>-empty`, the management form,
  pk/fk hidden fields. Break one and "Add another" dies with no error. Copy the
  scaffold from jazzmin's own `admin/edit_inline/stacked.html`.
- jazzmin allows exactly one `custom_css`; a second sheet goes in via `@import`
  at the top of the first.

## Enquiries reach a human now (2026-08-26)
- Before this the form only did `console.log(payload)` behind a TODO — the
  success screen and reference number were shown but **nothing was sent
  anywhere**, so every enquiry made through the site was lost.
- `Enquiry.html` posts to `POST /api/enquiry/` on the dashboard service.
  `enquiry/emails.py` sends a thank-you to the customer and a notification to
  `ADMIN_NOTIFICATION_EMAIL` with reply-to set to the customer.
- Email failure never fails the submission; the page never shows success for a
  request that failed.
- **Still needs SMTP env vars** (`EMAIL_BACKEND`, `EMAIL_HOST`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`). Until then
  the console backend applies — enquiries still save, mail just is not sent.
- CORS must list the website origin or the browser blocks the POST outright.

## Deployment shape (2026-08-26)
- Two Railway services from one repo, separated only by Root Directory:
  website at repo root, dashboard at `crystal/backend`
  (`https://crystal-production-eb2e.up.railway.app`), plus Postgres and a
  volume at `/app/media`.
- `SECRET_KEY` self-provisions to `media/.secret_key` on the volume — nobody
  has to hand-carry one.
- In the dashboard container Python is at `/opt/venv/bin/python`; plain
  `python` has no Django.
- Migrations run as `preDeployCommand`, `collectstatic` as the build command —
  running `migrate` at build time fails, since no database is reachable then.
- The healthcheck path is exempt from `SECURE_SSL_REDIRECT`; the probe arrives
  over plain HTTP and a 301 is recorded as a failure.
- Watch Paths are still unset, so a push rebuilds **both** services.

## Site-wide heading size (2026-08-26)
- One block controls every h1/h2 on the site; it lives in all 68 HTML pages.
  Currently **37px**, phones `clamp(26px, 6.4vw, 34px)`.
- **Change it in four places, not one**: the 68 pages *and*
  `home-v3-src/heading-size.css`, `apply_heading_size.py`, `build_v3.py`.
  `index.html` is generated, so missing the builder means the next home-page
  rebuild silently reverts it.
- `home-v3-src/apply_heading_size.py` re-applies the block across all pages;
  it matches on the marker comment `HEADING SIZE — every h1 and h2`.
- Deliberate exception: `.v3 .map3-right .v-head` stays
  `clamp(22px, 2vw, 30px)` — the client asked for that heading to be smaller.

## Category banner heroes (2026-08-26)
- 45 category pages share one hero shape. `home-v3-src/apply_category_banner.py
  <Page.html> <image>` does the whole job: webp+jpg encode, crop scoring,
  CSS + markup, and a contrast report. Re-running is safe.
- The banners are ~5:1. Only about half the width is ever visible, so the crop
  (`--banner-focus`) is scored from per-column brightness and edge energy, not
  centred. **Coverage of the subject must dominate the score** — weighting a
  quiet copy area first once picked a crop holding 25% of the subject.
- `--focus N` overrides it; the automatic value is a starting point.
- Two things break the moment a photograph sits behind the text: the fixed,
  transparent, dark-texted header lands on the picture (top white wash fixes
  it), and on phones the desktop foot fade swallows the subject (the narrow
  layout gets its own 2:1 band and a hairline fade).
- Contrast is measured per page by compositing both scrims over the real
  photograph — never assumed.
- Ideal source is ~1980x800+; the supplied 1980x390 upscales ~1.28x in the hero.

## Browser-pane screenshots are not trustworthy (2026-08-26)
- The pane returns `UnknownVizError`, and worse, returns **blank white captures
  of pages that render correctly** — including pages it photographed fine
  minutes earlier. It also mis-scales iframes.
- Verify with `getBoundingClientRect`, `img.complete`/`naturalWidth`,
  `elementFromPoint`, and by compositing offline with PIL. Do not diagnose a
  page from a blank capture.

## Banner crop scoring — the mistake to not repeat (2026-08-26)
- Score **visible** subject, not **framed** subject. The band's left is washed
  to near-white for the copy, so subject landing there is invisible. Weight
  each column by scrim transparency at its frame position.
- Even so, roughly a third of banners need `--focus` by hand. Always render the
  composited band and look at it; the score alone shipped a banner whose
  product was outside the frame.
- 11 pages done: Tripro 84, Cast-Iron 81, Non-Stick 54*, Non-Stick-Mini 55,
  Sandwich-Bottom-Steel 84, Hard-Anodised 93, Lighters 78, Knives 72*,
  Peelers 100, Chopping-Boards 64, Trolleys 62*  (* = set by hand)
- Client supplies one image per category, named after it, into ~/Downloads.

## Stand-in banners from product photos (2026-08-26)
- `pick_category_photo.py` + `compose_product_banner.py` build a banner from a
  catalogue product shot when the client's photo has not arrived.
- Page->products resolves via the page NAME against catalogue category and
  subcategory ids. The pages themselves filter three different ways, so do not
  try to reproduce their JS.
- Lift the background with a **flood fill from the frame edges**, never a
  brightness threshold — a threshold eats white parts of the product.
- **Scoring "clean white background" alone picks the carton.** Retail packaging
  is the cleanest shot a category owns. Prefer the product's own hero, scan
  deep, and expect to override a couple by hand.
- 13 pages cannot be done from the catalogue: Electric-Appliances + 9 subpages
  (no hero images), Cooktop (all photos <500px), Lunch-Box (no products at
  all), Wood-Range (all shot on dark teak).
- `CRYSTAL Light.html` is NOT a category page — it is a leftover template
  titled "CRYSTAL - Social Media Agency (Light)".

## Why browser-pane screenshots come back blank (2026-08-26)
- The real error is `the Browser pane is not displayed, so the page is not
  compositing frames`. An off-screen pane returns blank captures of pages that
  render perfectly. Not a page bug. Verify via DOM + offline PIL compositing.
