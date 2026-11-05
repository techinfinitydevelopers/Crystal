"""The super admin's own dashboard, at /admin/super/.

A second admin site with its own sign-in: only super admins (Django
superusers) get past it. It holds the two things that used to sit inside the
everyday dashboard -- user accounts and the restriction switches -- so the
other admins never even see a link to them.

Its own sign-in in the strict sense: being signed in to the everyday /admin/
does not open this one. Only a sign-in on this site's login page sets
SESSION_KEY, so the super admin's username and password are asked for here
every time, and signing out of either dashboard closes both.

Mounted under /admin/ on purpose: nginx on the VPS sends only /admin, /api and
/dashboard to Django, so a new top-level path would never reach it.
"""
from django import forms
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm

from .rules import is_super_admin

SESSION_KEY = 'crx_super_admin'


class SuperAdminLoginForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise forms.ValidationError(
                'Only a super admin can sign in here. Admins sign in at /admin/.',
                code='not_super_admin')


class SuperAdminSite(AdminSite):
    site_header = 'Crystal Super Admin'
    site_title = 'Crystal Super Admin'
    index_title = 'Super admin'
    login_form = SuperAdminLoginForm
    index_template = 'admin/superadmin/index.html'

    def has_permission(self, request):
        return (is_super_admin(request.user)
                and request.session.get(SESSION_KEY) == request.user.pk)

    def login(self, request, extra_context=None):
        response = super().login(request, extra_context)
        if request.method == 'POST' and is_super_admin(request.user):
            request.session[SESSION_KEY] = request.user.pk
        return response

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            if app['app_label'] == 'auth':
                app['name'] = 'Accounts'
        return app_list

    def each_context(self, request):
        ctx = super().each_context(request)
        ctx['is_super_site'] = True
        return ctx

    def index(self, request, extra_context=None):
        from django.contrib.auth import get_user_model
        from .models import HiddenFeature
        from .roles import role_of

        accounts = list(get_user_model().objects.prefetch_related('groups')
                        .order_by('-is_superuser', '-is_active', 'username'))
        for u in accounts:
            u.role = role_of(u)
        extra_context = {
            **(extra_context or {}),
            'accounts': accounts,
            'n_super': sum(1 for u in accounts if u.role == 'super' and u.is_active),
            'n_admin': sum(1 for u in accounts if u.role != 'super' and u.is_active),
            'n_blocked': sum(1 for u in accounts if not u.is_active),
            'n_hidden': HiddenFeature.objects.count(),
        }
        return super().index(request, extra_context)


super_site = SuperAdminSite(name='superadmin')
