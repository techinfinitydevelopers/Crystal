from django.contrib.admin import AdminSite
from django.db.models import Count


class CrystalAdminSite(AdminSite):
    site_header = "Crystal Cook"
    site_title = "Crystal Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from products.models import Product, Brand
        from enquiry.models import Enquiry
        from content.models import PageSection
        from content.pages_registry import PAGES_REGISTRY

        try:
            from blog.models import Blog
            stat_blogs = Blog.objects.count()
        except Exception:
            stat_blogs = 0

        section_counts = dict(
            PageSection.objects.values("page")
            .annotate(n=Count("id"))
            .values_list("page", "n")
        )
        pages_overview = [
            (group, [
                {"file": fn, "label": label, "count": section_counts.get(fn, 0)}
                for fn, label in pages
            ])
            for group, pages in PAGES_REGISTRY
        ]

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
