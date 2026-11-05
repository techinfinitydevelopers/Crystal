"""The super admin dashboard's screens (access.sites.super_site).

Accounts: create an admin with a username, password and role in one go, block
or unblock them, reset their password.

Restrict: one screen of switches. Left on = the other admins see it. Switched
off = hidden from them, in the sidebar, the page list and the page editor, and
blocked if they type its URL. Super admins always see everything, so the person
flipping switches can never lock themselves out.

Both used to live in the everyday dashboard; they are taken out of it here.
"""
import json
from itertools import groupby

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .backends import SUPER_ONLY_APPS
from .models import HiddenFeature
from .roles import ROLE_CHOICES, ROLE_LABELS, SUPER, apply_role, role_of
from .rules import is_super_admin
from .sites import super_site

User = get_user_model()

# Out of the everyday dashboard: accounts are the super admin's business only.
for _model in (User, Group):
    if admin.site.is_registered(_model):
        admin.site.unregister(_model)


# ── accounts ─────────────────────────────────────────────────────────────────

class _RoleMixin(forms.Form):
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial=ROLE_CHOICES[0][0],
                             widget=forms.RadioSelect)
    current_user = None   # set by AccountAdmin.get_form

    def clean(self):
        data = super().clean()
        me = self.current_user
        if me and self.instance.pk == me.pk:
            if data.get('role') != SUPER or data.get('is_active') is False:
                raise forms.ValidationError(
                    'You cannot take super admin away from your own account, or block it '
                    '-- you would lock yourself out. Ask another super admin.')
        return data


class AccountCreationForm(_RoleMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)


class AccountChangeForm(_RoleMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'password', 'first_name', 'last_name', 'email', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['role'].initial = role_of(self.instance)
        self.fields['is_active'].label = 'Can sign in'
        self.fields['is_active'].help_text = 'Untick to block this account without deleting it.'


class AccountAdmin(UserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    list_display = ('username', 'role_badge', 'full_name', 'email', 'signin', 'last_login')
    list_filter = ('is_superuser', 'is_active')
    ordering = ('-is_superuser', 'username')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'role', 'is_active')}),
        ('Name and email', {'fields': ('first_name', 'last_name', 'email')}),
        ('History', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'password1', 'password2', 'role')}),
    )
    readonly_fields = ('last_login', 'date_joined')
    filter_horizontal = ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.current_user = request.user
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        apply_role(obj, form.cleaned_data['role'])

    def has_delete_permission(self, request, obj=None):
        # Deleting yourself would end the session mid-click and could leave no super admin.
        if obj is not None and obj.pk == request.user.pk:
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description='Role')
    def role_badge(self, obj):
        role = role_of(obj)
        colour = {'super': '#ED3338', 'seo': '#0369a1'}.get(role, '#16a34a')
        return format_html('<span style="background:{};color:#fff;padding:2px 9px;border-radius:100px;'
                           'font-size:11px;font-weight:700;">{}</span>', colour, ROLE_LABELS[role])

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description='Can sign in', boolean=True, ordering='is_active')
    def signin(self, obj):
        return obj.is_active


super_site.register(User, AccountAdmin)


def _scope_user(request):
    uid = request.GET.get('user') or request.POST.get('user') or ''
    if not uid.isdigit():
        return None
    return get_user_model().objects.filter(pk=int(uid), is_superuser=False).first()


def _hidden_keys(user):
    """(kind, key) pairs hidden in this scope, and those hidden for everyone."""
    rows = HiddenFeature.objects.filter(user=user) if user else HiddenFeature.objects.filter(user__isnull=True)
    mine = {(k, key) for k, key in rows.values_list('kind', 'key')}
    for_all = set()
    if user:
        for_all = {(k, key) for k, key in HiddenFeature.objects.filter(user__isnull=True).values_list('kind', 'key')}
    return mine, for_all


# ── restrictions ─────────────────────────────────────────────────────────────

@admin.register(HiddenFeature, site=super_site)
class HiddenFeatureAdmin(admin.ModelAdmin):
    """Registered so the panel has a sidebar entry; its list is the panel."""

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    has_change_permission = has_delete_permission = has_view_permission

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        wrap = self.admin_site.admin_view
        return [
            path('control/', wrap(self.control_view), name='access_hiddenfeature_control'),
            path('control/page/<int:pk>.json', wrap(self.page_json), name='access_hiddenfeature_page'),
            path('control/toggle/', wrap(self.toggle), name='access_hiddenfeature_toggle'),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return redirect('admin:access_hiddenfeature_control')

    # ── the screen ────────────────────────────────────────────────────────────

    def control_view(self, request):
        if not is_super_admin(request.user):
            return HttpResponseForbidden('Super admins only.')
        request.current_app = self.admin_site.name
        from content.models import Page
        from content.pages_registry import PAGES_REGISTRY

        scope = _scope_user(request)
        mine, for_all = _hidden_keys(scope)

        def state(kind, key):
            if (kind, key) in for_all:
                return 'all'      # hidden for everyone; switch it there
            return 'off' if (kind, key) in mine else 'on'

        apps = []
        # The switches are for the everyday dashboard, not this one.
        for app in admin.site.get_app_list(request):
            label = app['app_label']
            if label in SUPER_ONLY_APPS:
                continue
            models = [{
                'key': f"{label}.{m['object_name'].lower()}",
                'name': m['name'],
                'state': state('model', f"{label}.{m['object_name'].lower()}"),
            } for m in app['models']]
            apps.append({'key': label, 'name': app['name'], 'state': state('app', label), 'models': models})

        pks = dict(Page.objects.values_list('filename', 'pk'))
        page_groups = [{
            'name': group,
            'pages': [{'file': fn, 'name': lbl, 'pk': pks.get(fn), 'state': state('page', fn)}
                      for fn, lbl in pages],
        } for group, pages in PAGES_REGISTRY]

        admins = get_user_model().objects.filter(is_staff=True, is_superuser=False, is_active=True).order_by('username')
        context = {
            **self.admin_site.each_context(request),
            'title': 'Super admin control',
            'opts': self.model._meta,
            'apps': apps,
            'page_groups': page_groups,
            'admins': admins,
            'scope': scope,
            'hidden_total': HiddenFeature.objects.count(),
        }
        return render(request, 'admin/access/control.html', context)

    def page_json(self, request, pk):
        if not is_super_admin(request.user):
            return HttpResponseForbidden()
        from content.models import Page, PageSection
        page = get_object_or_404(Page, pk=pk)
        scope = _scope_user(request)
        mine, for_all = _hidden_keys(scope)

        def state(kind, key):
            return 'all' if (kind, key) in for_all else ('off' if (kind, key) in mine else 'on')

        qs = (PageSection.objects.filter(page=page.filename, is_deleted=False)
              .order_by('section', 'section_key'))
        groups = []
        for title, rows in groupby(qs, key=lambda s: (s.section or '', s.section_title)):
            raw, nice = title
            gkey = f'{page.filename}::{raw}'
            groups.append({
                'key': gkey, 'name': nice, 'state': state('group', gkey),
                'sections': [{
                    'key': str(s.pk),
                    'name': s.label or s.section_key,
                    'kind': s.kind,
                    'state': state('section', str(s.pk)),
                } for s in rows],
            })
        return JsonResponse({'page': page.title, 'groups': groups})

    def toggle(self, request):
        if request.method != 'POST' or not is_super_admin(request.user):
            return HttpResponseForbidden()
        try:
            data = json.loads(request.body or b'{}')
        except ValueError:
            return JsonResponse({'ok': False}, status=400)
        kind, key = data.get('kind'), str(data.get('key') or '')
        if kind not in dict(HiddenFeature.KIND_CHOICES) or not key:
            return JsonResponse({'ok': False}, status=400)
        uid = str(data.get('user') or '')
        user = (get_user_model().objects.filter(pk=int(uid), is_superuser=False).first()
                if uid.isdigit() else None)
        if data.get('hidden'):
            HiddenFeature.objects.get_or_create(
                kind=kind, key=key, user=user, defaults={'label': (data.get('label') or '')[:200]})
        else:
            HiddenFeature.objects.filter(kind=kind, key=key, user=user).delete()
        return JsonResponse({'ok': True, 'hidden': bool(data.get('hidden'))})
