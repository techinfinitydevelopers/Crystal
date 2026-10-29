"""Festival themes: Diwali, Holi, Christmas... switched on from the dashboard.

Same inversion as `banners`, `content` and `awards`: the site is static files
and this is a separate service, so nothing here writes into the site. Every
page loads festival-theme.js, which asks /api/theme.json which theme (if any)
is live and dresses the page itself. Dashboard down = the normal site.

At most one theme is on at a time. That rule lives in `save()` rather than in
the admin, so the change form, the list's toggle column and the shell all
obey it: switching one on switches every other one off.
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone


# The look each built-in slug gets on the site (festival-theme.css/.js). Kept
# here only so the dashboard can show a colour dot next to each row; the site
# carries its own copy and is the authority on how a theme looks.
DEFAULT_ACCENTS = {
    'diwali': '#E9A23B',
    'holi': '#E3367A',
    'navratri': '#E8590C',
    'ganesh-chaturthi': '#F28C1B',
    'raksha-bandhan': '#D6336C',
    'janmashtami': '#1C7ED6',
    'independence-day': '#FF9933',
    'republic-day': '#FF9933',
    'sankranti': '#1098AD',
    'onam': '#E0A100',
    'eid': '#0E8A66',
    'christmas': '#C92A2A',
    'new-year': '#D4AF37',
}
GENERIC_ACCENT = '#D4AF37'

hex_colour = RegexValidator(
    r'^#[0-9A-Fa-f]{6}$', 'Use a six-digit hex colour like #E9A23B, or leave it empty.')


class FestivalTheme(models.Model):
    SCOPE_SITE = 'site'
    SCOPE_HOME = 'home'
    SCOPE_CHOICES = [
        (SCOPE_SITE, 'Whole website'),
        (SCOPE_HOME, 'Home page only'),
    ]

    name = models.CharField(max_length=80, help_text='e.g. "Diwali". Only shown here in the dashboard.')
    slug = models.SlugField(
        max_length=40, unique=True,
        help_text='The key the website uses to pick the look (colours, decorations, '
                  'falling particles). The built-in festivals already have one; a new '
                  'festival with a key the site does not know gets a general festive '
                  'gold look. Lowercase, hyphens only.')
    is_active = models.BooleanField(
        default=False, verbose_name='On',
        help_text='Only one theme can be on at a time. Switching this on switches '
                  'every other theme off.')
    greeting = models.CharField(
        max_length=120,
        help_text='The line in the festive ribbon at the top of every page, e.g. '
                  '"Happy Diwali from Crystal!". Keep it short — on a phone about '
                  '40 characters fit.')
    sub_text = models.CharField(
        max_length=200, blank=True,
        help_text='Optional second line. Shown on the Home page greeting card and '
                  'beside the greeting on wide screens.')
    link_text = models.CharField(
        max_length=40, blank=True,
        help_text='Optional button in the ribbon, e.g. "Festive picks". Needs a link below.')
    link_url = models.CharField(
        max_length=300, blank=True,
        help_text='Where that button goes: a page of the site like "Cookware.html" '
                  'or a full https:// address.')
    effects = models.BooleanField(
        default=True, verbose_name='Falling effects',
        help_text='Light, slow decorations drifting over the page (sparks for Diwali, '
                  'snow for Christmas...). Never shown to visitors who have asked '
                  'their device for reduced motion.')
    scope = models.CharField(
        max_length=8, choices=SCOPE_CHOICES, default=SCOPE_SITE, verbose_name='Show on',
        help_text='Whole website, or only the Home page.')
    starts_on = models.DateField(
        null=True, blank=True,
        help_text='Optional. If set, the theme stays hidden before this day even when '
                  'switched on.')
    ends_on = models.DateField(
        null=True, blank=True,
        help_text='Optional. If set, the theme disappears by itself after this day — '
                  'nobody has to remember to switch it off.')
    accent = models.CharField(
        max_length=7, blank=True, validators=[hex_colour], verbose_name='Accent colour',
        help_text='Optional, e.g. #E9A23B. Leave empty for the festival\'s own colours. '
                  'Used on decorations and the ribbon — the Crystal red stays the '
                  'brand colour.')
    banner = models.ImageField(
        upload_to='themes/', blank=True,
        help_text='Optional festive picture for the Home page greeting card. A wide '
                  'image around 1200 × 600 works best.')
    order = models.PositiveIntegerField(default=0, help_text='Lowest first in this list.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Festival theme'
        verbose_name_plural = 'Festival themes'

    def __str__(self):
        return self.name

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError({'ends_on': 'The last day cannot be before the first day.'})
        if self.link_text and not self.link_url:
            raise ValidationError({'link_url': 'The button needs somewhere to go.'})

    def save(self, *args, **kwargs):
        # One on at a time. In a transaction so a reader never sees two rows on,
        # and so a failed save does not leave every theme switched off.
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_active:
                (FestivalTheme.objects.exclude(pk=self.pk)
                 .filter(is_active=True).update(is_active=False))

    # -- what the site sees -------------------------------------------------

    def in_window(self, today=None):
        today = today or timezone.localdate()
        if self.starts_on and today < self.starts_on:
            return False
        if self.ends_on and today > self.ends_on:
            return False
        return True

    def is_live(self, today=None):
        return self.is_active and self.in_window(today)

    @classmethod
    def live(cls, today=None):
        """The theme visitors should see right now, or None."""
        t = cls.objects.filter(is_active=True).first()
        return t if t and t.in_window(today) else None

    @property
    def display_accent(self):
        return self.accent or DEFAULT_ACCENTS.get(self.slug, GENERIC_ACCENT)

    def as_feed(self, request=None):
        banner = None
        if self.banner:
            try:
                banner = self.banner.url
                if request is not None:
                    # Absolute: the website resolves a root-relative /media/... against
                    # its own origin, which is not always this service.
                    banner = request.build_absolute_uri(banner)
            except ValueError:
                banner = None
        return {
            'slug': self.slug,
            'name': self.name,
            'greeting': self.greeting,
            'sub_text': self.sub_text,
            'link_text': self.link_text if self.link_url else '',
            'link_url': self.link_url if self.link_text else '',
            'effects': self.effects,
            'scope': self.scope,
            'accent': self.accent,
            'banner': banner,
            'starts_on': self.starts_on.isoformat() if self.starts_on else None,
            'ends_on': self.ends_on.isoformat() if self.ends_on else None,
            'updated': self.updated_at.isoformat() if self.updated_at else None,
        }
