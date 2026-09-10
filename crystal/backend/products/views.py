from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .media_urls import _public_url
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


class ImageOverridesView(APIView):
    """The photos that were changed here and are not in the site's own file yet.

    The site is static files in git; this dashboard is a separate service and
    cannot write into that repo, so product-data/products.json still names the
    old photo until someone commits a new one. Same inversion as the category
    banners: every page asks this endpoint, on load, whether a newer photo has
    been set, and swaps it in.

    Only products whose main image was actually chosen in the dashboard are
    listed (`hero_overridden`), so this stays a handful of rows rather than a
    second copy of the whole catalogue, and a product nobody has touched can
    never be affected by it.

    Keyed by product code (`sku`), which is what the JSON entries are keyed by.
    A product with sizes contributes one entry per size, exactly as it does in
    products.json — the sizes can have their own photos.

    URLs are absolute: an uploaded photo lives on this service's /media/, an
    imported one on the website itself, and the page has no way to tell.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        products = (
            Product.objects.filter(is_active=True, hero_overridden=True)
            .select_related('brand', 'category__parent')
            .prefetch_related(
                'images', 'variants', 'specifications',
                'marketplace_links__marketplace',
            )
            .order_by('id')
        )
        overrides = {}
        for product in products:
            for entry in site_product_entries(product):
                sku = entry.get('sku')
                hero = _public_url(entry.get('hero') or '')
                if not sku or not hero:
                    continue
                overrides[sku] = {
                    'hero': hero,
                    'gallery': [
                        url for url in (
                            _public_url(g) for g in entry.get('gallery') or []
                        ) if url
                    ],
                }
        return Response({'products': overrides})
