from django.contrib import admin
from django.utils.html import format_html, mark_safe

from .models import Award, AwardSettings


@admin.register(AwardSettings)
class AwardSettingsAdmin(admin.ModelAdmin):
    """One row, so the list is pointless — go straight to editing it."""

    fieldsets = (
        ('How the strip moves', {
            'description': (
                'This is the <b>Awards &amp; Recognition</b> strip on the About '
                'page. It scrolls on its own and stops while a visitor is '
                'pointing at it or has just touched it, so they can read a '
                'certificate or click through to its PDF. Changes reach the site '
                'within a couple of minutes.'
            ),
            'fields': ('seconds_per_card', 'autoscroll', 'updated_at'),
        }),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        from django.urls import reverse
        obj = AwardSettings.load()
        return redirect(reverse('admin:awards_awardsettings_change', args=[obj.pk]))


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    """One row per certificate, in the order they appear on the page.

    The strip rotates itself, so there is nothing to lay out here — the only
    thing that decides where a certificate shows up is Order.
    """

    list_display = ('preview', 'what', 'pdf_link', 'order', 'is_active', 'updated_at')
    list_display_links = ('preview', 'what')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle', 'alt')
    readonly_fields = ('current_picture', 'updated_at')
    fieldsets = (
        ('The certificate', {
            'description': (
                'These are the cards in <b>Awards &amp; Recognition</b> on the '
                'About page. Add as many as you like — the strip scrolls itself '
                'and pauses when someone points at it. The change is live within '
                'a minute, with nothing to publish.'
            ),
            'fields': ('image', 'current_picture', 'alt'),
        }),
        ('Caption', {
            'description': 'Both optional. A certificate scan usually needs neither.',
            'fields': ('title', 'subtitle'),
        }),
        ('The full document', {
            'description': (
                'Attach the PDF and the card becomes clickable — visitors open '
                'the certificate in a new tab. Leave it empty and the card is '
                'just a picture.'
            ),
            'fields': ('pdf',),
        }),
        ('Placing', {
            'fields': ('order', 'is_active', 'image_path', 'updated_at'),
        }),
    )

    @admin.display(description='')
    def preview(self, obj):
        url = obj.picture_url()
        if not url:
            return mark_safe(
                '<span style="color:#94a3b8;font-size:11px;">no picture</span>'
            )
        return format_html(
            '<img src="{}" style="height:46px;width:auto;border-radius:6px;'
            'border:1px solid #e2e8f0;background:#fff;">', url,
        )

    @admin.display(description='Shown as')
    def what(self, obj):
        if obj.title:
            sub = (
                '<span style="display:block;color:#64748b;font-size:11px;">%s</span>'
                % obj.subtitle if obj.subtitle else ''
            )
            return mark_safe('<b>%s</b>%s' % (obj.title, sub))
        return mark_safe(
            '<span style="color:#64748b;font-size:12px;">%s</span>'
            % (obj.alt or 'Certificate, no caption')
        )

    @admin.display(description='PDF')
    def pdf_link(self, obj):
        if not obj.pdf:
            return mark_safe('<span style="color:#cbd5e1;">—</span>')
        return format_html(
            '<a href="{}" target="_blank" style="color:#ED3338;font-weight:600;'
            'font-size:12px;">\U0001F4C4 open</a>', obj.pdf.url,
        )

    @admin.display(description='Picture on the site now')
    def current_picture(self, obj):
        url = obj.picture_url()
        if not url:
            return 'Nothing uploaded yet.'
        return format_html(
            '<img src="{}" style="max-height:150px;width:auto;border-radius:10px;'
            'border:1px solid #e2e8f0;background:#fff;padding:6px;">', url,
        )
