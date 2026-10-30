"""Admins (staff who are not super admins) may use the whole dashboard.

Without this a new staff account sees an empty sidebar until someone ticks
dozens of permission boxes. Instead an admin gets every permission except the
two areas that belong to the super admin -- user accounts and this control
panel -- and the super admin narrows it from Super admin control.

A hidden item is simply not granted here. Django ORs backends together, so
that alone cannot take away a permission someone ticked by hand -- which is
why access.middleware and the sidebar filter in core.admin_site enforce hiding
as well, for every admin the same way.
"""
SUPER_ONLY_APPS = {'auth', 'access'}


class AdminAccessBackend:
    def authenticate(self, request, **kwargs):
        return None

    def get_user(self, user_id):
        return None

    @staticmethod
    def _is_admin(user_obj):
        return user_obj.is_active and user_obj.is_staff and not user_obj.is_superuser

    def has_perm(self, user_obj, perm, obj=None):
        if not self._is_admin(user_obj):
            return False
        app_label, _, codename = perm.partition('.')
        if app_label in SUPER_ONLY_APPS:
            return False
        # Not granting a hidden model also drops it from every
        # `{% if perms.x.y %}` on the dashboard home, with no template work.
        from .rules import model_hidden
        model_name = codename.split('_', 1)[1] if '_' in codename else codename
        return not model_hidden(user_obj, app_label, model_name)

    def has_module_perms(self, user_obj, app_label):
        if not self._is_admin(user_obj):
            return False
        from .rules import hidden_for
        return app_label not in SUPER_ONLY_APPS and app_label not in hidden_for(user_obj)['app']
