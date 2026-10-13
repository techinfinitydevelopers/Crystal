"""Turns the dashboard's SEO rows into files on disk.

Stages, in the order `bake_all` runs them:

  1. static pages     -- title, description, canonical, social cards, schema and
                         tracking code written into each real page in place
  2. product pages    -- one file per catalogue entry at /products/<slug>
  3. blog pages       -- one file per post at /blog/<slug>
  4. redirects        -- a small "moved" page at every old address
  5. sitemap.xml, robots.txt and product-urls.js

Nothing here raises into a caller that is saving something in the dashboard: the
admin hooks catch and report, so a failure to bake can never block an edit.
"""
import json
import re
import threading
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.utils import timezone
from django.utils.text import slugify

from . import defaults
from .bake import (
    GENERATED_MARK, STUB_MARK, PageInfo, abs_url, apply_to_html, asset_url, clip,
    esc, og_image_for, read, site_root, write, TITLE_BUDGET, DESC_BUDGET,
)
from .models import ProductPage, Redirect, ScriptBlock, SeoMeta, SeoSettings

_LOCK = threading.Lock()


class Report:
    """What a run did, for the command line and for the dashboard message."""

    def __init__(self):
        self.written = 0
        self.unchanged = 0
        self.removed = 0
        self.skipped = []
        self.notes = []

    def count(self, changed):
        if changed:
            self.written += 1
        else:
            self.unchanged += 1

    def __str__(self):
        bits = ['%d written' % self.written, '%d already current' % self.unchanged]
        if self.removed:
            bits.append('%d removed' % self.removed)
        if self.skipped:
            bits.append('%d skipped' % len(self.skipped))
        return ', '.join(bits)


# ---------------------------------------------------------------------------
# Static pages
# ---------------------------------------------------------------------------
def page_files(root):
    """The real pages, from the dashboard's registry. Stray design exports that
    sit in the same folder are included so they can be kept out of search."""
    from content.pages_registry import ALL_PAGES
    names = [p for p in ALL_PAGES if not p.startswith('_')]
    names += sorted(defaults.STRAYS)
    return [n for n in dict.fromkeys(names) if (Path(root) / n).is_file()]


def _title_of(source):
    m = re.search(r'<title>(.*?)</title>', source, re.S | re.I)
    if not m:
        return ''
    t = m.group(1)
    # Terms.html shipped with a second <title> nested inside the first.
    t = re.sub(r'<title>.*', '', t, flags=re.S | re.I) if t.count('<') else t
    import html as _h
    return _h.unescape(t).strip()


def _desc_of(source):
    head = source.split('</head>', 1)[0]
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>', head, re.S | re.I)
    if not m:
        return ''
    import html as _h
    return _h.unescape(m.group(1)).strip()


def seed_pages(root=None):
    """One SeoMeta row per page. Never overwrites anything a person typed.

    `shipped_*` records what the file said before this module first touched it,
    so a title left empty in the dashboard keeps exactly that. A file that
    already carries the marker block was seeded earlier and is not re-read --
    its title and description are by then our own output.
    """
    from content.pages_registry import PAGE_LABELS, PAGES_REGISTRY
    root = root or site_root()
    if not root:
        return 0
    groups = {fn: grp for grp, pages in PAGES_REGISTRY for fn, _ in pages}
    made = 0
    for name in page_files(root):
        row, created = SeoMeta.objects.get_or_create(page=name, defaults={
            'label': PAGE_LABELS.get(name) or name.replace('.html', ''),
            'group': groups.get(name, 'Not a live page' if name in defaults.STRAYS else ''),
        })
        made += created
        source = read(Path(root) / name)
        fresh = '<!-- seo:start -->' not in source
        changed = []
        if fresh or created:
            row.shipped_title = _title_of(source)
            row.shipped_description = _desc_of(source)
            changed += ['shipped_title', 'shipped_description']
        if created:
            row.priority = defaults.priority_for(name)
            row.in_sitemap = name not in defaults.NOT_IN_SITEMAP
            row.indexing = (SeoMeta.INDEX_NO if name in defaults.NOINDEX else SeoMeta.INDEX_YES)
            if name in defaults.COPY:
                t, d = defaults.COPY[name]
                # Only where the page had nothing usable: a written title or
                # description is kept as the starting value, not replaced.
                # "About Us — CRYSTAL" and "Crystal Cook N Serve Products - Home"
                # say nothing a search result needs; anything this short, or a
                # bare "- Home", is a placeholder rather than a title.
                weak_title = (not row.shipped_title or len(row.shipped_title) < 30
                              or '<title>' in row.shipped_title
                              or row.shipped_title.lower().rstrip().endswith('- home')
                              or row.shipped_title.lower().endswith('social media agency'))
                if weak_title:
                    row.title = t
                if not row.shipped_description:
                    row.description = d
            changed += ['priority', 'in_sitemap', 'indexing', 'title', 'description']
        if changed:
            row.save()
    return made


def static_info(row, st, root):
    name = row.page
    path = row.url_path
    title = row.effective_title or defaults.COPY.get(name, ('', ''))[0] or 'CRYSTAL'
    desc = row.effective_description
    canonical = row.canonical
    if not canonical and name in defaults.CANONICAL_OF:
        canonical = abs_url(st, SeoMeta(page=defaults.CANONICAL_OF[name]).url_path)
    noindex = row.indexing == SeoMeta.INDEX_NO
    info = PageInfo(
        path, title, desc,
        keywords=row.keywords, noindex=noindex, canonical=canonical,
        og_title=row.og_title, og_description=row.og_description,
        og_image=og_image_for(st, row.og_image, root),
        script_page=name,
        jsonld=static_jsonld(row, st, root),
    )
    return info


def _crumb_item(pos, name, url):
    return {'@type': 'ListItem', 'position': pos, 'name': name, 'item': url}


def breadcrumb(st, trail):
    """trail: [(name, path), ...] from Home down to the current page."""
    return {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [_crumb_item(i + 1, n, abs_url(st, p)) for i, (n, p) in enumerate(trail)],
    }


def organization(st, root):
    org = {
        '@context': 'https://schema.org', '@type': 'Organization',
        'name': st.organization_name, 'url': abs_url(st, '/'),
        'logo': abs_url(st, '/favicon.svg'),
    }
    same = [u.strip() for u in (st.social_profiles or '').splitlines() if u.strip()]
    if same:
        org['sameAs'] = same
    if st.organization_phone or st.organization_email:
        cp = {'@type': 'ContactPoint', 'contactType': 'customer service',
              'areaServed': 'IN', 'availableLanguage': ['English', 'Hindi']}
        if st.organization_phone:
            cp['telephone'] = st.organization_phone
        if st.organization_email:
            cp['email'] = st.organization_email
        org['contactPoint'] = cp
    return org


def static_jsonld(row, st, root):
    name = row.page
    docs = []
    if name == 'index.html':
        docs.append(organization(st, root))
        docs.append({'@context': 'https://schema.org', '@type': 'WebSite',
                     'name': 'CRYSTAL', 'url': abs_url(st, '/')})
        return docs
    if name in defaults.NOINDEX:
        return docs
    if name in ('About.html', 'Contact.html'):
        docs.append(organization(st, root))
    trail = [('Home', '/')]
    parent = defaults.parent_of(name)
    if parent:
        prow = SeoMeta.objects.filter(page=parent).first()
        trail.append((prow.label if prow else parent.replace('.html', ''),
                      prow.url_path if prow else '/' + parent[:-5]))
    trail.append((row.label or name[:-5], row.url_path))
    docs.append(breadcrumb(st, trail))
    return docs


def bake_static(report, only=None):
    root = site_root()
    if not root:
        return
    st = SeoSettings.load()
    qs = SeoMeta.objects.all()
    if only:
        qs = qs.filter(page__in=[only] if isinstance(only, str) else only)
    for row in qs:
        path = Path(root) / row.page
        if not path.is_file():
            continue
        try:
            source = read(path)
            out = apply_to_html(source, static_info(row, st, root), st)
            report.count(write(path, out))
        except Exception as exc:        # one bad page must not stop the rest
            report.skipped.append('%s: %s' % (row.page, exc))


# ---------------------------------------------------------------------------
# Product pages
# ---------------------------------------------------------------------------
def make_slug(name, sku, taken):
    """Readable and unique: the name, with the code appended on a clash."""
    # 'LONG SERIES)12"' would otherwise slugify to "series12", running the size
    # into the word before it.
    spaced = re.sub(r'\)(\d)', r') \1', name or '')
    base = slugify(spaced)[:70].strip('-') or slugify(sku or '') or 'product'
    if base not in taken:
        return base
    with_code = '%s-%s' % (base[:60].strip('-'), slugify(sku or '')) if sku else base
    if with_code not in taken:
        return with_code
    n = 2
    while '%s-%d' % (with_code, n) in taken:
        n += 1
    return '%s-%d' % (with_code, n)


def catalogue_entries(root):
    """The entries the live site shows: the database when it has them, else the
    catalogue file. Deduplicated by id, first one wins."""
    entries = []
    try:
        from products.models import Product
        from products.serializers import site_product_entries
        qs = (Product.objects.filter(is_active=True)
              .select_related('brand', 'category__parent')
              .prefetch_related('images', 'variants', 'specifications',
                                'marketplace_links__marketplace')
              .order_by('id'))
        for product in qs:
            entries.extend(site_product_entries(product))
    except Exception:
        entries = []
    if not entries and root:
        f = Path(root) / 'product-data' / 'products.json'
        if f.is_file():
            data = json.loads(read(f))
            entries = data['products'] if isinstance(data, dict) else data
    seen, out = set(), []
    for e in entries:
        eid = e.get('id')
        if eid and eid not in seen:
            seen.add(eid)
            out.append(e)
    return out


def sync_product_pages(entries):
    """Make sure every entry has an address row, and keep display fields fresh.

    Never changes an existing slug: that is the SEO team's to change, and a
    silent change here would orphan every link already out in the world.
    """
    from products.models import Product
    by_slug = {p.slug: p for p in Product.objects.all()}
    try:
        from products.models import ProductVariant
        variant_parent = {slugify(v.sku): v.product for v in ProductVariant.objects.select_related('product') if v.sku}
    except Exception:
        variant_parent = {}
    existing = {p.entry_id: p for p in ProductPage.objects.all()}
    taken = {p.slug for p in existing.values()}
    pages = {}
    for e in entries:
        eid = e['id']
        row = existing.get(eid)
        product = by_slug.get(eid) or variant_parent.get(eid)
        if row is None:
            slug = make_slug(e.get('name'), e.get('sku'), taken)
            taken.add(slug)
            row = ProductPage.objects.create(
                entry_id=eid, slug=slug, name=(e.get('name') or '')[:240],
                sku=(e.get('sku') or '')[:60], product=product)
        else:
            want = {'name': (e.get('name') or '')[:240], 'sku': (e.get('sku') or '')[:60],
                    'product': product}
            dirty = [k for k, v in want.items() if getattr(row, k) != v]
            for k in dirty:
                setattr(row, k, want[k])
            if dirty:
                row.save(update_fields=dirty + ['updated_at'])
        pages[eid] = row
    return pages


def product_title(e, brand_name):
    if e.get('meta_title'):
        return e['meta_title']
    name = (e.get('name') or '').strip()
    suffix = ' | CRYSTAL'
    room = TITLE_BUDGET - len(suffix)
    if brand_name and brand_name.lower() not in name.lower():
        name = '%s %s' % (brand_name, name) if len(name) + len(brand_name) + 1 <= room else name
    return clip(name, room) + suffix


def product_description(e, brand_name):
    if e.get('meta_description'):
        return e['meta_description']
    text = (e.get('highlight') or e.get('description') or '').strip()
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if text:
        return clip(text, DESC_BUDGET)
    return clip('%s by %s. Quality kitchen and home products from Crystal Cook N Serve, '
                'trusted since 1971.' % (e.get('name') or 'Product', brand_name or 'Crystal'), DESC_BUDGET)


def product_jsonld(e, row, st, brand_name, root):
    url = abs_url(st, row.path)
    images = [asset_url(st, x) for x in ([e.get('hero')] + list(e.get('gallery') or [])) if x]
    doc = {
        '@context': 'https://schema.org', '@type': 'Product',
        'name': e.get('name'), 'url': url,
        'description': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', e.get('description') or e.get('highlight') or '')).strip()[:900] or e.get('name'),
        'brand': {'@type': 'Brand', 'name': brand_name or 'Crystal'},
    }
    if e.get('sku'):
        doc['sku'] = e['sku']
    if images:
        doc['image'] = images[:6]
    if e.get('category'):
        doc['category'] = str(e['category']).replace('-', ' ').title()
    if e.get('mrp'):
        doc['offers'] = {
            '@type': 'Offer', 'priceCurrency': 'INR', 'price': str(e['mrp']),
            'availability': 'https://schema.org/InStock', 'url': url,
            'seller': {'@type': 'Organization', 'name': st.organization_name},
        }
    return doc


def product_info(e, row, st, root):
    brand_slug = (e.get('brand') or '').lower()
    brand_name = defaults.BRAND_NAMES.get(brand_slug, (e.get('brand') or '').title())
    title = product_title(e, brand_name)
    desc = product_description(e, brand_name)
    name = e.get('name') or ''
    hero = asset_url(st, e.get('hero')) or og_image_for(st, None, root)
    trail = [('Home', '/'), ('Products', '/All-Products')]
    bp = defaults.BRAND_PAGE_FOR.get(brand_slug)
    if bp:
        trail.append((brand_name, '/' + bp[:-5]))
    trail.append((name, row.path))
    intro = (e.get('highlight') or e.get('description') or '')
    import html as _h
    fills = {
        'pTitle': esc(name),
        'pSku': esc('Code: %s' % e['sku'].upper()) if e.get('sku') else '',
        'pIntro': esc(re.sub(r'<[^>]+>', ' ', intro).strip()),
    }
    inline = ('<script>window.__PRODUCT_ID__=%s;</script>' % json.dumps(e['id']))
    return PageInfo(
        row.path, title, desc, noindex=row.noindex, og_title=title, og_description=desc,
        og_image=hero, og_type='product', base_href=True, script_page='Product.html',
        jsonld=[product_jsonld(e, row, st, brand_name, root), breadcrumb(st, trail)],
        inline=inline, fills=fills,
    ), hero, name


def bake_products(report, entries=None):
    root = site_root()
    if not root:
        return {}
    st = SeoSettings.load()
    template_path = Path(root) / 'Product.html'
    if not template_path.is_file() or not st.generate_product_pages:
        return {}
    entries = entries if entries is not None else catalogue_entries(root)
    pages = sync_product_pages(entries)
    live_paths = set()
    template = read(template_path)
    out_dir = Path(root) / 'products'
    for e in entries:
        row = pages[e['id']]
        try:
            info, hero, name = product_info(e, row, st, root)
            body = apply_to_html(template, info, st)
            # the hero as a real image, so there is a picture before any script runs
            if e.get('hero'):
                body = body.replace('<img id="gMain" alt="" />',
                                    '<img id="gMain" src="%s" alt="%s" />' % (esc(e['hero']), esc(name)), 1)
            if GENERATED_MARK not in body:
                body = body.replace('<head>', '<head>' + chr(10) + GENERATED_MARK, 1)
            report.count(write(out_dir / (row.slug + '.html'), body))
            live_paths.add(row.slug + '.html')
        except Exception as exc:
            report.skipped.append('product %s: %s' % (e.get('id'), exc))
    # pages for products that are gone, or whose address changed
    if out_dir.is_dir():
        for f in out_dir.glob('*.html'):
            if f.name in live_paths:
                continue
            try:
                head = read(f)[:600]
            except OSError:
                continue
            if GENERATED_MARK in head:       # only ever remove what we made
                f.unlink()
                report.removed += 1
    return pages


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------
def _stub(to_url, st):
    target = to_url if to_url.startswith('http') else abs_url(st, to_url)
    rel = to_url if to_url.startswith(('/', 'http')) else '/' + to_url
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        + STUB_MARK + '\n<title>Moved</title>\n'
        '<meta name="robots" content="noindex,follow">\n'
        '<link rel="canonical" href="%s">\n'
        '<meta http-equiv="refresh" content="0; url=%s">\n'
        '<script>location.replace(%s + location.search + location.hash);</script>\n'
        '</head>\n<body><p>This page has moved to <a href="%s">%s</a>.</p></body>\n</html>\n'
        % (esc(target), esc(rel), json.dumps(rel), esc(rel), esc(target))
    )


def resolve_redirects():
    """from -> final destination, following chains and refusing loops."""
    rows = {r.from_path: r.to_path for r in Redirect.objects.filter(is_active=True)}
    out = {}
    for src in rows:
        dest, seen = rows[src], {src}
        while dest in rows and dest not in seen:
            seen.add(dest)
            dest = rows[dest]
        if dest in seen:                 # a loop: leave it alone
            continue
        out[src] = dest
    return out


def stub_file_for(root, from_path):
    p = from_path.strip('/')
    if not p:
        return None
    if '..' in p.split('/'):
        return None
    return Path(root) / (p if p.endswith('.html') else p + '.html')


def bake_redirects(report, live_urls):
    root = site_root()
    if not root:
        return
    st = SeoSettings.load()
    resolved = resolve_redirects()
    wanted = set()
    for src, dest in resolved.items():
        if src in live_urls:             # a real page lives here now: it wins
            continue
        f = stub_file_for(root, src)
        if f is None:
            continue
        if f.exists():
            try:
                if STUB_MARK not in read(f)[:600]:
                    report.skipped.append('redirect %s: a real page is already there' % src)
                    continue
            except OSError:
                continue
        report.count(write(f, _stub(dest, st)))
        wanted.add(f.resolve())
    # stubs whose redirect has been deleted or switched off
    for d in (Path(root), Path(root) / 'products', Path(root) / 'blog'):
        if not d.is_dir():
            continue
        for f in d.glob('*.html'):
            try:
                if STUB_MARK in read(f)[:600] and f.resolve() not in wanted:
                    f.unlink()
                    report.removed += 1
            except OSError:
                pass


# ---------------------------------------------------------------------------
# sitemap.xml, robots.txt, product-urls.js
# ---------------------------------------------------------------------------
def write_product_urls(pages, blog_urls, report):
    """The address maps the pages read through productHref() and blogHref()."""
    root = site_root()
    if not root:
        return
    products = {eid: row.slug for eid, row in sorted(pages.items())}
    posts = {path.rsplit('/', 1)[1]: True for path, _ in sorted(blog_urls)}
    nl = chr(10)
    body = (
        '/* Written by the dashboard (SEO). Maps a product id to its page address,' + nl
        + '   and lists the blog posts that have a page of their own. */' + nl
        + 'window.PRODUCT_URLS=' + json.dumps(products, separators=(',', ':')) + ';' + nl
        + 'window.BLOG_URLS=' + json.dumps(posts, separators=(',', ':')) + ';' + nl)
    report.count(write(Path(root) / 'product-urls.js', body))


def _lastmod(dt):
    return (dt or timezone.now()).astimezone(dt_timezone.utc).strftime('%Y-%m-%d')


def write_sitemap(pages, blog_urls, report):
    root = site_root()
    if not root:
        return
    st = SeoSettings.load()
    urls = []
    for row in SeoMeta.objects.filter(in_sitemap=True, indexing=SeoMeta.INDEX_YES).order_by('-priority', 'page'):
        f = Path(root) / row.page
        if not f.is_file():
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=dt_timezone.utc)
        urls.append((abs_url(st, row.url_path), _lastmod(mtime), 'weekly' if row.page == 'index.html' else 'monthly', row.priority))
    for eid, row in sorted(pages.items(), key=lambda kv: kv[1].slug):
        if row.noindex:
            continue
        urls.append((abs_url(st, row.path), _lastmod(row.updated_at), 'monthly', '0.6'))
    for path, when in blog_urls:
        urls.append((abs_url(st, path), _lastmod(when), 'monthly', '0.5'))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod, freq, prio in urls:
        parts.append('  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>'
                     % (esc(loc), mod, freq, prio))
    parts.append('</urlset>\n')
    report.count(write(Path(root) / 'sitemap.xml', '\n'.join(parts)))
    report.notes.append('sitemap: %d addresses' % len(urls))


def write_robots(report):
    root = site_root()
    if not root:
        return
    st = SeoSettings.load()
    # Product.html and Article.html are deliberately NOT blocked. They are
    # templates that forward an old ?p= / ?id= link to the real page; they carry
    # noindex, and blocking them from crawling would stop Google seeing either.
    lines = ['User-agent: *', 'Allow: /', '',
             'Disallow: /admin/', 'Disallow: /api/', 'Disallow: /dashboard/',
             'Disallow: /Enquiry']
    extra = (st.robots_extra or '').strip()
    if extra:
        lines += ['', extra]
    lines += ['', 'Sitemap: %s' % abs_url(st, '/sitemap.xml'), '']
    report.count(write(Path(root) / 'robots.txt', '\n'.join(lines)))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def live_url_set(pages, blog_urls):
    urls = {r.url_path for r in SeoMeta.objects.all()}
    urls |= {r.path for r in pages.values()}
    urls |= {p for p, _ in blog_urls}
    return urls


def bake_all(include_products=True, include_blog=True):
    """Everything. Takes the lock so two edits saved at once cannot interleave
    their writes into the same files."""
    report = Report()
    root = site_root()
    if not root:
        report.notes.append('The website files are not reachable from here (SITE_ROOT is not set), '
                            'so nothing was written.')
        return report
    with _LOCK:
        seed_pages(root)
        bake_static(report)
        pages = {}
        if include_products:
            pages = bake_products(report)
        else:
            pages = {p.entry_id: p for p in ProductPage.objects.all()}
        blog_urls = []
        if include_blog:
            try:
                from .blog import bake_blog
                blog_urls = bake_blog(report)
            except ImportError:
                blog_urls = []
        bake_redirects(report, live_url_set(pages, blog_urls))
        write_product_urls(pages, blog_urls, report)
        write_sitemap(pages, blog_urls, report)
        write_robots(report)
    return report


def bake_pages_only():
    """Cheap: just the 68 static pages. What a page's own SEO edit needs."""
    report = Report()
    if not site_root():
        report.notes.append('SITE_ROOT is not set; nothing written.')
        return report
    with _LOCK:
        seed_pages(site_root())
        bake_static(report)
        write_robots(report)
    return report


# ---------------------------------------------------------------------------
# Background rebuilds
# ---------------------------------------------------------------------------
_PENDING = {'timer': None, 'products': False, 'blog': False}
_PENDING_LOCK = threading.Lock()
DELAY_SECONDS = 2.0


def _run_pending():
    from django.db import connections
    with _PENDING_LOCK:
        want_products, want_blog = _PENDING['products'], _PENDING['blog']
        _PENDING.update(timer=None, products=False, blog=False)
    try:
        bake_all(include_products=want_products, include_blog=want_blog)
    except Exception:
        import logging
        logging.getLogger('seo').exception('background SEO rebuild failed')
    finally:
        connections.close_all()


def request_bake(products=True, blog=True):
    """Ask for a rebuild shortly, merging requests that arrive close together.

    Saving fifty rows in the product list would otherwise start fifty rebuilds
    of 650 files each. Two seconds after the *last* request, one rebuild runs
    in the background, so the edit that asked for it returns straight away.
    """
    with _PENDING_LOCK:
        _PENDING['products'] = _PENDING['products'] or products
        _PENDING['blog'] = _PENDING['blog'] or blog
        if _PENDING['timer'] is not None:
            _PENDING['timer'].cancel()
        t = threading.Timer(DELAY_SECONDS, _run_pending)
        t.daemon = True
        _PENDING['timer'] = t
        t.start()
