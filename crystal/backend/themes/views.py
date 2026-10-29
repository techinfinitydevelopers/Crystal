"""What every page asks for on load: which festival theme, if any, is live.

Mirrors content.views.PageSectionFeedView — one small round trip, a short
cache, and nothing the page cannot do without.

`?preview=<slug>` answers with that theme whatever its switch or dates say.
It is what the dashboard's Preview link uses (the site passes it on from its
own `?theme=<slug>`), so an admin can look at a theme before switching it on
without anyone else seeing it.
"""
from django.http import JsonResponse
from django.views import View

from .models import FestivalTheme


class ThemeFeedView(View):
    def get(self, request):
        preview = (request.GET.get('preview') or '').strip().lower()
        if preview:
            theme = FestivalTheme.objects.filter(slug=preview).first()
        else:
            theme = FestivalTheme.live()

        res = JsonResponse({'theme': theme.as_feed(request) if theme else None})
        # Short, like the other feeds: a theme switched on reaches visitors
        # within a couple of minutes. A preview is one person's look and is
        # never shared from a cache.
        res['Cache-Control'] = 'no-store' if preview else 'public, max-age=120'
        return res
