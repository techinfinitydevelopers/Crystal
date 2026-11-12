#!/usr/bin/env bash
# Show the site's own "Page not found" page (404.html) for addresses that do not exist,
# instead of nginx's plain white "404 Not Found".
#
# The page is an ordinary file in the repo, so it arrives with a normal deploy; this only
# tells nginx to use it. The status code stays 404 (search engines must still see that the
# address does not exist), only the body is the branded page. Dashboard (/admin, /api) errors
# are not touched: nginx only swaps the body of errors it generates itself.
#
# Safe to run more than once. Backs up the config, tests it, and puts the backup back if
# nginx rejects the result. Run it AFTER a deploy that contains 404.html.
#
#   ssh root@187.126.118.190 'bash /var/www/crystal/deploy/add-404-page.sh'
set -euo pipefail

APP=/var/www/crystal
CONF=/etc/nginx/sites-available/crystal
SNIP=/etc/nginx/snippets/crystal-404.conf

[ -f "$CONF" ] || { echo "no $CONF"; exit 1; }
[ -f "$APP/404.html" ] || { echo "$APP/404.html is not on the server yet - deploy first, then run this"; exit 1; }
mkdir -p /etc/nginx/snippets

cat > "$SNIP" <<'EOF'
# The site's own "page not found" page. (deploy/add-404-page.sh)
error_page 404 /404.html;
location = /404.html { internal; }
EOF

BACKUP="$CONF.bak-$(date +%Y%m%d-%H%M%S)"
cp "$CONF" "$BACKUP"

if ! grep -q "snippets/crystal-404.conf" "$CONF"; then
  # after every "root /var/www/crystal;" -- one per server block (80 and 443)
  perl -0pi -e 's{^(\s*root\s+/var/www/crystal/?;)}{$1\n    include snippets/crystal-404.conf;}mg' "$CONF"
fi

if ! grep -q "snippets/crystal-404.conf" "$CONF"; then
  echo "could not find a 'root /var/www/crystal;' line in $CONF -- nothing changed"
  cp "$BACKUP" "$CONF"
  exit 1
fi

if nginx -t 2>&1; then
  systemctl reload nginx
  echo "nginx reloaded (backup: $BACKUP)"
else
  echo "nginx rejected the change -- restoring $BACKUP"
  cp "$BACKUP" "$CONF"
  nginx -t && systemctl reload nginx
  exit 1
fi

echo
echo "Check (status must stay 404, and the body must be the branded page):"
for u in this-page-does-not-exist foo/bar/baz crystal/backend/.env; do
  code=$(curl -sk -o /tmp/crystal-404-check.html -w '%{http_code}' "https://127.0.0.1/$u" -H 'Host: 187.126.118.190' || true)
  if grep -q "Page not found | CRYSTAL" /tmp/crystal-404-check.html 2>/dev/null; then page="branded page"; else page="PLAIN nginx page"; fi
  printf '   /%-28s %s  %s\n' "$u" "$code" "$page"
done
rm -f /tmp/crystal-404-check.html
