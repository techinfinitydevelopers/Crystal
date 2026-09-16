"""A single editable piece of a site page -- a heading, a paragraph, or an image.

Same inversion as `banners.CategoryBanner`: the website is static files in git
and this dashboard is a separate service with its own volume, so it cannot
write into the site's repo. Every page ships its own copy already; on load it
asks this service whether a newer value has been set for each of its section
keys and swaps it in live if so. If this service is down or has nothing for a
key, the shipped content stands.
"""
from django.db import models


class Page(models.Model):
    """One page of the website, so the dashboard can be browsed the way the
    site is: a list of pages, then that page's own sections.

    A flat list of 984 sections with a page filter was technically complete and
    practically unusable — nobody thinks "edit section legacy-p-1", they think
    "edit the About page". The rows themselves have not moved; this is the
    doorway to them.
    """

    filename = models.CharField(
        max_length=120, unique=True,
        help_text='The file on the website, e.g. "About.html". This is what '
                  'ties the page to its sections — do not change it.')
    title = models.CharField(
        max_length=160,
        help_text='What this page is called in the dashboard.')
    group = models.CharField(
        max_length=80, blank=True, db_index=True,
        help_text='Heading this page is listed under, e.g. "Cookware".')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'group', 'title']
        verbose_name = 'Page'
        verbose_name_plural = 'Pages'

    def __str__(self):
        return self.title or self.filename

    @property
    def slug(self):
        """The key the website looks itself up by: the filename, lowercased
        and without its extension."""
        base = self.filename.rsplit('.', 1)[0]
        return base.strip().lower().replace(' ', '-')

    @property
    def url(self):
        return 'https://crystal-cook-production.up.railway.app/%s' % self.filename


class PageSection(models.Model):
    TEXT = 'text'
    IMAGE = 'image'
    KIND_CHOICES = [(TEXT, 'Text'), (IMAGE, 'Image')]

    page = models.CharField(
        max_length=120, db_index=True,
        help_text='The page this belongs to, exactly as the file is named, '
                  'e.g. "About.html".')
    page_ref = models.ForeignKey(
        Page, null=True, blank=True, on_delete=models.PROTECT,
        related_name='sections', verbose_name='Page',
        help_text='Set automatically from the filename above.')
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
        help_text='Used when Kind is Image. Shown on desktops and tablets, and '
                  'on phones too unless a phone picture is set below.')
    image_mobile = models.ImageField(
        upload_to='page-sections/mobile/', blank=True, null=True,
        verbose_name='Phone picture',
        help_text='Optional. A crop that suits a narrow screen — phones get '
                  'this one instead. Leave empty and phones show the picture '
                  'above.')
    section = models.CharField(
        max_length=120, blank=True, db_index=True,
        help_text='Which band of the page this sits in, e.g. "hero". Filled in '
                  'automatically; it is only used to group this list.')
    shipped_value = models.TextField(
        blank=True,
        help_text='What the page shows today, for reference. Leave the value '
                  'above empty and the page keeps showing this.')
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

    @property
    def section_title(self):
        """Human-readable group heading for the page-editor screen — 'hero'
        becomes 'Hero', 'about3' becomes 'About 3' (the trailing digit is a
        repeat count from the site's build, e.g. the third "about" band on
        the page — not part of the word, so it gets a space before it. Good
        enough as a heading; the label on each individual row is what
        carries the real meaning."""
        import re
        raw = re.sub(r'(\d+)$', r' \1', self.section or 'Other')
        return raw.replace('-', ' ').replace('_', ' ').strip().title()

    def save(self, *args, **kwargs):
        # Keep page_ref in step with the page filename so a row created any
        # way other than through Page's own inline (a fixture, seed_page_sections,
        # a future importer) still shows up under its page in the dashboard.
        if self.page and (self.page_ref_id is None or self.page_ref.filename != self.page):
            self.page_ref, _ = Page.objects.get_or_create(
                filename=self.page,
                defaults={'title': self.page, 'order': 999},
            )
        super().save(*args, **kwargs)


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
