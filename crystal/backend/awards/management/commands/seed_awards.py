"""Put the award About.html already ships into the dashboard.

Without this the Awards screen opens empty, and the first certificate someone
adds would be the *only* one on the page — the feed replaces the shipped set
wholesale, as every feed on this site does. Seeding first makes "add another"
mean what it says.

Idempotent, and it never touches a row someone has edited: it matches on
image_path, which only a seeded row has.
"""
from django.core.management.base import BaseCommand

from awards.models import Award


SHIPPED = [
    {
        'image_path': 'about-assets/award-trophy.jpg',
        'title': 'HomeShop18 STAR Award',
        'subtitle': 'Home & Kitchen',
        'alt': 'HomeShop18 STAR Award — Home & Kitchen',
        'order': 10,
    },
    # cert-1/2/3.png are deliberately not here. They were three copies of one
    # stock template ("Kristen Kennedy — E-Commerce Marketing Master") that
    # shipped as placeholder art, and the client asked for them to go. Seeding
    # them would put them straight back on the page, because the feed replaces
    # About.html's shipped set wholesale.
]


class Command(BaseCommand):
    help = 'Create the Award rows for the certificates About.html already ships.'

    def handle(self, *args, **options):
        created = 0
        for row in SHIPPED:
            _, made = Award.objects.get_or_create(
                image_path=row['image_path'],
                defaults={
                    'title': row.get('title', ''),
                    'subtitle': row.get('subtitle', ''),
                    'alt': row.get('alt', ''),
                    'order': row['order'],
                },
            )
            created += made
        total = Award.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Awards: {created} added, {total} on file.'
        ))
