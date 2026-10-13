from django.apps import AppConfig
from django.db.models.signals import post_migrate

GROUP_NAME = 'SEO Team'

# (app_label, model, actions). `view` on a model is what shows it in the sidebar;
# the rest are what they may do to it.
GROUP_PERMISSIONS = [
    ('seo', 'seometa', ('view', 'change')),
    ('seo', 'productpage', ('view', 'change')),
    ('seo', 'blogpostseo', ('view', 'change')),
    ('seo', 'scriptblock', ('view', 'add', 'change', 'delete')),
    ('seo', 'seosettings', ('view', 'change')),
    ('seo', 'redirect', ('view', 'add', 'change', 'delete')),
    # They also own the words on the pages and the blog, which is half of SEO.
    ('content', 'pagesection', ('view', 'change')),
    ('content', 'page', ('view', 'change')),
    ('blog', 'blog', ('view', 'add', 'change')),
    ('blog', 'blogcategory', ('view', 'add', 'change')),
]


def ensure_seo_group(sender, **kwargs):
    """Create or refresh the SEO Team group after every migrate.

    Run from post_migrate rather than a data migration because permissions do
    not exist until after migrate has created them, and this also repairs the
    group if someone has been fiddling with it.
    """
    from django.contrib.auth.models import Group, Permission
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    wanted = []
    for app_label, model, actions in GROUP_PERMISSIONS:
        for action in actions:
            perm = Permission.objects.filter(
                content_type__app_label=app_label,
                codename='%s_%s' % (action, model)).first()
            if perm:
                wanted.append(perm)
    group.permissions.set(wanted)


class SeoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seo'
    verbose_name = 'SEO'

    def ready(self):
        # Not limited to this app's own migrate: the permissions it hands out
        # belong to other apps and may only exist after theirs have run.
        post_migrate.connect(ensure_seo_group, dispatch_uid='seo-team-group')
        from . import signals  # noqa: F401  (connects the save handlers)
