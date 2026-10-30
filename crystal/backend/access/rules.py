"""One question, asked from many places: is this hidden from this user?

Answers are worked out once per request and kept on the user object, so the
sidebar, the page list and the editor can all ask without a query each.
"""
from collections import defaultdict


def is_super_admin(user):
    return bool(user and user.is_active and user.is_superuser)


def hidden_for(user):
    """{kind: set(keys)} hidden from `user`. Empty for super admins."""
    if not user or not user.is_authenticated or is_super_admin(user):
        return defaultdict(set)
    cached = getattr(user, '_hidden_features', None)
    if cached is not None:
        return cached
    from django.db.models import Q
    from .models import HiddenFeature
    out = defaultdict(set)
    for kind, key in (HiddenFeature.objects
                      .filter(Q(user__isnull=True) | Q(user=user))
                      .values_list('kind', 'key')):
        out[kind].add(key)
    user._hidden_features = out
    return out


def model_hidden(user, app_label, model_name):
    h = hidden_for(user)
    return app_label in h['app'] or f'{app_label}.{model_name}' in h['model']


def page_hidden(user, filename):
    return filename in hidden_for(user)['page']


def visible_sections(user, queryset):
    """A PageSection queryset without what is hidden from this user."""
    h = hidden_for(user)
    if not (h['page'] or h['group'] or h['section']):
        return queryset
    qs = queryset.exclude(page__in=h['page'])
    ids = [int(k) for k in h['section'] if k.isdigit()]
    if ids:
        qs = qs.exclude(pk__in=ids)
    for key in h['group']:
        page, _, section = key.partition('::')
        qs = qs.exclude(page=page, section=section)
    return qs
