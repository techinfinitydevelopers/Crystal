from django.db import models
from django.utils.text import slugify


class Download(models.Model):
    CATEGORY_CHOICES = [
        ('catalogue', 'Catalogue'),
        ('brochure', 'Brochure'),
        ('technical_sheet', 'Technical Sheet'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    brand = models.ForeignKey(
        'products.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='downloads',
        help_text='Leave blank for a general/all-brand download',
    )
    file = models.FileField(upload_to='downloads/')
    thumbnail = models.ImageField(upload_to='downloads/thumbnails/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='catalogue')
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
