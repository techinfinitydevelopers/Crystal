"""Let the new "match the strip above" default actually reach the site.

0004 made `seconds_per_card` optional, where empty means "move at the pace of
the product strip above". But the row already in the database still held 0.6 --
the *old* default, written by 0002/0003 before any of this was a choice. An
explicit value overrides the match, so deploying 0004 alone would have changed
nothing at all on the page, which is the opposite of what it was for.

Only 0.6 is cleared, and only when it is still the untouched default. Anything
else is a number somebody typed, and a migration has no business discarding it.
"""
from decimal import Decimal

from django.db import migrations


OLD_DEFAULT = Decimal('0.6')


def clear_old_default(apps, schema_editor):
    AwardSettings = apps.get_model('awards', 'AwardSettings')
    AwardSettings.objects.filter(seconds_per_card=OLD_DEFAULT).update(seconds_per_card=None)


def restore_old_default(apps, schema_editor):
    AwardSettings = apps.get_model('awards', 'AwardSettings')
    AwardSettings.objects.filter(seconds_per_card__isnull=True).update(seconds_per_card=OLD_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0004_alter_awardsettings_seconds_per_card'),
    ]

    operations = [
        migrations.RunPython(clear_old_default, restore_old_default),
    ]
