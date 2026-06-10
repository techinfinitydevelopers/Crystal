from django.contrib.admin import AdminSite


class CrystalAdminSite(AdminSite):
    site_header = "Crystal Cook"
    site_title = "Crystal Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from products.models import Product, Brand
        from enquiry.models import Enquiry

        try:
            from blog.models import Blog
            stat_blogs = Blog.objects.count()
        except Exception:
            stat_blogs = 0

        extra_context = extra_context or {}
        extra_context.update({
            "stat_products": Product.objects.count(),
            "stat_brands": Brand.objects.count(),
            "stat_enquiries": Enquiry.objects.count(),
            "stat_new_enquiries": Enquiry.objects.filter(status="new").count(),
            "stat_blogs": stat_blogs,
            "recent_enquiries": (
                Enquiry.objects
                .prefetch_related("items")
                .order_by("-created_at")[:8]
            ),
        })
        return super().index(request, extra_context)
