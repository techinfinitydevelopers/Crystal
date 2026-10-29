"""Which rows, in which tables, point at a given stored file.

The library never owns a file outright: picking a library photo for a banner
makes the banner point at the same stored name (no copy), and indexing makes
a library row point at a file a product photo already uses. So "can this file
be removed from disk?" and "where is this used?" are the same question, asked
of every FileField / ImageField in every installed app.

The fields are found with apps.get_models() at call time rather than listed by
hand, so a file field added to any model later is covered without anyone
having to remember this module exists.
"""
from collections import defaultdict

from django.apps import apps
from django.core.files.storage import default_storage
from django.db import models
from django.urls import NoReverseMatch, reverse

from products.media_urls import SITE_CONTENT_DIRS


def file_fields(include_library=False):
    """[(model, field)] for every concrete file field outside the library.

    Proxy models are skipped — they share their parent's table, so counting
    them would report every use twice (content.PageSectionTrash is one).
    Only *local* fields are taken, so a multi-table child does not re-report
    its parent's columns.
    """
    from .models import MediaItem
    out = []
    for model in apps.get_models():
        opts = model._meta
        if opts.proxy or not opts.managed:
            continue
        if model is MediaItem and not include_library:
            continue
        for field in opts.local_concrete_fields:
            if isinstance(field, models.FileField):
                out.append((model, field))
    return out


def source_label(model):
    """'Products › Product image' — how the library says where a file came from."""
    app = apps.get_app_config(model._meta.app_label)
    return f'{app.verbose_name} › {str(model._meta.verbose_name).capitalize()}'


def _admin_link(model, pk):
    try:
        return reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_change',
                       args=[pk])
    except NoReverseMatch:
        return ''


def usage_map(names):
    """{stored name: [use, ...]} for the given names, one query per file field.

    Each use is a dict with the model's label, the field, the object's text
    and an admin link (empty when that model has no admin screen).
    """
    names = [n for n in set(names) if n]
    found = defaultdict(list)
    if not names:
        return found
    for model, field in file_fields():
        rows = model._default_manager.filter(**{f'{field.attname}__in': names})
        for obj in rows:
            stored = getattr(obj, field.attname)
            stored = getattr(stored, 'name', stored)
            found[stored].append({
                'model': source_label(model),
                'field': str(field.verbose_name),
                'object': str(obj)[:120],
                'link': _admin_link(model, obj.pk),
            })
    return found


def is_used(name):
    return bool(usage_map([name]).get(name))


def is_site_file(name):
    """Files that belong to the website's own tree (product-photos/ and the
    rest). On the VPS MEDIA_ROOT *is* that tree, so these are also pages'
    shipped images and products.json's photos — never ours to delete, even
    when no dashboard row points at them any more."""
    return (name or '').split('/', 1)[0] in SITE_CONTENT_DIRS


def delete_file_if_unused(name, exclude_pk=None):
    """Remove the stored file only when nothing else still points at it.

    Returns True when the file was removed. Kept when another model uses it,
    when another library row points at it, or when it is one of the website's
    own files.
    """
    from .models import MediaItem
    if not name or is_site_file(name):
        return False
    others = MediaItem.objects.filter(file=name)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    if others.exists() or is_used(name):
        return False
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
            return True
    except Exception:
        return False
    return False
