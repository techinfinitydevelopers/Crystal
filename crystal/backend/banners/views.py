"""What the website asks for on load: every banner set from the dashboard.

One small document rather than a request per page, because a visitor lands on
one category page and should not pay a round trip to find out there is nothing
to swap. It is cached hard at the edge and cheap to regenerate.
"""
from django.conf import settings
from django.http import JsonResponse
from django.views import View

from .models import CategoryBanner


def _abs(request, url):
    return request.build_absolute_uri(url)


class BannerFeedView(View):
    def get(self, request):
        out = {}
        for b in CategoryBanner.objects.filter(is_active=True).exclude(image=''):
            try:
                url = b.image.url
            except ValueError:
                continue
            out[b.slug] = {
                'url': _abs(request, url),
                'focus': b.focus,
                'mobile_focus': b.mobile_focus,
                'updated': b.updated_at.isoformat(),
            }
        res = JsonResponse({'banners': out})
        # Short, because the point of this feature is that an edit shows up
        # without a deploy; long enough that it is not hit on every navigation.
        res['Cache-Control'] = 'public, max-age=120'
        return res
