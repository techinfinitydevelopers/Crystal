"""Keep admins out of what the super admin hid, even by typing the URL.

The sidebar filter only stops a hidden item being listed; a bookmarked or
pasted link would still open it. Every admin URL name starts with
"<app>_<model>_" (Django's own views, and every custom view in this project
follows the same naming), so the app and model can be read off the name.
"""
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .rules import hidden_for, is_super_admin, model_hidden, page_hidden


def _prefixes():
    out = []
    for model in admin.site._registry:
        meta = model._meta
        out.append((f'{meta.app_label}_{meta.model_name}_', meta.app_label, meta.model_name))
    # Longest first, so "content_pagesection_" is not read as "content_page_".
    return sorted(out, key=lambda t: -len(t[0]))


class HiddenFeatureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._prefix_cache = None

    def __call__(self, request):
        blocked = self._blocked(request)
        if blocked:
            messages.warning(request, 'That part of the dashboard is not available to your account.')
            return redirect('admin:index')
        return self.get_response(request)

    def _blocked(self, request):
        user = getattr(request, 'user', None)
        if not request.path.startswith('/admin/') or not user or not user.is_authenticated:
            return False
        if not user.is_staff or is_super_admin(user):
            return False
        h = hidden_for(user)
        if not any(h.values()):
            return False
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return False
        name = match.url_name or ''
        if self._prefix_cache is None:
            self._prefix_cache = _prefixes()
        for prefix, app_label, model_name in self._prefix_cache:
            if name.startswith(prefix) or name == prefix[:-1]:
                if model_hidden(user, app_label, model_name):
                    return True
                break
        else:
            # app index: /admin/<app_label>/
            if name == 'app_list' and match.kwargs.get('app_label') in h['app']:
                return True
        # A hidden website page's editor.
        if name == 'content_page_editor' and h['page']:
            from content.models import Page
            filename = Page.objects.filter(pk=match.kwargs.get('pk')).values_list('filename', flat=True).first()
            if filename and page_hidden(user, filename):
                return True
        return False
