"""Drop the redundant filter/spec rows that made facets render twice.

Every affected product carried the same attribute under two keys: the curated
short one used by product-data/pipeline/config.py, and a second copy slugified
straight from the spreadsheet column header. The listing pages build one filter
chip per distinct key, so each pair showed up twice ("Set" twice,
"Induction / Non-Induction" twice, "Edge" alongside "Blade Edge"...).

products.json — which sync_products.py rebuilds these rows from — has already
been cleaned, so a fresh sync would produce the right rows. This migration
brings databases that were populated *before* that cleanup in line, rather than
requiring a full re-sync of every product.

Deliberately conservative: a duplicate row is deleted only when it is provably
redundant — the canonical twin exists with the same value, or the value is a
placeholder ("NA", "None"). Anything else is left alone, so an environment whose
data differs from ours cannot silently lose a real value.
"""
from django.db import migrations

# duplicate key -> canonical key it mirrors
DUPLICATE_KEYS = {
    "Individual Set": "Set Type",
    "Induction Non Induction": "Induction",
    "Blade Edge Type": "Edge Type",
    "Coating Type": "Coating",
    "With Without Blade": "With Blade",
}

PLACEHOLDER_VALUES = {"", "-", "na", "n/a", "none", "null"}


def remove_duplicate_spec_keys(apps, schema_editor):
    Spec = apps.get_model("products", "ProductSpecification")

    for duplicate, canonical in DUPLICATE_KEYS.items():
        for row in Spec.objects.filter(key=duplicate).select_related(None):
            twin = Spec.objects.filter(
                product_id=row.product_id,
                variant_id=row.variant_id,
                key=canonical,
            ).first()

            value = (row.value or "").strip()
            redundant = twin is not None and (twin.value or "").strip() == value
            placeholder = value.lower() in PLACEHOLDER_VALUES

            if redundant or placeholder:
                row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0012_alter_product_image_url_alter_product_video_url_and_more"),
    ]

    operations = [
        # Irreversible by design: the rows carried no information the canonical
        # key does not already hold, so there is nothing to restore.
        migrations.RunPython(remove_duplicate_spec_keys, migrations.RunPython.noop),
    ]
