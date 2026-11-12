"""What the public website asks for on every page: which features are switched off.

The super admin's switches in Super admin control (sidebar groups and items) hide a feature from
the dashboards. When one is switched off for everyone, the website has to stop showing it too: a
"Gifting" nobody can edit any more should not stay in the menu. This is the one small document the
site reads to know (features-sync.js); the pages decide what each feature looks like.

Only switches that apply to ALL admins count -- a switch aimed at one admin account is about that
person's dashboard, not about the site.
"""
from django.http import JsonResponse
from django.views import View

from .rules import site_off


class FeatureFeedView(View):
    def get(self, request):
        res = JsonResponse({'off': sorted(site_off())})
        # Short: switching a feature off should reach visitors within a minute or two.
        res['Cache-Control'] = 'public, max-age=60'
        return res
