import os

from django import forms
from django.contrib import admin
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from medialib.models import IMAGE_EXT

from .models import BlogCategory, Blog

# A photo dropped into a post's body, not the library: no row, no listing
# anywhere else, just a file the <img> tag the toolbar writes can point at.
# svg/ico excluded same as the library's own upload — not real photographs,
# and an svg served from here would run inline with the dashboard's cookies.
BODY_IMAGE_EXT = IMAGE_EXT - {'svg', 'ico'}


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'post_count', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Posts')
    def post_count(self, obj):
        n = obj.blogs.count()
        live = obj.blogs.filter(is_published=True).count()
        return '%d published of %d' % (live, n)


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = '__all__'
        widgets = {
            # The article page drops this straight into the page as HTML, so
            # what is typed here is markup. crystal_blog.js puts a small
            # toolbar and a live preview over it -- see that file for why it
            # is not a third-party editor.
            'content': forms.Textarea(attrs={'rows': 18, 'class': 'crystal-blog-body'}),
            'excerpt': forms.Textarea(attrs={'rows': 2}),
        }


def body_image_problem(f):
    ext = os.path.splitext(f.name)[1].lower().lstrip('.')
    if ext not in BODY_IMAGE_EXT:
        return '"%s" was not added — %s is not a picture format this accepts.' % (
            f.name, ext.upper() or 'a file with no extension')
    return None


@require_POST
def _body_image_upload(request):
    """One picture, dropped into a post's body from the toolbar's Image
    button (crystal_blog.js) -- not the Media library, just a file saved
    under blog/inline/ that the <img> tag it writes can point at."""
    if not request.user.has_perm('blog.change_blog'):
        return JsonResponse({'error': 'Not allowed.'}, status=403)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file was sent.'}, status=400)
    problem = body_image_problem(f)
    if problem:
        return JsonResponse({'error': problem}, status=400)
    name = default_storage.save('blog/inline/' + f.name, f)
    return JsonResponse({'url': default_storage.url(name)})


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    form = BlogForm
    list_display = ['thumb', 'title_cell', 'category', 'author', 'status', 'published_at']
    list_display_links = ['thumb', 'title_cell']
    search_fields = ['title', 'slug', 'author', 'excerpt', 'content']
    list_filter = ['is_published', 'category', 'published_at']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['preview', 'live_link']
    fieldsets = (
        ('The post', {
            'fields': ('title', 'slug', 'category', 'author', 'excerpt'),
            'description': 'The excerpt is the line under the title on the blog '
                           'listing. Left empty, the card shows nothing there.',
        }),
        ('Picture', {
            'fields': ('featured_image', 'preview'),
            'description': 'Shown on the listing card and across the top of the '
                           'article. A wide photograph suits both.',
        }),
        ('Body', {
            'fields': ('content',),
        }),
        ('Publishing', {
            'fields': ('is_published', 'published_at', 'live_link'),
            'description': 'The date fills itself in the first time you publish. '
                           'Until then the post is invisible to the website, '
                           'which only ever asks for published ones.',
        }),
        ('Search engines', {
            'classes': ('collapse',),
            'fields': ('meta_title', 'meta_description'),
        }),
    )

    class Media:
        css = {'all': ('admin/crystal_blog.css',)}
        js = ('admin/crystal_blog.js',)

    def get_urls(self):
        custom = [
            path('body-image/', self.admin_site.admin_view(self.body_image_upload),
                 name='blog_body_image_upload'),
        ]
        return custom + super().get_urls()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Where the toolbar's Image button uploads to — set here rather than on
        # the widget directly, since the URL needs this admin site's own name
        # (reverse() isn't safe at class-definition time, before urls.py runs).
        from django.urls import reverse
        form.base_fields['content'].widget.attrs['data-upload-url'] = reverse(
            'admin:blog_body_image_upload')
        return form

    def body_image_upload(self, request):
        return _body_image_upload(request)

    @admin.display(description='')
    def thumb(self, obj):
        if not obj.featured_image:
            return mark_safe('<span class="bl-thumb bl-thumb--none"></span>')
        return format_html('<span class="bl-thumb" style="background-image:url({})"></span>',
                           obj.featured_image.url)

    @admin.display(description='Post', ordering='title')
    def title_cell(self, obj):
        return format_html('<strong>{}</strong><br><span class="bl-sub">{}</span>',
                           obj.title, obj.excerpt or obj.slug)

    @admin.display(description='Status', ordering='is_published')
    def status(self, obj):
        if obj.is_published:
            return mark_safe('<span class="bl-pill bl-pill--live">Published</span>')
        return mark_safe('<span class="bl-pill">Draft</span>')

    @admin.display(description='Picture now in use')
    def preview(self, obj):
        if not obj or not obj.featured_image:
            return mark_safe('<span class="bl-muted">Nothing uploaded yet.</span>')
        return format_html('<img src="{}" class="bl-preview">', obj.featured_image.url)

    @admin.display(description='On the website')
    def live_link(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span class="bl-muted">Save the post first.</span>')
        if not obj.is_published:
            return mark_safe('<span class="bl-muted">Not published, so the website '
                             'does not have it yet.</span>')
        return format_html('<a href="{}" target="_blank" rel="noopener">Read it on the site &#8599;</a>',
                           obj.url)
