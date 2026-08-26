"""Editing a banner is a visual job, so the form shows the result.

A percentage in a number box tells an admin nothing about where the pan ends
up. The change form therefore renders the real hero band -- same proportions,
same two scrims as the live CSS, the same crop maths -- and moves it live as the
sliders move. What you approve here is what the page shows.
"""
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import CategoryBanner

# Copied from the site's banner CSS. If those gradients change, change these
# too or the preview quietly starts lying.
SCRIM_H = ('linear-gradient(94deg,#fff 0%,rgba(255,255,255,.972) 32%,'
           'rgba(255,255,255,.885) 45%,rgba(255,255,255,.34) 63%,'
           'rgba(255,255,255,0) 78%)')
SCRIM_V = ('linear-gradient(to bottom,#fff 0%,rgba(255,255,255,.90) 14%,'
           'rgba(255,255,255,.46) 23%,rgba(255,255,255,0) 37%,'
           'rgba(255,255,255,0) 78%,#fff 100%)')


class CategoryBannerForm(forms.ModelForm):
    class Meta:
        model = CategoryBanner
        fields = '__all__'
        widgets = {
            'focus': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100,
                                              'step': 1, 'class': 'crystal-focus',
                                              'data-preview': 'desktop'}),
            'mobile_focus': forms.NumberInput(attrs={'type': 'range', 'min': 0, 'max': 100,
                                                     'step': 1, 'class': 'crystal-focus',
                                                     'data-preview': 'mobile'}),
        }

    def clean_page(self):
        page = (self.cleaned_data['page'] or '').strip()
        if not page.lower().endswith('.html'):
            page += '.html'
        return page

    def clean_image(self):
        img = self.cleaned_data.get('image')
        # Only validate a freshly uploaded file; an untouched existing one has
        # no readable dimensions here and must not be rejected on re-save.
        w = getattr(getattr(img, 'image', None), 'width', None)
        h = getattr(getattr(img, 'image', None), 'height', None)
        if w and h:
            if w < 1400:
                raise forms.ValidationError(
                    'This is only %dpx across. The banner is shown about 1265px '
                    'wide and only half the photo fits, so it needs to be at '
                    'least 1400px - ideally 1980px or more.' % w)
            if w / h < 3.0:
                raise forms.ValidationError(
                    'This is %.1f:1. A banner needs to be much wider than it is '
                    'tall - around 5:1. Anything squarer gets cropped so hard '
                    'that only a sliver of it is visible.' % (w / h))
        return img


@admin.register(CategoryBanner)
class CategoryBannerAdmin(admin.ModelAdmin):
    form = CategoryBannerForm
    list_display = ('thumb', 'page_cell', 'crop_cell', 'is_active', 'updated_at')
    list_display_links = ('thumb', 'page_cell')
    list_filter = ('is_active',)
    search_fields = ('page', 'label')
    readonly_fields = ('preview', 'updated_at')
    fields = ('preview', 'page', 'label', 'image', 'focus', 'mobile_focus',
              'is_active', 'updated_at')

    class Media:
        css = {'all': ('admin/crystal_banners.css',)}
        js = ('admin/crystal_banners.js',)

    @admin.display(description='')
    def thumb(self, obj):
        if not obj.image:
            return '—'
        return format_html(
            '<span class="cb-thumb" style="background-image:url({});'
            'background-position:{}% center"></span>', obj.image.url, obj.focus)

    @admin.display(description='Page', ordering='page')
    def page_cell(self, obj):
        return format_html('<strong>{}</strong><br><span class="cb-sub">{}</span>',
                           obj.label or obj.page, obj.page)

    @admin.display(description='Crop')
    def crop_cell(self, obj):
        return format_html('<span class="cb-sub">computer {}% · phone {}%</span>',
                           obj.focus, obj.mobile_focus)

    @admin.display(description='How it will look')
    def preview(self, obj):
        """The live hero band. Rendered even on the add form, where it starts
        empty and fills in as soon as a file is chosen."""
        url = obj.image.url if getattr(obj, 'image', None) else ''
        return mark_safe(
            '<div class="cb-preview" data-scrim-h="%s" data-scrim-v="%s">'
            '  <div class="cb-stage cb-desktop">'
            '    <div class="cb-shot" style="background-image:url(%s);'
            'background-position:%s%% center"></div>'
            '    <div class="cb-scrim"></div>'
            '    <div class="cb-copy">'
            '      <span class="cb-eyebrow">Category · Sub-category</span>'
            '      <span class="cb-head">Your heading sits here</span>'
            '      <span class="cb-body">And the sentence underneath it runs to about '
            'this length before it wraps.</span>'
            '      <span class="cb-btns"><i></i><i class="dark"></i></span>'
            '    </div>'
            '    <span class="cb-tag">On a computer</span>'
            '  </div>'
            '  <div class="cb-stage cb-mobile">'
            '    <div class="cb-shot" style="background-image:url(%s);'
            'background-position:%s%% center"></div>'
            '    <span class="cb-tag">On a phone</span>'
            '  </div>'
            '  <p class="cb-hint">Drag the two sliders below. Only about half the '
            'photograph fits on screen, so this slides which half you keep - lower '
            'moves the product right, higher moves it left. Keep the left side of '
            'the band clear, because the heading goes there.</p>'
            '</div>' % (SCRIM_H, SCRIM_V, url, obj.focus if obj.pk else 74,
                        url, obj.mobile_focus if obj.pk else 82)
        )
