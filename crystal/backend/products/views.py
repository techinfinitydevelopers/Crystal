from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Brand, Category, Product, Marketplace
from .serializers import (
    BrandSerializer, CategorySerializer, ProductListSerializer,
    ProductDetailSerializer, MarketplaceSerializer, site_product_entries,
)


class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'short_description']
    ordering_fields = ['name', 'created_at', 'price']

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related('brand', 'category')
        brand = self.request.query_params.get('brand')
        category = self.request.query_params.get('category')
        if brand:
            qs = qs.filter(brand__slug=brand)
        if category:
            qs = qs.filter(category__slug=category)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class MarketplaceListView(generics.ListAPIView):
    queryset = Marketplace.objects.filter(is_active=True)
    serializer_class = MarketplaceSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductDetailView(APIView):
    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.select_related('brand', 'category').prefetch_related(
                'images', 'specifications', 'marketplace_links__marketplace', 'variants'
            ),
            slug=slug, is_active=True
        )
        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data)


class SiteCatalogueView(APIView):
    """The catalogue in exactly the shape of product-data/products.json.

    The static site reads that file today; this endpoint lets it read the
    database instead without any frontend change. Key set and value types are
    kept identical - see SiteProductSerializer helpers in serializers.py.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        products = (
            Product.objects.filter(is_active=True)
            .select_related('brand', 'category__parent')
            .prefetch_related(
                'images', 'variants', 'specifications',
                'marketplace_links__marketplace',
            )
            .order_by('id')
        )
        entries = []
        for product in products:
            entries.extend(site_product_entries(product))
        return Response({'products': entries})
