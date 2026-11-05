"""Fill the Gifting tables with the gift sets Gifting.html already ships.

Runs with `migrate`, so a normal deploy seeds the dashboard by itself. See
gifting/seed.py: it does nothing once a gift set exists, and nothing where
product-data/gifting.json is not alongside the dashboard.
"""
from django.db import migrations

from gifting.seed import seed


def seed_gift_sets(apps, schema_editor):
    seed(
        apps.get_model('gifting', 'GiftRange'),
        apps.get_model('gifting', 'GiftSet'),
        apps.get_model('gifting', 'GiftSetModel'),
        apps.get_model('gifting', 'GiftingSettings'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('gifting', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_gift_sets, migrations.RunPython.noop),
    ]
