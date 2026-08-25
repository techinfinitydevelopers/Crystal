from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / '.env')

def _secret_key():
    """The signing key, in order of preference.

    An explicit SECRET_KEY environment variable always wins. Failing that, the
    app generates one itself and keeps it on the persistent volume, so it
    survives redeploys and nobody has to hand-carry a secret into the dashboard.
    Only if neither is possible does it fall back to the development placeholder,
    which the production block below refuses to boot on.
    """
    from_env = env('SECRET_KEY', default='')
    if from_env:
        return from_env

    key_file = BASE_DIR / 'media' / '.secret_key'
    try:
        if key_file.exists():
            existing = key_file.read_text().strip()
            if existing:
                return existing
        import secrets
        generated = secrets.token_urlsafe(64)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(generated)
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass  # Windows and some mounts do not support this
        return generated
    except OSError:
        return 'django-insecure-change-me-in-production'


SECRET_KEY = _secret_key()
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Railway — auto-add domain
_railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)

# PythonAnywhere — auto-add *.pythonanywhere.com if running there
_pa_host = os.environ.get('PYTHONANYWHERE_DOMAIN') or os.environ.get('PYTHONANYWHERE_SITE')
if not _pa_host:
    # detect by hostname pattern as fallback
    import socket
    _hn = socket.gethostname()
    if 'pythonanywhere' in _hn:
        _pa_host = _hn
if _pa_host and _pa_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_pa_host)

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3456',
    'http://127.0.0.1:3456',
]
if _railway_domain:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_railway_domain}')
if _pa_host:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_pa_host}')

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third-party
    'rest_framework',
    'corsheaders',
    # local apps
    'core',
    'products',
    'enquiry',
    'blog',
    'downloads',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serves the admin's own CSS/JS in production. Without it DEBUG=False means
    # Django serves no static files at all and the dashboard renders unstyled -
    # config/urls.py only wires static() up while DEBUG is on.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Compressed, not manifest-hashed: a manifest build fails the whole deploy if
# any stylesheet references a file that is not there, and Jazzmin ships a few.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
# The dashboard's product images are the website's own files: products.json stores
# paths like "product-photos/CNS-756/hero.jpg", relative to the site root. Rooting
# media there means /media/<that path> serves the real photo instead of 404ing, and
# anything uploaded from the dashboard lands where the static site can pick it up.
# Falls back to backend/media when the site tree isn't alongside (e.g. on Railway,
# where the backend is deployed as its own service).
_site_root = BASE_DIR.parent.parent
MEDIA_ROOT = Path(env('MEDIA_ROOT', default=str(
    _site_root if (_site_root / 'product-data').is_dir() else BASE_DIR / 'media')))

# ---------------------------------------------------------------------------
# Production hardening. All of it is conditional on DEBUG being off, so local
# development is untouched.
# ---------------------------------------------------------------------------
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    if SECRET_KEY.startswith('django-insecure-'):
        raise ImproperlyConfigured(
            "SECRET_KEY is still the development placeholder. Set a real "
            "SECRET_KEY environment variable on the service before deploying - "
            "session and password-reset tokens are signed with it."
        )

    # Railway terminates TLS at its edge and forwards over plain HTTP. Without
    # this header Django cannot tell the request was HTTPS, and SECURE_SSL_REDIRECT
    # would bounce every request into a redirect loop.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    # The platform's healthcheck reaches the container over plain HTTP on the
    # internal network, with no X-Forwarded-Proto to tell Django otherwise, so
    # SECURE_SSL_REDIRECT answers it with a 301 and the check is recorded as a
    # failure. The healthcheck endpoint is exempt; everything else still redirects.
    SECURE_REDIRECT_EXEMPT = [r'^api/products/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

# CORS — allow frontend HTML served locally or on Vercel
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3456',
    'http://127.0.0.1:3456',
])
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@crystal.com')
ADMIN_NOTIFICATION_EMAIL = env('ADMIN_NOTIFICATION_EMAIL', default='developers@techinfinity.io')

# ─── Jazzmin Admin UI ────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    # branding
    "site_title": "Crystal Admin",
    "site_header": "Crystal Cook",
    "site_brand": "Crystal Cook",
    "site_logo": "admin/logo.png",
    "site_logo_classes": "img-circle",
    "site_icon": "admin/logo.png",
    "welcome_sign": "Welcome to Crystal Cook Admin",
    "copyright": "Crystal Cook N Serve Products Pvt. Ltd.",

    # search
    "search_model": ["products.Product", "enquiry.Enquiry"],

    # top menu
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "http://localhost:3456", "new_window": True},
        {"model": "enquiry.Enquiry"},
    ],

    # user menu
    "usermenu_links": [
        {"name": "View Site", "url": "http://localhost:3456", "new_window": True, "icon": "fas fa-globe"},
    ],

    # sidebar
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": ["auth.group"],
    "order_with_respect_to": [
        "products", "enquiry", "blog", "downloads", "core", "auth",
    ],

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "products.product": "fas fa-box-open",
        "products.brand": "fas fa-tag",
        "products.category": "fas fa-th-large",
        "products.marketplace": "fas fa-store",
        "products.productmarketplacelink": "fas fa-link",
        "products.productimage": "fas fa-images",
        "products.productspecification": "fas fa-list-ul",
        "enquiry.enquiry": "fas fa-envelope-open-text",
        "enquiry.enquiryitem": "fas fa-shopping-basket",
        "blog.blog": "fas fa-newspaper",
        "blog.blogcategory": "fas fa-folder",
        "downloads.download": "fas fa-file-download",
        "core.contactsubmission": "fas fa-phone-alt",
    },

    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # UI tweaks
    "related_modal_active": True,
    "custom_css": "admin/crystal_theme.css",
    "custom_js": None,
    "use_google_fonts_cdn": False,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-danger",
    "accent": "accent-danger",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-danger",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-danger",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
