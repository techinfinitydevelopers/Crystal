"""What About.html asks for on load: the full Awards & Recognition set.

Mirrors banners.views.BannerFeedView — one round trip, a short cache, and
nothing the page cannot do without.
"""
from django.http import JsonResponse
from django.views import View

from .models import Award


class AwardFeedView(View):
    def get(self, request):
        items = []
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

        res = JsonResponse({'awards': items})
        res['Cache-Control'] = 'public, max-age=120'
        return res
