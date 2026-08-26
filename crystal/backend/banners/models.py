"""The photograph across the top of a category page.

The website is static files in git; the dashboard is a separate service with
its own volume, so a banner uploaded here cannot write into the site's repo.
Instead the pages ship with a local banner as their default and ask this
service, on load, whether a newer one has been set. If it has, the page swaps
it in; if this service is down or has nothing for that page, the shipped file
stands. That means an edit here is live immediately with no rebuild, and the
site never depends on the dashboard being up in order to render.
"""
from django.db import models


class CategoryBanner(models.Model):
    page = models.CharField(
        max_length=120, unique=True,
        help_text='The page this banner belongs to, exactly as the file is '
                  'named, e.g. "Cookware-Non-Stick.html".')
    label = models.CharField(
        max_length=120, blank=True,
        help_text='What to call it in this list. Left blank, the page name is used.')
    image = models.ImageField(
        upload_to='category-banners/',
        help_text='A wide, short photograph - around 5:1, at least 1900px '
                  'across. Shoot or crop it with the product to the RIGHT and '
                  'empty space to the LEFT, because the heading sits on the left.')
    focus = models.PositiveSmallIntegerField(
        default=74,
        help_text='Which part of the photo to keep on a computer, as a '
                  'percentage across it. Only about half the width fits, so '
                  'this slides the visible window: lower moves the subject '
                  'right, higher moves it left.')
    mobile_focus = models.PositiveSmallIntegerField(
        default=82,
        help_text='The same, for phones. Phones crop tighter, so the subject '
                  'usually needs to sit further along.')
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to fall back to the banner the site already ships '
                  'for this page, without deleting this one.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page']
        verbose_name = 'Category banner'
        verbose_name_plural = 'Category banners'

    def __str__(self):
        return self.label or self.page

    @property
    def slug(self):
        """The key the website looks itself up by: the page name, lowercased."""
        name = self.page[:-5] if self.page.lower().endswith('.html') else self.page
        return name.strip().lower().replace(' ', '-')
