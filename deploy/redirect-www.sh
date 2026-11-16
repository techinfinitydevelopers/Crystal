#!/usr/bin/env bash
# One address per page: send www.crystalcook.com to crystalcook.com with a 301.
#
# Before this, https://www.crystalcook.com/<page> and https://crystalcook.com/<page> both answered
# 200 with the same page, so search engines could index every page twice. The pages already carry a
# canonical tag (a hint); this makes it a rule.
#
# Adds one small file (/etc/nginx/conf.d/crystal-www-redirect.conf) with two server blocks that match
# the exact name www.crystalcook.com (they win over the catch-all block) and return 301 to the same
# path on crystalcook.com. The main site config is not touched. Needs the Let's Encrypt certificate
# to cover www too; if it does not, it is expanded with certbot first.
#
# Safe to run more than once. Backs the file up, tests nginx, removes the file if nginx rejects it.
#
#   ssh root@187.126.118.190 'bash /var/www/crystal/deploy/redirect-www.sh'
set -euo pipefail

HOST=crystalcook.com
WWW=www.crystalcook.com
CONF=/etc/nginx/conf.d/crystal-www-redirect.conf
LIVE=/etc/letsencrypt/live/$HOST

# Another block already answers for the www name (certbot or a hand edit): do not fight it.
if grep -rqsE "server_name[^;]*[[:space:]]$WWW[[:space:];]" /etc/nginx/sites-enabled /etc/nginx/conf.d --exclude="$(basename "$CONF")" 2>/dev/null; then
  echo "Another nginx block already names $WWW:"
  grep -rnE "server_name[^;]*[[:space:]]$WWW[[:space:];]" /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null | grep -v "$CONF" || true
  echo "Nothing changed. Put 'return 301 https://$HOST\$request_uri;' in that block instead."
  exit 1
fi

[ -f "$LIVE/fullchain.pem" ] || { echo "no certificate at $LIVE - run certbot for $HOST first"; exit 1; }

if ! openssl x509 -in "$LIVE/fullchain.pem" -noout -text | grep -q "DNS:$WWW"; then
  echo "Certificate does not cover $WWW - expanding it"
  certbot certonly --nginx --expand --cert-name "$HOST" -d "$HOST" -d "$WWW" --non-interactive
fi

[ -f "$CONF" ] && cp "$CONF" "$CONF.bak-$(date +%Y%m%d-%H%M%S)"
cat > "$CONF" <<EOT
# www -> apex, one address per page. (deploy/redirect-www.sh)
server {
    listen 80;
    listen [::]:80;
    server_name $WWW;
    return 301 https://$HOST\$request_uri;
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name $WWW;
    ssl_certificate     $LIVE/fullchain.pem;
    ssl_certificate_key $LIVE/privkey.pem;
    return 301 https://$HOST\$request_uri;
}
EOT

if nginx -t 2>&1; then
  systemctl reload nginx
  echo "nginx reloaded"
else
  echo "nginx rejected the change - removing $CONF"
  rm -f "$CONF"
  nginx -t && systemctl reload nginx
  exit 1
fi

echo
echo "Check (each must be 301 to https://$HOST/...):"
for u in "http://$WWW/" "https://$WWW/products/crystal-abs-lighter-plastic-body"; do
  printf '   %-70s ' "$u"
  curl -sI -m 15 "$u" | tr -d '\r' | awk 'NR==1{s=$2} tolower($1)=="location:"{l=$2} END{print s, l}'
done
