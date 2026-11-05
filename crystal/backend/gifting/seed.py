"""Put the gift sets Gifting.html already ships into the dashboard.

Without this the Gifting screens would open empty, and the first set someone
adds would be the *only* one on the page. Seeding first makes "add another"
mean what it says.

Takes the model classes as arguments so the same code serves the data migration
(which only has the historical models) and the management command. It never
runs when there is already a gift set on file, so it cannot overwrite an edit,
and it quietly does nothing where the website's files are not alongside the
dashboard (e.g. a dashboard deployed on its own).
"""
import json
from pathlib import Path

from django.conf import settings


def source_path():
    return Path(settings.BASE_DIR).parent.parent / 'product-data' / 'gifting.json'


def seed(Range, GiftSet, SetModel, Settings, log=lambda msg: None):
    Settings.objects.get_or_create(pk=1)
    if GiftSet.objects.exists():
        log('Gifting: gift sets already on file, nothing seeded.')
        return 0
    path = source_path()
    if not path.is_file():
        log('Gifting: %s not found, nothing seeded.' % path)
        return 0
    data = json.loads(path.read_text(encoding='utf-8'))

    ranges = {}
    for i, sec in enumerate(data.get('sections', [])):
        r, _ = Range.objects.get_or_create(
            slug=sec['slug'], defaults={'label': sec['label'], 'order': (i + 1) * 10})
        ranges[sec['slug']] = r

    made = 0
    for i, p in enumerate(data.get('products', [])):
        g = GiftSet.objects.create(
            name=p['name'], gift_range=ranges[p['section']], sku=p.get('sku', ''),
            features='\n'.join(p.get('features') or []),
            outer_pack=p.get('outer'), mrp=p.get('mrp'),
            image_path=p.get('hero', ''), ref=p['id'], order=(i + 1) * 10)
        for j, m in enumerate(p.get('models') or []):
            SetModel.objects.create(
                gift_set=g, code=m.get('sku', ''), name=m.get('name', ''),
                outer_pack=m.get('outer'), mrp=m.get('mrp'), order=j)
        made += 1
    log('Gifting: %d gift sets in %d ranges seeded.' % (made, len(ranges)))
    return made
