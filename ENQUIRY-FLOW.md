# Crystal Cook — Product Enquiry & Buy-Now Flow (Design Spec)

**Goal:** A premium B2B/B2C *enquiry* platform (no online checkout/payments) with two CTAs per product — **Enquire Now** (adds to an Enquiry Cart → enquiry form → admin) and **Buy Now** (redirects to external marketplaces: Amazon / Flipkart / JioMart).
**Date:** 2026-06-10 · **Applies to:** index, About, All-Products, Product, Brands, Catalogue + new Enquiry page.

---

## 0. Architecture Reality (read first)

The site is **static HTML/CSS/JS** (no server, no DB). That dictates the design:

| Concern | Solution |
|---------|----------|
| Enquiry Cart (add/remove/qty, persists across pages) | **100% client-side** via `localStorage` — no backend needed. |
| Cart badge in header (all pages) | Client-side, reads `localStorage` on every page load. |
| Submit enquiry → email admin + store in DB/admin panel | **Needs a backend or a form service** (static HTML can't store data). |

**Recommended two-phase backend:**

- **Phase A (launch fast, zero server):** [Web3Forms](https://web3forms.com) or Formspree. The form POSTs (incl. a JSON blob of cart items) → emails the admin instantly. Free tier, no infra. Gives email delivery + a basic dashboard.
- **Phase B (real admin panel + queryable DB):** a serverless function (Cloudflare Worker / Vercel / Netlify function) writing to **Supabase** (Postgres + instant admin UI) or **Airtable** (fastest no-code admin grid). The same function also emails the admin (Resend/SendGrid).

> Recommendation: ship **Phase A** with the full client-side cart now; layer in **Phase B** (Supabase) when an admin panel is required. The frontend code is identical — only the form's submit endpoint changes.

---

## 1. Complete User Flow

```
Browse (Home / Products / Brand / PDP)
        │
        ├──► [Enquire Now]  ──► item added to Enquiry Cart (localStorage)
        │                        toast "Added to enquiry" + header badge +1
        │                        user keeps browsing, adds more
        │
        ├──► header [🛒 Enquiry (n)] ──► Enquiry Cart page
        │                                  • list: image, name, brand, category, SKU, qty, remove
        │                                  • enquiry form (name, company, email, phone, city,
        │                                    state, country, business type, message)
        │                                  • "This is a product enquiry, not an online order"
        │                                  └──► [Submit Enquiry]
        │                                          ├─ attach all items + qty
        │                                          ├─ POST → backend/form-service
        │                                          ├─ email admin + store record
        │                                          └──► Success: ref no. CC-260610-A3F2,
        │                                               "Our team will contact you shortly",
        │                                               cart cleared
        │
        └──► [Buy Now] ──► 1 marketplace?  → open that URL in new tab
                           multiple?        → Marketplace Modal (Amazon / Flipkart / JioMart)
                                              → user picks → new tab
```

---

## 2. Page Flow Diagram

```
┌──────────────┐   Enquire Now    ┌───────────────────┐  Submit   ┌──────────────┐
│ Product Card │ ───────────────► │  Enquiry Cart      │ ────────► │ Success +    │
│  / PDP       │                  │  (Enquiry.html)    │           │ Ref Number   │
│              │   Buy Now        │  items + form      │           └──────────────┘
│              │ ───────┐         └───────────────────┘                  │
└──────────────┘        │                 ▲  cart badge (all pages)      │ cart cleared
                        ▼                 └──────────────────────────────┘
              ┌──────────────────┐
              │ Marketplace Modal│ ──► Amazon / Flipkart / JioMart (new tab, external)
              │ (if >1 link)     │
              └──────────────────┘
```

---

## 3. Product Card CTA Behavior

Each card (on All-Products grid, Brand pages, "Related"/"Featured" rails) gets **two CTAs**:

```
┌─────────────────────────┐
│   [product image]       │
│   BRAND ·  category      │
│   Product Name           │
│   short highlight        │
│   ┌─────────┐ ┌────────┐ │
│   │Enquire ＋│ │ Buy ▾ │ │   ← Enquire = btn-dark; Buy = btn-red w/ caret if multi
│   └─────────┘ └────────┘ │
└─────────────────────────┘
```

- **Enquire Now:** `+`-style button. On click → `addToEnquiry(productId)`, show toast, bump badge. Button briefly flips to "Added ✓". Does **not** navigate (user keeps browsing).
- **Buy Now:** if product has 1 marketplace → opens it (new tab). If >1 → opens **Marketplace Modal**. If 0 → button hidden (enquiry-only product).
- On compact cards, the two CTAs can collapse to icon buttons (cart-plus icon + bag icon) with `aria-label`s; full labels on hover/desktop.

---

## 4. Product Detail Page (Product.html) CTA Behavior

Primary action zone (right column, below trust badges):

```
Qty: [ – 1 + ]
┌────────────────────────┐ ┌────────────────────────┐
│  Enquire Now        ＋  │ │  Buy Now             🛒 │
└────────────────────────┘ └────────────────────────┘
Available on:  [Amazon] [Flipkart] [JioMart]   ← marketplace chips (also shown inline)
"Prefer bulk / dealer pricing? Add to enquiry — our team responds within 1 business day."
```

- **Enquire Now** respects the PDP quantity selector (adds N units).
- **Buy Now** → marketplace modal (or direct if single). On PDP, ALSO render the marketplace chips inline (discoverability) in addition to the Buy Now modal.
- Keep the existing "Enquire about this product" mailto as a fallback only if JS disabled.

---

## 5. Enquiry Cart Page (new: `Enquiry.html`)

Two-column on desktop, stacked on mobile (mirror Contact.html's `.ct-grid`).

**LEFT — Item list** (each row):
```
[img] Product Name                         [– qty +]   ✕
      BRAND · Category · SKU: CRY-LTR-001
```
Empty state: "Your enquiry list is empty" + "Browse Products" button → All-Products.html.

**RIGHT (or below on mobile) — Enquiry form**
A clear banner on top: **"You're submitting a product enquiry — not placing an online order. Our team will get back with pricing & availability."**

| Field | Type | Req |
|-------|------|-----|
| Full Name | text | ✓ |
| Company Name | text | – |
| Email Address | email | ✓ |
| Phone Number | tel | ✓ |
| City | text | ✓ |
| State | text | ✓ |
| Country | text/select (default India) | ✓ |
| Business Type | select: Dealer / Distributor / Retailer / Customer / Other | ✓ |
| Message / Requirement Details | textarea | – |

Submit button: **"Submit Enquiry"** (btn-red). Reuse Contact.html's validation + `.sent` success-state pattern.

---

## 6. Submission Flow

On submit (valid):
1. Build payload: `{ enquiry: {form fields}, items: [{id, name, brand, category, sku, qty}], ref, submittedAt }`.
2. POST to backend/form-service (Phase A: Web3Forms endpoint; Phase B: serverless fn).
3. Backend **emails admin** (full table of products + qty + customer) and **stores the record**.
4. On 200 → render success state, **clear the cart** (`localStorage`), reset badge to 0.
5. On failure → inline error + keep cart intact; offer mailto fallback.

---

## 7. Success State

```
        ✓  (animated check, brand red)
   Enquiry submitted successfully
   Reference: CC-260610-A3F2
   "Thank you, {Name}. The Crystal Cook team will contact you shortly
    with pricing and availability."
   [ Continue Browsing ]   [ Back to Home ]
```
- **Reference number** generated client-side: `CC-<YYMMDD>-<4 hex>` (also sent to backend & shown in admin/email). Cheap, unique enough, professional.

---

## 8. Buy Now — Marketplace Redirection

**Recommended UX for multiple links: a centered Modal** (not a dropdown).

Why modal over dropdown/popover:
- Touch-friendly (large tap targets) — critical on mobile.
- Lets each marketplace show **logo + name + optional "lowest price/quick ship" note** — feels premium.
- No clipping inside cards/overflow containers (dropdowns get cut off in grids).
- One pattern reused everywhere (cards + PDP).

```
        ┌───────────────────────────────┐
        │  Buy "Aristo SS Lighter"       │
        │  Choose where to purchase:     │
        │  ┌───────────────────────────┐ │
        │  │ [a] Amazon            ↗   │ │
        │  ├───────────────────────────┤ │
        │  │ [F] Flipkart          ↗   │ │
        │  ├───────────────────────────┤ │
        │  │ [J] JioMart           ↗   │ │
        │  └───────────────────────────┘ │
        │  Prices & availability set by  │
        │  the marketplace.              │
        └───────────────────────────────┘
```
- All external links: `target="_blank" rel="noopener nofollow sponsored"`.
- **Single** marketplace → skip modal, open directly.
- **Zero** → hide Buy Now; show only Enquire (enquiry-only product).
- On PDP also show marketplace chips inline (in addition to the modal).

---

## 9. Admin Management Requirements

**Per product (content/data):**
- `sku` (string)
- `enquiryEnabled` (bool, default true)
- `marketplaces`: array of `{ name, url, logo }` (0..n)
  - e.g. `{ name:"Amazon", url:"https://amzn.to/…", logo:"icons/amazon.svg" }`

**Per enquiry (admin can view):**
- Reference no., submission date/time
- Customer: name, company, email, phone, city, state, country, business type
- Requirement message
- Enquired products: name, brand, category, SKU, **quantity**
- Status field (New / Contacted / Quoted / Closed) — for follow-up tracking
- Export to CSV; filter by date/business-type/status

Phase A admin = Web3Forms/Formspree inbox + email. Phase B admin = Supabase Table view / Airtable grid (sortable, filterable, status dropdown, CSV export out-of-the-box).

---

## 10. Database / Content Structure

**A. Product schema additions** (extend the existing `P[]` array in All-Products.html + Product.html data):
```js
{
  n: "Aristo SS Lighter", b: "crystal", c: "lighters",
  sku: "CRY-LTR-001",                       // NEW
  img: "...", hl: "...", tags: [...],
  enquiryEnabled: true,                      // NEW
  marketplaces: [                            // NEW (0..n)
    { name: "Amazon",   url: "https://...", logo: "icons/amazon.svg" },
    { name: "Flipkart", url: "https://...", logo: "icons/flipkart.svg" }
  ]
}
```
> For maintainability, move the product catalogue into a single shared `products.js` (or `products.json`) consumed by All-Products, Product, and Enquiry pages — today the data is duplicated across pages.

**B. Enquiry cart (localStorage)** — key `crystalEnquiry`:
```js
{ items: [ { id:"aristo-lighter", qty:2 } ], updatedAt: 1789... }
```
(Only id + qty stored; full product details resolved from `products.js` at render — keeps cart small and always in sync with catalogue.)

**C. Enquiry record (backend, Phase B — Supabase/Airtable table `enquiries`):**
```
id (uuid) · ref (text) · created_at (timestamptz)
name · company · email · phone · city · state · country · business_type · message
items (jsonb: [{id,name,brand,category,sku,qty}])
status (enum: new|contacted|quoted|closed)
```

---

## 11. Header / Global Component

Add a persistent **Enquiry cart icon** to the header nav-right (left of "Request Quote"), on every page:
```
[🛒 Enquiry · 3]   [ Request Quote ↗ ]
```
- Badge count = sum of qty (or distinct items) from `localStorage`.
- Click → `Enquiry.html`.
- Mirror in the mobile menu.
- A small global script (`enquiry.js`) handles: `addToEnquiry`, `removeFromEnquiry`, `setQty`, `getCart`, `renderBadge`, toast — included on all pages.

---

## 12. Mobile & Desktop UX

**Desktop:** dual CTAs side-by-side on cards; PDP has qty + dual CTA + inline marketplace chips; Enquiry page two-column (items | form); marketplace modal centered ~420px.

**Mobile:**
- Cards: full-width stacked CTAs, or icon buttons to save space.
- PDP: **sticky bottom action bar** with `Enquire` + `Buy` (thumb-reachable) — premium app-like feel.
- Enquiry page: items list first, form below; sticky "Submit Enquiry" bar optional.
- Marketplace modal: bottom-sheet style (slides up), large 56px rows.
- Toast: top-center, auto-dismiss 2.5s, respects `prefers-reduced-motion`.

**A11y:** modal = focus-trap + `Esc` to close + `aria-modal`; CTAs have `aria-label`; badge has `aria-live="polite"`; external links labelled "(opens marketplace in new tab)".

---

## 13. Implementation Plan (when approved)

1. **`products.js`** — centralize catalogue; add `sku`, `enquiryEnabled`, `marketplaces[]`. Seed marketplace URLs (placeholders ok).
2. **`enquiry.js`** — global cart lib (localStorage) + header badge + toast + marketplace modal + `addToEnquiry`/`buyNow` handlers. Include on all pages.
3. **Header** — add Enquiry cart icon + badge (all 13 pages) + mobile.
4. **Product cards & PDP** — render dual CTAs + PDP inline marketplace chips + PDP sticky mobile bar.
5. **`Enquiry.html`** — new page: item list (img/name/brand/category/SKU/qty/remove) + enquiry form + success state + ref number.
6. **Submit** — Phase A: wire to Web3Forms (incl. items JSON). (Phase B later: serverless fn + Supabase + admin.)
7. **Marketplace icons** — add `icons/amazon.svg`, `flipkart.svg`, `jiomart.svg`.
8. **QA** — add/remove/qty persistence across pages; single vs multi vs zero marketplace; mobile sticky bar; success clears cart.

---

## Decisions (status)
1. **Build status:** ✅ **Frontend implemented** (cart, badge, dual CTAs on cards + PDP, Enquiry page + form + success/ref number, Buy-Now modal with marketplace search-URL placeholders). ⏳ **Backend pending** — form validates + shows success client-side and `console.log`s the payload; wire to Web3Forms/serverless when chosen (see `enquiry.js` + `Enquiry.html` TODO).
2. **Buy Now multi-link UX:** ✅ **Modal** (mobile = bottom-sheet) — confirmed.
3. **Marketplace data (URLs):** ⏳ to be provided later; build with placeholders when implementing.
4. **SKUs:** ⏳ to be decided later (real SKUs or auto scheme `CRY-LTR-001`).
5. **Backend:** ⏳ open — choose Phase A (Web3Forms email) or Phase B (Supabase/Airtable admin) at build time.
