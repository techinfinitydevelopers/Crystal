from rest_framework import serializers
from .models import Brand, Category, Product, ProductImage, ProductSpecification, Marketplace, ProductMarketplaceLink, ProductVariant


class BrandSerializer(serializers.ModelSerializer):
    catalogue_url = serializers.SerializerMethodField()

    def get_catalogue_url(self, obj):
        request = self.context.get('request')
        if obj.catalogue:
            return request.build_absolute_uri(obj.catalogue.url) if request else obj.catalogue.url
        return None

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'tagline', 'logo', 'catalogue_url', 'description', 'is_active']


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    parent_slug = serializers.CharField(source='parent.slug', read_only=True, default=None)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'parent_name', 'parent_slug', 'order']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order']


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['id', 'key', 'value', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku_suffix', 'is_default', 'order']


MARKETPLACE_DEFAULT_LOGOS = {
    'amazon':   '/static/marketplace-logos/amazon.svg',
    'flipkart': '/static/marketplace-logos/flipkart.svg',
    'jiomart':  '/static/marketplace-logos/jiomart.svg',
    'meesho':   '/static/marketplace-logos/meesho.svg',
}


def _marketplace_logo_url(obj, request):
    """Return uploaded logo URL, falling back to bundled default by slug."""
    if obj.logo:
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url
    default = MARKETPLACE_DEFAULT_LOGOS.get(obj.slug)
    if default and request:
        return request.build_absolute_uri(default)
    return default


class MarketplaceSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        return _marketplace_logo_url(obj, self.context.get('request'))

    class Meta:
        model = Marketplace
        fields = ['id', 'name', 'slug', 'logo', 'logo_url', 'is_active']


class ProductMarketplaceLinkSerializer(serializers.ModelSerializer):
    marketplace_name = serializers.CharField(source='marketplace.name', read_only=True)
    marketplace_slug = serializers.CharField(source='marketplace.slug', read_only=True)
    marketplace_logo = serializers.SerializerMethodField()

    def get_marketplace_logo(self, obj):
        return _marketplace_logo_url(obj.marketplace, self.context.get('request'))

    class Meta:
        model = ProductMarketplaceLink
        fields = ['id', 'marketplace_name', 'marketplace_slug', 'marketplace_logo', 'url']


class ProductListSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'short_description', 'highlight', 'collection_name', 'tags',
            'image_url', 'is_active', 'is_featured', 'is_new',
            'show_price', 'price', 'thumbnail', 'created_at',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    marketplace_links = ProductMarketplaceLinkSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'category',
            'short_description', 'overview', 'highlight', 'collection_name', 'tags',
            'image_url', 'is_active', 'is_featured', 'is_new',
            'show_price', 'price', 'featured_image', 'thumbnail',
            'images', 'specifications', 'marketplace_links', 'variants', 'created_at',
        ]
