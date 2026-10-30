"""Super admin control: one screen of switches.

Left on = the other admins see it. Switched off = hidden from them, in the
sidebar, the page list and the page editor, and blocked if they type its URL.
Super admins always see everything, so the person flipping switches can never
lock themselves out.
"""
import json
from itertools import groupby

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from .backends import SUPER_ONLY_APPS
from .models import HiddenFeature
from .rules import is_super_admin


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


@admin.register(HiddenFeature)
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
        from content.models import Page
        from content.pages_registry import PAGES_REGISTRY

        scope = _scope_user(request)
        mine, for_all = _hidden_keys(scope)

        def state(kind, key):
            if (kind, key) in for_all:
                return 'all'      # hidden for everyone; switch it there
            return 'off' if (kind, key) in mine else 'on'

        apps = []
        for app in self.admin_site.get_app_list(request):
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
