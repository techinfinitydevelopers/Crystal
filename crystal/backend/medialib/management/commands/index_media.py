"""Put every file already uploaded anywhere in the dashboard into the library.

    python manage.py index_media

Walks every FileField / ImageField of every installed app and makes sure a
library row points at each stored name. Nothing is copied or moved — the row
and the product photo (or banner, or PDF) share the one file.

Safe to run any number of times: a name that already has a row is left alone,
so it runs on every deploy (deploy/vps-deploy.sh) to pick up anything that
arrived without going through a save — a bulk import, say.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from medialib.indexing import ensure_item
from medialib.usage import file_fields, source_label


class Command(BaseCommand):
    help = 'Add every file already uploaded anywhere in the dashboard to the Media library.'

    def handle(self, *args, **options):
        totals = {'created': 0, 'exists': 0, 'missing': 0}
        for model, field in file_fields():
            label = source_label(model)
            names = (model._default_manager
                     .exclude(**{f'{field.attname}__isnull': True})
                     .exclude(**{field.attname: ''})
                     .values_list(field.attname, flat=True)
                     .distinct())
            made = 0
            # One transaction per field: thousands of single-row commits are
            # what made the first run slow on SQLite (each one is an fsync).
            with transaction.atomic():
                for name in names:
                    result = ensure_item(name, label)
                    totals[result] += 1
                    made += result == 'created'
            if made:
                self.stdout.write(f'  {label} ({field.name}): {made} added')
        self.stdout.write(self.style.SUCCESS(
            f"Media library: {totals['created']} added, {totals['exists']} already there, "
            f"{totals['missing']} skipped (file not in storage)."))
