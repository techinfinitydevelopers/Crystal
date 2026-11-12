"""`{% if perms.app.view_model %}` that also honours Super admin control.

The dashboard home decides which cards and quick links to draw with `perms`. For an ordinary admin
access.backends already withholds a hidden model's permissions, so those links vanish by
themselves. A super admin passes every permission test in Django, so on the everyday dashboard
(where a switched-off feature is hidden from everyone) the home would keep linking to screens the
sidebar no longer lists. This wrapper answers "no" for anything switched off, and is used only by
the everyday dashboard (core.admin_site); the super admin dashboard keeps the real `perms`.
"""
from django.contrib.auth.context_processors import PermLookupDict, PermWrapper

from .rules import hidden_for


class _HiddenAwareLookup(PermLookupDict):
    def __getitem__(self, perm_name):
        h = hidden_for(self.user)
        if self.app_label in h['app']:
            return False
        model_name = perm_name.split('_', 1)[1] if '_' in perm_name else perm_name
        if '%s.%s' % (self.app_label, model_name) in h['model']:
            return False
        return super().__getitem__(perm_name)


class HiddenAwarePerms(PermWrapper):
    def __getitem__(self, app_label):
        return _HiddenAwareLookup(self.user, app_label)
