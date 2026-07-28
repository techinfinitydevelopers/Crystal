"""Build the Crystal product catalog: parse the master xlsx, match each
product to real photos from the OneDrive export, normalize every matched
image onto a uniform padded canvas (no cropping), and write out
products.json / categories.json / brand-copy.json / unmatched-report.json
plus the normalized image files.

Usage:
    python build_catalog.py                # all configured sheets
    python build_catalog.py --sheets Lighter Cookware   # pilot subset
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

import pandas as pd
from PIL import Image, ImageOps
from rapidfuzz import fuzz

import config

SKU_RE = re.compile(r"\b([A-Za-z]{2,6}[-_]?\d{2,5}[A-Za-z]?)\b")
SKU_RANGE_RE = re.compile(r"\b([A-Za-z]{2,8})[-_ ]?(\d{2,5})\s*TO\s*(\d{2,5})\b", re.IGNORECASE)
ANGLE_SUFFIX_RE = re.compile(r"[\s_\-]*\(?\d{1,2}[a-zA-Z]?\)?\.?$")


def sku_base(raw):
    """Normalize a SKU-ish string to a comparison key: strip separators,
    uppercase, and drop a single trailing letter that follows a digit (so
    catalog 'LI001A' and photo-filename 'LI001'/'LI003N' compare equal)."""
    key = re.sub(r"[-_\s]", "", raw).upper()
    if len(key) >= 2 and key[-1].isalpha() and key[-2].isdigit():
        key = key[:-1]
    return key


def expand_sku_ranges(stem, folder_name):
    """Detect 'PREFIX 001 TO 007'-style filenames (a single family/lineup
    photo covering several SKUs) and return the list of individual SKU bases
    it covers, zero-padded to the same width as the range's own digits."""
    bases = []
    for text in (stem, folder_name):
        m = SKU_RANGE_RE.search(text)
        if not m:
            continue
        prefix, start_s, end_s = m.group(1).upper(), m.group(2), m.group(3)
        width = len(start_s)
        start, end = int(start_s), int(end_s)
        if end - start > 20 or end < start:
            continue  # sanity guard against mis-parses
        for n in range(start, end + 1):
            bases.append(f"{prefix}{n:0{width}d}")
    return bases


def log(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# 1. Catalog (xlsx) parsing
# ---------------------------------------------------------------------------
def col(df, canonical):
    """Find the actual column in df matching a canonical field name."""
    for alias in config.COLUMN_ALIASES.get(canonical, []):
        if alias in df.columns:
            return alias
    return None


def normalize_brand(raw):
    if not isinstance(raw, str):
        return "crystal"
    key = raw.strip().lower()
    return config.KNOWN_BRANDS.get(key, "crystal")


def resolve_subcategory(sheet_name, subgroup_val, default_sub):
    if default_sub is not None:
        return default_sub
    rules = config.SUBCATEGORY_RULES.get(sheet_name)
    if not rules or not isinstance(subgroup_val, str):
        return None
    low = subgroup_val.strip().lower()
    for sub_id, needles in rules:
        if any(n in low for n in needles):
            return sub_id
    return None


def load_products(sheet_names):
    products = []
    for sheet_name in sheet_names:
        meta = config.SHEETS[sheet_name]
        df = pd.read_excel(config.XLSX_PATH, sheet_name=sheet_name, header=meta["header_row"])
        df.columns = [str(c).strip() if not str(c).startswith("Product \n") else c for c in df.columns]

        sku_col = col(df, "sku")
        if sku_col is None:
            log(f"  ! sheet {sheet_name!r}: no SKU column found, skipping entirely")
            continue
        brand_col = col(df, "brand")
        subgroup_col = col(df, "subgroup")
        name_col = col(df, "product_name")
        item_desc_col = col(df, "item_description")
        desc_col = col(df, "description")
        gst_col = col(df, "gst_pct")
        mrp_col = col(df, "mrp")
        link_col = col(df, "amazon_link")
        kw_col = col(df, "keywords")

        clean = df[df[sku_col].notna()].copy()
        # Drop stray repeated-header / USP-blurb rows: a real product row's
        # brand must be one of the known brand strings (case-insensitive).
        if brand_col:
            clean = clean[clean[brand_col].astype(str).str.strip().str.lower().isin(config.KNOWN_BRANDS.keys())]

        n_before = len(clean)
        for _, row in clean.iterrows():
            sku = str(row[sku_col]).strip()
            subgroup_val = row[subgroup_col] if subgroup_col else None
            name = None
            if name_col and pd.notna(row.get(name_col)):
                name = str(row[name_col]).strip()
            elif item_desc_col and pd.notna(row.get(item_desc_col)):
                name = str(row[item_desc_col]).strip()
            if not name:
                name = sku

            products.append({
                "sku": sku,
                "sheet": sheet_name,
                "brand": normalize_brand(row[brand_col] if brand_col else None),
                "category": meta["top_category"],
                "subcategory": resolve_subcategory(sheet_name, subgroup_val, meta["subcategory"]),
                "collection": str(subgroup_val).strip() if isinstance(subgroup_val, str) else "",
                "name": name,
                "description": (str(row[desc_col]).strip() if desc_col and pd.notna(row.get(desc_col))
                                 else (str(row[item_desc_col]).strip() if item_desc_col and pd.notna(row.get(item_desc_col)) else "")),
                "gst_pct": float(row[gst_col]) if gst_col and pd.notna(row.get(gst_col)) else None,
                "mrp": float(row[mrp_col]) if mrp_col and pd.notna(row.get(mrp_col)) else None,
                "amazon_link": (str(row[link_col]).strip() if link_col and pd.notna(row.get(link_col)) else None),
                "tags": ([t.strip() for t in str(row[kw_col]).split(",")][:6] if kw_col and pd.notna(row.get(kw_col)) else []),
            })
        log(f"  sheet {sheet_name!r}: {n_before} product rows loaded")
    return products


def load_categories():
    df = pd.read_excel(config.XLSX_PATH, sheet_name=config.TAXONOMY_SHEET, header=None)
    # Row 2 (0-indexed) onward: col0 = top-level category, remaining cols = subcats
    tree = []
    for _, row in df.iloc[2:].iterrows():
        vals = [str(v).strip() for v in row.tolist() if pd.notna(v)]
        if not vals:
            continue
        top = vals[0]
        subs = vals[1:]
        tree.append({"label": top, "subcategories": subs})
    return tree


def load_brand_copy():
    df = pd.read_excel(config.XLSX_PATH, sheet_name=config.BRAND_COPY_SHEET, header=None)
    entries = []
    for v in df[0].dropna():
        text = str(v).strip()
        if text:
            entries.append(text)
    return entries


# ---------------------------------------------------------------------------
# 2. Image-source candidate collection
# ---------------------------------------------------------------------------
def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return text


def name_guess_from(filename_no_ext, folder_name):
    base = ANGLE_SUFFIX_RE.sub("", filename_no_ext).strip()
    base = SKU_RE.sub("", base).strip(" -_")
    if len(base) < 3:
        base = ANGLE_SUFFIX_RE.sub("", folder_name).strip()
        base = SKU_RE.sub("", base).strip(" -_")
    return slugify(base)


def collect_candidates(sheet_name):
    """Walk the configured image dirs for a sheet, return list of candidate
    image records: {path, sku_guesses, name_guess, width, height}."""
    dirs = config.IMAGE_DIRS_BY_SHEET.get(sheet_name, [])
    candidates = []
    for rel_dir in dirs:
        abs_dir = os.path.join(config.IMAGE_SOURCE_ROOT, rel_dir)
        if not os.path.isdir(abs_dir):
            log(f"  ! configured image dir missing: {abs_dir}")
            continue
        for root, dirnames, filenames in os.walk(abs_dir):
            dirnames[:] = [d for d in dirnames if d not in config.SKIP_DIRS]
            folder_name = os.path.basename(root)
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in config.IMAGE_EXT:
                    continue
                fpath = os.path.join(root, fn)
                try:
                    with Image.open(fpath) as im:
                        w, h = im.size
                except Exception as e:
                    log(f"  ! could not open {fpath}: {e}")
                    continue
                if max(w, h) < config.MIN_USABLE_PX:
                    continue
                stem = os.path.splitext(fn)[0]
                blob = re.sub(r"[^A-Za-z0-9]", "", stem + folder_name).upper()
                for wrong, right in config.KNOWN_BLOB_ALIASES.items():
                    if wrong in blob:
                        blob = blob.replace(wrong, right)
                range_bases = set(expand_sku_ranges(stem, folder_name))
                candidates.append({
                    "path": fpath,
                    "filename": fn,
                    "stem": stem,
                    "folder": folder_name,
                    "blob": blob,
                    "range_bases": range_bases,
                    "name_guess": name_guess_from(stem, folder_name),
                    "width": w,
                    "height": h,
                })
    return candidates


def angle_number(stem):
    m = re.search(r"\(?(\d{1,2})[a-zA-Z]?\)?\.?$", stem.strip())
    return int(m.group(1)) if m else 0


def pick_hero_and_gallery(files):
    files_sorted = sorted(files, key=lambda f: (angle_number(f["stem"]) != 1, angle_number(f["stem"]), -f["width"] * f["height"]))
    hero = files_sorted[0]
    gallery = files_sorted[1:1 + config.MAX_GALLERY]
    return hero, gallery


# ---------------------------------------------------------------------------
# 3. Matching
# ---------------------------------------------------------------------------
def blob_contains_sku(blob, base):
    """True if `base` occurs in `blob` and isn't immediately followed by
    another digit (avoids 'CNS905' spuriously matching inside 'CNS9050')."""
    idx = blob.find(base)
    if idx == -1:
        return False
    after = blob[idx + len(base): idx + len(base) + 1]
    return not after.isdigit()


def match_products_to_images(products, candidates_by_sheet):
    unmatched_products = []
    unmatched_images = []
    claimed_paths = set()

    for sheet_name, candidates in candidates_by_sheet.items():
        sheet_products = [p for p in products if p["sheet"] == sheet_name]

        # Tier 1: exact SKU match — the catalog SKU (letter-suffix-stripped)
        # must occur as a substring of the filename+folder blob. Also honors
        # 'PREFIX 001 TO 007' family/range photos via range_bases.
        for p in sheet_products:
            base = sku_base(p["sku"])
            hits = [c for c in candidates
                    if base in c["range_bases"] or blob_contains_sku(c["blob"], base)]
            if hits:
                p["_images"] = hits
                p["_match_tier"] = "exact_sku"
                claimed_paths.update(h["path"] for h in hits)

        # Tier 2: fuzzy name match for anything still unmatched — grouped by
        # each candidate's own name_guess (angle/SKU-stripped filename), NOT
        # by folder, since one folder commonly holds many distinct products
        # (e.g. all lighters live in a single KITCHENWARE/LIGHTERS folder).
        remaining_products = [p for p in sheet_products if "_images" not in p]
        remaining_candidates = [c for c in candidates if c["path"] not in claimed_paths]
        by_name_guess = {}
        for c in remaining_candidates:
            by_name_guess.setdefault(c["name_guess"], []).append(c)

        scores = []
        for p in remaining_products:
            p_name_slug = slugify(p["name"])
            for name_guess in by_name_guess:
                score = fuzz.token_set_ratio(p_name_slug, name_guess)
                scores.append((score, p["sku"], name_guess))
        scores.sort(key=lambda t: -t[0])

        assigned_groups = set()
        product_by_sku = {p["sku"]: p for p in remaining_products}
        for score, sku, name_guess in scores:
            if score < config.FUZZY_MATCH_THRESHOLD:
                break
            if name_guess in assigned_groups:
                continue
            p = product_by_sku.get(sku)
            if p is None or "_images" in p:
                continue
            files = by_name_guess[name_guess]
            p["_images"] = files
            p["_match_tier"] = "fuzzy_name"
            assigned_groups.add(name_guess)
            claimed_paths.update(f["path"] for f in files)

        # Bookkeeping
        for p in sheet_products:
            if "_images" not in p:
                p["_images"] = []
                p["_match_tier"] = "unmatched"
                unmatched_products.append({"sku": p["sku"], "name": p["name"], "sheet": sheet_name})

        for c in candidates:
            if c["path"] not in claimed_paths:
                unmatched_images.append({"path": c["path"], "sheet": sheet_name})

    return unmatched_products, unmatched_images


# ---------------------------------------------------------------------------
# 4. Normalization
# ---------------------------------------------------------------------------
def normalize_image(src_path, dst_path):
    im = Image.open(src_path)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    w, h = im.size
    scale = min(config.CANVAS_PX / max(w, h), 1.0)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    if (new_w, new_h) != (w, h):
        im = im.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (config.CANVAS_PX, config.CANVAS_PX), config.FILL_RGB)
    canvas.paste(im, ((config.CANVAS_PX - new_w) // 2, (config.CANVAS_PX - new_h) // 2))
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    canvas.save(dst_path, config.OUTPUT_FORMAT, quality=config.OUTPUT_QUALITY, method=6)


def sku_to_dirname(sku):
    return re.sub(r"[^A-Za-z0-9-]", "-", sku.upper()).strip("-")


def write_product_images(product):
    if not product["_images"]:
        return None, []
    hero, gallery = pick_hero_and_gallery(product["_images"])
    dirname = sku_to_dirname(product["sku"])
    rel_dir = f"product-photos/{dirname}"
    hero_rel = f"{rel_dir}/hero.webp"
    gallery_rel = []
    for root in config.OUTPUT_ROOTS:
        normalize_image(hero["path"], os.path.join(root, rel_dir, "hero.webp"))
    for i, g in enumerate(gallery, start=1):
        g_rel = f"{rel_dir}/g{i}.webp"
        for root in config.OUTPUT_ROOTS:
            normalize_image(g["path"], os.path.join(root, g_rel))
        gallery_rel.append(g_rel)
    return hero_rel, gallery_rel


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheets", nargs="*", default=None, help="restrict to these sheet names (pilot mode)")
    args = ap.parse_args()

    sheet_names = args.sheets if args.sheets else list(config.SHEETS.keys())
    unknown = [s for s in sheet_names if s not in config.SHEETS]
    if unknown:
        log(f"Unknown sheet name(s): {unknown}")
        sys.exit(1)

    log(f"Loading products from sheets: {sheet_names}")
    products = load_products(sheet_names)
    log(f"Total product rows: {len(products)}")

    log("Collecting image candidates...")
    candidates_by_sheet = {s: collect_candidates(s) for s in sheet_names}
    for s, c in candidates_by_sheet.items():
        log(f"  {s}: {len(c)} candidate images")

    log("Matching images to products...")
    unmatched_products, unmatched_images = match_products_to_images(products, candidates_by_sheet)
    log(f"Unmatched products: {len(unmatched_products)} / {len(products)}")
    log(f"Unmatched images: {len(unmatched_images)}")

    log("Normalizing + writing images...")
    out_products = []
    for p in products:
        hero_rel, gallery_rel = write_product_images(p)
        out_products.append({
            "sku": p["sku"],
            "name": p["name"],
            "brand": p["brand"],
            "category": p["category"],
            "subcategory": p["subcategory"],
            "collection": p["collection"],
            "highlight": (p["description"][:120] + "...") if len(p["description"]) > 120 else p["description"],
            "description": p["description"],
            "tags": p["tags"],
            "gst_pct": p["gst_pct"],
            "mrp": p["mrp"],
            "amazon_link": p["amazon_link"],
            "hero": hero_rel,
            "gallery": gallery_rel,
            "match_tier": p["_match_tier"],
            "id": sku_to_dirname(p["sku"]).lower(),
        })

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_xlsx": os.path.basename(config.XLSX_PATH),
        "sheets_included": sheet_names,
        "products": out_products,
    }
    unmatched_report = {
        "unmatched_products": unmatched_products,
        "unmatched_images": unmatched_images,
    }

    for root in config.OUTPUT_ROOTS:
        data_dir = os.path.join(root, "product-data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "products.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        with open(os.path.join(data_dir, "unmatched-report.json"), "w", encoding="utf-8") as f:
            json.dump(unmatched_report, f, ensure_ascii=False, indent=2)

    # categories.json / brand-copy.json only need generating once (full-catalog concern)
    # but cheap enough to regenerate every run.
    categories = load_categories()
    brand_copy = load_brand_copy()
    for root in config.OUTPUT_ROOTS:
        data_dir = os.path.join(root, "product-data")
        with open(os.path.join(data_dir, "categories.json"), "w", encoding="utf-8") as f:
            json.dump({"categories": categories}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(data_dir, "brand-copy.json"), "w", encoding="utf-8") as f:
            json.dump({"entries": brand_copy}, f, ensure_ascii=False, indent=2)

    log("Done.")
    log(f"products.json: {len(out_products)} products written to {len(config.OUTPUT_ROOTS)} output root(s)")


if __name__ == "__main__":
    main()
