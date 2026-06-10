from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products.views import BrandListView, CategoryListView, MarketplaceListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', include('products.urls')),
    path('api/brands/', BrandListView.as_view(), name='api-brands'),
    path('api/categories/', CategoryListView.as_view(), name='api-categories'),
    path('api/marketplaces/', MarketplaceListView.as_view(), name='api-marketplaces'),
    path('api/blog/', include('blog.urls')),
    path('api/downloads/', include('downloads.urls')),
    path('api/enquiry/', include('enquiry.urls')),
    path('api/contact/', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
