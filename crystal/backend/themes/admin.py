from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseModelFormSet
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from .models import FestivalTheme


class OneThemeOnFormSet(BaseModelFormSet):
    """The list's toggle column, saved in one go.

    Rows are saved one after another and each save switches the others off,
    so ticking two rows would quietly leave only the lower one on. Instead:
    the row you just switched on wins over the one that was already on (that
    is the toggle working), but switching on two rows in the same save is
    refused with a message, because there is no way to tell which you meant.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        switched_on = [
            f for f in self.forms
            if f.cleaned_data.get('is_active') and 'is_active' in f.changed_data
        ]
        if len(switched_on) > 1:
            names = ', '.join('"%s"' % f.instance.name for f in switched_on)
            raise ValidationError(
                'Only one festival theme can be on at a time — you switched on %s. '
                'Switch on just one and save again.' % names)


def _site_url():
    return (getattr(settings, 'PUBLIC_SITE_URL', '') or '').rstrip('/')


@admin.register(FestivalTheme)
class FestivalThemeAdmin(admin.ModelAdmin):
    change_list_template = 'admin/themes/festivaltheme/change_list.html'
    list_display = ('swatch', 'name', 'is_active', 'status', 'when', 'scope', 'effects', 'preview')
    list_display_links = ('name',)
    list_editable = ('is_active',)
    list_per_page = 100
    search_fields = ('name', 'slug', 'greeting')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('current_banner', 'preview_on_site', 'updated_at')
    actions = ['switch_off_selected']
    fieldsets = (
        ('Switch', {
            'description': (
                'Only <b>one</b> festival theme can be on at a time — switching this '
                'one on switches the others off. Changes reach the website within a '
                'couple of minutes.'
            ),
            'fields': ('is_active', 'scope', ('starts_on', 'ends_on'), 'preview_on_site'),
        }),
        ('What visitors read', {
            'description': (
                'The greeting sits in a slim festive ribbon at the top of every page, '
                'and on a greeting card in the Home page banner.'
            ),
            'fields': ('greeting', 'sub_text', ('link_text', 'link_url')),
        }),
        ('Look', {
            'fields': ('effects', 'accent', 'banner', 'current_banner'),
        }),
        ('Behind the scenes', {
            'classes': ('collapse',),
            'fields': ('name', 'slug', 'order', 'updated_at'),
        }),
    )

    class Media:
        css = {'all': ('themes/admin.css',)}
        js = ('themes/admin.js',)

    # -- one on at a time, from the list ------------------------------------

    def get_changelist_formset(self, request, **kwargs):
        kwargs['formset'] = OneThemeOnFormSet
        return super().get_changelist_formset(request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if 'is_active' in form.changed_data:
            if obj.is_active:
                note = ''
                if not obj.in_window():
                    note = ' It will show only between its first and last day.'
                messages.success(request, mark_safe(
                    '<b>%s</b> is now ON — every other theme was switched off. The '
                    'website shows it within a couple of minutes.%s'
                    % (obj.name, note)))
            elif not FestivalTheme.objects.filter(is_active=True).exists():
                messages.info(request, 'All festival themes are off — the website is back to normal.')

    # -- "Turn all off" ------------------------------------------------------

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path('all-off/', self.admin_site.admin_view(self.all_off_view),
                 name='%s_%s_all_off' % info),
        ] + super().get_urls()

    def all_off_view(self, request):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'])
        if not self.has_change_permission(request):
            messages.error(request, 'You do not have permission to change festival themes.')
        else:
            n = FestivalTheme.objects.filter(is_active=True).update(is_active=False)
            messages.success(
                request,
                'All festival themes are off — the website is back to normal.'
                if n else 'Nothing to do — every festival theme was already off.')
        return redirect(reverse('admin:themes_festivaltheme_changelist'))

    @admin.action(description='Switch off the selected themes')
    def switch_off_selected(self, request, queryset):
        n = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, '%d theme switched off.' % n if n == 1
                          else '%d themes switched off.' % n)

    def changelist_view(self, request, extra_context=None):
        extra = dict(extra_context or {})
        live = FestivalTheme.live()
        on = FestivalTheme.objects.filter(is_active=True).first()
        extra['theme_live'] = live
        extra['theme_on_waiting'] = on if (on and not live) else None
        return super().changelist_view(request, extra_context=extra)

    # -- columns -------------------------------------------------------------

    @admin.display(description='')
    def swatch(self, obj):
        return format_html(
            '<span class="ft-swatch" style="background:{}" title="{}"></span>',
            obj.display_accent, obj.display_accent)

    @admin.display(description='Status')
    def status(self, obj):
        if not obj.is_active:
            return mark_safe('<span class="ft-pill ft-off">Off</span>')
        today = timezone.localdate()
        if obj.starts_on and today < obj.starts_on:
            return format_html('<span class="ft-pill ft-wait">On — starts {}</span>',
                               obj.starts_on.strftime('%d %b'))
        if obj.ends_on and today > obj.ends_on:
            return format_html('<span class="ft-pill ft-wait">On — ended {}</span>',
                               obj.ends_on.strftime('%d %b'))
        return mark_safe('<span class="ft-pill ft-live">Live on the website</span>')

    @admin.display(description='Dates')
    def when(self, obj):
        if not (obj.starts_on or obj.ends_on):
            return mark_safe('<span style="color:#94a3b8;">any day</span>')
        a = obj.starts_on.strftime('%d %b %Y') if obj.starts_on else '…'
        b = obj.ends_on.strftime('%d %b %Y') if obj.ends_on else '…'
        return '%s → %s' % (a, b)

    def _preview_url(self, obj):
        return '%s/?theme=%s' % (_site_url(), obj.slug)

    @admin.display(description='')
    def preview(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" class="ft-preview" '
            'title="Opens the website in this theme for you only — nothing changes for '
            'visitors">Preview &#8599;</a>', self._preview_url(obj))

    @admin.display(description='Preview')
    def preview_on_site(self, obj):
        if not obj.pk:
            return 'Save first, then preview.'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" class="ft-preview">'
            'Open the website in this theme &#8599;</a>'
            '<div style="color:#64748b;font-size:12px;margin-top:4px;">Only you see it. '
            'Visitors keep seeing whatever is switched on. Add <code>?theme=off</code> '
            'to a page address to stop previewing.</div>', self._preview_url(obj))

    @admin.display(description='Picture now')
    def current_banner(self, obj):
        if not obj.banner:
            return 'None — the greeting card uses the festival\'s own decoration.'
        return format_html(
            '<img src="{}" style="max-height:140px;width:auto;border-radius:10px;'
            'border:1px solid #e2e8f0;">', obj.banner.url)
