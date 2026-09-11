from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .media_urls import _public_url
from . import overrides as ov
from .models import Brand, Category, Marketplace, Product, RetiredSku
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
    """What the dashboard has changed that the site's own catalogue file does not know.

    The site is static files in git; this dashboard is a separate service and
    cannot write into that repo, so `product-data/products.json` goes on naming
    the old value until someone commits a new one. Same inversion as the
    category banners: every page asks this endpoint on load and folds the answer
    into the catalogue it just fetched.

    Only what was actually edited here is published. `Product.overridden_fields`
    records the catalogue keys a person touched, so an untouched product is
    absent from this feed entirely and can never be affected by it. Products
    removed in the dashboard come back as `hidden`, which is a list of product
    codes the pages drop.

    Keyed by product code (`sku`), which is how the JSON entries are keyed. A
    product with sizes contributes one entry per size, exactly as in
    products.json.

    The name is historical — it started out publishing only the main image, and
    the URL is kept so the copies of product-image-sync.js already cached in
    people's browsers go on working.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        def absolute(value):
            """_public_url leaves an uploaded photo as /media/<path>, which is
            only root-relative. The page asking us is served from the website's
            host, so it would resolve that against *its* origin and 404 — the
            uploaded file lives on this service. build_absolute_uri pins it to
            this host and leaves the already-absolute website URLs alone."""
            url = _public_url(value)
            return request.build_absolute_uri(url) if url else None

        products = (
            Product.objects.exclude(overridden_fields=[])
            .select_related('brand', 'category__parent')
            .prefetch_related(
                'images', 'variants', 'specifications',
                'marketplace_links__marketplace',
            )
            .order_by('id')
        )

        overrides = {}
        hidden = set(RetiredSku.objects.values_list('sku', flat=True))

        for product in products:
            owned = set(product.overridden_fields or ())
            # Someone switched this product off here. It stays out of the feed's
            # body — there is nothing to render — and goes in the hidden list.
            if ov.IS_ACTIVE in owned and not product.is_active:
                if product.sku:
                    hidden.add(product.sku)
                continue
            if not product.is_active:
                continue

            publish = owned & ov.PUBLISHABLE
            if not publish:
                continue

            for entry in site_product_entries(product):
                sku = entry.get('sku')
                if not sku:
                    continue
                patch = {}
                for key in publish:
                    if key not in entry:
                        continue
                    value = entry[key]
                    if key == 'hero':
                        value = absolute(value)
                        if not value:
                            continue
                    elif key == 'gallery':
                        value = [u for u in (absolute(g) for g in value or []) if u]
                    elif key == 'marketplaces':
                        # A logo can be an upload on this service or a static
                        # file bundled with it; either way the page asking is on
                        # another host and needs it spelled out in full.
                        value = [dict(row, logo=absolute(row.get('logo')))
                                 for row in value or []]
                    patch[key] = value
                # 95 codes exist both as a standalone product and as a size of
                # another one (all the standalone copies are inactive, so only
                # one of each reaches the feed today). If that ever stops being
                # true, the first claim wins rather than the loop order deciding.
                if patch and sku not in overrides:
                    overrides[sku] = patch

        return Response({
            'products': overrides,
            'hidden': sorted(hidden),
            'brands': self._simple(Brand.objects.all(), ov.BRAND_PUBLISHABLE,
                                   ov.BRAND_FIELD_KEYS),
            'categories': self._simple(Category.objects.all(), ov.CATEGORY_PUBLISHABLE,
                                       ov.CATEGORY_FIELD_KEYS),
        })

    @staticmethod
    def _simple(queryset, publishable, field_keys):
        """Brands and categories, keyed by slug, carrying only edited fields.

        The pages ship their own wording for both and it is not always what the
        database holds — the site says "Wooden Range" where this says "Wood
        Range" — so publishing everything would silently rewrite copy nobody
        asked to change. Only what someone edited here is sent.
        """
        # Which model field feeds which published key, inverted once.
        source_for = {}
        for field, keys in field_keys.items():
            for key in keys:
                source_for[key] = field

        out = {}
        for obj in queryset.exclude(overridden_fields=[]):
            patch = {}
            for key in set(obj.overridden_fields or ()) & publishable:
                value = getattr(obj, source_for.get(key, ''), None)
                if value:
                    patch[key] = value
            if patch:
                out[obj.slug] = patch
        return out
