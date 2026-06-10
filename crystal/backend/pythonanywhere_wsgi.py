# PythonAnywhere WSGI configuration
# Copy this file's CONTENTS into your PythonAnywhere WSGI config file at:
# Web tab → WSGI configuration file → click the link to edit it
#
# Replace 'yourusername' with your actual PythonAnywhere username

import sys
import os

# --- EDIT THESE TWO LINES ---
USERNAME = 'yourusername'          # your PythonAnywhere username
PROJECT_PATH = f'/home/{USERNAME}/Crystal/crystal/backend'
VENV_PATH    = f'/home/{USERNAME}/.virtualenvs/crystal/lib/python3.13/site-packages'
# ----------------------------

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

if VENV_PATH not in sys.path:
    sys.path.insert(0, VENV_PATH)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
