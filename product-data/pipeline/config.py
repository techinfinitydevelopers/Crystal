"""Configuration for the Crystal product-catalog build pipeline.

Central place for: source paths, which OneDrive folders to skip (confirmed
duplicates), per-sheet column aliases (column names vary slightly sheet to
sheet), and the sheet -> (top-level category, subcategory) taxonomy mapping
derived from the "Home Page Segregation - Home Pa" sheet.
"""
import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
XLSX_PATH = r"C:\Users\prasa\Downloads\Crystal Product List for Techinfinity Final.xlsx"
IMAGE_SOURCE_ROOT = r"C:\Users\prasa\Downloads\OneDrive_1_7-27-2026"

REPO_ROOT = r"C:\Website\crystal"
OUTPUT_ROOTS = [REPO_ROOT, os.path.join(REPO_ROOT, "crystal")]

TAXONOMY_SHEET = "Home Page Segregation - Home Pa"
BRAND_COPY_SHEET = "Brand Perceptions "

# ---------------------------------------------------------------------------
# Image-source de-duplication (confirmed via md5sum during audit)
# ---------------------------------------------------------------------------
# Folder names (relative to IMAGE_SOURCE_ROOT) to skip entirely — each is a
# confirmed redundant subset/merge of a richer folder we use instead.
SKIP_DIRS = {"KW", "SPARKMATE", "Tri Val"}

IGNORE_EXT = {".pdf", ".mp4", ".gif", ".pptx", ".zip", ".xlsx", ".doc", ".docx"}
IMAGE_EXT = {".jpg", ".jpeg", ".png"}
MIN_USABLE_PX = 300  # filters out tiny banner/logo graphics

# ---------------------------------------------------------------------------
# Per-sheet parsing config
# ---------------------------------------------------------------------------
# header_row: which row (0-indexed) holds the column names in that sheet.
# top_category: canonical top-level taxonomy id this whole sheet belongs to
#   (a few sheets need per-row subcategory logic in addition — see
#   SUBCATEGORY_RULES below).
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
    "subgroup": ["ITEM SUBGROUP", "ITEM SUBCATEGORY", "Sub Category", "Material", "Type"],
    "product_name": ["Product Name (max 100 characters)"],
    "item_description": ["ITEM DESCRIPTION", "ITEM DESCRIPTION WITH PIC"],
    "description": ["Product \nDescription"],
    "gst_pct": ["GST %"],
    "mrp": ["MRP"],
    "amazon_link": ["LINK"],
    "keywords": ["Search Keywords\n( All keywords seperated by a comma)"],
}

KNOWN_BRANDS = {
    "crystal": "crystal", "crystalina": "crystalina", "crystalina ": "crystalina",
    "sparkmate": "sparkmate", "valmate": "valmate",
}

# Per-row subcategory resolution for sheets where one sheet spans several
# subcategories (matched against the sheet's "subgroup" alias column,
# case-insensitive substring match, first match wins).
SUBCATEGORY_RULES = {
    "Cookware": [
        ("triply", ["triply"]),
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
        ("plunger", ["plunger"]),
        ("brush", ["brush"]),
        ("scrubber", ["scrubber", "scourer"]),
        ("bins", ["bin"]),
        ("sink-organiser", ["sink organiser", "sink organizer"]),
    ],
}

# ---------------------------------------------------------------------------
# Image-source folder mapping: sheet name -> list of directories (relative to
# IMAGE_SOURCE_ROOT) to search for that sheet's product photos. Populated
# incrementally — Phase 1 pilot only needs Lighter + Cookware; other sheets
# are filled in during Phase 2 as their source folders are confirmed.
# ---------------------------------------------------------------------------
IMAGE_DIRS_BY_SHEET = {
    "Lighter": [r"KITCHENWARE\LIGHTERS"],
    "Cookware": [
        r"COOKWARE",              # walked recursively (includes Cast Iron/Non Stick/Tripro/Pressure Cooker subfolders + loose top-level files)
        r"Tri Val 4pcs set", r"Tri Val Fry and Sauce pan", r"Tri Val Kadai and Fry pan", r"Tri Val Kadai and Sauce Pan",
        r"Tri Bottom Kadai Casserole", r"Tri Bottom Kadai Sauce Pan Large", r"Tri Bottom Kadai sauce pan medium", r"Tri Bottom casserole",
    ],
}

# Known source-filename typos discovered during matching (confirmed by
# manual inspection, not guessed) — maps a substring as it appears in image
# filenames to the spelling actually used in the catalog SKU column.
KNOWN_BLOB_ALIASES = {
    "CTPEKD": "CTPEDK",  # COOKWARE/Tripro/"CTPEKD 001 TO 004.jpg" vs catalog CTP-EDK-0xx
}

MAX_GALLERY = 4
CANVAS_PX = 1200
FILL_RGB = (241, 241, 241)  # #f1f1f1 — matches .pcard .pimg background in site CSS
OUTPUT_FORMAT = "WEBP"
OUTPUT_QUALITY = 82
FUZZY_MATCH_THRESHOLD = 85
