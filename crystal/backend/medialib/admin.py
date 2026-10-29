import os

from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST

from .models import IMAGE_EXT, PDF_EXT, VIDEO_EXT, MediaItem
from .usage import delete_file_if_unused, usage_map

# What may be uploaded INTO the library. Wider than images, because brochures
# and videos are picked from here too, but no .html/.svg/.js: /media/ is served
# from the dashboard's own address, so a page or script uploaded here would run
# with the dashboard's cookies. (Indexed files of any type are still listed.)
UPLOAD_EXT = (IMAGE_EXT - {'svg', 'ico'}) | VIDEO_EXT | PDF_EXT | {
    'doc', 'docx', 'xls', 'xlsx', 'csv', 'ppt', 'pptx', 'txt', 'zip'}

PER_PAGE = 40

KIND_ICONS = {
    MediaItem.VIDEO: 'fas fa-film',
    MediaItem.PDF: 'fas fa-file-pdf',
    MediaItem.OTHER: 'fas fa-file',
    MediaItem.IMAGE: 'fas fa-image',
}


def item_json(item):
    return {
        'id': item.pk,
        'name': item.file.name,
        'filename': item.filename,
        'title': item.title or item.filename,
        'alt': item.alt_text,
        'url': item.url,
        'kind': item.kind,
        'width': item.width,
        'height': item.height,
        'size': item.size_label,
        'source': item.source,
    }


def upload_problem(f):
    ext = os.path.splitext(f.name)[1].lower().lstrip('.')
    if ext not in UPLOAD_EXT:
        return (f'“{f.name}” was not added — {ext.upper() or "files without an extension"} '
                f'cannot go in the library. Pictures, videos, PDFs and office documents can.')
    return None


def save_uploads(files):
    """Create one library row per file. Returns (items, problems)."""
    items, problems = [], []
    for f in files:
        problem = upload_problem(f)
        if problem:
            problems.append(problem)
            continue
        item = MediaItem(file=f)
        item.save()
        items.append(item)
    return items, problems


class SourceFilter(admin.SimpleListFilter):
    title = 'where it came from'
    parameter_name = 'from'

    def lookups(self, request, model_admin):
        return [('library', 'Uploaded to the library'),
                ('elsewhere', 'Uploaded somewhere else in the dashboard')]

    def queryset(self, request, queryset):
        if self.value() == 'library':
            return queryset.filter(source='')
        if self.value() == 'elsewhere':
            return queryset.exclude(source='')
        return queryset


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    """The library itself: a grid of everything uploaded, a multi-file upload
    page, and the two small JSON endpoints the "Choose from Media library"
    picker on every upload box talks to."""

    list_display = ('thumb', 'title_cell', 'kind', 'dimensions', 'size_cell',
                    'copy_url', 'used_in_count')
    list_display_links = ('thumb', 'title_cell')
    list_filter = ('kind', SourceFilter)
    search_fields = ('title', 'file', 'alt_text', 'source')
    list_per_page = 48
    change_list_template = 'admin/medialib/mediaitem/change_list.html'
    readonly_fields = ('preview', 'file_facts', 'copy_url', 'used_in', 'source', 'uploaded_at')

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('file', 'title', 'alt_text')
        return ('preview', 'title', 'alt_text', 'file_facts', 'copy_url',
                'used_in', 'source', 'uploaded_at')

    def get_urls(self):
        wrap = self.admin_site.admin_view
        return [
            path('upload/', wrap(self.upload_view), name='medialib_mediaitem_upload'),
            path('picker.json', wrap(self.picker_json), name='medialib_mediaitem_picker'),
            path('upload.json', wrap(self.upload_json), name='medialib_mediaitem_upload_json'),
        ] + super().get_urls()

    # ── list ────────────────────────────────────────────────────────────────

    def get_changelist_instance(self, request):
        """Work out "used in" for the whole page at once — one query per file
        field instead of one per field per tile."""
        cl = super().get_changelist_instance(request)
        rows = list(cl.result_list)
        uses = usage_map([r.file.name for r in rows])
        for r in rows:
            r._uses = uses.get(r.file.name, [])
        return cl

    @admin.display(description='')
    def thumb(self, obj):
        if obj.kind == MediaItem.IMAGE and obj.url:
            return format_html('<span class="ml-thumb"><img src="{}" alt="{}" loading="lazy"></span>',
                               obj.url, obj.alt_text or obj.title)
        return format_html('<span class="ml-thumb ml-thumb--icon"><i class="{}"></i>'
                           '<em>{}</em></span>',
                           KIND_ICONS.get(obj.kind, 'fas fa-file'),
                           os.path.splitext(obj.filename)[1].lstrip('.').upper())

    @admin.display(description='Title', ordering='title')
    def title_cell(self, obj):
        return format_html('<strong class="ml-title">{}</strong>'
                           '<span class="ml-filename">{}</span>',
                           obj.title or obj.filename, obj.filename)

    @admin.display(description='Size (pixels)')
    def dimensions(self, obj):
        if obj.width and obj.height:
            return f'{obj.width} × {obj.height}'
        return '—'

    @admin.display(description='File size', ordering='size')
    def size_cell(self, obj):
        return obj.size_label if obj.size else '—'

    @admin.display(description='Link')
    def copy_url(self, obj):
        if not obj or not obj.url:
            return '—'
        return format_html(
            '<button type="button" class="ml-copy" data-ml-copy="{}" '
            'title="Copy this file\'s web address">'
            '<i class="fas fa-link"></i> Copy URL</button>', obj.url)

    @admin.display(description='Used in')
    def used_in_count(self, obj):
        uses = getattr(obj, '_uses', None)
        if uses is None:
            uses = usage_map([obj.file.name]).get(obj.file.name, [])
        if not uses:
            return mark_safe('<span class="ml-used ml-used--none">Not used</span>')
        n = len(uses)
        return format_html('<span class="ml-used">Used in {} place{}</span>',
                           n, '' if n == 1 else 's')

    # ── change page ─────────────────────────────────────────────────────────

    @admin.display(description='Preview')
    def preview(self, obj):
        if not obj or not obj.file:
            return '—'
        if obj.kind == MediaItem.IMAGE:
            return format_html('<a href="{0}" target="_blank" rel="noopener">'
                               '<img src="{0}" class="ml-preview" alt=""></a>', obj.url)
        if obj.kind == MediaItem.VIDEO:
            return format_html('<video src="{}" class="ml-preview" controls preload="metadata"></video>',
                               obj.url)
        return format_html('<a href="{}" target="_blank" rel="noopener">'
                           '<i class="{}"></i> Open {}</a>',
                           obj.url, KIND_ICONS.get(obj.kind), obj.filename)

    @admin.display(description='File')
    def file_facts(self, obj):
        bits = [obj.get_kind_display(), obj.size_label]
        if obj.width and obj.height:
            bits.append(f'{obj.width} × {obj.height} pixels')
        return format_html('<code>{}</code><br><span style="color:#64748b">{}</span>',
                           obj.file.name, ' · '.join(bits))

    @admin.display(description='Used in')
    def used_in(self, obj):
        uses = usage_map([obj.file.name]).get(obj.file.name, []) if obj else []
        if not uses:
            return mark_safe('<span style="color:#64748b">Nothing uses this file yet. '
                             'Deleting it removes the file too.</span>')
        rows = format_html_join(
            '', '<li><strong>{}</strong> — {} {}</li>',
            ((u['model'],
              format_html('<a href="{}">{}</a>', u['link'], u['object']) if u['link'] else u['object'],
              format_html('<span style="color:#94a3b8">({})</span>', u['field']))
             for u in uses))
        return format_html('<ul class="ml-uses">{}</ul>'
                           '<div style="color:#64748b;font-size:12px">Deleting this library entry '
                           'keeps the file, because the places above still show it.</div>', rows)

    # ── delete: the row always, the file only when nothing else uses it ────

    def delete_model(self, request, obj):
        name, pk = obj.file.name, obj.pk
        super().delete_model(request, obj)
        self._report_file(request, [delete_file_if_unused(name, exclude_pk=pk)])

    def delete_queryset(self, request, queryset):
        done = []
        for obj in list(queryset):
            name, pk = obj.file.name, obj.pk
            obj.delete()
            done.append(delete_file_if_unused(name, exclude_pk=pk))
        self._report_file(request, done)

    def _report_file(self, request, removed):
        kept = removed.count(False)
        if kept:
            self.message_user(
                request,
                f'{kept} file{"" if kept == 1 else "s"} kept on the server because '
                f'{"it is" if kept == 1 else "they are"} still used elsewhere on the site.',
                level=messages.INFO)

    # ── multi-file upload page ──────────────────────────────────────────────

    def upload_view(self, request):
        if not self.has_add_permission(request):
            return redirect(reverse('admin:medialib_mediaitem_changelist'))
        if request.method == 'POST':
            items, problems = save_uploads(request.FILES.getlist('files'))
            for p in problems:
                messages.warning(request, p)
            if items:
                messages.success(request, f'{len(items)} file{"" if len(items) == 1 else "s"} '
                                          f'added to the Media library.')
                return redirect(reverse('admin:medialib_mediaitem_changelist'))
            if not problems:
                messages.error(request, 'No files were chosen.')
        context = {
            **self.admin_site.each_context(request),
            'title': 'Upload files',
            'opts': self.model._meta,
            'accept': ','.join('.' + e for e in sorted(UPLOAD_EXT)),
        }
        return render(request, 'admin/medialib/mediaitem/upload.html', context)

    # ── JSON for the picker ─────────────────────────────────────────────────

    def picker_json(self, request):
        return _picker_json(request)

    def upload_json(self, request):
        return _upload_json(request)


@require_GET
def _picker_json(request):
    qs = MediaItem.objects.all()
    kind = request.GET.get('kind', '')
    if kind in dict(MediaItem.KIND_CHOICES):
        qs = qs.filter(kind=kind)
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(file__icontains=q)
                       | Q(alt_text__icontains=q) | Q(source__icontains=q))
    paginator = Paginator(qs, PER_PAGE)
    page = paginator.get_page(request.GET.get('page') or 1)
    return JsonResponse({
        'items': [item_json(i) for i in page.object_list],
        'page': page.number,
        'pages': paginator.num_pages,
        'total': paginator.count,
    })


@require_POST
def _upload_json(request):
    items, problems = save_uploads(request.FILES.getlist('file'))
    status = 200 if items else 400
    if not items and not problems:
        problems = ['No file was received.']
    return JsonResponse({'items': [item_json(i) for i in items], 'errors': problems},
                        status=status)
