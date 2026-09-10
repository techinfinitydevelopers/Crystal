"""A single editable piece of a site page -- a heading, a paragraph, or an image.

Same inversion as `banners.CategoryBanner`: the website is static files in git
and this dashboard is a separate service with its own volume, so it cannot
write into the site's repo. Every page ships its own copy already; on load it
asks this service whether a newer value has been set for each of its section
keys and swaps it in live if so. If this service is down or has nothing for a
key, the shipped content stands.
"""
from django.db import models


class PageSection(models.Model):
    TEXT = 'text'
    IMAGE = 'image'
    KIND_CHOICES = [(TEXT, 'Text'), (IMAGE, 'Image')]

    page = models.CharField(
        max_length=120, db_index=True,
        help_text='The page this belongs to, exactly as the file is named, '
                  'e.g. "About.html".')
    section_key = models.SlugField(
        max_length=120,
        help_text='Matches the data-cms id on that element in the page HTML, '
                  'e.g. "hero-heading".')
    label = models.CharField(
        max_length=160, blank=True,
        help_text='What to call this in the list. Left blank, the section '
                  'key is used.')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=TEXT)
    text_value = models.TextField(
        blank=True, help_text='Used when Kind is Text. Plain text -- shown '
                              'exactly as typed, no HTML.')
    image = models.ImageField(
        upload_to='page-sections/', blank=True, null=True,
        help_text='Used when Kind is Image.')
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to fall back to the content the page already '
                  'ships, without deleting this.')
    updated_at = models.DateTimeField(auto_now=True)

    # Deleting from the main list moves a row here instead of removing it --
    # it disappears from the working list and the live feed the same as a
    # real delete would, but only Trash can remove it for good.
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['page', 'section_key']
        unique_together = [('page', 'section_key')]
        verbose_name = 'Page section'
        verbose_name_plural = 'Page sections'

    def __str__(self):
        return f'{self.page} · {self.label or self.section_key}'

    @property
    def slug(self):
        """The key the website looks itself up by: the page name, lowercased."""
        name = self.page[:-5] if self.page.lower().endswith('.html') else self.page
        return name.strip().lower().replace(' ', '-')


class PageSectionTrash(PageSection):
    """The same table, viewed and administered as the trash can.

    A proxy model rather than a second table: `PageSectionAdmin` soft-deletes
    into this same row set by flipping `is_deleted`, so the two admin classes
    just need to look at opposite halves of one table, not keep two in sync.
    """

    class Meta:
        proxy = True
        verbose_name = 'Page section (trash)'
        verbose_name_plural = 'Page sections — Trash'
