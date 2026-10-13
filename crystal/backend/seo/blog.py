"""One real page per blog post, at /blog/<slug>.

Article.html is a single shared template that looks its post up by ?id=. For a
crawler that is one address showing whichever post it happens to be asked for,
and for a WhatsApp link it is the same bare card every time. Each post gets its
own file instead, with the title, summary, picture and the article text already
in it.

Two sources feed it. Posts written in the dashboard come from the database. The
three articles the site was launched with live inside Article.html's script, so
they are read back out of it; a dashboard post with the same slug wins.
"""
import html as _html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .bake import (PageInfo, abs_url, apply_to_html, asset_url, clip, esc,
                   og_image_for, read, site_root, write, GENERATED_MARK)
from .models import SeoSettings

STATIC_RE = re.compile(
    r'"(?P<slug>[a-z0-9-]+)":\s*\{\s*'
    r'tag:\s*"(?P<tag>[^"]*)",\s*'
    r'title:\s*"(?P<title>[^"]*)",\s*'
    r'date:\s*"(?P<date>[^"]*)",\s*'
    r'excerpt:\s*"(?P<excerpt>[^"]*)",\s*'
    r'img:\s*(?P<img>[^,\n]+),\s*'
    r'body:\s*`(?P<body>.*?)`', re.S)


def _plain(text):
    return re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))).strip()


def static_articles(root):
    """The articles Article.html ships with, parsed back out of its script."""
    f = Path(root) / 'Article.html'
    if not f.is_file():
        return {}
    text = read(f)
    base = re.search(r'const\s+U\s*=\s*"([^"]*)"', text)
    base = base.group(1) if base else ''
    out = {}
    for m in STATIC_RE.finditer(text):
        img = m.group('img').strip()
        im = re.match(r'U\s*\+\s*"([^"]*)"', img)
        img = (base + im.group(1)) if im else img.strip('"')
        when = None
        try:
            when = datetime.strptime(m.group('date').replace(',', ''), '%d %B %Y').replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        out[m.group('slug')] = {
            'slug': m.group('slug'), 'tag': m.group('tag'), 'title': m.group('title'),
            'date': m.group('date'), 'when': when, 'excerpt': m.group('excerpt'),
            'img': img, 'body': m.group('body'), 'author': 'Team Crystal',
            'meta_title': '', 'meta_description': '', 'source': 'file',
        }
    return out


def _fmt_date(dt):
    return '%d %s %d' % (dt.day, dt.strftime('%B'), dt.year) if dt else ''


def db_posts():
    try:
        from blog.models import Blog
    except Exception:
        return []
    out = []
    for p in Blog.objects.filter(is_published=True).select_related('category'):
        out.append({
            'slug': p.slug, 'tag': p.category.name if p.category else '',
            'title': p.title, 'date': _fmt_date(p.published_at), 'when': p.published_at,
            'excerpt': p.excerpt, 'img': p.featured_image.url if p.featured_image else '',
            'body': p.content or '', 'author': p.author or 'Team Crystal',
            'meta_title': p.meta_title, 'meta_description': p.meta_description, 'source': 'db',
        })
    return out


def all_posts(root):
    posts = {s: a for s, a in static_articles(root).items()}
    for p in db_posts():          # a dashboard post replaces a shipped one of the same slug
        posts[p['slug']] = p
    return posts


def article_info(post, st, root):
    path = '/blog/%s' % post['slug']
    title = post['meta_title'] or clip(post['title'], 60 - len(' | CRYSTAL')) + ' | CRYSTAL'
    desc = post['meta_description'] or clip(post['excerpt'] or _plain(post['body']), 155)
    image = asset_url(st, post['img']) if post['img'] else og_image_for(st, None, root)
    when = post['when']
    doc = {
        '@context': 'https://schema.org', '@type': 'BlogPosting',
        'headline': clip(post['title'], 110), 'description': desc,
        'author': {'@type': 'Organization' if post['author'] == 'Team Crystal' else 'Person',
                   'name': post['author']},
        'publisher': {'@type': 'Organization', 'name': st.organization_name,
                      'logo': {'@type': 'ImageObject', 'url': abs_url(st, '/favicon.svg')}},
        'mainEntityOfPage': abs_url(st, path),
    }
    if image:
        doc['image'] = [image]
    if when:
        doc['datePublished'] = when.astimezone(timezone.utc).strftime('%Y-%m-%d')
    crumbs = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': abs_url(st, '/')},
            {'@type': 'ListItem', 'position': 2, 'name': 'Knowledge Centre', 'item': abs_url(st, '/Blog')},
            {'@type': 'ListItem', 'position': 3, 'name': post['title'], 'item': abs_url(st, path)},
        ],
    }
    fills = {
        'crumbTitle': esc(post['title']), 'artTag': esc(post['tag']),
        'artTitle': esc(post['title']), 'artDate': esc(post['date']),
        'artBody': post['body'],
    }
    return PageInfo(
        path, title, desc, og_title=title, og_description=desc, og_image=image,
        og_type='article', base_href=True, script_page='Article.html',
        jsonld=[doc, crumbs],
        inline='<script>window.__ARTICLE_ID__=%s;</script>' % json.dumps(post['slug']),
        fills=fills), image


def bake_blog(report):
    """Write every post's page. Returns [(path, last-modified)] for the sitemap."""
    root = site_root()
    if not root:
        return []
    template_path = Path(root) / 'Article.html'
    if not template_path.is_file():
        return []
    st = SeoSettings.load()
    template = read(template_path)
    out_dir = Path(root) / 'blog'
    posts = all_posts(root)
    live, urls = set(), []
    for slug, post in sorted(posts.items()):
        try:
            info, image = article_info(post, st, root)
            body = apply_to_html(template, info, st)
            if image:
                body = body.replace('<image-slot id="artHero" src=""',
                                    '<image-slot id="artHero" src="%s"' % esc(image), 1)
            if GENERATED_MARK not in body:
                body = body.replace('<head>', '<head>' + chr(10) + GENERATED_MARK, 1)
            report.count(write(out_dir / (slug + '.html'), body))
            live.add(slug + '.html')
            urls.append(('/blog/%s' % slug, post['when']))
        except Exception as exc:
            report.skipped.append('blog %s: %s' % (slug, exc))
    if out_dir.is_dir():
        for f in out_dir.glob('*.html'):
            if f.name in live:
                continue
            try:
                head = read(f)[:600]
            except OSError:
                continue
            if GENERATED_MARK in head:
                f.unlink()
                report.removed += 1
    return urls
