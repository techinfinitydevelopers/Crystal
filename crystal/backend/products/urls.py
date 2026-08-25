from django.urls import path
from .views import BrandListView, CategoryListView, ProductListView, ProductDetailView, SiteCatalogueView

urlpatterns = [
    # Same JSON shape as product-data/products.json (see SiteCatalogueView).
    # Must stay above the <slug> route so it isn't swallowed as a product slug.
    path('site.json/', SiteCatalogueView.as_view(), name='site-catalogue'),
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('', ProductListView.as_view(), name='product-list'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]
