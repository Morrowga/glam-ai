"""
GlamAI Prompt Engine v14 — zone-aware layering + multi-zone support

Disabled (pending skin tone classifier):
  - contour   → too subtle, deep skin invisible
  - foundation → needs skin tone matching
  - concealer  → needs skin tone matching

Active zones: lips, eyes, cheeks (blush/bronzer/highlighter only)
"""

# ── Individual prompt builders ────────────────────────────────────

def _lipstick_prompt(d, skin_tone="medium"):
    intensity = "with rich pigmentation, making sure the color is fully visible" if skin_tone in ("deep", "rich") else "evenly"
    return f"apply {d['brand_name']} {d['shade_name']} lipstick to her lips {intensity}"

def _lipgloss_prompt(d, skin_tone="medium"):
    return f"layer {d['brand_name']} {d['shade_name']} lip gloss on top of her lips for a glossy finish"

def _lipliner_prompt(d, skin_tone="medium"):
    return f"outline her lips precisely with {d['brand_name']} {d['shade_name']} lip liner"

def _eyeshadow_prompt(d, skin_tone="medium"):
    if skin_tone in ("deep", "rich"):
        return (
            f"apply {d['brand_name']} {d['shade_name']} eyeshadow to her eyelids "
            f"with heavy pigmentation so the color is clearly visible on her deep skin tone"
        )
    return f"apply {d['brand_name']} {d['shade_name']} eyeshadow softly to her eyelids"

def _eyeliner_prompt(d, skin_tone="medium"):
    return f"apply {d['brand_name']} {d['shade_name']} eyeliner along her lash line"

def _mascara_prompt(d, skin_tone="medium"):
    return (
        f"apply {d['brand_name']} {d['shade_name']} mascara to her upper eyelashes only — "
        f"make them look longer, fuller and darker, not clumpy or spidery"
    )

def _eyebrow_prompt(d, skin_tone="medium"):
    return (
        f"change the color of her existing eyebrows to {d['shade_name']} "
        f"using {d['brand_name']} brow product — do not change brow shape or thickness, only color"
    )

def _blush_prompt(d, skin_tone="medium"):
    if skin_tone in ("deep", "rich"):
        return (
            f"apply {d['brand_name']} {d['shade_name']} blush with strong pigmentation "
            f"to the apples of her cheeks and blend upward — make it clearly visible on her deep skin tone"
        )
    return (
        f"apply {d['brand_name']} {d['shade_name']} blush softly to the apples of her cheeks, "
        f"blending upward toward the cheekbones"
    )

def _bronzer_prompt(d, skin_tone="medium"):
    if skin_tone in ("deep", "rich"):
        return (
            f"apply {d['brand_name']} {d['shade_name']} bronzer with visible pigmentation "
            f"along her temples and cheekbones — ensure it shows on her deep skin tone"
        )
    return (
        f"apply {d['brand_name']} {d['shade_name']} bronzer softly along her temples "
        f"and cheekbones in a natural sun-kissed way, fully blended with no harsh lines"
    )

def _highlighter_prompt(d, skin_tone="medium"):
    if skin_tone in ("deep", "rich"):
        return (
            f"apply {d['brand_name']} {d['shade_name']} highlighter to the tops of her cheekbones "
            f"and nose bridge — use strong pigmentation so the glow is clearly visible on her deep skin tone"
        )
    return (
        f"apply {d['brand_name']} {d['shade_name']} highlighter to the tops of her cheekbones "
        f"and nose bridge only — natural glow, not glitter"
    )


# ── Registry ──────────────────────────────────────────────────────

PROMPT_BUILDERS = {
    "lipstick":    _lipstick_prompt,
    "lip-gloss":   _lipgloss_prompt,
    "lip-liner":   _lipliner_prompt,
    "eyeshadow":   _eyeshadow_prompt,
    "eyeliner":    _eyeliner_prompt,
    "mascara":     _mascara_prompt,
    "eyebrow":     _eyebrow_prompt,
    "blush":       _blush_prompt,
    "bronzer":     _bronzer_prompt,
    "highlighter": _highlighter_prompt,
}


# ── Zone definitions ──────────────────────────────────────────────

ZONE_ORDER = {
    "lips":   ["lip-liner", "lipstick", "lip-gloss"],
    "eyes":   ["eyeshadow", "eyeliner", "mascara", "eyebrow"],
    "cheeks": ["blush", "bronzer", "highlighter"],
}

# Global application order across zones: cheeks → eyes → lips
# mirrors real makeup application order
MULTIZONE_ZONE_ORDER = ["cheeks", "eyes", "lips"]

CATEGORY_ZONE = {cat: zone for zone, cats in ZONE_ORDER.items() for cat in cats}

CATEGORY_DISPLAY = {
    "lip-liner":   "lip liner",
    "lipstick":    "lipstick",
    "lip-gloss":   "lip gloss",
    "eyeshadow":   "eyeshadow",
    "eyeliner":    "eyeliner",
    "mascara":     "mascara",
    "eyebrow":     "eyebrow product",
    "blush":       "blush",
    "bronzer":     "bronzer",
    "highlighter": "highlighter",
}


# ── Zone layering strategies ──────────────────────────────────────

ZONE_LAYER_STRATEGY = {
    "lips":   "layer",
    "eyes":   "region",
    "cheeks": "blend",
}

ZONE_CONNECTORS = {
    "layer":  ", then ",
    "region": ", then ",
    "blend":  ", then ",
}


# ── Sort helpers ──────────────────────────────────────────────────

def sort_shade_ids_by_zone_order(category_slugs: list[str]) -> list[str]:
    order_map = {}
    for zone, cats in ZONE_ORDER.items():
        for i, cat in enumerate(cats):
            order_map[cat] = i
    known   = [c for c in category_slugs if c in order_map]
    unknown = [c for c in category_slugs if c not in order_map]
    known.sort(key=lambda c: order_map[c])
    return known + unknown


def sort_rows_by_multizone_order(rows: list) -> list:
    """
    Sort (shade, product, brand, category) rows by:
    1. Zone order: cheeks → eyes → lips
    2. Within zone: category application order
    """
    zone_priority = {zone: i for i, zone in enumerate(MULTIZONE_ZONE_ORDER)}

    def sort_key(row):
        cat_slug  = row[3].slug
        zone      = CATEGORY_ZONE.get(cat_slug, "unknown")
        zone_idx  = zone_priority.get(zone, 99)
        zone_cats = ZONE_ORDER.get(zone, [])
        cat_idx   = zone_cats.index(cat_slug) if cat_slug in zone_cats else 99
        return (zone_idx, cat_idx)

    return sorted(rows, key=sort_key)


# ── Single prompt ─────────────────────────────────────────────────

def build_prompt(category_slug: str, product_data: dict, detected_skin_tone: str = "medium") -> str:
    builder = PROMPT_BUILDERS.get(category_slug)
    if not builder:
        raise ValueError(f"No prompt builder for '{category_slug}'. Available: {list(PROMPT_BUILDERS.keys())}")
    try:
        return builder(product_data, detected_skin_tone)
    except TypeError:
        return builder(product_data)


def get_supported_categories():
    return list(PROMPT_BUILDERS.keys())


# ── Single-zone combo prompt ──────────────────────────────────────

def build_combined_prompt(
    steps: list[dict],
    detected_skin_tone: str = "medium",
) -> str:
    """
    Build a zone-aware combined prompt for multiple products in the SAME zone.

    Each step must have:
        - category_slug: str
        - product_data: dict with brand_name, shade_name
    """
    if len(steps) == 1:
        return build_prompt(steps[0]["category_slug"], steps[0]["product_data"], detected_skin_tone)

    zone      = CATEGORY_ZONE.get(steps[0]["category_slug"], "unknown")
    connector = ZONE_CONNECTORS.get(ZONE_LAYER_STRATEGY.get(zone, "layer"), ", then ")

    parts = []
    for step in steps:
        builder = PROMPT_BUILDERS.get(step["category_slug"])
        if not builder:
            raise ValueError(f"No prompt builder for '{step['category_slug']}'.")
        try:
            parts.append(builder(step["product_data"], detected_skin_tone))
        except TypeError:
            parts.append(builder(step["product_data"]))

    return connector.join(parts)


# ── Multi-zone prompt ─────────────────────────────────────────────

def build_multizone_prompt(
    rows: list,
    detected_skin_tone: str = "medium",
) -> str:
    """
    Build a single combined prompt for products across multiple zones.

    rows: list of (shade, product, brand, category) tuples
          already sorted by sort_rows_by_multizone_order()

    Applies in real makeup order: cheeks → eyes → lips
    Cheeks zone is limited to 1 product (validated upstream in main.py)
    """
    # Group by zone preserving MULTIZONE_ZONE_ORDER
    zone_groups: dict[str, list] = {}
    for row in rows:
        cat_slug = row[3].slug
        zone     = CATEGORY_ZONE.get(cat_slug, "unknown")
        if zone not in zone_groups:
            zone_groups[zone] = []
        zone_groups[zone].append(row)

    zone_sections = []

    for zone in MULTIZONE_ZONE_ORDER:
        if zone not in zone_groups:
            continue

        zone_rows  = zone_groups[zone]
        connector  = ZONE_CONNECTORS.get(ZONE_LAYER_STRATEGY.get(zone, "layer"), ", then ")

        parts = []
        for shade, product, brand, category in zone_rows:
            builder = PROMPT_BUILDERS.get(category.slug)
            if not builder:
                continue
            product_data = {"brand_name": brand.name, "shade_name": shade.name}
            try:
                parts.append(builder(product_data, detected_skin_tone))
            except TypeError:
                parts.append(builder(product_data))

        if parts:
            zone_sections.append(f"{zone.upper()}: {connector.join(parts)}")

    steps_text = "\n".join(f"- {s}" for s in zone_sections)

    return (
        f"Apply the following makeup products to this girl's face exactly as described. "
        f"Apply each zone carefully and do not skip any step. "
        f"Do not add any products or effects not listed below.\n\n"
        f"{steps_text}\n\n"
        f"Keep her skin, facial features, hair, and background completely unchanged. "
        f"The result should look like a real professionally applied makeup look."
    )