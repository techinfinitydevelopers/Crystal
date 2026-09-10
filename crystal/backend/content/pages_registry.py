"""The site's real pages, grouped for the dashboard's page picker.

Kept as a plain list here (not scanned from disk) because this Django project
and the static site are separate deployables -- the site's repo is not
guaranteed to be checked out next to this one in production. A few stray
export files that live in the site's repo root (design-tool leftovers, not
live pages) are deliberately left out.
"""

PAGES_REGISTRY = [
    ('Home', [
        ('index.html', 'Home'),
        ('index-v2.html', 'Home (v2)'),
    ]),
    ('Company', [
        ('About.html', 'About'),
        ('Contact.html', 'Contact'),
        ('Career.html', 'Careers'),
        ('Enquiry.html', 'Enquiry'),
        ('Quote.html', 'Request a quote'),
        ('Privacy.html', 'Privacy policy'),
        ('Terms.html', 'Terms'),
    ]),
    ('Content', [
        ('Blog.html', 'Blog'),
        ('Article.html', 'Article'),
        ('Catalogue.html', 'Catalogue'),
    ]),
    ('Brands', [
        ('Brands.html', 'Brands (all)'),
        ('Brand-Crystal.html', 'Crystal'),
        ('Brand-Crystalina.html', 'Crystalina'),
        ('Brand-SparkMate.html', 'SparkMate'),
        ('Brand-ValMate.html', 'ValMate'),
    ]),
    ('Products', [
        ('All-Products.html', 'All products'),
        ('Product.html', 'Product detail (shared template)'),
    ]),
    ('Cookware', [
        ('Cookware.html', 'Cookware (all)'),
        ('Cookware-Tripro.html', 'Tripro'),
        ('Cookware-Cast-Iron.html', 'Cast Iron'),
        ('Cookware-Non-Stick.html', 'Non-Stick'),
        ('Cookware-Non-Stick-Mini.html', 'Non-Stick Mini'),
        ('Cookware-Hard-Anodised.html', 'Hard Anodised'),
        ('Cookware-Sandwich-Bottom-Steel.html', 'Sandwich Bottom Steel'),
    ]),
    ('Kitchenware', [
        ('Kitchenware.html', 'Kitchenware (all)'),
        ('Kitchenware-Knives.html', 'Knives'),
        ('Kitchenware-Cutlery.html', 'Cutlery'),
        ('Kitchenware-Chopping-Boards.html', 'Chopping Boards'),
        ('Kitchenware-Kitchen-Tools.html', 'Kitchen Tools'),
        ('Kitchenware-Peelers.html', 'Peelers'),
        ('Kitchenware-Servers.html', 'Servers'),
        ('Kitchenware-Trolleys.html', 'Trolleys'),
        ('Kitchenware-Lighters.html', 'Lighters'),
        ('Kitchenware-Manual-Appliances.html', 'Manual Appliances'),
        ('Kitchenware-Water-Filter.html', 'Water Filter'),
    ]),
    ('Cleaning Aid', [
        ('Cleaning-Aid.html', 'Cleaning Aid (all)'),
        ('Cleaning-Aid-Brooms.html', 'Brooms'),
        ('Cleaning-Aid-Brush.html', 'Brush'),
        ('Cleaning-Aid-Scrubber.html', 'Scrubber'),
        ('Cleaning-Aid-Wipe.html', 'Wipe'),
        ('Cleaning-Aid-Wipers.html', 'Wipers'),
        ('Cleaning-Aid-Spin-Mops.html', 'Spin Mops'),
        ('Cleaning-Aid-Hand-Held-Mops.html', 'Hand Held Mops'),
        ('Cleaning-Aid-Bins.html', 'Bins'),
        ('Cleaning-Aid-Plunger.html', 'Plunger'),
        ('Cleaning-Aid-Sink-Organiser.html', 'Sink Organiser'),
    ]),
    ('Electric Appliances', [
        ('Electric-Appliances.html', 'Electric Appliances (all)'),
        ('Electric-Appliances-Air-Fryer.html', 'Air Fryer'),
        ('Electric-Appliances-OTG.html', 'OTG'),
        ('Electric-Appliances-Kettle.html', 'Kettle'),
        ('Electric-Appliances-Iron.html', 'Iron'),
        ('Electric-Appliances-Chimney.html', 'Chimney'),
        ('Electric-Appliances-Rice-Cooker.html', 'Rice Cooker'),
        ('Electric-Appliances-Food-Processor.html', 'Food Processor'),
        ('Electric-Appliances-Ice-Cream-Maker.html', 'Ice Cream Maker'),
        ('Electric-Appliances-JMG.html', 'JMG'),
    ]),
    ('Standalone categories', [
        ('Water-Bottle.html', 'Water Bottle'),
        ('Oil-Pourer-Sprayer.html', 'Oil Pourer & Sprayer'),
        ('Wood-Range.html', 'Wooden Range'),
        ('Pressure-Cooker.html', 'Pressure Cooker'),
        ('Cooktop.html', 'Cooktop'),
        ('Lunch-Box.html', 'Lunch Box'),
    ]),
]

# Flat lookup: filename -> friendly label
PAGE_LABELS = {fn: label for _, pages in PAGES_REGISTRY for fn, label in pages}
ALL_PAGES = list(PAGE_LABELS.keys())
