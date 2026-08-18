import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils.text import slugify

from products.models import (
    Brand, Category, Product, ProductImage, ProductSpecification,
    ProductVariant, Marketplace, ProductMarketplaceLink,
)

JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "product-data", "products.json")

CAT_LABELS = {
    "cookware": "Cookware", "kitchenware": "Kitchenware", "water-bottle": "Water Bottle",
    "oil-pourer": "Oil Pourer & Sprayer", "wood-range": "Wood Range", "pressure-cooker": "Pressure Cooker",
    "electric-appliances": "Electric Appliances", "cooktop": "Cooktop", "lunch-box": "Lunch Box",
    "cleaning-aid": "Cleaning Aid",
}
BRAND_LABELS = {
    "crystal": ("Crystal", "World of Kitchenware"),
    "crystalina": ("Crystalina", "Splendid Finish"),
    "sparkmate": ("SparkMate", "Cleaning Simplified"),
    "valmate": ("ValMate", "Value for Money"),
}


def slugify_sub(sub):
    return sub.replace(" ", "-").lower()


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    items = raw["products"]

    brand_objs = {}
    for slug, (name, tagline) in BRAND_LABELS.items():
        b, _ = Brand.objects.get_or_create(slug=slug, defaults={"name": name, "tagline": tagline})
        brand_objs[slug] = b

    cat_objs = {}
    for slug, label in CAT_LABELS.items():
        c, _ = Category.objects.get_or_create(slug=slug, defaults={"name": label})
        cat_objs[slug] = c

    marketplace_amazon, _ = Marketplace.objects.get_or_create(slug="amazon", defaults={"name": "Amazon"})

    created, updated, skipped = 0, 0, 0
    for p in items:
        sku = (p.get("sku") or "").strip()
        if not sku:
            skipped += 1
            continue
        brand_slug = (p.get("brand") or "crystal").strip().lower()
        brand_obj = brand_objs.get(brand_slug) or brand_objs["crystal"]

        cat_slug = p.get("category")
        sub_slug = p.get("subcategory")
        if sub_slug:
            sub_key = f"{cat_slug}__{sub_slug}"
            cat_obj = cat_objs.get(sub_key)
            if not cat_obj:
                parent = cat_objs.get(cat_slug)
                sub_label = sub_slug.replace("-", " ").title()
                cat_obj, _ = Category.objects.get_or_create(
                    slug=slugify_sub(f"{cat_slug}-{sub_slug}"),
                    defaults={"name": sub_label, "parent": parent},
                )
                cat_objs[sub_key] = cat_obj
        else:
            cat_obj = cat_objs.get(cat_slug)
        if cat_obj is None:
            cat_obj = cat_objs["cookware"]

        name = p.get("name") or sku
        defaults = {
            "name": name,
            "slug": slugify(sku),
            "brand": brand_obj,
            "category": cat_obj,
            "short_description": (p.get("highlight") or "")[:300],
            "overview": p.get("description") or "",
            "highlight": (p.get("highlight") or "")[:300],
            "collection_name": p.get("collection") or "",
            "tags": p.get("tags") or [],
            "image_url": p.get("hero") or "",
            "is_active": True,
            "price": p.get("mrp") if isinstance(p.get("mrp"), (int, float)) else None,
            "show_price": bool(isinstance(p.get("mrp"), (int, float))),
        }
        prod, was_created = Product.objects.update_or_create(sku=sku, defaults=defaults)
        if was_created:
            created += 1
        else:
            updated += 1

        # Note: ProductImage.image is a file field (ImageField), so external gallery
        # URLs from the JSON can't be assigned directly without downloading each file.
        # Skipped for this sync; Product.image_url (hero) is set above and covers the
        # primary product photo. Gallery URLs remain in product-data/products.json.

        # specifications from filters{}
        prod.specifications.all().delete()
        for i, (k, v) in enumerate((p.get("filters") or {}).items()):
            if v:
                ProductSpecification.objects.create(product=prod, key=k.replace("_", " ").title(), value=str(v), order=i)

        # amazon marketplace link
        link = p.get("amazon_link")
        if link:
            ProductMarketplaceLink.objects.update_or_create(
                product=prod, marketplace=marketplace_amazon, defaults={"url": link}
            )

    print(f"Created: {created}, Updated: {updated}, Skipped (no sku): {skipped}")
    print(f"Total products in DB: {Product.objects.count()}")
    print(f"Total brands: {Brand.objects.count()}, categories: {Category.objects.count()}")


if __name__ == "__main__":
    main()
