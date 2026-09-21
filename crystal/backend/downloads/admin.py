from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_filter = ['brand', 'category', 'is_active']
    list_select_related = ['brand']
    readonly_fields = ['live_status']
    fieldsets = (
        ('File Details', {
            'fields': ('title', 'brand', 'category', 'description'),
            'description': (
                'Upload the catalogue here and the website picks it up on its own — '
                'no deploy needed. Set <b>Category</b> to <b>Catalogue</b>: that is what '
                'the Catalogue page reads. Leave <b>Brand</b> blank for the general '
                'catalogue behind the <b>Download PDF</b> button, or pick a brand to fill '
                'that brand’s card lower down the page.'
            ),
        }),
        ('Upload', {
            'fields': ('file', 'thumbnail'),
            'description': (
                'PDF only, up to 80 MB. The <b>newest</b> active catalogue wins, so '
                'uploading a new edition is enough — there is nothing to delete or '
                'reorder. Each brand is counted separately, so a new general '
                'catalogue never displaces a brand one.'
            ),
        }),
        ('Visibility', {
            'fields': ('is_active', 'live_status'),
        }),
    )

    def get_list_display(self, request):
        """Say plainly which row the website is serving right now.

        Newest-active-wins is easy to implement and impossible to see, so the
        rule gets spelled out on the row instead of living only in the docs.
        Resolved once per request and closed over, rather than re-queried per
        row or cached on the admin singleton, which is shared across threads.
        """
        live_pks = Download.live_catalogue_pks()

        @admin.display(description='On the website')
        def live_badge(obj):
            if obj.pk in live_pks:
                return mark_safe(
                    '<span style="background:#16a34a;color:#fff;padding:3px 10px;'
                    'border-radius:100px;font-size:11px;font-weight:700;">LIVE NOW</span>'
                )
            if obj.category != 'catalogue':
                return '—'
            if not obj.is_active:
                return mark_safe('<span style="color:#94a3b8;font-size:11px;">retired</span>')
            return mark_safe('<span style="color:#94a3b8;font-size:11px;">superseded</span>')

        return ['title', live_badge, 'brand_badge', 'category',
                'file_link', 'thumbnail_preview', 'is_active', 'created_at']

    @admin.display(description='Status')
    def live_status(self, obj):
        """The same answer on the change form, where someone edits one file."""
        if obj.pk is None:
            return 'Save this download to see whether the website will serve it.'
        if obj.category != 'catalogue':
            return 'Not a catalogue, so the Catalogue page ignores it.'

        audience = obj.brand.slug if obj.brand else None
        where = f'the {obj.brand.name} card' if obj.brand else 'the Download PDF button'
        live = Download.live_catalogue(audience)

        if live and live.pk == obj.pk:
            return format_html(
                '<b style="color:#16a34a;">Live on the website</b> — this is what {} serves.',
                where,
            )
        if not obj.is_active:
            return 'Inactive — the website skips it.'
        if live:
            return format_html(
                'Superseded by "{}" (uploaded {}), which {} serves instead.',
                live.title, live.created_at.strftime('%d %b %Y'), where,
            )
        return 'No file on this record yet.'

    @admin.display(description='Brand')
    def brand_badge(self, obj):
        if not obj.brand:
            return mark_safe(
                '<span style="background:#f1f5f9;padding:3px 10px;border-radius:100px;'
                'font-size:11px;font-weight:600;color:#64748b;">All Brands</span>'
            )
        colors = {
            'crystal': '#ED3338', 'crystalina': '#7c3aed',
            'sparkmate': '#0ea5e9', 'valmate': '#059669',
        }
        bg = colors.get(obj.brand.slug, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, obj.brand.name,
        )

    @admin.display(description='File')
    def file_link(self, obj):
        if not obj.file:
            return '—'
        try:
            size = f' ({obj.file.size / 1048576:.1f} MB)'
        except (OSError, ValueError):
            size = ''  # the row outlived its file
        return format_html(
            '<a href="{}" target="_blank" style="color:#ED3338;font-weight:600;font-size:12px;">'
            '📄 {}</a><span style="color:#94a3b8;font-size:11px;">{}</span>',
            obj.file.url,
            obj.file.name.split('/')[-1],
            size,
        )

    @admin.display(description='Thumbnail')
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:36px;width:auto;border-radius:6px;">',
                obj.thumbnail.url,
            )
        return '—'
