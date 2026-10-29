"""Categories -> Arrange products: put a category page's products in the order
the client wants, by dragging.

The website lists a category's products in catalogue order -- products made in
the dashboard first, newest first, then products.json as it stands. Saving here
numbers every product of the category 1..N in `Product.site_position`; the
override feed sends those numbers and product-image-sync.js sorts by them.

A product nobody has arranged yet (a new one) has no number and is listed
before the numbered ones, so "a new product shows at the top of its category"
still holds after a category has been arranged.
"""
import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .media_urls import _public_url
from .models import Category, Product


def _catalogue_index():
    """products.json order, keyed by product code."""
    root = getattr(settings, 'SITE_ROOT', None)
    if not root:
        return {}
    try:
        data = json.loads((Path(root) / 'product-data' / 'products.json')
                          .read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    items = data.get('products', data) if isinstance(data, dict) else data
    index = {}
    for i, entry in enumerate(items or []):
        sku = isinstance(entry, dict) and entry.get('sku')
        if sku and sku not in index:
            index[sku] = i
    return index


def site_order(products):
    """The order the website shows these products in today -- the same rule
    product-image-sync.js applies, so what is dragged here is what visitors see."""
    index = _catalogue_index()
    managed = sorted((p for p in products if p.is_dashboard_managed),
                     key=lambda p: (-p.created_at.timestamp(), -p.pk))
    managed_rank = {p.pk: i for i, p in enumerate(managed)}

    def base(p):
        if p.pk in managed_rank:
            return (0, managed_rank[p.pk])
        skus = [p.sku] + [v.sku for v in p.variants.all()]
        found = [index[s] for s in skus if s and s in index]
        return (1, min(found) if found else 10 ** 6, p.pk)

    return sorted(products, key=lambda p: (p.site_position is not None,
                                           p.site_position or 0, base(p)))


def arrange_view(model_admin, request, pk):
    category = get_object_or_404(Category, pk=pk)
    qs = (Product.objects.filter(Q(category=category) | Q(category__parent=category),
                                 is_active=True)
          .select_related('brand', 'category').prefetch_related('variants'))
    products = site_order(list(qs))

    if request.method == 'POST':
        wanted = [int(x) for x in request.POST.get('order', '').split(',') if x.isdigit()]
        by_pk = {p.pk: p for p in products}
        wanted = [pk for pk in wanted if pk in by_pk]
        # Anything not in the posted list (it should all be) keeps its place
        # after the posted ones rather than losing its number.
        wanted += [p.pk for p in products if p.pk not in wanted]
        with transaction.atomic():
            for position, pk_ in enumerate(wanted, start=1):
                p = by_pk[pk_]
                if p.site_position != position:
                    Product.objects.filter(pk=pk_).update(site_position=position)
        messages.success(request, 'Saved the order of “%s”. The category page shows it '
                                  'within a couple of minutes.' % category.name)
        return redirect(request.path)

    rows = []
    for p in products:
        variants = list(p.variants.all())
        rows.append({
            'pk': p.pk,
            'name': p.name,
            'sku': p.sku or '',
            'brand': p.brand.name if p.brand_id else '',
            'sub': p.category.name if p.category_id != category.pk else '',
            'thumb': _public_url(p.image_url),
            'sizes': len(variants),
            'arranged': p.site_position is not None,
        })
    context = {
        **model_admin.admin_site.each_context(request),
        'title': 'Arrange products — %s' % category.name,
        'opts': model_admin.model._meta,
        'category': category,
        'rows': rows,
        'children': category.children.all(),
        'parent': category.parent,
        'any_arranged': any(r['arranged'] for r in rows),
    }
    return render(request, 'admin/products/category/arrange.html', context)


def reset_view(model_admin, request, pk):
    """Forget the arrangement: the category goes back to catalogue order."""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        n = (Product.objects.filter(Q(category=category) | Q(category__parent=category))
             .exclude(site_position=None).update(site_position=None))
        messages.success(request, '“%s” is back in its original order (%d products).'
                         % (category.name, n))
    return redirect('admin:products_category_arrange', pk)
