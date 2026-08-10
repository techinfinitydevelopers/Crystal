"""Configuration for the Crystal product-catalog build pipeline.

Central place for: source paths, which OneDrive folders to skip (confirmed
duplicates), per-sheet column aliases (column names vary slightly sheet to
sheet), per-sheet image-source folders, and the sheet -> (top-level category,
subcategory) taxonomy mapping derived from the "Home Page Segregation - Home
Pa" sheet and cross-checked against the reference site's live mega-menu
(proj.leo9studio.in/projects/crystal-wp).
"""
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
XLSX_PATH = r"D:\CRYSTAL\Crystal\crystal\Crystal Product List for Techinfinity Final.xlsx"
IMAGE_SOURCE_ROOT = r"D:\CRYSTAL\Crystal\crystal\Product Dump for Techinfinity"

REPO_ROOT = r"D:\CRYSTAL\Crystal\crystal"
OUTPUT_ROOTS = [REPO_ROOT]

TAXONOMY_SHEET = "Home Page Segregation - Home Pa"
BRAND_COPY_SHEET = "Brand Perceptions "

# ---------------------------------------------------------------------------
# Image-source de-duplication (confirmed via md5sum / visual check during audit)
# ---------------------------------------------------------------------------
# Folder names (relative to IMAGE_SOURCE_ROOT) to skip entirely — each is a
# confirmed redundant subset/merge/staging-cache of a richer folder we use
# instead (KW and loose KITCHENWARE-root files mirror SKUs already present in
# the proper subfolders; SPARKMATE is a thin subset of "Sparkmate BY Crystal";
# "Tri Val" is a byte-identical merge of the 4 individual Tri Val folders).
SKIP_DIRS = {"KW", "SPARKMATE", "Tri Val"}

IGNORE_EXT = {".pdf", ".mp4", ".gif", ".pptx", ".zip", ".xlsx", ".doc", ".docx"}
IMAGE_EXT = {".jpg", ".jpeg", ".png"}
MIN_USABLE_PX = 300  # filters out tiny banner/logo graphics

# ---------------------------------------------------------------------------
# Per-sheet parsing config
# ---------------------------------------------------------------------------
# header_row: which row (0-indexed) holds the column names in that sheet.
# top_category / subcategory: canonical taxonomy ids (subcategory None means
# resolved per-row via SUBCATEGORY_RULES below).
SHEETS = {
    "Lighter":                    {"header_row": 0, "top_category": "kitchenware", "subcategory": "lighters"},
    "Knife":                      {"header_row": 0, "top_category": "kitchenware", "subcategory": "knives"},
    "Peeler":                     {"header_row": 1, "top_category": "kitchenware", "subcategory": "peelers"},
    "Chopping Boards":            {"header_row": 0, "top_category": "kitchenware", "subcategory": "chopping-boards"},
    "Trolley":                    {"header_row": 0, "top_category": "kitchenware", "subcategory": "trolleys"},
    "Kitchen Tools":               {"header_row": 0, "top_category": "kitchenware", "subcategory": "kitchen-tools"},
    "Manual Kitchen Appliances":  {"header_row": 0, "top_category": "kitchenware", "subcategory": "manual-appliances"},
    "Cutlery":                    {"header_row": 0, "top_category": "kitchenware", "subcategory": "cutlery"},
    "Servers":                    {"header_row": 0, "top_category": "kitchenware", "subcategory": "servers"},
    "Water Filter":               {"header_row": 0, "top_category": "kitchenware", "subcategory": "water-filter"},
    "Water Bottle":               {"header_row": 0, "top_category": "water-bottle", "subcategory": None},
    "Oil Pourer & Sprayer":       {"header_row": 0, "top_category": "oil-pourer", "subcategory": None},
    "Wood Range":                  {"header_row": 0, "top_category": "wood-range", "subcategory": None},
    "Cookware":                   {"header_row": 0, "top_category": "cookware", "subcategory": None},  # per-row via Material
    "Pressure Cooker":            {"header_row": 0, "top_category": "pressure-cooker", "subcategory": None},
    "Electric Appliances":        {"header_row": 0, "top_category": "electric-appliances", "subcategory": None},  # per-row via Type
    "Cooktop":                    {"header_row": 1, "top_category": "cooktop", "subcategory": None},
    "LUNCHBOX":                   {"header_row": 0, "top_category": "lunch-box", "subcategory": None},
    "cleaningaid":                {"header_row": 0, "top_category": "cleaning-aid", "subcategory": None},  # per-row via Sub Category
}

# Column-name aliases: canonical field -> list of possible header strings
# (accounts for inconsistent whitespace/newlines/casing across sheets).
COLUMN_ALIASES = {
    "brand": ["Brand"],
    "sku": ["NEW PRODUCT CODE", "PRODUCT CODE"],
    "item_category": ["ITEM CATEGORY", "Category"],
    "subgroup": ["ITEM SUBGROUP", "ITEM SUBCATEGORY", "Sub Category", "Material", "Material ", "Type"],
    "product_name": ["Product Name (max 100 characters)"],
    "item_description": ["ITEM DESCRIPTION", "ITEM DESCRIPTION WITH PIC"],
    "description": ["Product \nDescription"],
    "gst_pct": ["GST %"],
    "mrp": ["MRP"],
    "amazon_link": ["LINK"],
    "keywords": ["Search Keywords\n( All keywords seperated by a comma)"],
}

# Extra per-sheet attribute columns surfaced as filter facets on the product
# grid (mirrors the reference site's sidebar filters, e.g. Cookware/Tripro's
# "Induction / Non-Induction", "Individual / Set", "Type"). Canonical filter
# key -> list of possible column header strings for that sheet.
FILTER_COLUMNS_BY_SHEET = {
    "Cookware": {"induction": ["Induction / Non-Induction"], "set_type": ["Individual / Set"], "type": ["Type"]},
    "Knife": {"set_type": ["Individual / Set"], "handle_material": ["Handle Material"], "edge_type": ["Blade Edge Type"], "coating": ["Coating Type"]},
    "Chopping Boards": {"material": ["Material"], "size": ["Size"], "with_blade": ["With / without Blade"]},
    "Trolley": {"material": ["Material"], "design": ["Shape/Design"]},
    "Kitchen Tools": {"use": ["Use"]},
    "Manual Kitchen Appliances": {"use": ["Use"]},
    "Cutlery": {"design": ["Design"], "set_size": ["Set Size"], "set_type": ["Individual / Set"]},
    "Servers": {"material": ["Material"], "design": ["Design"], "set_type": ["Individual / Set"]},
    "Water Filter": {"capacity": ["Capacity"]},
    "Water Bottle": {"type": ["TYPE"], "material": ["MATERIAL"]},
    "Oil Pourer & Sprayer": {"material": ["Material"], "use": ["Use"]},
    "Wood Range": {"material": ["Material "], "use": ["Use"]},
    "Pressure Cooker": {"size": ["Size"], "lid_type": ["Lid Type"], "shape": ["Shape"], "material": ["Material"]},
    "Electric Appliances": {"type": ["Type"], "material": ["Material"]},
    "Cooktop": {"size": ["Size"], "type": ["Type"], "material": ["Material"]},
    "LUNCHBOX": {"size": ["Size"], "type": ["Type"], "material": ["Material"]},
}

KNOWN_BRANDS = {
    "crystal": "crystal", "crystalina": "crystalina", "crystalina ": "crystalina",
    "sparkmate": "sparkmate", "valmate": "valmate",
}

# Per-row subcategory resolution for sheets where one sheet spans several
# subcategories (matched against the sheet's "subgroup" alias column,
# case-insensitive substring match, first match wins).
# NOTE: "tripro" (not "triply") is the correct canonical id — confirmed
# against the reference site's live mega-menu (Cookware > Tripro), which
# also matches this site's own pre-existing nav slug (?sub=tripro).
SUBCATEGORY_RULES = {
    "Cookware": [
        ("tripro", ["triply"]),
        ("cast-iron", ["cast iron"]),
        ("non-stick-mini", ["non-stick - mini", "nonstick - mini", "non stick mini"]),
        ("non-stick", ["non-stick", "nonstick"]),
        ("sandwich-bottom-steel", ["sandwich bottom"]),
        ("hard-anodised", ["hard anodised", "hard anodized"]),
    ],
    "Electric Appliances": [
        ("chimney", ["chimney"]),
        ("kettle", ["kettle"]),
        ("iron", ["iron"]),
        ("ice-cream-maker", ["ice cream", "ice-cream"]),
        ("otg", ["otg"]),
        ("air-fryer", ["air fryer"]),
        ("rice-cooker", ["rice cooker"]),
        ("food-processor", ["food processor"]),
        ("jmg", ["jmg"]),
    ],
    "cleaningaid": [
        ("spin-mops", ["spin mop"]),
        ("hand-held-mops", ["hand held mop", "handheld mop"]),
        ("brooms", ["broom"]),
        ("wipers", ["wiper"]),
        ("wipe", ["wipe"]),  # distinct from "wipers" — confirmed on reference site nav + xlsx Sub Category column (SMG019/SMG020)
        ("plunger", ["plunger"]),
        ("brush", ["brush"]),
        ("scrubber", ["scrubber", "scourer"]),
        ("bins", ["bin"]),
        ("sink-organiser", ["sink organiser", "sink organizer"]),
    ],
}

# ---------------------------------------------------------------------------
# Image-source folder mapping: sheet name -> list of directories (relative to
# IMAGE_SOURCE_ROOT) to search for that sheet's product photos.
#
# Kitchen Tools / Manual Kitchen Appliances deliberately share several source
# folders (their SKUs are interleaved within the same OneDrive folders) —
# this is safe because matching is SKU-substring based per catalog row, not
# folder-exclusive, so each sheet only claims the SKUs that are actually its
# own regardless of which other sheet also scans the same folder.
#
# Electric Appliances, Cooktop, and LUNCHBOX have NO photos in this OneDrive
# export (confirmed absent after an exhaustive search) — left with empty
# lists; their products will show as unmatched (placeholder image, flagged
# in unmatched-report.json) until photos are supplied separately.
# ---------------------------------------------------------------------------
IMAGE_DIRS_BY_SHEET = {
    "Lighter": [r"KITCHENWARE\LIGHTERS"],
    "Cookware": [
        r"COOKWARE",
        r"Tri Val 4pcs set", r"Tri Val Fry and Sauce pan", r"Tri Val Kadai and Fry pan", r"Tri Val Kadai and Sauce Pan",
        r"Tri Bottom Kadai Casserole", r"Tri Bottom Kadai Sauce Pan Large", r"Tri Bottom Kadai sauce pan medium", r"Tri Bottom casserole",
        r"Small Taper Amazon", r"Taper 200 Amazon",
    ],
    "Knife": [
        r"KITCHENWARE\KNIVES",
        r"Crystal Stainless Steel knife Amazon", r"Multi Purpose knife Amazon", r"Butter Knife Amazon",
        r"Handy Peeling Knife perple blue", r"Sleek Knife",
    ],
    "Peeler": [r"KITCHENWARE\Peelers", r"Swivel Peeler"],
    "Chopping Boards": [
        r"KITCHENWARE\Chopping Board",
        r"Inox Chopping board 2 in 1", r"Teakwood 3compartment Chopping board", r"Teakwood 7Compartment Chopping board",
        r"Wooden Chopping Board",
    ],
    "Trolley": [r"KITCHENWARE\TROLLEY", r"Crystal Gas trolly Amazon"],
    "Kitchen Tools": [
        r"KITCHENWARE\MODERN KA", r"KITCHENWARE\MKA",
        r"Ice Scoop Amazon",
    ],
    "Manual Kitchen Appliances": [
        r"KITCHENWARE\MODERN KA", r"KITCHENWARE\MKA", r"KITCHENWARE\Manual KA",
        r"12 in 1 Dicer Amazon", r"Dryfruit Cutter", r"Fine Grater Amazon", r"Salt Shaker Amazon", r"Xpress Juicer Amazon",
    ],
    "Cutlery": [
        r"KITCHENWARE\Cutlery",
        r"Vivid cutlery set Amazon", r"Titanium Series A",
    ],
    "Servers": [r"KITCHENWARE\SERVING SS"],
    "Water Filter": [r"KITCHENWARE\WATER FILTERS", r"KITCHENWARE\Water Filter", r"KITCHENWARE\CANDLE"],
    "Water Bottle": [
        r"KITCHENWARE\BOTTLE",
        r"Aqua Blaze Amazon", r"Aqua Blaze Set of 3", r"Aqua Bliss Amazon", r"Aqua Bold Amazon",
        r"Aqua Duo Blue Amazon", r"Aqua Duo Blue Set of 2", r"Aqua Duo PInk set of 2", r"Aqua Duo Pink Amazon",
        r"Aqua Duo SS Blue Amazon", r"Aqua Duo SS Pink Amazon", r"Aqua duo blue SS set of 2", r"Aqua duo pink SS set of 2",
    ],
    "Oil Pourer & Sprayer": [r"KITCHENWARE\OIL POURER", r"2in1 Oil Dispenser"],
    "Wood Range": [
        r"TeakWood",
        r"Teakwood Milano 2 bowl tray", r"Teakwood Store N serve 3pcs", r"TEA COASTER ROUND", r"TEA COASTER SQUARE",
        r"Spice BOx", r"Handy Caddy 4 in 1", r"Hnady Caddy 2 in 1", r"Revolving Caddy", r"Paper Hoder With Weight Amazon",
    ],
    "Pressure Cooker": [r"COOKWARE\Pressure Cooker"],
    "Electric Appliances": [],  # not present in this OneDrive export
    "Cooktop": [],              # not present in this OneDrive export
    "LUNCHBOX": [],             # not present in this OneDrive export
    "cleaningaid": [r"Sparkmate BY Crystal"],
}

# Known source-filename typos discovered during matching (confirmed by
# manual inspection, not guessed) — maps a substring as it appears in image
# filenames to the spelling actually used in the catalog SKU column.
KNOWN_BLOB_ALIASES = {
    "CTPEKD": "CTPEDK",  # COOKWARE/Tripro/"CTPEKD 001 TO 004.jpg" vs catalog CTP-EDK-0xx
}

# Display-label corrections applied when generating categories.json — the
# taxonomy sheet's raw text says "Triply" for this subcategory, but the
# reference site's live nav and this site's own existing ?sub= slug both
# say "Tripro" (Tri-Pro is the collection/marketing name; Triply is just
# the underlying material). Keep the sheet's own wording for everything else.
CATEGORY_LABEL_OVERRIDES = {
    "Triply": "Tripro",
}

# The "Home Page Segregation" taxonomy sheet is missing "Wipe" under
# Cleaning Aid (it's a real, distinct 10th subcategory confirmed both by the
# reference site's live nav and the cleaningaid sheet's own Sub Category
# column — see SUBCATEGORY_RULES above) — append it when generating categories.json.
CATEGORY_SUBCATEGORY_ADDITIONS = {
    "Cleaning Aid": ["Wipe"],
}

MAX_GALLERY = 4
CANVAS_PX = 1200
FILL_RGB = (241, 241, 241)  # #f1f1f1 — matches .pcard .pimg background in site CSS
OUTPUT_FORMAT = "WEBP"
OUTPUT_QUALITY = 82
FUZZY_MATCH_THRESHOLD = 85
