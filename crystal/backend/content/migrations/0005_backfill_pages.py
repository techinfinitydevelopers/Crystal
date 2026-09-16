"""Create a Page row for every page in pages_registry, and point every
existing PageSection at its Page.

Idempotent: matches on filename, so re-running (or running again after
someone adds a page to the registry and redeploys) only fills in what is
missing. Reverse just detaches the sections and removes the rows it made -
nothing about a section's own content is touched either way.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Page = apps.get_model('content', 'Page')
    PageSection = apps.get_model('content', 'PageSection')
    from content.pages_registry import PAGES_REGISTRY

    order = 0
    for group, pages in PAGES_REGISTRY:
        for filename, label in pages:
            order += 1
            page, _ = Page.objects.get_or_create(
                filename=filename,
                defaults={'title': label, 'group': group, 'order': order},
            )
            PageSection.objects.filter(page=filename, page_ref__isnull=True).update(page_ref=page)


def backwards(apps, schema_editor):
    Page = apps.get_model('content', 'Page')
    PageSection = apps.get_model('content', 'PageSection')
    PageSection.objects.update(page_ref=None)
    Page.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0004_page_pagesection_image_mobile_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
