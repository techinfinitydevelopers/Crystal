#!/bin/bash
# PythonAnywhere setup script
# Run this in PythonAnywhere Bash console after cloning the repo
# Usage: bash pa_setup.sh yourusername

USERNAME=${1:-yourusername}
PROJECT_DIR="/home/$USERNAME/Crystal/crystal/backend"

echo "=== Setting up Crystal backend on PythonAnywhere ==="

# 1. Clone repo (skip if already done)
if [ ! -d "/home/$USERNAME/Crystal" ]; then
  cd /home/$USERNAME
  git clone https://github.com/techinfinitydevelopers/Crystal.git
fi

# 2. Create virtualenv
mkvirtualenv crystal --python=python3.13
workon crystal

# 3. Install dependencies
pip install -r $PROJECT_DIR/requirements.txt

# 4. Create .env file
cat > $PROJECT_DIR/.env << 'EOF'
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com
DATABASE_URL=sqlite:///db.sqlite3
CORS_ALLOWED_ORIGINS=https://yourusername.pythonanywhere.com
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
ADMIN_NOTIFICATION_EMAIL=developers@techinfinity.io
EOF

echo ">>> Edit $PROJECT_DIR/.env with your real values"

# 5. Migrate and collect static
cd $PROJECT_DIR
python manage.py migrate --no-input
python manage.py collectstatic --no-input

# 6. Seed initial data (optional)
# python manage.py seed_data

echo ""
echo "=== Done! Now: ==="
echo "1. Go to Web tab → Add new web app → Manual config → Python 3.13"
echo "2. Set source code: $PROJECT_DIR"
echo "3. Set virtualenv: /home/$USERNAME/.virtualenvs/crystal"
echo "4. Edit WSGI file — paste contents of pythonanywhere_wsgi.py"
echo "5. Static files mapping:"
echo "   URL: /static/   → Directory: $PROJECT_DIR/staticfiles"
echo "   URL: /media/    → Directory: $PROJECT_DIR/media"
echo "6. Reload the web app"
echo "7. Create superuser: python manage.py createsuperuser"
