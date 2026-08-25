r"""
Collapse each `variant_group` of sibling Products into ONE parent Product that
owns N real ProductVariant rows.

Why
---
product-data/products.json is flattened: every SIZE of a product is its own
entry, tied to its siblings only by a shared `variant_group` string. The import
mirrored that shape, so the dashboard holds 95 Products across 29 groups, each
carrying a single decorative ProductVariant and no per-variant images at all.
Editing "the kadai" therefore means editing eight rows.

After this command a group is one Product with eight ProductVariant rows, each
variant owning its own SKU, name, price, Amazon link, video, features, images
and specification rows. products/serializers.py already resolves every one of
those from the variant first and the product second, and emits one catalogue
entry per variant - so the exported catalogue is unchanged, entry for entry.

Parent selection
----------------
Within a group, the member whose existing ProductVariant.order is lowest, ties
broken by Product.id. That is the entry products.json gave variant_order 0 -
the size the site shows by default and the SKU its listing cards link to.
Deterministic, so a re-run picks the same parent.

Sibling disposal
----------------
Deactivate, never delete: is_active=False and variant_group cleared (so a
re-run cannot re-pick them as members). export_to_json already filters on
is_active, so deactivation removes them from the export for free - and putting
is_active back is the rollback.

Usage
-----
    python manage.py collapse_variant_groups --dry-run --group vg-09
    python manage.py collapse_variant_groups --group vg-09 --i-have-a-backup
    python manage.py collapse_variant_groups --i-have-a-backup \
        --snapshot /tmp/before-entries.json
"""
import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import (
    Product,
    ProductImage,
    ProductMarketplaceLink,
    ProductSpecification,
    ProductVariant,
)
from products.serializers import site_amazon_link, site_product_entries


class GroupRefused(Exception):
    """A group cannot be collapsed without changing what the site would show."""


def _resolved_highlight(product):
    """Exactly what serializers._resolve() emits for this row today."""
    return (product.highlight or product.short_description or "")[:300]


def _resolved_description(product):
    return product.overview or product.short_description or ""


def _resolved_match_tier(product):
    return (
        product.match_tier
        or ("dashboard_admin" if product.is_dashboard_managed else "imported")
    )


class Command(BaseCommand):
    help = (
        "Fold each variant_group of sibling Products into one parent Product "
        "holding real ProductVariant rows (images and specs re-pointed, "
        "siblings deactivated)."
    )

    # ---------------------------------------------------------------- args

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Do the whole run inside a rolled-back transaction and write nothing.",
        )
        parser.add_argument(
            "--group", dest="group", default=None,
            help="Collapse only this variant_group (e.g. vg-09). Default: all groups.",
        )
        parser.add_argument(
            "--snapshot", dest="snapshot", default=None,
            help="Before doing anything, dump the current catalogue entries to "
                 "this path as {sku: entry}. Cheap insurance for diffing after.",
        )
        parser.add_argument(
            "--i-have-a-backup", action="store_true",
            help="Required for a real (non --dry-run) run. This rewrites product "
                 "rows in place; take a copy of db.sqlite3 first.",
        )
        parser.add_argument(
            "--force-hero-fallback", action="store_true",
            help="Collapse a group even when a member owns no ProductImage rows "
                 "and its image_url differs from the parent's - i.e. even though "
                 "that size's hero photo WILL change in the export. Off by default.",
        )

    # -------------------------------------------------------------- handle

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if not dry_run and not options["i_have_a_backup"]:
            raise CommandError(
                "Refusing to run: pass --i-have-a-backup once you have copied "
                "backend/db.sqlite3 somewhere safe, or use --dry-run."
            )

        if options["snapshot"]:
            self._write_snapshot(Path(options["snapshot"]))

        members_by_group = defaultdict(list)
        qs = (
            Product.objects.filter(is_active=True)
            .exclude(variant_group="")
            .select_related("brand", "category")
            .prefetch_related("variants", "images", "specifications",
                              "marketplace_links__marketplace")
        )
        if options["group"]:
            qs = qs.filter(variant_group=options["group"])
        for product in qs:
            members_by_group[product.variant_group].append(product)

        if options["group"] and not members_by_group:
            raise CommandError(
                f"No active products carry variant_group={options['group']!r}. "
                "(Already collapsed groups keep only the parent, which still "
                "carries the group id - so an empty result means the id is wrong.)"
            )

        stats = defaultdict(int)
        refused, skipped, touched = [], [], []

        with transaction.atomic():
            for group in sorted(members_by_group):
                members = members_by_group[group]
                stats_before = dict(stats)
                try:
                    # Its own savepoint: a group refused half-way through (a SKU
                    # clash only visible on the third member, say) must leave
                    # nothing behind, while the groups around it still stand.
                    with transaction.atomic():
                        changed = self._collapse_group(
                            group, members, stats,
                            force_hero_fallback=options["force_hero_fallback"],
                        )
                except GroupRefused as exc:
                    stats.clear()
                    stats.update(stats_before)  # the savepoint undid the writes
                    refused.append((group, str(exc)))
                    stats["groups_refused"] += 1
                    continue
                if changed is None:
                    skipped.append(group)
                    stats["groups_already_collapsed"] += 1
                else:
                    touched.append(group)
                    stats["groups_collapsed"] += 1

            if dry_run:
                transaction.set_rollback(True)

        self._report(stats, touched, skipped, refused, dry_run)

        if refused:
            raise CommandError(
                f"{len(refused)} group(s) were REFUSED and left untouched - see above. "
                "Nothing about them was changed; the rest of the run stands."
                if not dry_run else
                f"{len(refused)} group(s) would be REFUSED - see above."
            )

    # ------------------------------------------------------------ snapshot

    def _write_snapshot(self, path):
        products = (
            Product.objects.filter(is_active=True)
            .select_related("brand", "category__parent")
            .prefetch_related("specifications", "images", "variants",
                              "marketplace_links__marketplace")
            .order_by("id")
        )
        snapshot = {}
        for product in products:
            for entry in site_product_entries(product):
                snapshot[entry["sku"]] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2, ensure_ascii=False, default=str)
        self.stdout.write(f"Snapshot: {len(snapshot)} entries -> {path}")

    # --------------------------------------------------------- one group

    def _collapse_group(self, group, members, stats, force_hero_fallback=False):
        """Returns None when the group was already collapsed, else the parent."""
        members = self._ordered_members(group, members)
        parent = members[0]

        if len(members) == 1 and parent.variants.filter(sku=parent.sku).exists():
            return None  # a previous run already did this one

        self._preflight(group, members, parent, force_hero_fallback)

        for member in members:
            label = self._label_of(member)
            variant = self._upsert_variant(parent, member, label, stats)
            if member.pk == parent.pk:
                # The parent's own rows come across with variant=NULL. They MUST
                # be claimed by its own variant: once the parent owns eight
                # sizes' photos, a variant=NULL image becomes the fallback for
                # every size, so a size with no photo of its own would silently
                # show a different size's picture.
                stats["images_repointed"] += ProductImage.objects.filter(
                    product=parent, variant__isnull=True).update(variant=variant)
                stats["specs_repointed"] += ProductSpecification.objects.filter(
                    product=parent, variant__isnull=True).update(variant=variant)
                continue
            self._absorb_member(parent, member, variant, stats)

        # Every entry now comes from a variant, and each variant carries its own
        # link/video verbatim - so these product-level values are pure fallback.
        # They must be cleared, or a size that legitimately has no Amazon link
        # or no video would inherit the parent's. (vg-24 has one size without a
        # link; seven groups have a video on the parent but not on every size.)
        blanked = []
        if parent.amazon_link:
            parent.amazon_link = ""
            blanked.append("amazon_link")
        if parent.video_url:
            parent.video_url = ""
            blanked.append("video_url")
        if parent.video:
            parent.video = None
            blanked.append("video")
        if blanked:
            parent.save(update_fields=blanked)
            stats["parent_fallbacks_cleared"] += len(blanked)

        return parent

    # ------------------------------------------------------------ helpers

    def _ordered_members(self, group, members):
        """Lowest existing ProductVariant.order first, ties broken by Product.id."""
        def key(product):
            orders = [v.order for v in product.variants.all()]
            return (min(orders) if orders else 0, product.id)
        return sorted(members, key=key)

    def _label_of(self, product):
        """The size label for this member: its existing decorative variant's name."""
        variants = list(product.variants.all())
        if not variants:
            raise GroupRefused(
                f"{product.sku or product.pk} has no ProductVariant, so its size "
                "label is unknown. Give it one (the label products.json used in "
                "variant_label) and re-run."
            )
        return min(variants, key=lambda v: (v.order, v.id)).name

    def _preflight(self, group, members, parent, force_hero_fallback):
        """Refuse anything that would change what the site shows."""
        for member in members:
            if not member.sku:
                raise GroupRefused(
                    f"product #{member.pk} has no SKU; the collapsed variant is "
                    "identified by it."
                )

        labels = [self._label_of(m) for m in members]
        if len(set(labels)) != len(labels):
            raise GroupRefused(
                "two members share a size label "
                f"({', '.join(sorted(labels))}); ProductVariant is unique per "
                "(product, name), so they cannot live on one parent."
            )

        skus = [m.sku for m in members]
        clash = (
            ProductVariant.objects.filter(sku__in=skus)
            .exclude(product=parent)
            .exclude(product__in=[m.pk for m in members])
            .values_list("sku", flat=True)
        )
        if clash:
            raise GroupRefused(
                "ProductVariant.sku is unique and already taken elsewhere for: "
                + ", ".join(sorted(clash))
            )

        if force_hero_fallback:
            return
        # A member with no photos of its own currently exports hero=its OWN
        # image_url. Collapsed, the fallback becomes the PARENT's image_url,
        # because ProductVariant has nowhere to keep a per-size image_url. When
        # the two differ that silently swaps the photo, so refuse.
        bad = [
            m.sku for m in members
            if not m.images.all()
            and (m.image_url or "") != (parent.image_url or "")
        ]
        if bad:
            raise GroupRefused(
                f"{', '.join(bad)} own no ProductImage rows and their image_url "
                f"differs from the parent's ({parent.sku}). Collapsing would make "
                "them fall back to the parent's hero photo - a different product "
                "picture. Fix: give those sizes real ProductImage rows, or add a "
                "per-variant image_url. Pass --force-hero-fallback to accept the "
                "change anyway."
            )

    def _desired_variant_fields(self, member, label):
        """Everything the exporter reads, resolved from the member as it stands
        today, so the collapsed parent reproduces this member's entry exactly."""
        order = min((v.order for v in member.variants.all()), default=0)
        return {
            # The imported SKUs are unrelated strings (LI007/LI008/LI009), so
            # nothing can be rebuilt by concatenating a suffix.
            "sku": member.sku,
            "display_name": member.name,
            "highlight": _resolved_highlight(member),
            "description": _resolved_description(member),
            # A list (not None) so the parent's tags/features never leak in.
            "tags": list(member.tags or []),
            "features": list(member.features or []),
            "amazon_link": site_amazon_link(member, None) or "",
            "price": member.price,
            "video_url": member.video_url or "",
            "match_tier": _resolved_match_tier(member)[:64],
            "order": order,
            "is_default": order == 0,
            "is_active": True,
            "name": label,
        }

    def _upsert_variant(self, parent, member, label, stats):
        """Idempotent: ProductVariant.sku is unique, so a previous run's row is
        found by it rather than duplicated."""
        variant = ProductVariant.objects.filter(sku=member.sku).first()
        if variant is None and member.pk == parent.pk:
            # The parent's own decorative variant (sku still NULL) - reuse it,
            # or the unique (product, name) constraint would reject a second row.
            variant = parent.variants.filter(name=label).first()
        if variant is not None and variant.product_id != parent.pk:
            raise GroupRefused(
                f"variant sku={member.sku} already hangs off product "
                f"#{variant.product_id}, not the parent #{parent.pk}."
            )

        desired = self._desired_variant_fields(member, label)
        video_name = member.video.name if member.video else ""

        if variant is None:
            variant = ProductVariant.objects.create(
                product=parent, sku_suffix="", video=video_name or None, **desired)
            stats["variants_created"] += 1
            return variant

        changed = [f for f, v in desired.items() if getattr(variant, f) != v]
        if (variant.video.name or "") != video_name:
            variant.video = video_name or None
            changed.append("video")
        if changed:
            for field, value in desired.items():
                setattr(variant, field, value)
            variant.save(update_fields=sorted(set(changed)))
            stats["variants_updated"] += 1
        else:
            stats["variants_unchanged"] += 1
        return variant

    def _absorb_member(self, parent, member, variant, stats):
        # enquiry.EnquiryItem.product is SET_NULL - re-point BEFORE touching the
        # member, so no historical enquiry loses its product.
        from enquiry.models import EnquiryItem
        stats["enquiry_items_repointed"] += EnquiryItem.objects.filter(
            product=member).update(product=parent)

        stats["images_repointed"] += ProductImage.objects.filter(
            product=member).update(product=parent, variant=variant)
        stats["specs_repointed"] += ProductSpecification.objects.filter(
            product=member).update(product=parent, variant=variant)

        # ProductMarketplaceLink is unique_together (product, marketplace), so
        # re-pointing collides whenever the parent already has that marketplace.
        # The Amazon URL is already on the variant, so the duplicate is dropped.
        taken = set(
            ProductMarketplaceLink.objects.filter(product=parent)
            .values_list("marketplace_id", flat=True)
        )
        for link in ProductMarketplaceLink.objects.filter(product=member):
            if link.marketplace_id in taken:
                link.delete()
                stats["marketplace_links_dropped"] += 1
            else:
                link.product = parent
                link.save(update_fields=["product"])
                taken.add(link.marketplace_id)
                stats["marketplace_links_repointed"] += 1

        # Deactivate, never delete. variant_group is cleared so a re-run cannot
        # re-pick this row as a member of the group.
        member.is_active = False
        member.variant_group = ""
        member.save(update_fields=["is_active", "variant_group"])
        stats["members_deactivated"] += 1

    # -------------------------------------------------------------- report

    def _report(self, stats, touched, skipped, refused, dry_run):
        head = "DRY RUN - nothing was written" if dry_run else "Collapse complete"
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{head}"))
        for key in (
            "groups_collapsed", "groups_already_collapsed", "groups_refused",
            "variants_created", "variants_updated", "variants_unchanged",
            "images_repointed", "specs_repointed",
            "marketplace_links_repointed", "marketplace_links_dropped",
            "enquiry_items_repointed", "parent_fallbacks_cleared",
            "members_deactivated",
        ):
            self.stdout.write(f"  {key:<28}: {stats[key]}")
        if touched:
            self.stdout.write("\n  Collapsed: " + ", ".join(touched))
        if skipped:
            self.stdout.write("  Already collapsed (no-op): " + ", ".join(skipped))
        if refused:
            self.stdout.write(self.style.ERROR("\n  REFUSED (left exactly as they were):"))
            for group, reason in refused:
                self.stdout.write(self.style.ERROR(f"    - {group}: {reason}"))
