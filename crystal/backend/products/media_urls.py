"""Turning a stored media reference into a URL a browser can actually fetch.

Lived in admin.py until the product form's main-image picker needed it too;
importing it from there would have been a cycle (admin imports forms).
"""

from django.conf import settings


# Top-level folders the static website serves; anything else is dashboard media.
SITE_CONTENT_DIRS = frozenset({
    'product-photos', 'about-assets', 'brand-assets', 'home-v3-assets',
    'uploads', 'brand-logos', 'product-data',
    # The catalogue keeps 451 SparkMate photos under their own root rather than
    # product-photos/. Left out of this set they resolved to /media/sparkmate/…
    # on the dashboard's own volume, where no such file exists, so every one of
    # them would have been a broken thumbnail here.
    'sparkmate',
})


def _public_url(value):
    """Resolve a stored image/video reference to something a browser can fetch.

    Every imported product stores a *site-root-relative* path such as
    "product-photos/CL-414/hero.jpg" - that is the form the static website
    wants, and MEDIA_ROOT is rooted at the site tree so /media/<path> serves it.

    Emitted raw into an <img src> the browser resolves it against the current
    admin URL and requests
    /admin/products/product/product-photos/CL-414/hero.jpg. Django's legacy
    catch-all route reads that as an object id, the lookup fails, and the
    resulting "Product with ID ... doesn't exist" message is queued into the
    session and shown as a banner on whatever page loads next - which is why it
    looks unrelated to whatever the admin was doing. 491 products carry such a
    path, so one changelist page can fire a hundred of these.
    """
    if not value:
        return None
    if value.startswith(('http://', 'https://', '/', 'data:')):
        return value
    # Site content lives on the website service, not here. Locally MEDIA_ROOT
    # happens to be the site tree so /media/ would also work, but on Railway
    # MEDIA_ROOT is the dashboard's own volume and these files are not in it.
    # Resolving against the website is the answer that is right in both places.
    if value.split('/', 1)[0] in SITE_CONTENT_DIRS:
        return '%s/%s' % (settings.PUBLIC_SITE_URL.rstrip('/'), value.lstrip('/'))
    return '%s%s' % (settings.MEDIA_URL, value.lstrip('/'))
