"""Create the gift sets Gifting.html already ships (see gifting/seed.py).

Safe to run any time: it does nothing once any gift set exists. The same thing
runs automatically as a data migration, so a normal deploy has already done it.
"""
from django.core.management.base import BaseCommand

from gifting.models import GiftRange, GiftSet, GiftSetModel, GiftingSettings
from gifting.seed import seed


class Command(BaseCommand):
    help = 'Fill the Gifting tables from product-data/gifting.json (only when they are empty).'

    def handle(self, *args, **options):
        made = seed(GiftRange, GiftSet, GiftSetModel, GiftingSettings, log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS('Gifting: %d added, %d on file.' % (made, GiftSet.objects.count())))
