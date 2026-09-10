"""What the website asks for on load: every page-section override set from
the dashboard, grouped by page so a page pays one round trip, not one per
section. Mirrors banners.views.BannerFeedView.
"""
from django.http import JsonResponse
from django.views import View

from .models import PageSection


def _abs(request, url):
    return request.build_absolute_uri(url)


class PageSectionFeedView(View):
    def get(self, request):
        pages = {}
        qs = PageSection.objects.filter(is_active=True)
        for s in qs:
            entry = {'kind': s.kind, 'updated': s.updated_at.isoformat()}
            if s.kind == PageSection.IMAGE:
                if not s.image:
                    continue
                try:
                    entry['url'] = _abs(request, s.image.url)
                except ValueError:
                    continue
            else:
                if not s.text_value:
                    continue
                entry['text'] = s.text_value
            pages.setdefault(s.slug, {})[s.section_key] = entry

        res = JsonResponse({'pages': pages})
        res['Cache-Control'] = 'public, max-age=120'
        return res
