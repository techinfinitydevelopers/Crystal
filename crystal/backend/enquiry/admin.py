from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import Enquiry, EnquiryItem, WebsiteMessage

STATUS_COLORS = {
    'new':             ('#3b82f6', '#fff'),
    'contacted':       ('#f59e0b', '#1a1a1a'),
    'in_discussion':   ('#8b5cf6', '#fff'),
    'quotation_sent':  ('#0ea5e9', '#fff'),
    'converted':       ('#10b981', '#fff'),
    'closed':          ('#64748b', '#fff'),
}

BTYPE_COLORS = {
    'dealer':      ('#ed3338', '#fff'),
    'distributor': ('#7c3aed', '#fff'),
    'retailer':    ('#0ea5e9', '#fff'),
    'customer':    ('#10b981', '#fff'),
    'other':       ('#64748b', '#fff'),
}


class EnquiryItemInline(admin.TabularInline):
    model = EnquiryItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_sku', 'brand', 'category', 'quantity', 'site_id']
    can_delete = False
    fields = ['product_name', 'product_sku', 'brand', 'category', 'quantity', 'site_id', 'product']
    verbose_name = 'Enquiry Item'
    verbose_name_plural = 'Items in this Enquiry'


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display  = [
        'ref_number', 'full_name', 'email', 'phone',
        'btype_badge', 'location', 'status_badge', 'item_count', 'created_at'
    ]
    search_fields = ['ref_number', 'full_name', 'email', 'phone', 'company_name', 'city', 'state']
    list_filter   = ['status', 'business_type', 'country', 'created_at']
    readonly_fields = ['ref_number', 'created_at']
    ordering = ['-created_at']
    inlines = [EnquiryItemInline]
    list_per_page = 25

    fieldsets = (
        ('Reference', {
            'fields': ('ref_number', 'status'),
        }),
        ('Contact Details', {
            'fields': (('full_name', 'company_name'), ('email', 'phone'), 'business_type'),
        }),
        ('Location', {
            'fields': (('city', 'state', 'country'),),
        }),
        ('Message', {
            'fields': ('message', 'source_page'),
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        bg, fg = STATUS_COLORS.get(obj.status, ('#64748b', '#fff'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Type')
    def btype_badge(self, obj):
        bg, fg = BTYPE_COLORS.get(obj.business_type, ('#64748b', '#fff'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;">{}</span>',
            bg, fg, obj.get_business_type_display(),
        )

    @admin.display(description='Location')
    def location(self, obj):
        parts = [p for p in [obj.city, obj.state] if p]
        if not parts:
            return '—'
        return format_html(
            '<span style="font-size:12px;color:#94a3b8;">{}</span>',
            ', '.join(parts),
        )

    @admin.display(description='Items')
    def item_count(self, obj):
        n = obj.items.count()
        if not n:
            return '—'
        return format_html(
            '<span style="background:#ed3338;color:#fff;padding:2px 9px;border-radius:100px;'
            'font-size:11px;font-weight:700;">{}</span>',
            n,
        )


@admin.register(WebsiteMessage)
class WebsiteMessageAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'kind', 'full_name', 'email', 'phone', 'subject', 'status']
    list_filter = ['kind', 'status', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'company_name', 'subject', 'message']
    readonly_fields = ['kind', 'full_name', 'email', 'phone', 'company_name', 'subject',
                       'product_interest', 'quantity', 'message', 'source_page', 'created_at']
    fields = ['status', 'kind', ('full_name', 'company_name'), ('email', 'phone'),
              ('subject', 'product_interest', 'quantity'), 'message', 'source_page', 'created_at']
    ordering = ['-created_at']
    list_per_page = 25

    def has_add_permission(self, request):
        return False
