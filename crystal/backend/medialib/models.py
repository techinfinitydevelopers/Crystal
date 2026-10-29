"""One row per file the dashboard knows about — the WordPress-style library.

Two kinds of row live here side by side:

* files uploaded straight into the library (stored under library/YYYY/MM/);
* files that were uploaded somewhere else — a product photo, a banner, a
  brochure PDF — and were *indexed*: the row points at the very same stored
  name, nothing is copied. `source` says where it came from.

Because a row only ever points at a stored name, picking a library file for a
banner, a product photo or a page section makes that model point at the same
file too. One file on disk, any number of places using it — which is why
deleting a row has to check every other model before it removes the file
(see medialib.usage.delete_file_if_unused).
"""
import os

from django.core.files.images import get_image_dimensions
from django.core.files.storage import default_storage
from django.db import models

from products.media_urls import _public_url


IMAGE_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'avif', 'bmp', 'tif', 'tiff', 'svg', 'ico'}
VIDEO_EXT = {'mp4', 'webm', 'mov', 'm4v', 'ogv', 'avi', 'mkv'}
PDF_EXT = {'pdf'}


def kind_for_name(name):
    """image / video / pdf / other, from the file's extension alone.

    The extension rather than the bytes: indexing has to classify thousands of
    files that already exist without opening each one, and every place on the
    site decides how to show a file by its extension too.
    """
    ext = os.path.splitext(name or '')[1].lower().lstrip('.')
    if ext in IMAGE_EXT:
        return MediaItem.IMAGE
    if ext in VIDEO_EXT:
        return MediaItem.VIDEO
    if ext in PDF_EXT:
        return MediaItem.PDF
    return MediaItem.OTHER


def human_size(n):
    n = int(n or 0)
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n} {unit}' if unit == 'bytes' else f'{n:.1f} {unit}'
        n = n / 1024
    return f'{n} bytes'


class MediaItem(models.Model):
    IMAGE, VIDEO, PDF, OTHER = 'image', 'video', 'pdf', 'other'
    KIND_CHOICES = [
        (IMAGE, 'Image'),
        (VIDEO, 'Video'),
        (PDF, 'PDF'),
        (OTHER, 'Other file'),
    ]

    file = models.FileField(
        upload_to='library/%Y/%m/', max_length=500, db_index=True,
        help_text='The file itself. Anything uploaded here can then be picked '
                  'from any upload box in the dashboard with “Choose from Media library”.')
    title = models.CharField(
        max_length=200, blank=True,
        help_text='A name to find it by. Left blank, the file name is used.')
    alt_text = models.CharField(
        'Description (alt text)', max_length=300, blank=True,
        help_text='What the picture shows, in a few words — read out to blind '
                  'visitors and used by Google. Not needed for videos or PDFs.')
    kind = models.CharField(
        max_length=10, choices=KIND_CHOICES, default=OTHER, editable=False,
        help_text='Worked out from the file name.')
    size = models.PositiveBigIntegerField(
        default=0, editable=False, help_text='File size in bytes.')
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=200, blank=True,
        help_text='Where this file was first uploaded, for files that were '
                  'already in the dashboard before the library existed.')

    class Meta:
        ordering = ['-uploaded_at', '-id']
        verbose_name = 'Media file'
        verbose_name_plural = 'Media library'

    def __str__(self):
        return self.title or self.filename

    @property
    def filename(self):
        return os.path.basename(self.file.name or '')

    @property
    def url(self):
        """Through the same resolver the product screens use: imported product
        photos live on the website's tree, and a bare .url would point them at
        the dashboard's /media/ instead."""
        return _public_url(self.file.name or '') or ''

    @property
    def size_label(self):
        return human_size(self.size)

    def save(self, *args, **kwargs):
        name = self.file.name or ''
        self.kind = kind_for_name(name)
        if not self.title and name:
            stem = os.path.splitext(os.path.basename(name))[0]
            self.title = stem.replace('-', ' ').replace('_', ' ').strip()[:200]
        self._fill_file_facts()
        super().save(*args, **kwargs)

    def _fill_file_facts(self):
        """Size and, for pictures, pixel dimensions.

        A fresh upload is read from the upload itself (it is not in storage
        yet); an indexed file is read from storage. Never fatal — a picture
        Pillow cannot read is still a file worth listing.
        """
        f = self.file
        if not f or not f.name:
            return
        committed = getattr(f, '_committed', True)
        if not self.size:
            try:
                self.size = f.size if not committed else default_storage.size(f.name)
            except Exception:
                self.size = 0
        if self.kind == self.IMAGE and self.width is None and not f.name.lower().endswith('.svg'):
            try:
                if committed:
                    with default_storage.open(f.name, 'rb') as fh:
                        w, h = get_image_dimensions(fh)
                else:
                    w, h = get_image_dimensions(f.file)
                if w and h:
                    self.width, self.height = w, h
            except Exception:
                pass
