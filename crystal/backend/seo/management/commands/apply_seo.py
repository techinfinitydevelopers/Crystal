"""Write the dashboard's SEO into the website's files.

    manage.py apply_seo                 everything
    manage.py apply_seo --pages-only    just the static pages (fast)

The deploy runs this after pulling, because `git reset --hard` puts every page
back to what is committed and the database is the source of truth for the rest.
"""
from django.core.management.base import BaseCommand

from seo import pipeline


class Command(BaseCommand):
    help = 'Write titles, descriptions, tracking code, product pages and the sitemap into the site.'

    def add_arguments(self, parser):
        parser.add_argument('--pages-only', action='store_true',
                            help='Only the static pages, not product or blog pages.')
        parser.add_argument('--no-products', action='store_true')
        parser.add_argument('--no-blog', action='store_true')

    def handle(self, *args, **opts):
        if opts['pages_only']:
            report = pipeline.bake_pages_only()
        else:
            report = pipeline.bake_all(include_products=not opts['no_products'],
                                       include_blog=not opts['no_blog'])
        for note in report.notes:
            self.stdout.write(note)
        for skipped in report.skipped[:25]:
            self.stderr.write('skipped: %s' % skipped)
        self.stdout.write(self.style.SUCCESS('SEO: %s' % report))
