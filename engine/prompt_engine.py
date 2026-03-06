"""
GlamAI Prompt Engine v11 — ultra minimal, ref images handle color accuracy

Formula: "You are a pro makeup artist. put the [brand] [shade] [product] on this girl."
Color consistency comes from ref images, not prompt text.
"""

# ── Individual prompt builders ────────────────────────────────────

def _lipstick_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} lipstick on this girl."

def _lipgloss_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} lip gloss on this girl."

def _lipliner_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} lip liner on this girl."

def _eyeshadow_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} eyeshadow on this girl."

def _eyeliner_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} eyeliner on this girl."

def _mascara_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} mascara on this girl."

def _eyebrow_prompt(d):
    return f"fill in this girl's eyebrows with {d['brand_name']} {d['shade_name']} brow product."

def _foundation_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} foundation on this girl's face."

def _concealer_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} concealer under this girl's eyes."

def _blush_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} blush on this girl's cheeks."

def _bronzer_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} bronzer on this girl's cheekbones and temples."

def _highlighter_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} highlighter on this girl's cheekbones and nose bridge."

def _contour_prompt(d):
    return f"put the {d['brand_name']} {d['shade_name']} contour on this girl's cheekbones."


# ── Registry ─────────────────────────────────────────────────────

PROMPT_BUILDERS = {
    "lipstick":    _lipstick_prompt,
    "lip-gloss":   _lipgloss_prompt,
    "lip-liner":   _lipliner_prompt,
    "eyeshadow":   _eyeshadow_prompt,
    "eyeliner":    _eyeliner_prompt,
    "mascara":     _mascara_prompt,
    "eyebrow":     _eyebrow_prompt,
    "foundation":  _foundation_prompt,
    "concealer":   _concealer_prompt,
    "blush":       _blush_prompt,
    "bronzer":     _bronzer_prompt,
    "highlighter": _highlighter_prompt,
    "contour":     _contour_prompt,
}


def build_prompt(category_slug: str, product_data: dict, detected_skin_tone: str = "medium") -> str:
    builder = PROMPT_BUILDERS.get(category_slug)
    if not builder:
        raise ValueError(f"No prompt builder for '{category_slug}'. Available: {list(PROMPT_BUILDERS.keys())}")
    return builder(product_data)

def get_supported_categories():
    return list(PROMPT_BUILDERS.keys())


# ── Combo support ─────────────────────────────────────────────────

ZONE_ORDER = {
    "lips":   ["lip-liner", "lipstick", "lip-gloss"],
    "eyes":   ["eyeshadow", "eyeliner", "mascara", "eyebrow"],
    "face":   ["foundation", "concealer"],
    "cheeks": ["blush", "bronzer", "contour", "highlighter"],
}

CATEGORY_ZONE = {cat: zone for zone, cats in ZONE_ORDER.items() for cat in cats}

CATEGORY_DISPLAY = {
    "lip-liner":   "lip liner",
    "lipstick":    "lipstick",
    "lip-gloss":   "lip gloss",
    "eyeshadow":   "eyeshadow",
    "eyeliner":    "eyeliner",
    "mascara":     "mascara",
    "eyebrow":     "eyebrow product",
    "foundation":  "foundation",
    "concealer":   "concealer",
    "blush":       "blush",
    "bronzer":     "bronzer",
    "contour":     "contour",
    "highlighter": "highlighter",
}


def sort_shade_ids_by_zone_order(category_slugs: list[str]) -> list[str]:
    order_map = {}
    for zone, cats in ZONE_ORDER.items():
        for i, cat in enumerate(cats):
            order_map[cat] = i
    known   = [c for c in category_slugs if c in order_map]
    unknown = [c for c in category_slugs if c not in order_map]
    known.sort(key=lambda c: order_map[c])
    return known + unknown


def build_combined_prompt(
    steps: list[dict],
    detected_skin_tone: str = "medium",
) -> str:
    parts = []
    for step in steps:
        builder = PROMPT_BUILDERS.get(step["category_slug"])
        if not builder:
            raise ValueError(f"No prompt builder for '{step['category_slug']}'.")
        parts.append(builder(step["product_data"]))

    combined = " and ".join(parts)
    return combined