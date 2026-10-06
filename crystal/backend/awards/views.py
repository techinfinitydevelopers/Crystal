"""What About.html asks for on load: the full Awards & Recognition set.

Mirrors banners.views.BannerFeedView — one round trip, a short cache, and
nothing the page cannot do without.
"""
from django.http import JsonResponse
from django.views import View

from .models import Award, AwardSettings


class AwardFeedView(View):
    def get(self, request):
        items = []
        settings = AwardSettings.load()
        for a in Award.objects.filter(is_active=True):
            picture = a.picture_url(request)
            # A row with no picture would render as an empty card, which looks
            # like a broken image rather than a deliberate blank.
            if not picture:
                continue
            items.append({
                'title': a.title,
                'subtitle': a.subtitle,
                'image': picture,
                'pdf': a.pdf_url(request),
                'alt': a.alt or a.title or 'Certificate',
            })

        res = JsonResponse({
            'awards': items,
            # Sent with the awards rather than from a second endpoint: the page
            # needs both before it can start, and one round trip is the whole
            # point of this feed.
            'scroll': {
                'secondsPerCard': float(settings.seconds_per_card),
                'autoscroll': settings.autoscroll,
            },
        })
        res['Cache-Control'] = 'public, max-age=120'
        return res
