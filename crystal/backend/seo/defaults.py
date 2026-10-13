"""Starting copy for the pages that had none, and the rules for the rest.

Only pages whose current title or description is missing, a placeholder, or
broken get entries in COPY. Everything else keeps what it already says -- the
category pages were written carefully and were not touched -- until the SEO team
changes it in the dashboard.

Every claim below comes from the website's own text: "since 1971", the four
brand names and their taglines, the two addresses on the Contact page. Nothing
here is invented, because this ends up in Google.
"""

# filename -> (title, description)
COPY = {
    'index.html': (
        'Crystal Cook N Serve | Kitchenware, Cookware & Cleaning Aids',
        'Crystal Cook N Serve makes kitchenware, cookware, cutlery, storage and '
        'cleaning aids for Indian homes — trusted since 1971 across four brands.',
    ),
    'About.html': (
        'About Crystal | Indian Kitchenware Maker Since 1971',
        'Crystal Cook N Serve has grown alongside the Indian kitchen since 1971 — '
        'from precision gas lighters to cookware, cutlery, storage and cleaning aids.',
    ),
    'All-Products.html': (
        'All Products | Cookware, Kitchenware & Appliances | CRYSTAL',
        'Browse the full Crystal range — cookware, kitchenware, cleaning aids and '
        'electric appliances across Crystal, Crystalina, SparkMate and ValMate.',
    ),
    'Brands.html': (
        'Our Brands | Crystal, Crystalina, SparkMate & ValMate',
        'Explore Crystal (World of Kitchenware), Crystalina (Splendid Finish), '
        'SparkMate (Cleaning Simplified) and ValMate (Value for Money).',
    ),
    'Brand-Crystal.html': (
        'Crystal | World of Kitchenware | CRYSTAL',
        'Crystal — the World of Kitchenware. Browse the Crystal range of cookware, '
        'cutlery, lighters and everyday kitchen tools from Crystal Cook N Serve.',
    ),
    'Brand-Crystalina.html': (
        'Crystalina | Splendid Finish | CRYSTAL',
        'Crystalina — Splendid Finish. Explore the Crystalina range from '
        'Crystal Cook N Serve Products.',
    ),
    'Brand-SparkMate.html': (
        'SparkMate | Cleaning Simplified | CRYSTAL',
        'SparkMate — Cleaning Simplified. Spin mops, brushes, wipers, scrubbers '
        'and cleaning aids from Crystal Cook N Serve Products.',
    ),
    'Brand-ValMate.html': (
        'ValMate | Value for Money | CRYSTAL',
        'ValMate — Value for Money. Practical storage, flasks and home solutions '
        'from Crystal Cook N Serve Products.',
    ),
    'Blog.html': (
        'Knowledge Centre | Kitchen Guides & Tips | CRYSTAL',
        'Kitchen know-how from Crystal — cookware care, buying guides and everyday '
        'cooking tips for Indian homes.',
    ),
    'Career.html': (
        'Careers at Crystal | Join Crystal Cook N Serve',
        'See current openings at Crystal Cook N Serve Products and join the team '
        'behind the Crystal family of kitchenware brands.',
    ),
    'Catalogue.html': (
        'Product Catalogue 2026-27 | Download PDF | CRYSTAL',
        'Download the Crystal 2026-27 product catalogue — cookware, kitchenware, '
        'cleaning aids and electric appliances across four brands.',
    ),
    'Contact.html': (
        'Contact Crystal | Rajkot Factory & Mumbai Office',
        'Reach Crystal Cook N Serve Products: manufacturing at G.I.D.C Metoda, Rajkot '
        'and corporate office at Sahar Plaza, Andheri (East), Mumbai. 022-49702803.',
    ),
    'Quote.html': (
        'Request a Quote | Trade & Bulk Enquiries | CRYSTAL',
        'Ask Crystal Cook N Serve for a quote on kitchenware, cookware, cleaning aids '
        'and electric appliances. Tell us what you need and we will get back to you.',
    ),
    'Enquiry.html': (
        'Your Enquiry List | CRYSTAL',
        'The products you have selected to enquire about from Crystal Cook N Serve.',
    ),
    'Privacy.html': (
        'Privacy Policy | CRYSTAL',
        'How Crystal Cook N Serve Products collects, uses and protects the information '
        'you share through this website.',
    ),
    'Terms.html': (
        'Terms & Conditions | CRYSTAL',
        'The terms that apply when you use the Crystal Cook N Serve Products website '
        'and send an enquiry.',
    ),
    'Product.html': (
        'Product | CRYSTAL',
        'Crystal Cook N Serve product details.',
    ),
    'Article.html': (
        'Knowledge Centre | CRYSTAL',
        'Kitchen know-how from Crystal Cook N Serve.',
    ),
}

# Pages that must stay out of search results. The strays are design-tool exports
# that were never live pages but sit in the same folder and would be served.
NOINDEX = {
    'Enquiry.html', 'Product.html', 'Article.html', 'index-v2.html',
    'index-old-v1.html', 'CRYSTAL Home.html', 'CRYSTAL Light.html', 'LOUD Agency.html',
}
STRAYS = {'index-old-v1.html', 'CRYSTAL Home.html', 'CRYSTAL Light.html', 'LOUD Agency.html'}
# Duplicates of another page, so their canonical points there.
CANONICAL_OF = {'index-v2.html': 'index.html'}

# Left out of sitemap.xml: hidden pages, plus ones with nothing to find.
NOT_IN_SITEMAP = NOINDEX | {'Quote.html'}

PRIORITY = {
    'index.html': '1.0', 'All-Products.html': '0.9', 'Brands.html': '0.8',
    'About.html': '0.6', 'Contact.html': '0.6', 'Catalogue.html': '0.6',
    'Blog.html': '0.6', 'Career.html': '0.4', 'Privacy.html': '0.2',
    'Terms.html': '0.2', 'Quote.html': '0.4',
}
HUBS = {'Cookware.html', 'Kitchenware.html', 'Cleaning-Aid.html',
        'Electric-Appliances.html', 'Water-Bottle.html', 'Pressure-Cooker.html',
        'Cooktop.html', 'Oil-Pourer-Sprayer.html', 'Wood-Range.html', 'Lunch-Box.html'}
BRAND_PAGES = {'Brand-Crystal.html', 'Brand-Crystalina.html',
               'Brand-SparkMate.html', 'Brand-ValMate.html'}

# A sub-category page's parent, for the breadcrumb trail.
PARENT_PREFIXES = [
    ('Cookware-', 'Cookware.html'),
    ('Kitchenware-', 'Kitchenware.html'),
    ('Cleaning-Aid-', 'Cleaning-Aid.html'),
    ('Electric-Appliances-', 'Electric-Appliances.html'),
    ('Brand-', 'Brands.html'),
]


def priority_for(page):
    if page in PRIORITY:
        return PRIORITY[page]
    if page in HUBS or page in BRAND_PAGES:
        return '0.8'
    return '0.7'


def parent_of(page):
    for prefix, parent in PARENT_PREFIXES:
        if page.startswith(prefix):
            return parent
    return None


BRAND_NAMES = {
    'crystal': 'Crystal', 'crystalina': 'Crystalina',
    'sparkmate': 'SparkMate', 'valmate': 'ValMate',
}
BRAND_PAGE_FOR = {
    'crystal': 'Brand-Crystal.html', 'crystalina': 'Brand-Crystalina.html',
    'sparkmate': 'Brand-SparkMate.html', 'valmate': 'Brand-ValMate.html',
}
