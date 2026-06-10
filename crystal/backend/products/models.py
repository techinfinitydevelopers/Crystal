from django.db import models
from django.utils.text import slugify


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True)
    catalogue = models.FileField(upload_to='brands/catalogues/', blank=True, null=True, help_text='Upload brand catalogue PDF')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    short_description = models.CharField(max_length=300, blank=True)
    overview = models.TextField(blank=True)
    highlight = models.CharField(max_length=300, blank=True)
    collection_name = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    show_price = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    featured_image = models.ImageField(upload_to='products/featured/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} image {self.order}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name}: {self.key}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)  # e.g. "22 cm", "24 cm", "1.5 L"
    sku_suffix = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class Marketplace(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='marketplaces/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductMarketplaceLink(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='marketplace_links')
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE, related_name='product_links')
    url = models.URLField()

    class Meta:
        unique_together = ('product', 'marketplace')

    def __str__(self):
        return f"{self.product.name} on {self.marketplace.name}"
