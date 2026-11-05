"""The Gifting page (Gifting.html): the gift sets, the ranges they are filed
under, and the wording on the page.

Same inversion as `banners` and `awards`: the site is static files in git and
this dashboard is a separate service, so the page ships with the full gift list
(`product-data/gifting.json`) and, on load, asks this service for the live one.
If this service is down, or nothing has been added here yet, the shipped list
stands. Everything on the page can therefore be changed from the dashboard with
no rebuild and no deploy; the hero photograph is already controlled from
Category banners (page "Gifting.html").
"""
import re

from django.db import models
from django.utils.text import slugify


class GiftingSettings(models.Model):
    """The wording on the page. One row, edited, never added to or deleted."""

    hero_pretext = models.CharField(
        'Small line above the heading', max_length=120, default='Diwali Gift Sets · 2026')
    hero_title = models.CharField(
        'Heading', max_length=120, default='Gift Sets *&* Combos',
        help_text='Put *stars* around a word to colour it red, e.g. Gift Sets *&* Combos.')
    hero_lead = models.CharField(
        'Line under the heading', max_length=200,
        default='Ready-to-gift combos for every kitchen.')
    hero_points = models.TextField(
        'Bullet points', blank=True,
        default='Nonstick, stainless steel and tri-ply cookware sets\n'
                'Teak wood serveware, organisers and trays\n'
                'Mixer grinders, induction cooktops, kettles and gas cooktops\n'
                'Add the sets you like to your enquiry list and send it to us in one go',
        help_text='One bullet per line. Leave empty for no bullets.')
    browse_title = models.CharField(
        'Heading above the gift sets', max_length=120, default='Browse all gift sets')
    browse_lead = models.TextField(
        'Sentence beside it', blank=True,
        default='Pick a range, tap Enquire on the sets you like, and send your enquiry '
                'list to our team in one go.')
    cta_title = models.CharField(
        'Bottom banner heading', max_length=120, default='Gifting in bulk?')
    cta_text = models.TextField(
        'Bottom banner text', blank=True,
        default='Festive, corporate or wedding gifting — tell our team what you need '
                'and we will help with the right sets.')
    show_mrp = models.BooleanField(
        'Show the MRP on each card', default=False,
        help_text='Off by default: the rest of the site does not show prices on product cards. '
                  'Tick it to print the MRP you enter on each gift set.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Page wording'
        verbose_name_plural = 'Page wording'

    def __str__(self):
        return 'Gifting page wording'

    def save(self, *args, **kwargs):
        self.pk = 1          # one row: a second set would silently win or lose
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def points(self):
        return [ln.strip() for ln in self.hero_points.splitlines() if ln.strip()]


class GiftRange(models.Model):
    """A filter button on the page: Nonstick Gift Set, Teak Wood, Appliances..."""

    label = models.CharField(max_length=80, help_text='The button text, e.g. "Teak Wood".')
    slug = models.SlugField(
        max_length=80, unique=True, blank=True,
        help_text='Used in the web address (Gifting?section=teakwood). Filled in for you.')
    order = models.PositiveIntegerField(default=0, help_text='Lowest first.')
    is_active = models.BooleanField(default=True, help_text='Untick to hide this range and its sets.')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Range'
        verbose_name_plural = 'Ranges'

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.label) or 'range'
            slug, n = base, 2
            while GiftRange.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = '%s-%d' % (base, n), n + 1
            self.slug = slug
        super().save(*args, **kwargs)


class GiftSet(models.Model):
    """One card on the page: a gift set or combo."""

    name = models.CharField(max_length=200, help_text='The title on the card.')
    gift_range = models.ForeignKey(
        GiftRange, on_delete=models.PROTECT, related_name='sets', verbose_name='Range',
        help_text='Which filter button this set belongs under.')
    sku = models.CharField(
        'Code(s)', max_length=200, blank=True,
        help_text='Shown as "Code: ..." on the card. For a combo list every code, e.g. '
                  'CPW-025 / CPW-011 / CPW-012. Left empty, the codes of the models below are used.')
    features = models.TextField(
        blank=True,
        help_text='The line under the code. One point per line; the lines are joined with " · ". '
                  'Left empty the card says "Outer pack of N" when an outer pack is set.')
    outer_pack = models.PositiveIntegerField(
        'Outer pack', null=True, blank=True,
        help_text='How many sets come in one outer carton.')
    mrp = models.PositiveIntegerField(
        'MRP (Rs)', null=True, blank=True,
        help_text='Whole rupees. Only shown on the page if "Show the MRP" is ticked in Page wording.')
    image = models.ImageField(
        upload_to='gift-sets/', blank=True,
        help_text='The card picture, square works best (the page fits it whole, nothing is cropped). '
                  'For a combo, put the whole set and its gift box together in one picture.')
    image_path = models.CharField(
        max_length=300, blank=True,
        help_text='Set automatically for the sets the site already ships. Upload a picture above to replace it.')
    ref = models.CharField(
        max_length=120, unique=True, blank=True, editable=False,
        help_text='Stable id used by the enquiry list.')
    order = models.PositiveIntegerField(default=0, help_text='Lowest first, within its range.')
    is_active = models.BooleanField(default=True, help_text='Untick to take this set off the page without deleting it.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Gift set'
        verbose_name_plural = 'Gift sets'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.ref:
            base = 'gift-' + (slugify(re.sub(r'[/,]+', ' ', self.sku or self.name)) or 'set')
            ref, n = base, 2
            while GiftSet.objects.filter(ref=ref).exclude(pk=self.pk).exists():
                ref, n = '%s-%d' % (base, n), n + 1
            self.ref = ref
        super().save(*args, **kwargs)

    @property
    def codes(self):
        """What the card prints after "Code:"."""
        if self.sku.strip():
            return self.sku.strip()
        return ' / '.join(m.code for m in self.models_in_set.all() if m.code)

    @property
    def feature_list(self):
        return [ln.strip() for ln in self.features.splitlines() if ln.strip()]

    def picture(self, request=None):
        """An upload lives on this service and must be addressed on this host; a
        shipped picture is a path inside the website and stays relative so each
        site (live, staging, localhost) resolves it against itself."""
        if self.image:
            url = self.image.url
            return request.build_absolute_uri(url) if request else url
        return self.image_path.strip() or None


class GiftSetModel(models.Model):
    """One product inside a combo (code, name, pack, MRP). Optional detail."""

    gift_set = models.ForeignKey(GiftSet, on_delete=models.CASCADE, related_name='models_in_set')
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=200, blank=True)
    outer_pack = models.PositiveIntegerField(null=True, blank=True)
    mrp = models.PositiveIntegerField('MRP (Rs)', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Model in this combo'
        verbose_name_plural = 'Models in this combo'

    def __str__(self):
        return self.code
