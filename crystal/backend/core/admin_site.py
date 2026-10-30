from django.contrib.admin import AdminSite
from django.db.models import Count


class CrystalAdminSite(AdminSite):
    site_header = "Crystal Cook"
    site_title = "Crystal Admin"
    index_title = "Dashboard"

    def get_app_list(self, request, app_label=None):
        """The sidebar and the dashboard home, minus what the super admin hid
        from this account (Super admin control). Super admins see everything."""
        app_list = super().get_app_list(request, app_label)
        from access.rules import hidden_for
        h = hidden_for(request.user)
        if not (h['app'] or h['model']):
            return app_list
        out = []
        for app in app_list:
            if app['app_label'] in h['app']:
                continue
            app = dict(app)
            app['models'] = [m for m in app['models']
                             if '%s.%s' % (app['app_label'], m['object_name'].lower()) not in h['model']]
            if app['models']:
                out.append(app)
        return out

    def index(self, request, extra_context=None):
        from products.models import Product, Brand
        from enquiry.models import Enquiry
        from content.models import Page, PageSection
        from content.pages_registry import PAGES_REGISTRY

        try:
            from blog.models import Blog
            stat_blogs = Blog.objects.count()
        except Exception:
            stat_blogs = 0

        section_counts = dict(
            PageSection.objects.filter(is_deleted=False).values("page")
            .annotate(n=Count("id"))
            .values_list("page", "n")
        )
        # Every chip jumps straight into the same per-page editor the "Pages"
        # sidebar entry opens — this card used to link the flat, page-filtered
        # PageSection list instead, a second, confusing route to the same job.
        page_pks = dict(Page.objects.values_list("filename", "pk"))
        from access.rules import hidden_for
        hidden_pages = hidden_for(request.user)["page"]
        pages_overview = [
            (group, [
                {"file": fn, "label": label, "count": section_counts.get(fn, 0),
                 "pk": page_pks.get(fn)}
                for fn, label in pages if fn not in hidden_pages
            ])
            for group, pages in PAGES_REGISTRY
        ]
        pages_overview = [(g, ps) for g, ps in pages_overview if ps]

        extra_context = extra_context or {}
        extra_context.update({
            "stat_products": Product.objects.count(),
            "stat_brands": Brand.objects.count(),
            "stat_enquiries": Enquiry.objects.count(),
            "stat_new_enquiries": Enquiry.objects.filter(status="new").count(),
            "stat_blogs": stat_blogs,
            "stat_pages": sum(len(pages) for _, pages in PAGES_REGISTRY),
            "pages_overview": pages_overview,
            "recent_enquiries": (
                Enquiry.objects
                .prefetch_related("items")
                .order_by("-created_at")[:8]
            ),
        })
        return super().index(request, extra_context)
