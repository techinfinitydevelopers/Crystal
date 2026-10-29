"""The festivals the site has a built-in look for. All seeded OFF.

No dates: festival days move every year, so the client sets them per theme
(or just uses the switch). Re-running never overwrites an edited row.
"""
from django.db import migrations

FESTIVALS = [
    # slug, name, greeting, sub_text
    ('diwali', 'Diwali', 'Happy Diwali from Crystal!',
     'May your home glow with light, warmth and good food.'),
    ('holi', 'Holi', 'Happy Holi from Crystal!',
     'Wishing you a season full of colour, laughter and sweets.'),
    ('navratri', 'Navratri / Dussehra', 'Happy Navratri & Dussehra from Crystal!',
     'Nine nights of devotion, dandiya and festive feasts.'),
    ('ganesh-chaturthi', 'Ganesh Chaturthi', 'Happy Ganesh Chaturthi from Crystal!',
     'Ganpati Bappa Morya! Wishing your home wisdom and prosperity.'),
    ('raksha-bandhan', 'Raksha Bandhan', 'Happy Raksha Bandhan from Crystal!',
     'Celebrating the bond that holds a family together.'),
    ('janmashtami', 'Janmashtami', 'Happy Janmashtami from Crystal!',
     'May Kanha fill your home with joy and makhan-mishri.'),
    ('independence-day', 'Independence Day', 'Happy Independence Day from Crystal!',
     'Celebrating the spirit of a free India.'),
    ('republic-day', 'Republic Day', 'Happy Republic Day from Crystal!',
     'Saluting the spirit of our Constitution.'),
    ('sankranti', 'Makar Sankranti / Pongal / Lohri', 'Happy Sankranti, Pongal & Lohri!',
     'May the harvest season fill every kitchen with abundance.'),
    ('onam', 'Onam', 'Happy Onam from Crystal!',
     'Wishing you a sadya-full season of joy and togetherness.'),
    ('eid', 'Eid', 'Eid Mubarak from Crystal!',
     'Wishing you peace, joy and feasts shared with loved ones.'),
    ('christmas', 'Christmas', 'Merry Christmas from Crystal!',
     'Warm wishes for a season of togetherness and good food.'),
    ('new-year', 'New Year', 'Happy New Year from Crystal!',
     'Here is to a year of great meals and greater company.'),
]


def seed(apps, schema_editor):
    FestivalTheme = apps.get_model('themes', 'FestivalTheme')
    for i, (slug, name, greeting, sub) in enumerate(FESTIVALS):
        FestivalTheme.objects.get_or_create(slug=slug, defaults={
            'name': name, 'greeting': greeting, 'sub_text': sub,
            'is_active': False, 'effects': True, 'scope': 'site',
            'order': (i + 1) * 10,
        })


def unseed(apps, schema_editor):
    FestivalTheme = apps.get_model('themes', 'FestivalTheme')
    FestivalTheme.objects.filter(slug__in=[f[0] for f in FESTIVALS]).delete()


class Migration(migrations.Migration):
    dependencies = [('themes', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
