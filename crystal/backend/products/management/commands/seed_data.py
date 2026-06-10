"""
Seed command — populates brands, categories, marketplaces, products,
variants, and specs from the hardcoded frontend JS data.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from products.models import (
    Brand, Category, Product, ProductVariant,
    ProductSpecification, Marketplace,
)

BRANDS = [
    {
        "slug": "crystal",
        "name": "Crystal",
        "tagline": "World of Kitchenware",
        "description": (
            "From the gas lighter that started it all to a full world of kitchen "
            "essentials — cookware, cutlery, lighters and appliances trusted in "
            "Indian homes since 1971."
        ),
    },
    {
        "slug": "crystalina",
        "name": "Crystalina",
        "tagline": "Splendid Finish",
        "description": (
            "Premium stainless-steel serveware and dinnerware with a splendid "
            "mirror finish — where everyday dining feels like an occasion."
        ),
    },
    {
        "slug": "sparkmate",
        "name": "SparkMate",
        "tagline": "Cleaning Simplified",
        "description": (
            "Effortless cleaning essentials — spin mops, brooms, wipers and more "
            "— for a sparkling, low-effort home."
        ),
    },
    {
        "slug": "valmate",
        "name": "ValMate",
        "tagline": "Value for Money",
        "description": (
            "Smart everyday value — storage, flasks and bottles that keep food "
            "fresh and drinks at the right temperature, built for modern Indian homes."
        ),
    },
]

CATEGORIES = [
    # ── Main categories (no parent)
    {"slug": "cookware",            "name": "Cookware",             "parent": None},
    {"slug": "kitchenware",         "name": "Kitchenware",          "parent": None},
    {"slug": "cleaning-aid",        "name": "Cleaning Aid",         "parent": None},
    {"slug": "electric-appliances", "name": "Electric Appliances",  "parent": None},
    # ── Cookware sub-categories
    {"slug": "tripro",              "name": "Tripro",               "parent": "cookware"},
    {"slug": "cast-iron",           "name": "Cast Iron",            "parent": "cookware"},
    {"slug": "non-stick",           "name": "Non-Stick",            "parent": "cookware"},
    {"slug": "non-stick-mini",      "name": "Non-Stick Mini",       "parent": "cookware"},
    {"slug": "sandwich-bottom",     "name": "Sandwich Bottom Steel","parent": "cookware"},
    {"slug": "hard-anodised",       "name": "Hard Anodised",        "parent": "cookware"},
    # ── Kitchenware sub-categories
    {"slug": "lighters",            "name": "Lighters",             "parent": "kitchenware"},
    {"slug": "knives",              "name": "Knives",               "parent": "kitchenware"},
    {"slug": "peelers",             "name": "Peelers",              "parent": "kitchenware"},
    {"slug": "chopping-boards",     "name": "Chopping Boards",      "parent": "kitchenware"},
    {"slug": "trolleys",            "name": "Trolleys",             "parent": "kitchenware"},
    {"slug": "kitchen-tools",       "name": "Kitchen Tools",        "parent": "kitchenware"},
    {"slug": "manual-appliances",   "name": "Manual Kitchen Appliances", "parent": "kitchenware"},
    {"slug": "cutlery",             "name": "Cutlery",              "parent": "kitchenware"},
    {"slug": "servers",             "name": "Servers",              "parent": "kitchenware"},
    {"slug": "water-filter",        "name": "Water Filter",         "parent": "kitchenware"},
    # ── Cleaning Aid sub-categories
    {"slug": "spin-mops",           "name": "Spin Mops",            "parent": "cleaning-aid"},
    {"slug": "hand-held-mops",      "name": "Hand Held Mops",       "parent": "cleaning-aid"},
    {"slug": "broom-dust-pans",     "name": "Broom & Dust Pans",    "parent": "cleaning-aid"},
    {"slug": "wipers",              "name": "Wipers",               "parent": "cleaning-aid"},
    {"slug": "plunger",             "name": "Plunger",              "parent": "cleaning-aid"},
    {"slug": "brush",               "name": "Brush",                "parent": "cleaning-aid"},
    {"slug": "scrubber-scourer",    "name": "Scrubber & Scourer",   "parent": "cleaning-aid"},
    {"slug": "bins",                "name": "Bins",                 "parent": "cleaning-aid"},
    {"slug": "sink-organiser",      "name": "Sink Organiser",       "parent": "cleaning-aid"},
    # ── Electric Appliances sub-categories
    {"slug": "chimney",             "name": "Chimney",              "parent": "electric-appliances"},
    {"slug": "kettle",              "name": "Kettle",               "parent": "electric-appliances"},
    {"slug": "iron",                "name": "Iron",                 "parent": "electric-appliances"},
    {"slug": "ice-cream-maker",     "name": "Ice Cream Maker",      "parent": "electric-appliances"},
    {"slug": "otg",                 "name": "OTG",                  "parent": "electric-appliances"},
    {"slug": "air-fryer",           "name": "Air Fryer",            "parent": "electric-appliances"},
    {"slug": "rice-cooker",         "name": "Rice Cooker",          "parent": "electric-appliances"},
    {"slug": "food-processor",      "name": "Food Processor",       "parent": "electric-appliances"},
    {"slug": "jmg",                 "name": "JMG",                  "parent": "electric-appliances"},
    # ── Also explore (serveware / storage / flasks — mapped under kitchenware for now)
    {"slug": "water-bottle",        "name": "Water Bottle",         "parent": "kitchenware"},
    {"slug": "pressure-cooker-cat", "name": "Pressure Cooker",      "parent": "cookware"},
    {"slug": "lunch-box",           "name": "Lunch Box",            "parent": "kitchenware"},
]

MARKETPLACES = [
    {"slug": "amazon",   "name": "Amazon"},
    {"slug": "flipkart", "name": "Flipkart"},
    {"slug": "jiomart",  "name": "JioMart"},
    {"slug": "meesho",   "name": "Meesho"},
]

U = "https://proj.leo9studio.in/wp-content/uploads/"

PRODUCTS = [
    # CRYSTAL — Lighters
    {
        "id": "aristo-lighter",
        "name": "Aristo SS Lighter",
        "brand": "crystal", "category": "lighters",  # sub of kitchenware
        "collection": "Classic Lighters",
        "tags": ["Stainless Steel", "Refillable"],
        "intro": "A sure spark for every Indian kitchen.",
        "description": (
            "The Aristo SS lighter pairs a premium stainless-steel body with reliable, "
            "single-press ignition. Refillable and built to last, it's the dependable "
            "everyday lighter Crystal made its name on."
        ),
        "highlight": "Refillable stainless-steel gas lighter with a sure, single-press spark.",
        "image_url": "about-assets/prod-1.jpg",
        "variants": ["Standard"],
        "specs": {},
    },
    {
        "id": "slimline-lighter",
        "name": "Slimline Gas Lighter 305mm",
        "brand": "crystal", "category": "lighters",  # sub of kitchenware
        "collection": "Classic Lighters",
        "tags": ["Long Reach", "Flintless"],
        "intro": "Long reach, slim profile.",
        "description": (
            "Designed for deep burners, gas stoves and outdoor grills, the Slimline "
            "keeps hands clear of the flame. A refillable, flintless mechanism delivers "
            "a clean spark every time."
        ),
        "highlight": "Long-reach slimline lighter for deep burners and outdoor grills.",
        "image_url": "about-assets/prod-2.jpg",
        "variants": ["305 mm", "380 mm"],
        "specs": {},
    },
    # CRYSTAL — Cutlery
    {
        "id": "knife-set-5pc",
        "name": "5-Pc Surgical Steel Knife Set",
        "brand": "crystal", "category": "knives",
        "collection": "Surgical Steel Knives",
        "tags": ["Surgical Steel", "Set of 5"],
        "intro": "India's first surgical-steel knives.",
        "description": (
            "A complete five-piece set forged from high-carbon surgical stainless steel "
            "that holds its edge for years. From paring to chef's knife, every blade "
            "brings professional precision to your kitchen."
        ),
        "highlight": "India's first surgical-steel knives — a full set that stays sharp for years.",
        "image_url": U + "2026/01/Crystal-5-Pcs-Knife-Set.jpg",
        "variants": ["Set of 5", "Set of 8"],
        "specs": {},
    },
    {
        "id": "chef-knife",
        "name": "Laser-Edge Chef Knife",
        "brand": "crystal", "category": "knives",
        "collection": "Surgical Steel Knives",
        "tags": ["Laser Edge", "Ergonomic"],
        "intro": "Laser-honed precision.",
        "description": (
            "A balanced, full-tang chef knife with a laser-honed edge for clean, "
            "effortless cuts. The ergonomic handle keeps prep comfortable, meal after meal."
        ),
        "highlight": "Precision laser-honed edge for clean, effortless cuts every time.",
        "image_url": U + "2026/04/Knife-2.jpg",
        "variants": ["8 inch", "Single"],
        "specs": {},
    },
    # CRYSTAL — Appliances
    {
        "id": "chimney",
        "name": "Auto-Clean Chimney 90cm",
        "brand": "crystal", "category": "chimney",
        "collection": "Modern Appliances",
        "tags": ["Auto-Clean", "Silent"],
        "intro": "A grease-free, silent kitchen.",
        "description": (
            "Powerful suction clears smoke and odour while auto-clean technology keeps "
            "maintenance effortless. Sleek, quiet and built for the modern Indian kitchen."
        ),
        "highlight": "Powerful suction with auto-clean tech for a grease-free kitchen.",
        "image_url": U + "2026/04/8.jpg",
        "variants": ["60 cm", "90 cm"],
        "specs": {"Suction": "1200 m³/hr", "Filter": "Auto-clean baffle", "Compatibility": "220–240V"},
    },
    {
        "id": "kettle",
        "name": "Electric Kettle 1.5L",
        "brand": "crystal", "category": "kettle",
        "collection": "Modern Appliances",
        "tags": ["1.5L", "Auto Cut-off"],
        "intro": "Fast-boil convenience.",
        "description": (
            "A 1.5L stainless-steel electric kettle with rapid boil, auto cut-off and "
            "a cool-touch body. Perfect for tea, coffee and quick cooking."
        ),
        "highlight": "Fast-boil stainless kettle with auto cut-off and cool-touch body.",
        "image_url": U + "2026/04/5.jpg",
        "variants": ["1.5 L", "1.8 L"],
        "specs": {"Capacity": "1.5 L", "Power": "1500 W", "Body": "Stainless steel"},
    },
    # CRYSTALINA — Serveware
    {
        "id": "serving-set",
        "name": "Mirror-Finish Serving Set",
        "brand": "crystalina", "category": "servers",
        "collection": "Splendid Serveware",
        "tags": ["Mirror Finish", "Food-Grade"],
        "intro": "Dining, elevated.",
        "description": (
            "A mirror-finish stainless serving set that turns everyday meals into "
            "occasions. Heavy-gauge, food-safe and effortless to clean."
        ),
        "highlight": "Gleaming stainless serveware that turns everyday meals into occasions.",
        "image_url": "about-assets/prod-3.jpg",
        "variants": ["3 Pc", "5 Pc"],
        "specs": {},
    },
    {
        "id": "hot-pot-casserole",
        "name": "Insulated Hot-Pot Casserole",
        "brand": "crystalina", "category": "servers",
        "collection": "Splendid Serveware",
        "tags": ["Insulated", "Stay-Warm"],
        "intro": "Warm meals, for hours.",
        "description": (
            "A double-wall insulated casserole that keeps rotis and curries hot long "
            "after they leave the stove. Splendid finish outside, practical inside."
        ),
        "highlight": "Double-wall casserole that keeps rotis and curries warm for hours.",
        "image_url": "about-assets/prod-4.jpg",
        "variants": ["1.5 L", "2.5 L", "3.5 L"],
        "specs": {},
    },
    {
        "id": "thali-set",
        "name": "Steel Dinner Thali Set",
        "brand": "crystalina", "category": "servers",
        "collection": "Elite Dinnerware",
        "tags": ["Heavy Gauge", "Family Set"],
        "intro": "Built for daily dining.",
        "description": (
            "A heavy-gauge steel thali set with Crystalina's signature splendid finish "
            "— generously sized and made for the whole family."
        ),
        "highlight": "Heavy-gauge thali set with a splendid finish, built for daily dining.",
        "image_url": "about-assets/prod-5.jpg",
        "variants": ["Set of 2", "Set of 4", "Set of 6"],
        "specs": {},
    },
    # CRYSTAL — Cookware
    {
        "id": "triply-frypan",
        "name": "Tri-Ply Frypan 24cm",
        "brand": "crystal", "category": "tripro",
        "collection": "Tri-Ply Pro",
        "tags": ["Tri-Ply", "Induction"],
        "intro": "Pro-grade, even heat.",
        "description": (
            "Three bonded layers of steel and aluminium spread heat evenly for perfect "
            "searing and sautéing. Induction-ready and built to last a lifetime of cooking."
        ),
        "highlight": "Three bonded layers for even heat and pro-grade searing.",
        "image_url": U + "2026/04/Tri-Pro-2-1.jpg",
        "variants": ["22 cm", "24 cm", "26 cm"],
        "specs": {"Material": "Tri-ply (steel-alu-steel)", "Diameter": "24 cm"},
    },
    {
        "id": "nonstick-kadai",
        "name": "Platinum Non-Stick Kadai",
        "brand": "crystal", "category": "non-stick",
        "collection": "Platinum Non-Stick",
        "tags": ["Non-Stick", "Low-Oil"],
        "intro": "Healthier, low-oil cooking.",
        "description": (
            "A 3-coat platinum non-stick kadai built to DuPont-grade standards. Food "
            "releases cleanly with minimal oil, and clean-up takes seconds."
        ),
        "highlight": "3-coat platinum non-stick, DuPont-grade, for healthier low-oil cooking.",
        "image_url": U + "2026/05/CTV-097.jpg",
        "variants": ["2 L", "2.5 L", "3 L"],
        "specs": {"Coating": "3-coat platinum non-stick", "Capacity": "2.5 L", "Diameter": "24 cm"},
    },
    {
        "id": "pressure-cooker",
        "name": "Tri-Pro Pressure Cooker 3L",
        "brand": "crystal", "category": "tripro",
        "collection": "Tri-Pro Pro",
        "tags": ["Induction", "Triply"],
        "intro": "Cook faster, every day.",
        "description": (
            "An induction-ready triply pressure cooker that saves fuel and time on "
            "every meal, with a secure locking system and even-heat base."
        ),
        "highlight": "Induction-ready triply cooker that saves fuel and time on every meal.",
        "image_url": U + "2026/04/Pressure-Cooker-5.jpg",
        "variants": ["3 L", "5 L", "7.5 L"],
        "specs": {"Material": "Triply stainless steel", "Capacity": "3 L", "Safety": "Locking lid + valve"},
    },
    {
        "id": "cast-iron-tawa",
        "name": "Heritage Cast Iron Tawa",
        "brand": "crystal", "category": "cast-iron",
        "collection": "Heritage Cast Iron",
        "tags": ["Cast Iron", "Pre-Seasoned"],
        "intro": "Heritage cooking, modernised.",
        "description": (
            "A pre-seasoned cast iron tawa that delivers steady, retained heat for "
            "perfect rotis and dosas — and gets better with every use."
        ),
        "highlight": "Pre-seasoned cast iron that gets better with every use.",
        "image_url": U + "2026/04/CPC_023.jpg",
        "variants": ["25 cm", "28 cm"],
        "specs": {"Material": "Pre-seasoned cast iron", "Diameter": "28 cm"},
    },
    # VALMATE — Storage
    {
        "id": "container-set",
        "name": "Airtight Container Set",
        "brand": "valmate", "category": "kitchen-tools",
        "collection": "Lock-Fresh Containers",
        "tags": ["Airtight", "Set of 6"],
        "intro": "Freshness, locked in.",
        "description": (
            "A set of leak-proof, airtight containers that keep food fresher for longer. "
            "Stackable, food-safe and fridge-to-table ready."
        ),
        "highlight": "Leak-proof, airtight containers that lock freshness in.",
        "image_url": "about-assets/prod-6.jpg",
        "variants": ["Set of 3", "Set of 6", "Set of 9"],
        "specs": {},
    },
    {
        "id": "storage-jars",
        "name": "Modular Storage Jars",
        "brand": "valmate", "category": "kitchen-tools",
        "collection": "Modular Kitchen",
        "tags": ["Stackable", "BPA-Free"],
        "intro": "Order for every shelf.",
        "description": (
            "Modular, stackable jars that bring tidy order to your kitchen. BPA-free "
            "and crystal-clear so you always see what's inside."
        ),
        "highlight": "Stackable modular jars that bring order to every shelf.",
        "image_url": "about-assets/prod-7.jpg",
        "variants": ["Small", "Medium", "Large"],
        "specs": {},
    },
    {
        "id": "lunch-box",
        "name": "Steel Lunch Box 3-Tier",
        "brand": "valmate", "category": "lunch-box",
        "collection": "On-the-Go",
        "tags": ["Insulated", "Leak-Proof"],
        "intro": "Warm lunches, on the go.",
        "description": (
            "An insulated three-tier steel tiffin that keeps lunch warm till noon. "
            "Leak-proof and built for daily commutes."
        ),
        "highlight": "Insulated three-tier tiffin that keeps lunch warm till noon.",
        "image_url": "about-assets/prod-8.jpg",
        "variants": ["2 Tier", "3 Tier"],
        "specs": {},
    },
    # SPARKMATE — Cleaning
    {
        "id": "spin-mop",
        "name": "360° Spin Mop",
        "brand": "sparkmate", "category": "spin-mops",
        "collection": "Spin & Clean",
        "tags": ["360° Spin", "Hands-Free"],
        "intro": "Hands-free, sparkling floors.",
        "description": (
            "A single-bucket 360° spin system that wrings the mop for you. "
            "Lightweight, sturdy and quick to dry."
        ),
        "highlight": "Single-bucket spin system for hands-free wringing and a sparkling floor.",
        "image_url": U + "2026/04/Spin-Mops-2.jpg",
        "variants": ["Standard", "Pro"],
        "specs": {},
    },
    {
        "id": "spin-mop-pro",
        "name": "Easy-Press Spin Mop Pro",
        "brand": "sparkmate", "category": "spin-mops",
        "collection": "Spin & Clean",
        "tags": ["Foot Pedal", "Microfibre"],
        "intro": "Foot-pedal spin power.",
        "description": (
            "An upgraded spin mop with an easy foot pedal and high-absorbency "
            "microfibre head that lifts grime fast."
        ),
        "highlight": "Foot-pedal spin with a microfibre head that lifts grime fast.",
        "image_url": U + "2026/05/SMM013-1024x1024.jpg",
        "variants": ["Pro", "Pro Max"],
        "specs": {},
    },
    {
        "id": "wiper-brush",
        "name": "Floor Wiper & Brush Combo",
        "brand": "sparkmate", "category": "wipers",
        "collection": "Sparkle Essentials",
        "tags": ["Combo", "Everyday"],
        "intro": "Quick, streak-free cleaning.",
        "description": (
            "An everyday wiper and brush combo for fast, effortless cleaning across "
            "floors and surfaces."
        ),
        "highlight": "Everyday wiper and brush set for quick, streak-free cleaning.",
        "image_url": U + "2026/04/13.jpg",
        "variants": ["Combo"],
        "specs": {},
    },
    # VALMATE — Flasks
    {
        "id": "vacuum-flask",
        "name": "Vacuum Flask 1L",
        "brand": "valmate", "category": "water-bottle",
        "collection": "Thermo Lock",
        "tags": ["24h Hot/Cold", "1L"],
        "intro": "24 hours hot or cold.",
        "description": (
            "A double-wall vacuum flask in rugged 18/8 steel that holds temperature "
            "for up to 24 hours. Leak-proof and travel-ready."
        ),
        "highlight": "Double-wall vacuum flask that keeps drinks hot or cold for 24 hours.",
        "image_url": U + "2026/04/10.jpg",
        "variants": ["500 ml", "750 ml", "1 L"],
        "specs": {"Capacity": "1 L"},
    },
    {
        "id": "sipper-bottle",
        "name": "Insulated Sipper Bottle",
        "brand": "valmate", "category": "water-bottle",
        "collection": "Thermo Lock",
        "tags": ["Leak-Proof", "Insulated"],
        "intro": "Hydration on the move.",
        "description": (
            "A leak-proof insulated sipper for gym, office and travel. Keeps drinks "
            "at the perfect temperature for hours."
        ),
        "highlight": "Leak-proof insulated sipper for the gym, office and travel.",
        "image_url": U + "2026/04/11.jpg",
        "variants": ["500 ml", "750 ml"],
        "specs": {},
    },
    {
        "id": "carafe",
        "name": "Double-Wall Carafe",
        "brand": "valmate", "category": "water-bottle",
        "collection": "Serve Warm",
        "tags": ["Double-Wall", "Table-Ready"],
        "intro": "Serve at the perfect temp.",
        "description": (
            "An elegant double-wall carafe for the table that keeps water and juice "
            "hot or cold while it serves."
        ),
        "highlight": "Elegant table carafe that serves water and juice at the perfect temp.",
        "image_url": U + "2026/04/6.jpg",
        "variants": ["1 L", "1.5 L"],
        "specs": {},
    },
]


class Command(BaseCommand):
    help = "Seed database with all Crystal product data from frontend"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data first")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing product data...")
            ProductSpecification.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            Marketplace.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared."))

        # Brands
        self.stdout.write("Seeding brands...")
        brand_map = {}
        for b in BRANDS:
            obj, created = Brand.objects.update_or_create(
                slug=b["slug"],
                defaults={"name": b["name"], "tagline": b["tagline"], "description": b["description"]},
            )
            brand_map[b["slug"]] = obj
            self.stdout.write(f"  {'Created' if created else 'Updated'} brand: {obj.name}")

        # Categories — two passes: parents first, then children
        self.stdout.write("Seeding categories...")
        cat_map = {}
        parents_first = sorted(CATEGORIES, key=lambda c: 0 if c["parent"] is None else 1)
        for i, c in enumerate(parents_first):
            parent_obj = cat_map.get(c["parent"]) if c["parent"] else None
            obj, created = Category.objects.update_or_create(
                slug=c["slug"],
                defaults={"name": c["name"], "parent": parent_obj, "order": i},
            )
            cat_map[c["slug"]] = obj
            self.stdout.write(f"  {'Created' if created else 'Updated'} category: {obj.name}")

        # Marketplaces
        self.stdout.write("Seeding marketplaces...")
        for m in MARKETPLACES:
            obj, created = Marketplace.objects.update_or_create(
                slug=m["slug"],
                defaults={"name": m["name"], "is_active": True},
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'} marketplace: {obj.name}")

        # Products
        self.stdout.write("Seeding products...")
        for p in PRODUCTS:
            brand = brand_map[p["brand"]]
            category = cat_map[p["category"]]

            product, created = Product.objects.update_or_create(
                slug=p["id"],
                defaults={
                    "name": p["name"],
                    "brand": brand,
                    "category": category,
                    "collection_name": p["collection"],
                    "short_description": p["intro"],
                    "overview": p["description"],
                    "highlight": p.get("highlight", ""),
                    "tags": p["tags"],
                    "image_url": p["image_url"],
                    "is_active": True,
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'} product: {product.name}")

            # Variants
            ProductVariant.objects.filter(product=product).delete()
            for i, v_name in enumerate(p["variants"]):
                ProductVariant.objects.create(
                    product=product,
                    name=v_name,
                    sku_suffix=v_name.replace(" ", "-").lower(),
                    is_default=(i == 0),
                    order=i,
                )

            # Specs
            ProductSpecification.objects.filter(product=product).delete()
            for i, (k, value) in enumerate(p["specs"].items()):
                ProductSpecification.objects.create(
                    product=product,
                    key=k,
                    value=value,
                    order=i,
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Seeded {len(BRANDS)} brands, {len(CATEGORIES)} categories, "
            f"{len(MARKETPLACES)} marketplaces, {len(PRODUCTS)} products."
        ))
