from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import GiftingSettings, GiftRange, GiftSet, GiftSetModel


def picture_src(obj):
    """Where the admin page itself can load the picture from.

    An upload is on this service. A shipped picture is a path inside the website:
    when the site's files sit alongside the dashboard (the VPS, and a local checkout)
    it is served from here under /media/, which is why it always shows; otherwise it
    is addressed on the public site."""
    url = obj.picture()
    if not url or url.startswith(('http://', 'https://', '/')):
        return url
    if (Path(settings.MEDIA_ROOT) / url).is_file():
        return settings.MEDIA_URL.rstrip('/') + '/' + url.lstrip('/')
    return '%s/%s' % (settings.PUBLIC_SITE_URL.rstrip('/'), url.lstrip('/'))



@admin.register(GiftingSettings)
class GiftingSettingsAdmin(admin.ModelAdmin):
    """One row, so the list is pointless: go straight to editing it."""

    fieldsets = (
        ('Top of the page', {
            'description': (
                'The words in the banner at the top of the <b>Gifting</b> page. The banner '
                '<b>picture</b> is changed in <b>Category banners</b> (page: Gifting.html). '
                'Changes reach the site within a minute or two, with nothing to publish.'),
            'fields': ('hero_pretext', 'hero_title', 'hero_lead', 'hero_points'),
        }),
        ('Above the gift sets', {'fields': ('browse_title', 'browse_lead')}),
        ('Bottom banner', {'fields': ('cta_title', 'cta_text')}),
        ('Prices', {'fields': ('show_mrp',)}),
        (None, {'fields': ('updated_at',)}),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = GiftingSettings.load()
        return redirect(reverse('admin:gifting_giftingsettings_change', args=[obj.pk]))


@admin.register(GiftRange)
class GiftRangeAdmin(admin.ModelAdmin):
    """The filter buttons above the gift sets."""

    list_display = ('label', 'set_count', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_n=Count('sets'))

    @admin.display(description='Gift sets', ordering='_n')
    def set_count(self, obj):
        return obj._n


class GiftSetModelInline(admin.TabularInline):
    model = GiftSetModel
    extra = 0
    fields = ('code', 'name', 'outer_pack', 'mrp', 'order')
    verbose_name = 'Model in this combo'
    verbose_name_plural = (
        'Models in this combo (optional: list each code of a combo here, with its own '
        'pack and MRP. A single set needs none.)')


@admin.register(GiftSet)
class GiftSetAdmin(admin.ModelAdmin):
    """One row per card on the Gifting page."""

    list_display = ('thumb', 'name', 'codes_cell', 'gift_range', 'order', 'is_active', 'updated_at')
    list_display_links = ('thumb', 'name')
    list_editable = ('order', 'is_active')
    list_filter = ('gift_range', 'is_active')
    search_fields = ('name', 'sku', 'models_in_set__code')
    list_select_related = ('gift_range',)
    readonly_fields = ('current_picture', 'updated_at')
    inlines = [GiftSetModelInline]
    actions = ['show_on_page', 'hide_from_page']
    fieldsets = (
        ('The gift set', {
            'description': (
                'One card on the <b>Gifting</b> page. Changes reach the site within a minute or two, '
                'with nothing to publish. Visitors tap <b>Enquire</b> on a card and it goes into their '
                'enquiry list, like any other product.'),
            'fields': ('name', 'gift_range', 'sku', 'features'),
        }),
        ('Picture', {
            'description': 'For a combo, put the whole set and its gift box together in one picture.',
            'fields': ('image', 'current_picture', 'image_path'),
        }),
        ('Pack and price', {'fields': ('outer_pack', 'mrp')}),
        ('Placing', {'fields': ('order', 'is_active', 'updated_at')}),
    )

    @admin.display(description='')
    def thumb(self, obj):
        url = picture_src(obj)
        if not url:
            return mark_safe('<span style="color:#94a3b8;font-size:11px;">no picture</span>')
        return format_html(
            '<img src="{}" style="height:52px;width:52px;object-fit:contain;border-radius:8px;'
            'border:1px solid #e2e8f0;background:#fff;">', url)

    @admin.display(description='Code(s)')
    def codes_cell(self, obj):
        return obj.codes or '—'

    @admin.display(description='Picture on the page now')
    def current_picture(self, obj):
        url = picture_src(obj)
        if not url:
            return 'Nothing yet. Upload a picture above.'
        return format_html(
            '<img src="{}" style="max-height:220px;width:auto;border-radius:10px;'
            'border:1px solid #e2e8f0;background:#fff;padding:6px;">', url)

    @admin.action(description='Show the selected gift sets on the page')
    def show_on_page(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, '%d gift set(s) shown.' % n)

    @admin.action(description='Hide the selected gift sets from the page')
    def hide_from_page(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, '%d gift set(s) hidden.' % n)
