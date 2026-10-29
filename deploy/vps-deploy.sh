#!/usr/bin/env bash
# Pull the latest site and dashboard onto this server.
#
#   ssh root@187.126.118.190 /root/deploy.sh
#
# Safe to run any time. It does not touch the database's contents beyond
# applying migrations and re-reading the catalogue file, and it never touches
# DNS or certificates.
set -euo pipefail

APP=/var/www/crystal
BACKEND="$APP/crystal/backend"
VENV=/opt/crystal-venv

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

cd "$APP"
BEFORE=$(git rev-parse --short HEAD)

say "Fetching"
git fetch --depth 1 origin main -q
git reset --hard origin/main -q
AFTER=$(git rev-parse --short HEAD)
if [ "$BEFORE" = "$AFTER" ]; then
  echo "   already at $AFTER - nothing new"
else
  echo "   $BEFORE -> $AFTER"
fi

say "Ownership"
# git runs as root and creates root-owned files; gunicorn runs as www-data and
# has to be able to write uploads into this same tree (MEDIA_ROOT is the repo
# root). Without this, saving anything in the dashboard 500s.
chown -R www-data:www-data "$APP"
find "$APP" -type d -exec chmod 2775 {} +
echo "   www-data owns the tree again"

say "Python dependencies"
"$VENV/bin/pip" install --quiet -r "$BACKEND/requirements.txt"
echo "   up to date"

cd "$BACKEND"
set -a; . ./.env; set +a

say "Database"
"$VENV/bin/python" manage.py migrate --no-input | tail -3

say "Media library"
# Lists every file already uploaded anywhere in the dashboard in the Media
# library. Points at the same files (no copies) and skips anything already
# listed, so it is cheap to run every time. Not fatal: the library is a
# convenience and must never stop a deploy.
"$VENV/bin/python" manage.py index_media | tail -1 || echo "   media library indexing failed - the site is unaffected"

say "Catalogue"
# From the file in this checkout, not over HTTP: the repo is right here, and a
# local read cannot be served a stale or truncated copy by a cache.
# SEO_AUTOBAKE=0: the sync saves every product, and each save would otherwise
# queue a page rebuild. The next step does that once, properly.
SEO_AUTOBAKE=0 "$VENV/bin/python" manage.py sync_catalogue --file "$APP/product-data/products.json" | tail -3

say "SEO"
# `git reset --hard` above put every page back to what is committed, so the
# titles, descriptions, tracking code, product pages, blog pages, redirects,
# sitemap.xml and robots.txt that live in the dashboard are written out again.
# Not fatal: a failure here leaves the committed pages, which are still correct.
SEO_AUTOBAKE=0 "$VENV/bin/python" manage.py apply_seo | tail -4 || echo "   SEO step failed - committed pages are in place"
# apply_seo runs as root and has just created files; the dashboard (www-data)
# has to be able to rewrite them when someone edits a title.
chown -R www-data:www-data "$APP"
find "$APP" -type d -exec chmod 2775 {} +

say "Static files"
"$VENV/bin/python" manage.py collectstatic --no-input | tail -1
chown -R www-data:www-data "$BACKEND/staticfiles"

say "Restart"
systemctl restart crystal
sleep 3
if systemctl is-active --quiet crystal; then
  echo "   crystal.service is up"
else
  echo "   crystal.service FAILED:"; journalctl -u crystal -n 25 --no-pager; exit 1
fi

say "Check"
code=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/api/products/ -H 'Host: 187.126.118.190')
echo "   /api/products/ -> $code"
[ "$code" = "200" ] || { echo "   site is not answering properly"; exit 1; }

say "Deployed $AFTER"
