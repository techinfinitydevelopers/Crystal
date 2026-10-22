# Crystal Cook N Serve — website + dashboard

Live: https://crystalcook.com (Hostinger VPS; `main` deploys itself every 5 minutes).

## What lives where

| Path | What it is |
|---|---|
| `*.html` (root) | The public pages. Their file names are the live URLs (`About.html` → `/About`), so they stay at the root. |
| `content-sync.js`, `product-image-sync.js`, `enquiry.js`, `product-page.js/.css`, `seo-links.js`, `product-urls.js`, `image-slot.js`, `product-tweaks.js` | Shared scripts/styles the pages load by these exact paths. |
| `product-data/` | `products.json` — the catalogue every page reads. |
| `product-photos/`, `about-assets/`, `brand-assets/`, `brand-images/`, `brand-logos/`, `category-banners/`, `catalogue-assets/`, `home-v3-assets/`, `uploads/`, `sparkmate/`, `downloads/` | Images, videos and PDFs. Paths are stored in `products.json` and the dashboard database — do not move. |
| `home-v3-src/` | Sources for the Home page; `build_v3.py` writes `index.html` (a rebuild drops the SEO head — see `docs/BUILD_LOG.md`). |
| `crystal/backend/` | The Django dashboard (`/admin`, `/api`). |
| `tools/` | `cms_tag.py` (dashboard-editable keys) and `cms-manifest.json` (read by the dashboard). |
| `deploy/` | Server setup, deploy and `harden-nginx.sh`. |
| `scripts/` | One-off maintenance scripts. |
| `docs/` | Notes and logs (`BUILD_LOG.md`, `memory.md`, audits), `docs/data/` spreadsheets and documents, `docs/screenshots/`. |
| `archive/` | Old design-tool exports that were never live pages. |

`docs/`, `scripts/`, `archive/`, `deploy/`, `crystal/`, `home-v3-src/`, dotfiles and `*.md` are blocked
from the public site by `deploy/harden-nginx.sh` (re-run it on the server after changing its rules).
