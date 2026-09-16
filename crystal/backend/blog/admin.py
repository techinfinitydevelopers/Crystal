from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import BlogCategory, Blog


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
