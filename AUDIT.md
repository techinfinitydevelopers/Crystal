# Crystal Cook — Website Structure & Content Audit

**Reference:** https://proj.leo9studio.in/projects/crystal-wp
**Audited:** index, About, All-Products, Product, Contact (5 live pages)
**Date:** 2026-06-10

---

## 0. Executive Summary — Top 5 Critical Gaps

| # | Gap | Severity |
|---|-----|----------|
| 1 | **Brand architecture mismatch.** We invented *Czarin, Freshmate, Vacu*; reference uses 4 real brands: **Crystal, Crystalina, SparkMate, ValMate**. ValMate is missing entirely. | 🔴 High |
| 2 | **Missing nav items:** Catalogue, Knowledge Centre, Request Quote. | 🔴 High |
| 3 | **Missing pages:** Catalogue, Knowledge Centre/Blog, Career, Privacy Policy, Terms — all are dead/anchor links today. | 🔴 High |
| 4 | **Flat product taxonomy.** Reference uses a 4-group mega menu (Cookware / Kitchenware / Cleaning Aid / Electric Appliances) with ~40 sub-categories; we have 8 flat categories. | 🟠 Medium |
| 5 | **Infrastructure stats absent.** Reference: 3 offices, 3 factories, 5 warehouses, 1,00,000+ outlets, 3,00,000 sq ft. Not on our site. | 🟠 Medium |

---

## 1. Recommended Sitemap

```
Home (index.html)
├── About Us (About.html)
├── Products (All-Products.html)
│   ├── Cookware            → ?cat=cookware
│   ├── Kitchenware         → ?cat=kitchenware
│   ├── Cleaning Aid        → ?cat=cleaning
│   ├── Electric Appliances → ?cat=appliances
│   └── Product Detail (Product.html?p=…)
├── Brands (Brands.html)              ← NEW (landing) 
│   ├── Crystal     → All-Products.html?brand=crystal
│   ├── Crystalina  → ?brand=crystalina
│   ├── SparkMate   → ?brand=sparkmate
│   └── ValMate     → ?brand=valmate
├── Catalogue (Catalogue.html)        ← NEW — view/download PDF
├── Knowledge Centre (Blog.html)      ← NEW — article index
│   └── Article (Article.html?id=…)   ← NEW
├── Contact (Contact.html)
├── Request a Quote (Quote.html)      ← NEW — form
├── Career (Career.html)              ← NEW
├── Privacy Policy (Privacy.html)     ← NEW
└── Terms & Conditions (Terms.html)   ← NEW
```

---

## 2. Header Navigation — Recommended

**Current:** About · Products · Brands · Network · Contact Us
**Recommended (match reference):**

```
About Us | Products ▾ | Brands ▾ | Catalogue | Knowledge Centre | Contact Us | [Request Quote]
```

- **Products ▾** = mega menu (4 columns — see §4).
- **Brands ▾** = Crystal, Crystalina, SparkMate, ValMate (drop Czarin/Freshmate/Vacu).
- **Remove "Network"** — not in reference; fold its content into About.
- **Add "Request Quote"** as the primary red CTA (replacing/alongside Contact Us).
- Priority: **High** — nav is the primary IA signal and currently diverges most.

---

## 3. Footer Navigation — Recommended

| Column | Links |
|--------|-------|
| **Brand + blurb + social** | Instagram, Facebook, YouTube, LinkedIn |
| **Brands** | Crystal, Crystalina, SparkMate, ValMate |
| **Quick Links** | About Us, Catalogue, **Career** *(make live)* |
| **Products** *(add)* | Cookware, Kitchenware, Cleaning Aid, Electric Appliances |
| **Contact** | Rajkot addr, Mumbai addr, 022-49702803/06, sales@crystalcook.com |
| **Legal bar** | Privacy Policy, Terms & Condition *(make live)* |

Structure already matches; the fix is **making Catalogue / Career / Privacy / Terms real pages** and **adding a Products column**. Priority: **Medium**.

---

## 4. Product Ecosystem — Mega Menu (Reference Taxonomy)

Replace 8 flat categories with the reference's 4-group structure:

| Group | Sub-categories |
|-------|----------------|
| **Cookware** | Tripro, Cast Iron, Non-Stick, Non-Stick Mini, Sandwich Bottom Steel, Hard Anodised, Pressure Cooker |
| **Kitchenware** | Lighters, Knives, Peelers, Chopping Boards, Trolleys, Kitchen Tools, Manual Appliances, Cutlery, Servers, Water Filter, Lunch Box, Water Bottle, Oil Pourer & Sprayer, Wood Range |
| **Cleaning Aid** | Spin Mops, Hand-Held Mops, Brooms, Wipers, Plungers, Brushes, Scrubbers, Bins, Sink Organisers, Wipes |
| **Electric Appliances** | Chimney, Kettle, Iron, Ice Cream Maker, OTG, Air Fryer, Rice Cooker, Food Processor, JMG, Cooktop |

- Map filter chips on All-Products.html to these 4 groups + sub-filters.
- PDP (Product.html) already strong; align its category label to this taxonomy.
- Priority: **Medium** (High if a real product DB is being wired).

---

## 5. Required New Pages

| Page | Purpose | Priority |
|------|---------|----------|
| **Catalogue.html** | Embedded PDF viewer + download; brand-wise catalogues | High |
| **Blog.html** + **Article.html** | Knowledge Centre index + article template | High |
| **Quote.html** | Request-a-Quote form (bulk/export/distribution) | High |
| **Brands.html** | Brand landing hub with 4 brand cards → filtered products | Medium |
| **Career.html** | Openings + culture + apply form | Medium |
| **Privacy.html / Terms.html** | Legal | Medium |

---

## 6. Content Gap Analysis

### 6a. Missing Content (add)
- **Infrastructure block** (Home + About): 3 offices · 3 factories · 5 warehouses · 1,00,000+ outlets · 3,00,000 sq ft.
- **Trusted Partners / retail logos** confirmed on reference — keep & populate ours with real logos.
- **Knowledge Centre articles** (exact reference titles to seed):
  - "Built for the Way India Cooks" — 8 Feb 2026
  - "Why Triply Cookware is a Smart Choice" — 8 Jan 2026
  - "Everyday Cooking Made Effortless" — 8 Dec 2025
- **Request Quote flow** — currently only `mailto:`.

### 6b. Content to Update
- **Stats consistency.** Home says "54+ Years", About says "50+ Years / 2000+ Employees / 10+ Cr Customers" — reference discloses none of these. Pick ONE verified set and reuse site-wide. Recommend: align to reference infrastructure numbers + a single "Since 1971" age line.
- **Hero copy** → adopt reference voice: *"Simplifying daily chores, adding pride to every home — Since 1971."* Sub: *"From cooking to serving to cleaning — making everyday living effortless, elegant & extraordinary…"*
- **About blurb** → *"Half a century of trust, a lifetime of home pride…"* (reference copy is stronger; ours paraphrases it).

### 6c. Content to Replace
- **Brand names & taglines** across ALL pages (nav, footer, dropdowns, All-Products data, Product.html brand block):
  - Keep: Crystal — *World of Kitchenware*; Crystalina — *Splendid Finish*; SparkMate — *Cleaning Simplified*.
  - Add: **ValMate — *Value for Money***.
  - Remove: Czarin, Freshmate, Vacu (and reassign their products to the 4 real brands).
- **All-Products sample product data** — re-tag the 21 demo products to the 4 real brands.

### 6d. Content to Remove
- "Network" nav item (no reference equivalent).
- Invented brand pages/filters (`?brand=czarin|freshmate|vacu`).

### 6e. Content to Add (net-new sections)
- Catalogue CTA section linking to real Catalogue page.
- "Made in India" certification detail (reference has the section; expand copy).

---

## 7. Page-by-Page Recommendations

| Page | Action | Priority |
|------|--------|----------|
| **index** | Add Infrastructure stats block; wire "From the Blog" cards to real Blog.html; fix brand cards to 4 brands; align hero/about copy to reference. | High |
| **About** | Fix brand mentions to 4; reconcile stats; keep VMV/timeline/CSR (stronger than reference — retain). | High |
| **All-Products** | Re-map categories to 4-group taxonomy; re-tag products to 4 brands; fix brand dropdown. | High |
| **Product** | Update category label + brand block to real taxonomy/brands; otherwise solid. | Medium |
| **Contact** | Add **Request Quote** entry point / subject; otherwise complete & strong. | Low |

> **Note:** Our About (Vision-Mission-Values, timeline, CSR, awards) and Product detail pages are **richer than the reference** — do **not** strip them. Retain as brand differentiators.

---

## 8. Recommended User Flows

1. **Discover → Buy-intent:** Home → Products mega menu → Category → PDP → Request Quote.
2. **Brand-led:** Home/Brands → Brand filter → PDP → Enquire.
3. **Trust-building:** Home → About (legacy/CSR) → Catalogue → Contact.
4. **Content/SEO:** Knowledge Centre → Article → related Product → Quote.
5. **B2B/dealer:** Any page → Request Quote (bulk/export/distribution) → confirmation.

---

## 9. Priority Roadmap

**Phase 1 (High):** Fix brand architecture (4 brands) site-wide · Add Catalogue, Blog, Quote pages · Update header nav · Align hero/about copy.
**Phase 2 (Medium):** Mega-menu taxonomy · Infrastructure stats · Brands landing · Career page · Footer Products column.
**Phase 3 (Low):** Privacy/Terms · Search · article CMS · partner logo population.

---

## 10. Rationale (why this matters)

- **Brand truth > invention:** shipping fictional brands (Czarin/Freshmate/Vacu) is a factual defect — highest-priority fix.
- **Nav parity** drives discoverability of Catalogue/Knowledge Centre/Quote — the reference's main conversion paths.
- **Stat consistency** protects credibility; conflicting numbers across pages read as untrustworthy.
- **Retain our richer About/PDP** — they exceed the reference and differentiate the brand while staying on-design.
