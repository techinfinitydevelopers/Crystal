from django.db import migrations, models


# Photos already replaced in the dashboard before deletions were recorded.
# Measured on 2026-10-21 against the live feed: each of these catalogue photos
# is absent from the product's dashboard set, which holds an uploaded copy or
# a replacement instead, so the site was showing old and new side by side.
# CC-850 is deliberately NOT here: its dashboard set is 2 photos against the
# catalogue's 9 because it was edited before photos were synced, not because
# anyone removed them.
BACKFILL = {
    'CL-216': ['product-photos/CL-216/amz-1.jpg', 'product-photos/CL-216/amz-2.jpg'],
    'MKA-008': ['product-photos/MKA-008/amz-%d.jpg' % i for i in range(1, 9)],
    'MKA-010': ['product-photos/MKA-010/amz-%d.jpg' % i for i in range(1, 10)],
    'MKA114': ['product-photos/MKA114/g4.jpg', 'product-photos/MKA114/g5.jpg'],
    'CLMK-019': ['product-photos/CLMK-019/amz-4.jpg'],
}


def backfill(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    ProductVariant = apps.get_model('products', 'ProductVariant')
    for sku, paths in BACKFILL.items():
        product = Product.objects.filter(sku=sku).first()
        if product is None:
            variant = ProductVariant.objects.filter(sku=sku).select_related('product').first()
            product = variant.product if variant else None
        if product is None:
            continue
        current = list(product.removed_photos or [])
        for path in paths:
            if path not in current:
                current.append(path)
        product.removed_photos = current
        product.save(update_fields=['removed_photos'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0017_brand_overridden_fields_category_overridden_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='removed_photos',
            field=models.JSONField(blank=True, default=list, help_text='Internal — photos removed in the dashboard, so the website drops them too.'),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
