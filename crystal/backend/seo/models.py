"""What search engines and social previews see, edited from the dashboard.

Unlike the banners, page sections and awards, **none of this can be done by
asking an API on load**. A title or description written in by JavaScript is
read by almost nothing: Google sometimes picks it up after rendering, every
other crawler does not, and WhatsApp, Facebook and X never run scripts at all,
so a shared link would still show whatever the file itself said.

So this is baked instead. `manage.py apply_seo` writes these values into the
static HTML, and the deploy runs it after pulling. The served file really does
carry the title, which is the only version that counts.
"""
from django.db import models


class SeoMeta(models.Model):
    """One row per page of the website."""

    page = models.CharField(
        max_length=160, unique=True,
        help_text='The file on the website, e.g. "About.html". Do not change '
                  'it — this is what ties the row to the page.')
    label = models.CharField(
        max_length=160, blank=True,
        help_text='What to call this page in the list.')
    group = models.CharField(
        max_length=80, blank=True, db_index=True,
        help_text='Heading this page is listed under.')

    title = models.CharField(
        max_length=200, blank=True,
        help_text='The tab name, and the blue line in Google. Around 50–60 '
                  'characters; longer and Google cuts it off. Leave empty to '
                  'keep what the page already has.')
    description = models.TextField(
        blank=True,
        help_text='The grey paragraph under the title in Google. Around '
                  '140–160 characters. It does not affect ranking directly, '
                  'but it is what decides whether anyone clicks.')
    keywords = models.CharField(
        max_length=300, blank=True,
        help_text='Optional and ignored by Google since 2009. Here only '
                  'because some other tools still read it.')

    canonical = models.URLField(
        blank=True,
        help_text='Leave empty. Filled in automatically with this page\'s own '
                  'address, which is what stops the same page counting twice. '
                  'Set one only to point this page at a different one.')

    og_title = models.CharField(
        max_length=200, blank=True,
        help_text='The heading on a WhatsApp, Facebook or LinkedIn preview. '
                  'Empty uses the title above.')
    og_description = models.TextField(
        blank=True, help_text='The preview\'s second line. Empty uses the '
                              'description above.')
    og_image = models.ImageField(
        upload_to='seo/', blank=True, null=True,
        help_text='The picture on a shared link. 1200x630 works everywhere. '
                  'Without one, a shared link is a bare grey box.')

    INDEX_YES = 'index'
    INDEX_NO = 'noindex'
    INDEX_CHOICES = [
        (INDEX_YES, 'Yes — show this page in search results'),
        (INDEX_NO, 'No — keep this page out of search results'),
    ]
    indexing = models.CharField(
        max_length=10, choices=INDEX_CHOICES, default=INDEX_YES,
        verbose_name='Show in search',
        help_text='"No" asks search engines to leave this page out. Use it for '
                  'thank-you pages and the like, never on a page you want found.')
    in_sitemap = models.BooleanField(
        default=True, verbose_name='List in sitemap.xml',
        help_text='The file that tells search engines which pages exist. Leave '
                  'ticked unless the page is deliberately hidden.')
    priority = models.DecimalField(
        max_digits=2, decimal_places=1, default=0.5,
        help_text='A hint about how important this page is relative to the '
                  'others, from 0.1 to 1.0. The home page is usually 1.0.')

    shipped_title = models.CharField(
        max_length=300, blank=True,
        help_text='What the page says today, for reference. Leave the title '
                  'above empty and this is what stays.')
    shipped_description = models.TextField(
        blank=True, help_text='The same, for the description.')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group', 'label', 'page']
        verbose_name = 'Page SEO'
        verbose_name_plural = 'Page SEO'

    def __str__(self):
        return self.label or self.page

    @property
    def url_path(self):
        """The address this page is served at.

        nginx resolves /About to About.html, so the extensionless form is the
        real address and the one a canonical tag has to name — otherwise the
        two spellings compete as duplicates of each other.
        """
        name = self.page[:-5] if self.page.lower().endswith('.html') else self.page
        return '/' if name.lower() in ('index', 'home') else '/' + name

    @property
    def effective_title(self):
        return self.title.strip() or self.shipped_title.strip()

    @property
    def effective_description(self):
        return self.description.strip() or self.shipped_description.strip()

    @property
    def is_edited(self):
        return bool(self.title or self.description or self.og_image)


class ScriptBlock(models.Model):
    """Analytics, ad and verification code, placed without touching the files.

    Every page already carries a hard-coded GA4 snippet and a Search Console
    verification tag. Anything added here goes in alongside them, so check
    before pasting a second copy of the same tag — two GA4 installs double
    every number they report.
    """

    HEAD = 'head'
    BODY_START = 'body_start'
    BODY_END = 'body_end'
    PLACEMENT_CHOICES = [
        (HEAD, 'Header — inside <head>'),
        (BODY_START, 'Body — right after <body> opens'),
        (BODY_END, 'Footer — just before </body>'),
    ]

    name = models.CharField(
        max_length=120,
        help_text='What this is, for the list — e.g. "Meta Pixel" or '
                  '"Google Ads conversion".')
    placement = models.CharField(
        max_length=20, choices=PLACEMENT_CHOICES, default=HEAD,
        help_text='Where the code goes. Most analytics tags want the header; '
                  'Google Tag Manager wants its second snippet at the top of '
                  'the body; chat widgets usually want the footer.')
    code = models.TextField(
        help_text='Paste the snippet exactly as the provider gives it, '
                  '&lt;script&gt; tags and all. It is written into the page as '
                  'typed — nothing is escaped or checked.')
    pages = models.TextField(
        blank=True,
        help_text='Leave empty for every page. Otherwise one file name per '
                  'line, e.g. "Contact.html", to load it only there.')
    is_active = models.BooleanField(
        default=True,
        help_text='Untick to take the code off the site without deleting it.')
    order = models.PositiveIntegerField(
        default=0, help_text='Lowest first, when several sit in the same place.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['placement', 'order', 'id']
        verbose_name = 'Tracking code'
        verbose_name_plural = 'Tracking codes'

    def __str__(self):
        return self.name

    def page_list(self):
        """The pages this applies to, or an empty list meaning all of them."""
        return [p.strip() for p in self.pages.splitlines() if p.strip()]

    def applies_to(self, page):
        wanted = self.page_list()
        return not wanted or page in wanted


class SeoSettings(models.Model):
    """Site-wide SEO, one row."""

    site_url = models.URLField(
        default='https://crystalcook.com',
        help_text='The address the site is served at, used to build canonical '
                  'tags and the sitemap. No trailing slash.')
    default_title_suffix = models.CharField(
        max_length=80, blank=True, default=' | CRYSTAL',
        help_text='Added to the end of a generated title, e.g. " | CRYSTAL". '
                  'Titles typed in by hand are left exactly as written.')
    default_og_image = models.ImageField(
        upload_to='seo/', blank=True, null=True,
        help_text='Used for any page without its own preview picture.')
    ga4_id = models.CharField(
        max_length=30, blank=True, default='G-MET1S841PH',
        verbose_name='Google Analytics 4 ID',
        help_text='Looks like G-XXXXXXXXXX. The site-wide analytics tag is '
                  'written from this, so change it here and nowhere else — a '
                  'second copy pasted under Tracking codes would count every '
                  'visit twice. Empty switches Analytics off.')
    search_console_code = models.CharField(
        max_length=120, blank=True,
        default='ZyRWD5LneUt7TPCHFChYuxj9wQcn2S-g1GOneojgbw0',
        verbose_name='Google Search Console verification',
        help_text='Just the long code from the "HTML tag" method, not the '
                  'whole tag. Removing it can make Google forget the site is '
                  'yours.')
    bing_verification = models.CharField(
        max_length=120, blank=True, verbose_name='Bing Webmaster verification',
        help_text='The content value of the msvalidate.01 tag. Optional.')
    organization_name = models.CharField(
        max_length=120, default='Crystal Cook N Serve Products Pvt. Ltd.',
        help_text='Shown to Google as the business name.')
    organization_phone = models.CharField(
        max_length=40, blank=True, default='+91-22-49702803')
    organization_email = models.CharField(
        max_length=120, blank=True, default='sales@crystalcook.com')
    social_profiles = models.TextField(
        blank=True,
        default='\n'.join([
            'https://www.instagram.com/crystalcooknserve',
            'https://www.facebook.com/share/1HMc4pSziY/',
            'https://www.linkedin.com/company/crystal-cook-and-serve-products-pvt-ltd/',
            'https://youtube.com/@crystalcooknserve',
        ]),
        help_text='One address per line. Tells Google these accounts belong to '
                  'the business.')
    robots_extra = models.TextField(
        blank=True,
        help_text='Extra lines for robots.txt. The sitemap line and the '
                  'allow-everything rule are written for you.')
    generate_product_pages = models.BooleanField(
        default=True, verbose_name='Build a page per product',
        help_text='Gives every product its own address instead of sharing one. '
                  'Turning this off leaves the pages already built in place.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SEO settings'
        verbose_name_plural = 'SEO settings'

    def __str__(self):
        return 'SEO settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Redirect(models.Model):
    """Send an old address to its new one, so changing a URL costs nothing.

    The site is plain files behind nginx, so there is no server to answer with a
    real 301 without editing its configuration. Instead each redirect is written
    out as a small page at the old address that says, to a search engine and to a
    browser alike, "this has moved here" -- an instant meta refresh, a canonical
    link and a script redirect. Google treats an instant meta refresh as a
    permanent redirect and passes the old address's standing along.

    Product and blog slugs add rows here by themselves when they are changed.
    """

    from_path = models.CharField(
        max_length=300, unique=True,
        help_text='The old address, starting with a slash — e.g. '
                  '"/products/old-name". No domain.')
    to_path = models.CharField(
        max_length=300,
        help_text='Where it goes now, starting with a slash — or a full '
                  'address for another site.')
    note = models.CharField(
        max_length=200, blank=True,
        help_text='Why, for whoever looks at this next.')
    automatic = models.BooleanField(
        default=False, editable=False,
        help_text='Made by the dashboard when a slug changed.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Redirect'
        verbose_name_plural = 'Redirects'

    def __str__(self):
        return '%s → %s' % (self.from_path, self.to_path)

    def clean(self):
        from django.core.exceptions import ValidationError
        f = (self.from_path or '').strip()
        t = (self.to_path or '').strip()
        if not f.startswith('/'):
            raise ValidationError({'from_path': 'Start with a slash, e.g. /old-page'})
        if not (t.startswith('/') or t.startswith('http')):
            raise ValidationError({'to_path': 'Start with a slash, or give a full address.'})
        if f.rstrip('/') == t.rstrip('/'):
            raise ValidationError('From and to are the same address.')
        if f == '/':
            raise ValidationError({'from_path': 'The home page cannot be redirected.'})
        self.from_path, self.to_path = f, t


class ProductPage(models.Model):
    """The address of one product's own page, e.g. /products/crystal-peeler.

    Keyed by the catalogue's own id for the entry rather than tied to a Product
    row. The site's 650 entries are not 650 products: a product with sizes
    appears once per size, each with its own id and each addressable, so a
    one-to-one with Product would have left every size without a page.

    Title and description are *not* stored here. They already live on
    Product.meta_title / meta_description, where the dashboard's own override
    feed and the catalogue sync know about them, and a second copy would be one
    more thing to disagree. This table owns the address and nothing else.
    """

    entry_id = models.CharField(
        max_length=120, unique=True,
        help_text='The product\'s id in the catalogue. Do not change it — the '
                  'rest of the site finds the product by this.')
    slug = models.SlugField(
        max_length=90, unique=True,
        verbose_name='Page address',
        help_text='The last part of the web address, e.g. '
                  '"crystal-23-cm-pointed-knife". Lower-case words joined by '
                  'hyphens. Changing it is safe: the old address is redirected '
                  'to the new one automatically.')
    name = models.CharField(
        max_length=240, blank=True, editable=False,
        help_text='Copied from the catalogue, for the list.')
    sku = models.CharField(max_length=60, blank=True, editable=False)
    product = models.ForeignKey(
        'products.Product', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='seo_pages', editable=False,
        help_text='The dashboard product this entry belongs to — where its '
                  'search title and description are kept.')
    noindex = models.BooleanField(
        default=False, verbose_name='Hide from search',
        help_text='Ask search engines to leave this product out of results.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'entry_id']
        verbose_name = 'Product page'
        verbose_name_plural = 'Product pages'

    def __str__(self):
        return self.name or self.entry_id

    @property
    def path(self):
        return '/products/%s' % self.slug

    def save(self, *args, **kwargs):
        # The address is what other sites link to, so a change has to leave a
        # forwarding note behind. Done here rather than in the admin so that
        # the list's inline edit, the form, a CSV import and a shell all get it.
        if self.pk:
            old = (ProductPage.objects.filter(pk=self.pk)
                   .values_list('slug', flat=True).first())
            super().save(*args, **kwargs)
            note_slug_change('products', old, self.slug)
        else:
            super().save(*args, **kwargs)


def note_slug_change(prefix, old, new):
    """Keep every address that ever worked pointing at the one that does now.

    Called when a product or blog slug is changed. Two things matter: the old
    address gets a redirect to the new one, and any redirect that was sending
    traffic *to* the old address is re-pointed at the new one so it does not
    become a two-step hop. A redirect that used to leave the new address is
    deleted, since the real page lives there again.
    """
    if not old or not new or old == new:
        return
    old_path, new_path = '/%s/%s' % (prefix, old), '/%s/%s' % (prefix, new)
    Redirect.objects.filter(from_path=new_path).delete()
    Redirect.objects.filter(to_path=old_path).update(to_path=new_path)
    Redirect.objects.update_or_create(
        from_path=old_path,
        defaults={'to_path': new_path, 'automatic': True, 'is_active': True,
                  'note': 'Address changed in the dashboard'})


def _blog_proxy():
    from blog.models import Blog

    class BlogPostSeo(Blog):
        """The blog's posts, as the SEO team sees them: address and search copy.

        A proxy, so there is one table and one set of posts. Its own permission
        is what lets the SEO team edit these fields without being handed the
        whole blog screen.
        """

        class Meta:
            proxy = True
            app_label = 'seo'
            verbose_name = 'Blog post SEO'
            verbose_name_plural = 'Blog post SEO'

    return BlogPostSeo


BlogPostSeo = _blog_proxy()
