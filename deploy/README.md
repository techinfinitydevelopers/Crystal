# Deploying Crystal

The site and the dashboard run on the client's own Hostinger VPS
(`187.126.118.190`, Ubuntu 24.04). The static site is served by nginx straight
off `/var/www/crystal`; `/admin` and `/api` are proxied to gunicorn.

## Pushing a change

Push to `main` and wait up to five minutes — a systemd timer checks GitHub and
deploys when `origin/main` has moved. To go now instead:

    ssh root@187.126.118.190 /root/deploy.sh

## Stopping auto-deploy without disabling it

During a DNS cutover, or any time the server must not change under you:

    ssh root@187.126.118.190 touch /root/HOLD-DEPLOY     # pause
    ssh root@187.126.118.190 rm /root/HOLD-DEPLOY        # resume

The timer keeps ticking and keeps logging that it is holding, so a forgotten
hold is visible rather than silent.

## The scripts

| file | what it does |
|---|---|
| `vps-setup.sh` | builds the box from bare Ubuntu. Idempotent. Never touches DNS or certificates. |
| `vps-deploy.sh` | fetch, re-chown, pip, migrate, sync catalogue, collectstatic, restart, then verify `/api/products/` answers 200 before reporting success. |
| `vps-autodeploy.sh` | deploys only when `origin/main` has moved; what the timer runs. |

**These are copies.** `vps-setup.sh` installs them into `/root`, and the timer runs
`/root/deploy.sh`, not the file in the repo. Editing `vps-deploy.sh` and pushing
does nothing until it is copied over (`cp /var/www/crystal/deploy/vps-deploy.sh
/root/deploy.sh`). The SEO step was missing from a deploy for exactly this reason.

## Two things that will bite you

**Ownership.** `MEDIA_ROOT` is the repo root on this server — that is deliberate,
so a dashboard upload lands where the static site can serve it. But git runs as
root and gunicorn as `www-data`, so a plain `git pull` leaves the tree
unwritable and **every save in the dashboard 500s**. `vps-deploy.sh` re-chowns
on every run; if you ever pull by hand, do the same.

**nginx location order.** `/media/` must be `location ^~ /media/`. A plain
prefix location loses to the image regex block, because nginx matches regex
locations first, and every uploaded image 404s.

## Logs

    journalctl -u crystal -n 50          # the Django app
    tail -f /var/log/crystal-autodeploy.log
    tail -f /var/log/nginx/access.log

## SEO

Titles, descriptions, canonical tags, tracking code, one page per product
(`/products/<slug>`), one per blog post (`/blog/<slug>`), redirects,
`sitemap.xml` and `robots.txt` are written into the site's files by
`manage.py apply_seo`. They cannot be fetched by the page after it loads — a
crawler or a WhatsApp preview never runs the script.

`vps-deploy.sh` runs it after the catalogue sync, because `git reset --hard` puts
every page back to what is committed. It is not fatal: if it fails, the
committed pages are still correct and the site works. Edits made in the
dashboard rebuild the affected files on their own, two seconds after the last
save.

Generated and gitignored: `products/`, `blog/*.html`, `sitemap.xml`,
`robots.txt`. `product-urls.js` is tracked but is overwritten by the server.

**Give the SEO team a login** (on the server):

    cd /var/www/crystal/crystal/backend
    set -a; . ./.env; set +a
    /opt/crystal-venv/bin/python manage.py create_seo_user priya --email priya@agency.com

It prints a generated password once. The account is staff but never superuser,
in the group "SEO Team": the SEO screens, page and blog text, nothing else.
Anyone in that group can paste a script that runs on every page of the site, so
give it only to people you would give the site's code to.

**Rebuild by hand:** `apply_seo` (everything) or `apply_seo --pages-only`.
