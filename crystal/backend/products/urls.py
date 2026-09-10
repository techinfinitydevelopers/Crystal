from django.urls import path
from .views import (
    BrandListView, CategoryListView, ImageOverridesView, ProductListView,
    ProductDetailView, SiteCatalogueView,
)

urlpatterns = [
    # Same JSON shape as product-data/products.json (see SiteCatalogueView).
    # Must stay above the <slug> route so it isn't swallowed as a product slug.
    path('site.json/', SiteCatalogueView.as_view(), name='site-catalogue'),
    # Photos changed here that the site's own products.json does not know about.
    path('image-overrides.json/', ImageOverridesView.as_view(), name='image-overrides'),
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('', ProductListView.as_view(), name='product-list'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]
