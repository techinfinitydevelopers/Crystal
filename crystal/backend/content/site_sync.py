"""Keep one page's dashboard rows in step with the page file itself.

The dashboard and the website share one tree on the VPS (settings.SITE_ROOT),
so the page editor can read the page it is about to show and add whatever the
page has gained since: a new `data-cms` section, a `data-cms-video`, a new
`data-block` band. It used to depend on `seed_page_sections` having run after
the deploy, and the deploy script on the server never runs it -- so a section
added to a page simply never appeared in the dashboard.

Only ever adds rows and refreshes reference columns. Nothing someone typed or
uploaded is touched.
"""
import json
import re
from html import unescape
from pathlib import Path

from django.conf import settings

from .models import PageBlock, PageSection

TAG = re.compile(r'<([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*)>', re.S)
ATTR = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("([^"]*)"|\'([^\']*)\')', re.S)


def _attrs(raw):
    return {m.group(1).lower(): unescape(m.group(3) if m.group(3) is not None else m.group(4))
            for m in ATTR.finditer(raw)}


def _humanise(key):
    words = re.sub(r'[-_]+', ' ', key).strip()
    words = re.sub(r'(\D)(\d+)\b', r'\1 \2', words)
    return words[:1].upper() + words[1:]


def site_file(filename):
    root = getattr(settings, 'SITE_ROOT', None)
    if not root:
        return None
    path = Path(root) / filename
    return path if path.is_file() else None


def manifest_rows(filename):
    root = getattr(settings, 'SITE_ROOT', None)
    if not root:
        return []
    path = Path(root) / 'tools' / 'cms-manifest.json'
    try:
        rows = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [r for r in rows if r.get('page') == filename]


def sync_page(page):
    """Add rows for anything editable on `page` that the dashboard lacks.

    Returns (sections_added, blocks_added). Safe to call on every visit to
    the editor: when the page has not changed it writes nothing.
    """
    path = site_file(page.filename)
    if path is None:
        return 0, 0
    html = path.read_text(encoding='utf-8', errors='replace')
    body = html[html.find('<body'):] if '<body' in html else html

    have = set(PageSection.objects.filter(page=page.filename)
               .values_list('section_key', flat=True))
    added = 0

    # 1. What the manifest already describes (labels, box sizes).
    for row in manifest_rows(page.filename):
        key = (row.get('key') or row.get('section_key') or '').strip()
        if not key or key in have:
            continue
        PageSection.objects.create(
            page=page.filename, section_key=key,
            kind=PageSection.IMAGE if row.get('kind') == 'image' else PageSection.TEXT,
            label=(row.get('label') or '')[:160],
            section=(row.get('section') or '')[:120],
            shipped_value=row.get('shipped') or '',
            expected_size=(row.get('box') or '')[:200])
        have.add(key)
        added += 1

    # 2. Anything tagged by hand since the manifest was written, and videos.
    block = ''
    for m in TAG.finditer(body):
        tag, attrs = m.group(1).lower(), _attrs(m.group(2))
        if attrs.get('data-block'):
            block = attrs['data-block']
        for attr_name, kind in (('data-cms-video', PageSection.VIDEO), ('data-cms', None)):
            key = attrs.get(attr_name)
            if not key or key in have:
                continue
            if kind is None:
                media_attr = attrs.get('data-cms-attr')
                is_image = tag in ('img', 'image-slot') or media_attr in ('src', 'poster')
                kind = PageSection.IMAGE if is_image else PageSection.TEXT
            if kind == PageSection.VIDEO:
                shipped = attrs.get('src', '')
            elif kind == PageSection.IMAGE:
                shipped = attrs.get(attrs.get('data-cms-attr') or 'src', '')
            else:
                shipped = ''
            PageSection.objects.create(
                page=page.filename, section_key=key, kind=kind,
                label=(attrs.get('data-cms-label') or _humanise(key))[:160],
                section=(block or key.split('-')[0])[:120],
                shipped_value=shipped)
            have.add(key)
            added += 1

    # 3. The bands whose order the dashboard may change.
    found = []
    blocks_added = 0
    for m in TAG.finditer(body):
        attrs = _attrs(m.group(2))
        key = attrs.get('data-block')
        if not key or key in found:
            continue
        found.append(key)
        position = len(found)
        label = attrs.get('data-block-label') or _humanise(key)
        existing = PageBlock.objects.filter(page=page, key=key).first()
        if existing is None:
            # A band new to the page goes where the page puts it, after any
            # reordering already saved -- not on top of position 1.
            PageBlock.objects.create(page=page, key=key, label=label,
                                     order=position, default_order=position)
            blocks_added += 1
            continue
        changes = {}
        if existing.default_order != position:
            changes['default_order'] = position
        if existing.label != label:
            changes['label'] = label
        if not existing.present:
            changes['present'] = True
        if changes:
            for f, v in changes.items():
                setattr(existing, f, v)
            existing.save(update_fields=list(changes))
    PageBlock.objects.filter(page=page).exclude(key__in=found).update(present=False)
    return added, blocks_added
