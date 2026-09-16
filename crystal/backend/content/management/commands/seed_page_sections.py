"""Fill the dashboard's page-section list from the site's data-cms manifest.

`tools/cms_tag.py` marks every editable heading, paragraph and image on the
site with a `data-cms` key and writes what it marked to
`tools/cms-manifest.json`. This turns that into rows someone can actually edit.

Rows are created **empty**: the feed skips a section with no value, so seeding
publishes nothing and every page goes on showing exactly what it ships. The row
exists so the section is listed, labelled, and one edit away from being live.

Run against production the same way the catalogue sync is: this service is
deployed from `crystal/backend`, so the manifest two levels up is not in its
container and has to come over HTTP from the website service.

    python manage.py seed_page_sections                 # fetch from the site
    python manage.py seed_page_sections --file ../../tools/cms-manifest.json
    python manage.py seed_page_sections --dry-run
"""
import json
import os
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Page, PageSection
from content.pages_registry import ALL_PAGES, PAGES_REGISTRY

DEFAULT_URL = os.environ.get(
    "CMS_MANIFEST_URL",
    "https://crystal-cook-production.up.railway.app/tools/cms-manifest.json",
)

# The manifest covers the whole site; a run that suddenly describes a handful
# of sections means a truncated or wrong file, and acting on it would retire
# most of the list. Same guard as sync_catalogue's.
MIN_ROWS = 200


class Command(BaseCommand):
    help = "Create a page-section row for every data-cms key on the site."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=DEFAULT_URL)
        parser.add_argument("--file")
        parser.add_argument("--timeout", type=int, default=30)
        parser.add_argument("--allow-small", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        pages_created, pages_updated = self._sync_pages(opts["dry_run"])
        rows = self._load(opts)

        if not isinstance(rows, list):
            raise CommandError("The manifest is not a list of sections.")
        if len(rows) < MIN_ROWS and not opts["allow_small"]:
            raise CommandError(
                "Only %d sections in the manifest; expected at least %d. "
                "Pass --allow-small if that is really right."
                % (len(rows), MIN_ROWS)
            )

        known = set(ALL_PAGES)
        created = updated = skipped = 0

        with transaction.atomic():
            for row in rows:
                page = (row.get("page") or "").strip()
                key = (row.get("section_key") or row.get("key") or "").strip()
                if not page or not key:
                    skipped += 1
                    continue
                if page not in known:
                    # Not offered by the dashboard's page picker, so a row here
                    # would be unreachable.
                    skipped += 1
                    continue

                defaults = {
                    "kind": PageSection.IMAGE if row.get("kind") == "image" else PageSection.TEXT,
                    "label": (row.get("label") or "")[:160],
                    "section": (row.get("section") or "")[:120],
                    "shipped_value": row.get("shipped") or "",
                }

                existing = PageSection.objects.filter(page=page, section_key=key).first()
                if existing is None:
                    if not opts["dry_run"]:
                        PageSection.objects.create(page=page, section_key=key, **defaults)
                    created += 1
                    continue

                # Never touch what someone typed — only the reference columns.
                changes = {
                    f: v for f, v in defaults.items()
                    if getattr(existing, f) != v and f != "kind"
                }
                if changes:
                    if not opts["dry_run"]:
                        for f, v in changes.items():
                            setattr(existing, f, v)
                        existing.save(update_fields=list(changes))
                    updated += 1

        self.stdout.write(
            "Pages: %d new, %d refreshed | sections in manifest: %d | "
            "created: %d | refreshed: %d | skipped: %d"
            % (pages_created, pages_updated, len(rows), created, updated, skipped)
        )
        self.stdout.write("Total rows now: %d" % PageSection.objects.count())
        if opts["dry_run"]:
            self.stdout.write("(dry run — nothing written)")

    def _sync_pages(self, dry_run):
        """Make sure every page in pages_registry has a Page row, with the
        title, group and order the registry currently says.

        Runs before the manifest import so a page that only just appeared in
        the registry already has somewhere for its sections to attach to.
        Never deletes: a page removed from the registry keeps its row and its
        sections, just unreachable from the picker until it is added back.
        """
        created = updated = 0
        order = 0
        for group, pages in PAGES_REGISTRY:
            for filename, label in pages:
                order += 1
                defaults = {"title": label, "group": group, "order": order}
                existing = Page.objects.filter(filename=filename).first()
                if existing is None:
                    if not dry_run:
                        Page.objects.create(filename=filename, **defaults)
                    created += 1
                    continue
                changes = {f: v for f, v in defaults.items() if getattr(existing, f) != v}
                if changes:
                    if not dry_run:
                        for f, v in changes.items():
                            setattr(existing, f, v)
                        existing.save(update_fields=list(changes))
                    updated += 1
        return created, updated

    def _load(self, opts):
        if opts["file"]:
            with open(opts["file"], encoding="utf-8") as fh:
                return json.load(fh)
        url = opts["url"]
        try:
            with urllib.request.urlopen(url, timeout=opts["timeout"]) as resp:
                raw = resp.read()
        except Exception as exc:
            raise CommandError("Could not fetch %s: %s" % (url, exc))
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise CommandError(
                "%s did not return JSON — the site probably served an HTML "
                "error page." % url
            )
