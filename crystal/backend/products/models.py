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
    # The site shows a product video and a list of feature bullets, both of which
    # lived only in product-data/products.json - the dashboard had no field for
    # either, so editing a product here could never produce them.
    video = models.FileField(
        upload_to='products/videos/', blank=True, null=True,
        help_text='Product video. Shown as the second thumbnail in the gallery.')
    video_url = models.URLField(
        max_length=500, blank=True,
        help_text='Use instead of uploading, when the video is already hosted '
                  '(e.g. product-photos/<SKU>/video.mp4).')
    features = models.JSONField(
        default=list, blank=True,
        help_text='Feature cards: [[icon, title, detail], ...]. Falls back to the '
                  'category defaults when empty.')
    amazon_link = models.URLField(
        max_length=500, blank=True, help_text='Buy Now sends customers here.')
    variant_group = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text='Products sharing this value are shown as size options of one '
                  'another on the website. Leave blank if this product has no '
                  'size siblings.')
    match_tier = models.CharField(
        max_length=64, blank=True,
        help_text='Internal provenance note carried over from the original site '
                  'catalogue (how this row was matched during import). Nothing '
                  'on the website reads it.')
    specs = models.JSONField(
        default=dict, blank=True,
        help_text='Logistics/packaging details shown in the specification table '
                  '(weight, pack dimensions, HSN code, manufacturer).')
    gst_pct = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True,
        help_text='As a fraction, e.g. 0.18 for 18%.')

    is_dashboard_managed = models.BooleanField(
        default=True,
        help_text="Internal — leave this on. Only products created here (rather than bulk-imported from the "
                   "existing site catalogue) are pushed to the live site by 'Export to website'.",
    )
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
    variant = models.ForeignKey(
        'ProductVariant', null=True, blank=True, on_delete=models.CASCADE, related_name='images',
        help_text="Leave blank for a general product photo. Set this to attach the photo to one specific size/variant only — e.g. so the '16 cm' variant shows its own pan instead of the 14 cm one.",
    )
    image = models.ImageField(upload_to='products/gallery/')
    is_hero = models.BooleanField(default=False, help_text='Use as the main/large photo for this product (or this variant, if set).')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        scope = f" ({self.variant.name})" if self.variant_id else ""
        return f"{self.product.name}{scope} image {self.order}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    variant = models.ForeignKey(
        'ProductVariant', null=True, blank=True, on_delete=models.CASCADE, related_name='specifications',
        help_text="Leave blank for a spec that applies to the whole product. Set this to attach the spec to one specific size/variant only — e.g. so the '16 cm' variant lists its own diameter instead of the 14 cm one.",
    )
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        scope = f" ({self.variant.name})" if self.variant_id else ""
        return f"{self.product.name}{scope}: {self.key}"


class ProductVariant(models.Model):
    """One size / option of a product.

    Every field below except `name` is optional. The rule is uniform: if you
    leave a field blank, the website falls back to whatever the product above
    it says. Fill a field in only when this particular size differs.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(
        max_length=100,
        help_text='The size or option label shown on the size selector, e.g. "22 cm", "1.5 L", \'15"\'. Must be unique within this product.')
    sku_suffix = models.CharField(
        max_length=20, blank=True,
        help_text='Old-style: added to the end of the product SKU to build this size\'s code. Only used when the full SKU below is blank. Leave blank and use "SKU" instead.')
    sku = models.CharField(
        max_length=50, unique=True, null=True, blank=True, db_index=True,
        help_text='The complete item code for this size, exactly as it appears on the packaging (e.g. LI008). Leave blank to use the product\'s own SKU.')
    display_name = models.CharField(
        max_length=200, blank=True,
        help_text='The full product title for this size, exactly as it should appear on the website. Leave blank to use the same name as the product above.')
    highlight = models.CharField(
        max_length=300, blank=True,
        help_text='The one-line selling point shown under the title. Leave blank to use the same one as the product above.')
    description = models.TextField(
        blank=True,
        help_text='The full description for this size. Leave blank to use the same description as the product above.')
    tags = models.JSONField(
        null=True, blank=True, default=None,
        help_text='Search/filter tags for this size, as a list. Leave blank to use the same tags as the product above.')
    features = models.JSONField(
        null=True, blank=True, default=None,
        help_text='Feature cards for this size: [[icon, title, detail], ...]. Leave blank to use the same features as the product above.')
    amazon_link = models.URLField(
        max_length=500, blank=True,
        help_text='The Amazon listing for this exact size. Most sizes have their own. Leave blank to use the same link as the product above.')
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='MRP for this size, in rupees. Leave blank to use the same price as the product above.')
    video = models.FileField(
        upload_to='products/videos/', blank=True, null=True,
        help_text='A video for this size only. Leave blank to use the same video as the product above.')
    video_url = models.URLField(
        max_length=500, blank=True,
        help_text='Use instead of uploading, when the video for this size is already hosted somewhere. Leave blank to use the same one as the product above.')
    match_tier = models.CharField(
        max_length=64, blank=True,
        help_text='Internal provenance note carried over from the original site catalogue. Nothing on the website reads it.')
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to hide this size from the website without deleting it.')
    is_default = models.BooleanField(
        default=False,
        help_text='Tick for the size that should be selected first when a customer opens this product.')
    order = models.PositiveIntegerField(
        default=0,
        help_text='Position in the size selector. Lower numbers appear first.')

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['product', 'name'], name='uniq_variant_name_per_product'),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def full_sku(self):
        """This size's item code: its own SKU if set, else product SKU + suffix."""
        return self.sku or f"{self.product.sku or ''}{self.sku_suffix}"


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
