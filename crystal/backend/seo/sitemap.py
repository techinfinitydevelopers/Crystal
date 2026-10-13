"""Checking a sitemap file someone has uploaded, before it is served.

Whatever is accepted here becomes /sitemap.xml exactly as written, and a broken
one is worse than none: search engines drop a sitemap they cannot read and report
it as an error weeks later. So the file is read first, and refused with a reason
if it is not a sitemap.
"""
import re
import xml.etree.ElementTree as ET

MAX_BYTES = 10 * 1024 * 1024
MAX_URLS = 50000
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


class SitemapProblem(Exception):
    pass


def inspect(data):
    """Return (kind, count) for sitemap bytes, or raise SitemapProblem.

    kind is "urlset" for a list of pages, or "sitemapindex" for a list of other
    sitemaps. count is the number of entries in it.
    """
    if not data or not data.strip():
        raise SitemapProblem('The file is empty.')
    if len(data) > MAX_BYTES:
        raise SitemapProblem('The file is %.1f MB; search engines accept up to 10 MB uncompressed.'
                             % (len(data) / 1048576))
    head = data[:4096].lstrip()
    if head[:3] == b'\xef\xbb\xbf':
        data = data[3:]
    # An XML parser expands entities, and a file crafted around that can eat all
    # the memory on the server. A sitemap has no use for a DOCTYPE, so one is a
    # reason to refuse the file rather than to parse it carefully.
    if re.search(rb'<!\s*(DOCTYPE|ENTITY)', data[:200000], re.I):
        raise SitemapProblem('The file contains a DOCTYPE or ENTITY declaration, which a sitemap '
                             'never needs. Remove it and upload again.')
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SitemapProblem('This is not valid XML: %s.' % exc)
    tag = root.tag.split('}', 1)[-1]
    if tag not in ('urlset', 'sitemapindex'):
        raise SitemapProblem('The first element is <%s>; a sitemap starts with <urlset> '
                             '(a list of pages) or <sitemapindex> (a list of sitemaps).' % tag)
    child = 'url' if tag == 'urlset' else 'sitemap'
    locs = []
    for node in root:
        if node.tag.split('}', 1)[-1] != child:
            continue
        loc = next((c for c in node if c.tag.split('}', 1)[-1] == 'loc'), None)
        text = (loc.text or '').strip() if loc is not None else ''
        if not text:
            raise SitemapProblem('An entry has no <loc> address.')
        if not text.startswith(('http://', 'https://')):
            raise SitemapProblem('"%s" is not a full address; every <loc> must start with https://.' % text[:80])
        locs.append(text)
    if not locs:
        raise SitemapProblem('The sitemap lists nothing.')
    if len(locs) > MAX_URLS:
        raise SitemapProblem('It lists %d addresses; one sitemap holds up to 50,000. '
                             'Split it and upload a sitemap index instead.' % len(locs))
    return tag, len(locs)
