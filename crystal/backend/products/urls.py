from django.urls import path
from .views import BrandListView, CategoryListView, ProductListView, ProductDetailView

urlpatterns = [
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('', ProductListView.as_view(), name='product-list'),
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]
