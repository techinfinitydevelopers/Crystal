#!/usr/bin/env bash
# Build the Crystal box on a bare Ubuntu 24.04 VPS.
#
# Run as root on the VPS. Idempotent: safe to re-run after a failed step, and it
# never touches DNS -- pointing the domain here is a separate, deliberate act
# once the site has been proved on the bare IP.
#
# What ends up where:
#   /var/www/crystal                 the website's static files (the repo root)
#   /var/www/crystal/crystal/backend the Django dashboard
#   /var/www/crystal/<media paths>   dashboard uploads land in the site tree,
#                                    which is the whole point of co-locating
#                                    them -- see settings.py MEDIA_ROOT
set -euo pipefail

APP_DIR=/var/www/crystal
BACKEND="$APP_DIR/crystal/backend"
VENV=/opt/crystal-venv
DB_NAME=crystal
DB_USER=crystal
PY=python3

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

say "System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  python3-venv python3-dev build-essential \
  postgresql postgresql-contrib libpq-dev \
  nginx certbot python3-certbot-nginx \
  git curl unzip ufw >/dev/null

say "Postgres role and database"
# A password is generated here rather than chosen, and only ever written to the
# app's .env with 600 perms.
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  DB_PASS=$(openssl rand -base64 30 | tr -d '/+=' | head -c 32)
  sudo -u postgres psql -qc "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';"
  echo "$DB_PASS" > /root/.crystal-db-pass
  chmod 600 /root/.crystal-db-pass
  echo "   role created"
else
  DB_PASS=$(cat /root/.crystal-db-pass)
  echo "   role already present"
fi
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
  || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

say "Python environment"
[ -d "$VENV" ] || $PY -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip wheel
"$VENV/bin/pip" install --quiet -r "$BACKEND/requirements.txt"

say "Application settings"
# SECRET_KEY is generated once and kept; regenerating it would log every
# dashboard user out and invalidate any signed value already in the wild.
ENV_FILE="$BACKEND/.env"
if [ ! -f "$ENV_FILE" ]; then
  SECRET=$("$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(64))')
  cat > "$ENV_FILE" <<EOF
DEBUG=False
SECRET_KEY=$SECRET
DATABASE_URL=postgres://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME
ALLOWED_HOSTS=$(hostname -I | awk '{print $1}'),localhost,127.0.0.1
PUBLIC_SITE_URL=http://$(hostname -I | awk '{print $1}')
CORS_ALLOWED_ORIGINS=http://$(hostname -I | awk '{print $1}')
CSRF_TRUSTED_ORIGINS=http://$(hostname -I | awk '{print $1}')
EOF
  chmod 600 "$ENV_FILE"
  echo "   .env written (ALLOWED_HOSTS is the bare IP for now; the domain gets added at DNS time)"
else
  echo "   .env already present, left alone"
fi

say "Django: migrate and collect static"
cd "$BACKEND"
set -a; . "$ENV_FILE"; set +a
"$VENV/bin/python" manage.py migrate --no-input
"$VENV/bin/python" manage.py collectstatic --no-input >/dev/null
echo "   done"

say "gunicorn service"
cat > /etc/systemd/system/crystal.service <<EOF
[Unit]
Description=Crystal dashboard (Django/gunicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$BACKEND
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/gunicorn config.wsgi --workers 2 --bind 127.0.0.1:8001 --timeout 60
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now crystal >/dev/null
sleep 2
systemctl is-active --quiet crystal && echo "   crystal.service is up" || {
  echo "   crystal.service FAILED:"; journalctl -u crystal -n 30 --no-pager; exit 1; }

say "Nginx"
cat > /etc/nginx/sites-available/crystal <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root $APP_DIR;
    index index.html;

    client_max_body_size 64M;

    # The dashboard. Everything else on this box is a static file.
    location ~ ^/(admin|api|dashboard)(/|\$) {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }

    location /static/ { alias $BACKEND/staticfiles/; access_log off; expires 30d; }

    # Uploads are written into the site tree itself, so /media/<path> and the
    # static site's own /<path> are the same file. Served straight off disk.
    location /media/ { alias $APP_DIR/; access_log off; expires 7d; }

    # The catalogue must never be cached hard -- a stale copy is exactly how
    # fixes stopped reaching the client before.
    location = /product-data/products.json {
        add_header Cache-Control "no-cache, must-revalidate";
    }

    location ~* \.(jpg|jpeg|png|webp|gif|svg|woff2?|ico)\$ {
        expires 30d; access_log off; try_files \$uri =404;
    }

    location / { try_files \$uri \$uri/ \$uri.html =404; }
}
EOF
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/crystal /etc/nginx/sites-enabled/crystal
nginx -t
systemctl reload nginx
echo "   nginx reloaded"

say "Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null
echo "   ssh + http/https open"

say "Done"
IP=$(hostname -I | awk '{print $1}')
echo "   site      http://$IP/"
echo "   dashboard http://$IP/admin/"
echo
echo "   DNS has NOT been touched. Point the domain only after testing on this IP,"
echo "   then add it to ALLOWED_HOSTS / CORS / CSRF in $ENV_FILE, restart crystal,"
echo "   and run: certbot --nginx -d <domain> -d www.<domain>"
