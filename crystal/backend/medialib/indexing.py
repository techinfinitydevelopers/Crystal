"""Keeping the library in step with files uploaded anywhere else.

`index_media` walks every file field once (run on each deploy); the post_save
handler covers everything saved after that, so a photo uploaded on a product
turns up in the library straight away without waiting for the next deploy.

Rows point at the SAME stored name — nothing is copied. A name that is not
actually in storage is skipped: the library promises that anything in it can
be picked, and a picked name that is not there is refused (picking.py).
"""
import logging

from django.core.files.storage import default_storage
from django.db.models import FileField
from django.db.models.signals import post_save

from .usage import file_fields, source_label

log = logging.getLogger(__name__)


def ensure_item(name, source=''):
    """Make sure a library row exists for this stored name.

    Returns 'created', 'exists' or 'missing'.
    """
    from .models import MediaItem
    if not name or name.startswith(('http://', 'https://', 'data:')):
        return 'missing'
    if MediaItem.objects.filter(file=name).exists():
        return 'exists'
    try:
        if not default_storage.exists(name):
            return 'missing'
    except Exception:
        return 'missing'
    MediaItem(file=name, source=source[:200]).save()
    return 'created'


def _on_save(sender, instance, raw=False, **kwargs):
    if raw:
        return  # loaddata: files may not be on disk yet, and fixtures should load as-is
    label = None
    for field in sender._meta.local_concrete_fields:
        if not isinstance(field, FileField):
            continue
        value = getattr(instance, field.attname, None)
        name = getattr(value, 'name', value) or ''
        if not name:
            continue
        label = label or source_label(sender)
        try:
            ensure_item(name, label)
        except Exception:  # indexing must never break the save that triggered it
            log.exception('medialib: could not index %s', name)


def connect_signals():
    from .models import MediaItem
    seen = set()
    for model, _field in file_fields():
        if model is MediaItem or model in seen:
            continue
        seen.add(model)
        post_save.connect(_on_save, sender=model, weak=False,
                          dispatch_uid=f'medialib-index-{model._meta.label_lower}')
