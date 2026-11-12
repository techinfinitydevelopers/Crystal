"""One question, asked from many places: is this hidden from this user?

Answers are worked out once per request and kept on the user object, so the
sidebar, the page list and the editor can all ask without a query each.
"""
from collections import defaultdict


def is_super_admin(user):
    return bool(user and user.is_active and user.is_superuser)


def hidden_for(user):
    """{kind: set(keys)} hidden from `user`.

    Empty for a super admin working in the super admin dashboard (/admin/super/), which always shows
    everything so a switch can always be flipped back. On the everyday dashboard (/admin/) a switch
    that is off hides the item from EVERY account, super admins included -- access.middleware marks
    those requests with `_crx_everyday` before anything asks."""
    if not user or not user.is_authenticated:
        return defaultdict(set)
    everyday = getattr(user, '_crx_everyday', False)
    if is_super_admin(user) and not everyday:
        return defaultdict(set)
    attr = '_hidden_features_everyday' if (is_super_admin(user) and everyday) else '_hidden_features'
    cached = getattr(user, attr, None)
    if cached is not None:
        return cached
    from django.db.models import Q
    from .models import HiddenFeature
    out = defaultdict(set)
    rows = HiddenFeature.objects.filter(Q(user__isnull=True) | Q(user=user))
    for kind, key in rows.values_list('kind', 'key'):
        out[kind].add(key)
    setattr(user, attr, out)
    return out


def site_off():
    """Features the super admin switched off for everyone: {'gifting', 'themes', 'awards.award', ...}.

    One entry per hidden sidebar group (the app label) or sidebar item ("app.model"). What the
    public website does with them is decided by the website itself (features-sync.js) and by the
    feeds that check `site_off_app()`."""
    from .models import HiddenFeature
    keys = set()
    for kind, key in (HiddenFeature.objects.filter(user__isnull=True, kind__in=['app', 'model'])
                      .values_list('kind', 'key')):
        keys.add(key)
    return keys


def site_off_app(app_label):
    return app_label in site_off()


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
