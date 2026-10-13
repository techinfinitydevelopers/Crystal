"""Keep the pages in step with the content they are made from.

Saving a product or a blog post in the dashboard changes what its page should
say, and changing a blog post's address has to leave a redirect behind. Both are
done here rather than in each admin so that every way of saving -- the main
screens, the SEO screens, an import -- behaves the same.

Everything is guarded: no handler may ever make a save fail, and none does
anything when the website files are not reachable from this process.
"""
import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

log = logging.getLogger('seo')


def _can_bake():
    """Only inside the running dashboard, and only when asked.

    The deploy's catalogue sync saves every product and would otherwise queue a
    rebuild for each; it sets SEO_AUTOBAKE=0 because apply_seo runs straight
    after it anyway."""
    import os
    if os.environ.get('SEO_AUTOBAKE', '1') == '0':
        return False
    from .bake import site_root
    return bool(site_root())


@receiver(pre_save, sender='blog.Blog', dispatch_uid='seo-blog-slug-watch')
@receiver(pre_save, sender='seo.BlogPostSeo', dispatch_uid='seo-blogseo-slug-watch')
def blog_slug_watch(sender, instance, raw=False, **kwargs):
    """A post's address is /blog/<slug>, so changing the slug moves the page.

    Connected to the proxy model as well as Blog: a proxy sends its own class as
    the signal's sender, so saving through the SEO screen would otherwise bypass
    every handler here -- the redirect would never be written.
    """
    if raw or not instance.pk:
        return
    try:
        old = sender.objects.filter(pk=instance.pk).values_list('slug', flat=True).first()
        if old and old != instance.slug:
            instance._seo_old_slug = old
    except Exception:
        log.exception('could not read the old blog slug')


@receiver(post_save, sender='blog.Blog', dispatch_uid='seo-blog-saved')
@receiver(post_save, sender='seo.BlogPostSeo', dispatch_uid='seo-blogseo-saved')
def blog_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    try:
        old = getattr(instance, '_seo_old_slug', None)
        if old:
            from .models import note_slug_change
            note_slug_change('blog', old, instance.slug)
        if _can_bake():
            from . import pipeline
            pipeline.request_bake(products=False, blog=True)
    except Exception:
        log.exception('blog post saved but its page was not rebuilt')


@receiver(post_delete, sender='blog.Blog', dispatch_uid='seo-blog-deleted')
@receiver(post_delete, sender='seo.BlogPostSeo', dispatch_uid='seo-blogseo-deleted')
def blog_deleted(sender, instance, **kwargs):
    try:
        if _can_bake():
            from . import pipeline
            pipeline.request_bake(products=False, blog=True)
    except Exception:
        log.exception('blog post deleted but its page was not removed')


@receiver(post_save, sender='products.Product', dispatch_uid='seo-product-saved')
def product_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    try:
        if _can_bake():
            from . import pipeline
            pipeline.request_bake(products=True, blog=False)
    except Exception:
        log.exception('product saved but its page was not rebuilt')
