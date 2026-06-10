from django.db import models
from django.utils.text import slugify


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Blog Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Blog(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, max_length=300)
    excerpt = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    author = models.CharField(max_length=100, default='Team Crystal')
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogs')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    meta_title = models.CharField(max_length=300, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
