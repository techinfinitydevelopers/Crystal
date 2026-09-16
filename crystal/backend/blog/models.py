from django.db import models
from django.utils import timezone
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

    @property
    def url(self):
        """Where this post reads on the website. Article.html is one shared
        template that looks its post up by slug."""
        return 'https://crystal-cook-production.up.railway.app/Article.html?id=%s' % self.slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        # Publishing is the act that dates a post. Left to be filled in by
        # hand it stayed empty, and both the site and this list sort on it --
        # so a published post with no date sorted to the bottom and showed a
        # blank date under its title.
        #
        # Only ever filled in, never cleared: taking a post down for a week
        # and putting it back should not lose the day it first went out. The
        # date stays editable by hand for a post that needs a different one.
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
