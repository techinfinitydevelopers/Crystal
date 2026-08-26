from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from products.views import BrandListView, CategoryListView, MarketplaceListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', include('products.urls')),
    path('api/brands/', BrandListView.as_view(), name='api-brands'),
    path('api/categories/', CategoryListView.as_view(), name='api-categories'),
    path('api/marketplaces/', MarketplaceListView.as_view(), name='api-marketplaces'),
    path('api/banners.json', include('banners.urls')),
    path('api/blog/', include('blog.urls')),
    path('api/downloads/', include('downloads.urls')),
    path('api/enquiry/', include('enquiry.urls')),
    path('api/contact/', include('core.urls')),
]

# django.conf.urls.static.static() returns an EMPTY list when DEBUG is off, so
# in production nothing under /media/ was routed at all and every uploaded file
# 404ed. Verified against the live dashboard: /static/ answered 200 (whitenoise
# handles it) while /media/ answered 404. Whitenoise deliberately covers static
# files only -- it fingerprints at build time, which uploaded files cannot be.
#
# So media gets its own route, unconditionally. django.views.static.serve is
# not built for heavy traffic, but this is a small internal catalogue and the
# alternative is that nothing an admin uploads is ever visible -- including
# every category banner.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATICFILES_DIRS[0])
