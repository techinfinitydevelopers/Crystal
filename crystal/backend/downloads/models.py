from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


# The 2024 edition was 52 MB and the 2026-27 one is 25 MB, so the ceiling has to
# leave real headroom. It exists to catch a wrong file, not to ration space.
MAX_UPLOAD_BYTES = 80 * 1024 * 1024


class Download(models.Model):
    CATEGORY_CHOICES = [
        ('catalogue', 'Catalogue'),
        ('brochure', 'Brochure'),
        ('technical_sheet', 'Technical Sheet'),
        ('other', 'Other'),
    ]

    title = models.CharField(
        max_length=200,
        help_text='Shown as the link tooltip on the website, e.g. "Crystal Catalogue 2026-27".',
    )
    slug = models.SlugField(unique=True, blank=True)
    brand = models.ForeignKey(
        'products.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='downloads',
        help_text='Leave blank for a general/all-brand download',
    )
    file = models.FileField(
        upload_to='downloads/',
        help_text='PDF file. The Catalogue page serves this directly, so upload the final artwork.',
    )
    thumbnail = models.ImageField(upload_to='downloads/thumbnails/', blank=True, null=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='catalogue',
        help_text='"Catalogue" is the one wired to the Download PDF button on Catalogue.html.',
    )
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to retire this file without deleting it. The website skips inactive files.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        """Guard the one file the public button serves.

        The website links straight at whatever is uploaded here, so a .docx or a
        renamed .zip would reach visitors as a broken catalogue. Checking at save
        time turns that into a form error instead.
        """
        super().clean()
        if not self.file:
            return

        size = getattr(self.file, 'size', None)
        if size and size > MAX_UPLOAD_BYTES:
            raise ValidationError({'file': (
                f'That file is {size / 1048576:.1f} MB, over the '
                f'{MAX_UPLOAD_BYTES // 1048576} MB limit. Compress the PDF and try again.'
            )})

        if self.category != 'catalogue':
            return

        name = (getattr(self.file, 'name', '') or '').lower()
        if not name.endswith('.pdf'):
            raise ValidationError({'file': (
                'The catalogue has to be a PDF — the website hands this file straight '
                'to the browser. Pick a .pdf, or change the category.'
            )})

        # Only a freshly uploaded file is readable here; an untouched file on an
        # edit is already on disk and there is nothing to re-check.
        head = None
        handle = getattr(self.file, 'file', None)
        if handle is not None:
            try:
                where = handle.tell()
                handle.seek(0)
                head = handle.read(5)
                handle.seek(where)
            except (AttributeError, ValueError, OSError):
                head = None
        if head is not None and not head.startswith(b'%PDF'):
            raise ValidationError({'file': (
                'That file is named .pdf but is not one — it was probably renamed '
                'rather than exported. Export it as a PDF and upload again.'
            )})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'download'
            taken = Download.objects.all()
            if self.pk:
                taken = taken.exclude(pk=self.pk)
            slug, suffix = base, 2
            while taken.filter(slug=slug).exists():
                slug, suffix = f'{base}-{suffix}', suffix + 1
            self.slug = slug
        super().save(*args, **kwargs)

    @classmethod
    def live_catalogue(cls):
        """The row the website actually serves: newest active catalogue with a file."""
        return (cls.objects
                .filter(is_active=True, category='catalogue')
                .exclude(file='')
                .order_by('-created_at')
                .first())
