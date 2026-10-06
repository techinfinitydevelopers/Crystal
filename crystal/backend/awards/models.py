"""The Awards & Recognition strip on About.html.

Same inversion as `banners.CategoryBanner` and `content.PageSection`: the site
is static files in git and this dashboard is a separate service, so a
certificate added here cannot be written into the site's repo. About.html ships
the four it knows about and asks this service on load whether there is a fuller
set; if this service is down or has nothing, the shipped four stand.

The reason this needed a table of its own rather than more `PageSection` rows:
the page had exactly four slots baked into a CSS grid, one `data-cms` key each.
That lets someone swap a certificate but never add a fifth, which is the whole
request.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AwardSettings(models.Model):
    """How the strip moves. One row, edited, never added to or deleted.

    Kept apart from `Award` because it describes the strip rather than any
    certificate in it -- putting a speed on every row would invite four
    different answers to one question.
    """

    seconds_per_card = models.DecimalField(
        max_digits=4, decimal_places=1, default=0.6,
        verbose_name='Seconds per certificate',
        validators=[MinValueValidator(0.2), MaxValueValidator(20)],
        help_text='How long one certificate takes to go past. Lower is faster. '
                  '0.6 is the default, 0.3 is quick, 3 gives people time to '
                  'read a caption before it leaves. Anything from 0.2 to 20.')
    autoscroll = models.BooleanField(
        default=True, verbose_name='Scroll by itself',
        help_text='Untick to leave the strip still. Visitors can still drag or '
                  'swipe through the certificates.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scrolling speed'
        verbose_name_plural = 'Scrolling speed'

    def __str__(self):
        return 'Awards strip — %s s per certificate' % self.seconds_per_card

    def save(self, *args, **kwargs):
        # Pinned to one row: a second set of settings would silently win or lose
        # depending on which the feed read first.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Award(models.Model):
    title = models.CharField(
        max_length=160, blank=True,
        help_text='Shown under the picture, e.g. "HomeShop18 STAR Award". '
                  'Leave blank for a plain certificate with no caption.')
    subtitle = models.CharField(
        max_length=160, blank=True,
        help_text='The smaller second line, e.g. "Home & Kitchen".')
    image = models.ImageField(
        upload_to='awards/', blank=True,
        help_text='The certificate or trophy photograph. Landscape scans work '
                  'best — they are shown about 168px tall and fitted whole, so '
                  'nothing is cropped.')
    image_path = models.CharField(
        max_length=300, blank=True,
        help_text='Set automatically for the certificates the site already '
                  'ships. Leave it alone and upload a picture above instead.')
    pdf = models.FileField(
        upload_to='awards/pdf/', blank=True, null=True,
        help_text='Optional. Attach the full certificate and the card becomes '
                  'clickable — visitors open the PDF in a new tab.')
    alt = models.CharField(
        max_length=200, blank=True,
        help_text='What the picture shows, for screen readers and for when the '
                  'image fails to load. Falls back to the title.')
    order = models.PositiveIntegerField(
        default=0,
        help_text='Lowest first. Ties fall back to the order they were added.')
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to take this off the site without deleting it.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Award / certificate'
        verbose_name_plural = 'Awards & certificates'

    def __str__(self):
        return self.title or self.alt or f'Certificate {self.pk}'

    @property
    def has_picture(self):
        return bool(self.image or self.image_path)

    def picture_url(self, request=None):
        """Where the picture actually lives.

        An upload is on this service's volume and has to be addressed on this
        host, which is why `request` matters: a root-relative /media/... would
        be resolved by the *website* against its own origin and 404. A seeded
        row instead carries a path inside the website's repo and is addressed
        there. Same split `content.PageSection.shipped_image_url` makes.
        """
        if self.image:
            url = self.image.url
            return request.build_absolute_uri(url) if request else url
        if not self.image_path:
            return None
        src = self.image_path.strip()
        if src.startswith(('http://', 'https://', '//')):
            return src
        from django.conf import settings
        base = getattr(settings, 'PUBLIC_SITE_URL', '').rstrip('/')
        return '%s/%s' % (base, src.lstrip('/'))

    def pdf_url(self, request=None):
        if not self.pdf:
            return None
        url = self.pdf.url
        return request.build_absolute_uri(url) if request else url
