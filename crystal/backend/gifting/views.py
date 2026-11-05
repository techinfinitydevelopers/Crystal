"""What Gifting.html asks for on load: the ranges, the gift sets and the wording.

One small document, a short cache (an edit shows up within a minute with no
deploy), and the same shape as the shipped product-data/gifting.json so the page
treats the two alike.
"""
from django.http import JsonResponse
from django.views import View

from .models import GiftingSettings, GiftRange, GiftSet


class GiftingFeedView(View):
    def get(self, request):
        s = GiftingSettings.load()
        ranges = list(GiftRange.objects.filter(is_active=True))
        live = {r.pk for r in ranges}
        products = []
        qs = (GiftSet.objects.filter(is_active=True, gift_range_id__in=live)
              .select_related('gift_range').prefetch_related('models_in_set'))
        for g in sorted(qs, key=lambda g: (g.gift_range.order, g.gift_range_id, g.order, g.id)):
            pic = g.picture(request)
            if not pic:                       # an empty card looks like a broken image
                continue
            models_ = [{'sku': m.code, 'name': m.name, 'outer': m.outer_pack, 'mrp': m.mrp}
                       for m in g.models_in_set.all()]
            products.append({
                'id': g.ref,
                'sku': g.codes,
                'name': g.name,
                'section': g.gift_range.slug,
                'features': g.feature_list,
                'outer': g.outer_pack,
                'mrp': g.mrp,
                'models': models_ or None,
                'hero': pic,
                'gallery': [],
            })
        res = JsonResponse({
            # The page uses this feed only once something has been entered here;
            # until then it keeps the list it ships.
            'configured': GiftSet.objects.exists(),
            'settings': {
                'heroPretext': s.hero_pretext,
                'heroTitle': s.hero_title,
                'heroLead': s.hero_lead,
                'heroPoints': s.points,
                'browseTitle': s.browse_title,
                'browseLead': s.browse_lead,
                'ctaTitle': s.cta_title,
                'ctaText': s.cta_text,
                'showMrp': s.show_mrp,
            },
            'sections': [{'slug': r.slug, 'label': r.label} for r in ranges],
            'products': products,
        })
        res['Cache-Control'] = 'public, max-age=60'
        return res
