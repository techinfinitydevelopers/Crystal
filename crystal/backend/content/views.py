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
        qs = PageSection.objects.filter(is_active=True, is_deleted=False)
        for s in qs:
            entry = {'kind': s.kind, 'updated': s.updated_at.isoformat()}
            if s.kind == PageSection.IMAGE:
                if not s.image:
                    continue
                try:
                    entry['url'] = _abs(request, s.image.url)
                except ValueError:
                    continue
                # A phone-specific crop, optional. Sent as a second URL rather
                # than picked here — this view has no idea what device is
                # asking, and the page is the one that knows its own
                # breakpoint.
                if s.image_mobile:
                    try:
                        entry['url_mobile'] = _abs(request, s.image_mobile.url)
                    except ValueError:
                        pass
            else:
                if not s.text_value:
                    continue
                entry['text'] = s.text_value
                # How the page should render this. Sent per section rather
                # than decided on the page, because the page's own
                # `data-cms-rich` attribute is baked into the static HTML and
                # the dashboard cannot reach it -- which is exactly why a <br>
                # typed into an untagged paragraph used to reach visitors as
                # the literal text "<br>".
                if s.text_format == PageSection.HTML:
                    entry['format'] = PageSection.HTML
                elif s.text_format == PageSection.LIST:
                    # Parsed here, once, rather than leaving every page to
                    # agree on what "a bullet" looks like.
                    lead, bullets = PageSection.parse_list(s.text_value)
                    if bullets:
                        entry['format'] = PageSection.LIST
                        entry['lead'] = lead
                        entry['bullets'] = bullets
            pages.setdefault(s.slug, {})[s.section_key] = entry

        res = JsonResponse({'pages': pages})
        res['Cache-Control'] = 'public, max-age=120'
        return res
