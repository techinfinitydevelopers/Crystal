#!/usr/bin/env bash
# Stop nginx serving the repo's internals from the live site.
#
# The site root is the git checkout itself (/var/www/crystal), and both "/" and
# the /media/ alias point at it, so without this anyone could download
# crystal/backend/.env (production secrets), .git/, the Django source, deploy
# scripts and the internal notes (*.md). Only the public pages, assets,
# product-data/products.json and tools/cms-manifest.json (read by the dashboard
# over HTTP) stay reachable.
#
# Safe to run more than once. Backs up the config, tests it, and puts the backup
# back if nginx rejects the result.
#
#   ssh root@187.126.118.190 'bash /var/www/crystal/deploy/harden-nginx.sh'
set -euo pipefail

CONF=/etc/nginx/sites-available/crystal
SNIP=/etc/nginx/snippets/crystal-deny.conf
SNIP_MEDIA=/etc/nginx/snippets/crystal-deny-media.conf

[ -f "$CONF" ] || { echo "no $CONF"; exit 1; }
mkdir -p /etc/nginx/snippets

cat > "$SNIP" <<'EOF'
# Internals of the site checkout -- never public. (deploy/harden-nginx.sh)
location ~ /\.(?!well-known/) { return 404; }
location ^~ /crystal/      { return 404; }
location ^~ /deploy/       { return 404; }
location ^~ /home-v3-src/  { return 404; }
location ^~ /docs/         { return 404; }
location ^~ /scripts/      { return 404; }
location ^~ /archive/      { return 404; }
location ~ ^/tools/(?!cms-manifest\.json$) { return 404; }
location ~* \.(md|py|pyc|sh|sqlite3|env|log|bak|toml|ini|cfg|lock|zip|docx)$ { return 404; }
EOF

# /media/ is an alias of the same tree, so it needs the same rules inside it
# (a ^~ prefix location stops nginx from ever reaching the regexes above).
cat > "$SNIP_MEDIA" <<'EOF'
# Same rules for the /media/ alias of the site tree. (deploy/harden-nginx.sh)
location ~ /\. { return 404; }
location ~ ^/media/(crystal|deploy|home-v3-src|docs|scripts|archive)/ { return 404; }
location ~ ^/media/tools/ { return 404; }
location ~* \.(md|py|pyc|sh|sqlite3|env|log|bak|toml|ini|cfg|lock|zip|docx)$ { return 404; }
EOF

BACKUP="$CONF.bak-$(date +%Y%m%d-%H%M%S)"
cp "$CONF" "$BACKUP"

if ! grep -q "snippets/crystal-deny.conf" "$CONF"; then
  # after every "root /var/www/crystal;" -- one per server block (80 and 443)
  perl -0pi -e 's{^(\s*root\s+/var/www/crystal/?;)}{$1\n    include snippets/crystal-deny.conf;}mg' "$CONF"
fi
if ! grep -q "snippets/crystal-deny-media.conf" "$CONF"; then
  # straight after the opening brace of each /media/ location, so it lands
  # inside the block even when the whole location is written on one line
  perl -0pi -e 's{(location\s+(?:\^~\s+)?/media/\s*\{)}{$1 include snippets/crystal-deny-media.conf;}g' "$CONF"
fi

if ! grep -q "snippets/crystal-deny.conf" "$CONF"; then
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
echo "Check (all should be 404 except the last two, which must be 200):"
for u in crystal/backend/.env .git/config media/crystal/backend/.env docs/BUILD_LOG.md docs/memory.md \
         docs/data/CRYSTAL-Product-List.docx "archive/LOUD%20Agency.html" scripts/merge_excel_products.py \
         crystal/backend/config/settings.py deploy/vps-setup.sh tools/cms_tag.py \
         tools/cms-manifest.json product-data/products.json; do
  printf "  %-36s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' "https://crystalcook.com/$u")"
done

echo
echo "Earlier requests for .env / .git in the access logs (who may already have them):"
zgrep -hE 'GET /(media/)?(crystal/backend/\.env|\.git/)' /var/log/nginx/access.log* 2>/dev/null \
  | awk '{print $1, $4, $7, $9}' | tail -n 40 || true
