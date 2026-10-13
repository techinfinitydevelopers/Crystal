"""Make a login for someone on the SEO team.

    manage.py create_seo_user priya --email priya@agency.com

They get the dashboard with only the SEO screens, the page and blog text, and
nothing that touches orders, enquiries, products' prices or other users. The
password is generated and printed once, here; there is no way to read it back,
so hand it over straight away and ask them to change it.
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from seo.apps import GROUP_NAME, ensure_seo_group


class Command(BaseCommand):
    help = 'Create (or reset) a dashboard login for an SEO team member.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--email', default='')
        parser.add_argument('--first-name', default='')
        parser.add_argument('--password', default='',
                            help='Choose one yourself. Left out, a strong one is generated.')

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts['username'].strip()
        if not username:
            raise CommandError('Give a username.')
        ensure_seo_group(sender=None)
        group = Group.objects.get(name=GROUP_NAME)
        password = opts['password'] or ''.join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(14))
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = False      # never: they are limited to the group's screens
        if opts['email']:
            user.email = opts['email']
        if opts['first_name']:
            user.first_name = opts['first_name']
        user.set_password(password)
        user.save()
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(
            '%s %s (%s)' % ('Created' if created else 'Reset', username, GROUP_NAME)))
        self.stdout.write('Password: %s' % password)
        self.stdout.write('They can sign in at /admin/ and should change it straight away.')
