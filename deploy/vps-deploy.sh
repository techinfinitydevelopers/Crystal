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

say "Catalogue"
# From the file in this checkout, not over HTTP: the repo is right here, and a
# local read cannot be served a stale or truncated copy by a cache.
"$VENV/bin/python" manage.py sync_catalogue --file "$APP/product-data/products.json" | tail -3

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
