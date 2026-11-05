"""The three kinds of account, as the super admin picks them.

Stored the Django way rather than in a new column: a super admin is a
superuser, an SEO Team member is staff in the "SEO Team" group, and an admin is
staff in no group at all (access.backends gives them the whole dashboard).
"""
SUPER = 'super'
ADMIN = 'admin'
SEO = 'seo'

ROLE_CHOICES = [
    (ADMIN, 'Admin - the whole dashboard, minus what you restrict'),
    (SEO, 'SEO Team - SEO screens, page text and blog only'),
    (SUPER, 'Super admin - everything, including this super admin dashboard'),
]
ROLE_LABELS = {ADMIN: 'Admin', SEO: 'SEO Team', SUPER: 'Super admin'}


def _seo_group():
    from django.contrib.auth.models import Group
    from seo.apps import GROUP_NAME, ensure_seo_group
    group = Group.objects.filter(name=GROUP_NAME).first()
    if group is None:
        ensure_seo_group(sender=None)
        group = Group.objects.get(name=GROUP_NAME)
    return group


def role_of(user):
    from seo.apps import GROUP_NAME
    if user.is_superuser:
        return SUPER
    if any(g.name == GROUP_NAME for g in user.groups.all()):
        return SEO
    return ADMIN


def apply_role(user, role):
    """Set the flags for `role`. The user must already be saved (groups)."""
    user.is_staff = True
    user.is_superuser = role == SUPER
    user.save(update_fields=['is_staff', 'is_superuser'])
    if role == SEO:
        user.groups.set([_seo_group()])
    else:
        user.groups.clear()
