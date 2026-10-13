"""Writes search-engine copy and tracking code into the website's own files.

Why this is baked rather than fetched. Every other editable thing on this site
(banners, page sections, awards) is read from an API by the page after it loads.
That cannot work here: a title written in by JavaScript is read by almost
nothing. Google sometimes picks it up after rendering, every other crawler does
not, and WhatsApp, Facebook, X and LinkedIn never run scripts at all -- a shared
link shows whatever the *file* says. So the values have to be in the file.

Everything here is idempotent. Each thing this module owns sits between a pair of
marker comments, so running it twice leaves the file byte-identical, and a page
nobody has touched keeps its original text until the first run replaces it.
"""
import html as _html
import json
import re
import threading
from datetime import timezone as _tz
from pathlib import Path
from urllib.parse import quote

from django.conf import settings as dj_settings
from django.utils import timezone

from .models import ProductPage, Redirect, ScriptBlock, SeoMeta, SeoSettings

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
SEO_A, SEO_B = '<!-- seo:start -->', '<!-- seo:end -->'
HEAD_A, HEAD_B = '<!-- seo:head-start -->', '<!-- seo:head-end -->'
BODY_A, BODY_B = '<!-- seo:body-start -->', '<!-- seo:body-end -->'
FOOT_A, FOOT_B = '<!-- seo:foot-start -->', '<!-- seo:foot-end -->'
STUB_MARK = '<!-- seo:redirect -->'
GENERATED_MARK = '<!-- seo:generated -->'


def _block(a, b):
    return re.compile(re.escape(a) + r'.*?' + re.escape(b) + r'[ \t]*\r?\n?', re.S)


_MANAGED = [_block(SEO_A, SEO_B), _block(HEAD_A, HEAD_B),
            _block(BODY_A, BODY_B), _block(FOOT_A, FOOT_B)]

# What the pages shipped with before this existed: the Search Console meta and
# the GA4 snippet, hard-coded into every page's head. They now come from the
# settings screen, so the first run removes the originals; leaving them would
# count every visit twice.
_LEGACY_TRACKING = re.compile(
    r'<!--\s*Google Search Console[^>]*?-->\s*'
    r'<meta\s+name="google-site-verification"[^>]*>\s*'
    r'<!--\s*Google Analytics 4\s*-->\s*'
    r'<script\s+async\s+src="https://www\.googletagmanager\.com/gtag/js\?id=[^"]+"></script>\s*'
    r'<script>.*?</script>[ \t]*\r?\n?', re.S)

# Singleton tags in <head> that this module writes itself. Only ever applied to
# the head, never to the body, so page content cannot be touched by accident.
_HEAD_SINGLETONS = [
    re.compile(r'<meta\s+name=["\']description["\'][^>]*>[ \t]*\r?\n?', re.I),
    re.compile(r'<meta\s+name=["\']robots["\'][^>]*>[ \t]*\r?\n?', re.I),
    re.compile(r'<meta\s+name=["\']keywords["\'][^>]*>[ \t]*\r?\n?', re.I),
    re.compile(r'<link\s+rel=["\']canonical["\'][^>]*>[ \t]*\r?\n?', re.I),
    re.compile(r'<meta\s+(?:property|name)=["\'](?:og|twitter):[^"\']*["\'][^>]*>[ \t]*\r?\n?', re.I),
    re.compile(r'<script\s+type=["\']application/ld\+json["\']>.*?</script>[ \t]*\r?\n?', re.S | re.I),
    re.compile(r'<meta\s+name=["\']msvalidate\.01["\'][^>]*>[ \t]*\r?\n?', re.I),
]
_RE_TITLE = re.compile(r'<title>.*?</title>', re.S | re.I)
_RE_CHARSET = re.compile(r'<meta\s+charset=[^>]*>', re.I)
_RE_BODY_OPEN = re.compile(r'<body[^>]*>', re.I)

FALLBACK_OG_IMAGE = 'home-v3-assets/video/hero-poster.jpg'
TITLE_BUDGET = 60
DESC_BUDGET = 155


# ---------------------------------------------------------------------------
# Where things are
# ---------------------------------------------------------------------------
def site_root():
    """The website's file tree, or None when this process cannot see it."""
    root = getattr(dj_settings, 'SITE_ROOT', None)
    if not root:
        return None
    root = Path(root)
    return root if root.is_dir() else None


def read(path):
    with open(path, 'r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write(path, text):
    """Write only when it changed, so an untouched page keeps its mtime and a
    re-run does not look like an edit to anything watching the tree."""
    path = Path(path)
    try:
        if path.exists() and read(path) == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    return True


def esc(value):
    return _html.escape(str(value or ''), quote=True)


def clip(text, limit):
    """Cut at a word boundary, with an ellipsis, never mid-word."""
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:-')
    return (cut or text[:limit - 1]) + '…'


def abs_url(settings_row, path):
    base = settings_row.site_url.rstrip('/')
    if not path or path == '/':
        return base + '/'
    if path.startswith('http'):
        return path
    return base + (path if path.startswith('/') else '/' + path)


def asset_url(settings_row, ref):
    """A catalogue or upload reference as a full, correctly encoded address."""
    if not ref:
        return ''
    ref = str(ref)
    if ref.startswith(('http://', 'https://')):
        return ref
    return settings_row.site_url.rstrip('/') + '/' + quote(ref.lstrip('/'), safe='/')


def og_image_for(settings_row, own=None, root=None):
    if own:
        return asset_url(settings_row, getattr(own, 'name', own))
    if settings_row.default_og_image:
        return asset_url(settings_row, settings_row.default_og_image.name)
    if root and (Path(root) / FALLBACK_OG_IMAGE).exists():
        return asset_url(settings_row, FALLBACK_OG_IMAGE)
    return ''


# ---------------------------------------------------------------------------
# Page description
# ---------------------------------------------------------------------------
class PageInfo:
    """Everything one page needs written into it."""

    def __init__(self, path, title, description, **kw):
        self.path = path                      # '/About', '/' or '/products/x'
        self.title = title
        self.description = description
        self.keywords = kw.get('keywords', '')
        self.noindex = kw.get('noindex', False)
        self.canonical = kw.get('canonical', '')
        self.og_title = kw.get('og_title', '')
        self.og_description = kw.get('og_description', '')
        self.og_image = kw.get('og_image', '')
        self.og_type = kw.get('og_type', 'website')
        self.jsonld = kw.get('jsonld', [])
        self.base_href = kw.get('base_href', False)
        self.script_page = kw.get('script_page', '')   # name ScriptBlocks match
        self.inline = kw.get('inline', '')             # extra <head> lines
        self.fills = kw.get('fills', {})                # element id -> inner HTML


def meta_block(info, st):
    """The <head> lines that carry this page's search and social copy."""
    # A canonical typed in for this page always wins. Otherwise the page names
    # itself -- unless the team has switched that off in SEO settings, in which
    # case no canonical tag is written at all.
    explicit = (info.canonical or '').strip()
    if explicit.startswith('/') and not explicit.startswith('//'):
        explicit = abs_url(st, explicit)
    canonical = explicit or abs_url(st, info.path)
    write_canonical = bool(explicit) or st.auto_canonical
    robots = ('noindex,follow' if info.noindex
              else 'index,follow,max-image-preview:large,max-snippet:-1')
    og_title = info.og_title or info.title
    og_desc = info.og_description or info.description
    lines = [SEO_A]
    if info.description:
        lines.append('<meta name="description" content="%s">' % esc(info.description))
    if info.keywords:
        lines.append('<meta name="keywords" content="%s">' % esc(info.keywords))
    lines.append('<meta name="robots" content="%s">' % robots)
    if write_canonical:
        lines.append('<link rel="canonical" href="%s">' % esc(canonical))
    lines.append('<meta property="og:site_name" content="%s">' % esc('CRYSTAL'))
    lines.append('<meta property="og:locale" content="en_IN">')
    lines.append('<meta property="og:type" content="%s">' % esc(info.og_type))
    lines.append('<meta property="og:title" content="%s">' % esc(og_title))
    if og_desc:
        lines.append('<meta property="og:description" content="%s">' % esc(og_desc))
    lines.append('<meta property="og:url" content="%s">' % esc(canonical))
    if info.og_image:
        lines.append('<meta property="og:image" content="%s">' % esc(info.og_image))
    lines.append('<meta name="twitter:card" content="%s">'
                 % ('summary_large_image' if info.og_image else 'summary'))
    lines.append('<meta name="twitter:title" content="%s">' % esc(og_title))
    if og_desc:
        lines.append('<meta name="twitter:description" content="%s">' % esc(og_desc))
    if info.og_image:
        lines.append('<meta name="twitter:image" content="%s">' % esc(info.og_image))
    for doc in info.jsonld:
        # </ inside a string would end the script early; \/ is the same character.
        body = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        lines.append('<script type="application/ld+json">%s</script>' % body)
    # Anything else the page needs in its head lives inside the markers too, so
    # that running this again replaces it instead of stacking a second copy.
    if info.inline:
        lines.append(info.inline.rstrip())
    lines.append(SEO_B)
    return '\n'.join(lines) + '\n'


def tracking(placement, page_name):
    """Dashboard-managed code for one placement, honouring the page filter."""
    out = []
    for block in ScriptBlock.objects.filter(is_active=True, placement=placement):
        if block.applies_to(page_name):
            out.append('<!-- %s -->\n%s' % (esc(block.name), block.code.strip()))
    return out


def head_scripts_block(st, page_name, base_href=False):
    lines = [HEAD_A]
    if base_href:
        lines.append('<base href="/">')
    if st.search_console_code:
        lines.append('<meta name="google-site-verification" content="%s">' % esc(st.search_console_code))
    if st.bing_verification:
        lines.append('<meta name="msvalidate.01" content="%s">' % esc(st.bing_verification))
    if st.ga4_id:
        gid = esc(st.ga4_id.strip())
        lines.append('<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>' % gid)
        lines.append('<script>\n  window.dataLayer = window.dataLayer || [];\n'
                     '  function gtag(){dataLayer.push(arguments);}\n'
                     "  gtag('js', new Date());\n  gtag('config', '%s');\n</script>" % gid)
    lines.extend(tracking(ScriptBlock.HEAD, page_name))
    lines.append(HEAD_B)
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# The one transformation every page goes through
# ---------------------------------------------------------------------------
def fill_element(text, element_id, inner):
    """Replace the contents of a simple, non-nested element found by its id."""
    pat = re.compile(
        r'(<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid="%s"[^>]*>)(.*?)(</(?P=tag)>)' % re.escape(element_id),
        re.S)
    return pat.sub(lambda m: m.group(1) + inner + m.group(4), text, count=1)


def apply_to_html(source, info, st):
    """Return `source` with this page's SEO, tracking and baked content in it.

    Safe to run on its own output: anything this function wrote is removed first.

    Works on the text with plain newlines and puts the file's own line endings
    back at the end. Blocks written with one style into a file using the other
    would not match their own markers' trailing newline the next time round, and
    every run would rewrite every page.
    """
    crlf = source.count('\r\n') > source.count('\n') * 0.5
    out = _apply_lf(source.replace('\r\n', '\n'), info, st)
    return out.replace('\n', '\r\n') if crlf else out


def _apply_lf(source, info, st):
    # 1. clear what we own, wherever it sits
    text = source
    for rx in _MANAGED:
        text = rx.sub('', text)
    text = _LEGACY_TRACKING.sub('', text)

    # 2. split off the head so the singleton cleanup cannot reach the body
    split = re.search(r'</head\s*>', text, re.I)
    if not split:
        return source            # not a page we understand: leave it alone
    head, rest = text[:split.start()], text[split.start():]
    for rx in _HEAD_SINGLETONS:
        head = rx.sub('', head)
    # A malformed title (Terms.html shipped with a second <title> inside the
    # first) is repaired by replacing the whole span, not parsed.
    title_html = '<title>%s</title>' % esc(info.title)
    m_title = _RE_TITLE.search(head)
    if m_title:
        # Terms.html shipped as <title>Terms <title>CRYSTAL...</title>amp; ...
        # </title>: the first closing tag ends a title that was never finished,
        # and the rest of the sentence is left over as loose text in <head>.
        # Anything that looks like a stray tail up to a second </title> goes too.
        tail = head[m_title.end():]
        orphan = re.match(r'[^<]{1,120}</title>', tail)
        end = m_title.end() + (orphan.end() if orphan else 0)
        head = head[:m_title.start()] + title_html + head[end:]
    else:
        head = head + title_html + '\n'

    # 3. head scripts straight after the charset, as before
    page_name = info.script_page or 'index.html'
    block = head_scripts_block(st, page_name, info.base_href)
    m = _RE_CHARSET.search(head)
    if m:
        head = head[:m.end()] + '\n' + block.rstrip('\n') + head[m.end():]
    else:
        m2 = re.search(r'<head[^>]*>', head, re.I)
        head = head[:m2.end()] + '\n' + block + head[m2.end():]

    # 4. the meta block right after the title. It is followed directly by the
    # newline that already followed </title>, never by one of its own: removing
    # a block takes the newline after it, so adding one here would leave a blank
    # line behind on every run.
    t = _RE_TITLE.search(head)
    head = head[:t.end()] + '\n' + meta_block(info, st).rstrip('\n') + head[t.end():]
    text = head + rest

    # 5. body scripts
    bm = _RE_BODY_OPEN.search(text)
    if bm:
        body_start = tracking(ScriptBlock.BODY_START, page_name)
        if body_start:
            text = (text[:bm.end()] + '\n' + BODY_A + '\n' + '\n'.join(body_start)
                    + '\n' + BODY_B + text[bm.end():])
    close = text.lower().rfind('</body>')
    if close != -1:
        foot = tracking(ScriptBlock.BODY_END, page_name)
        if foot:
            text = (text[:close] + FOOT_A + '\n' + '\n'.join(foot) + '\n' + FOOT_B
                    + '\n' + text[close:])

    # 6. baked content, for crawlers that never run the page's script
    for element_id, inner in info.fills.items():
        text = fill_element(text, element_id, inner)
    return text
