"""
GlamAI Prompt Engine v13 — zone-aware layering, no hardcoding

Disabled (pending skin tone classifier):
  - contour   → too subtle, deep skin invisible
  - foundation → needs skin tone matching
  - concealer  → needs skin tone matching

Active zones: lips, eyes, cheeks (blush/bronzer/highlighter only)
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
    return (
        f"Apply {d['brand_name']} {d['shade_name']} mascara to this girl's "
        f"upper eyelashes only. Make them look longer, fuller and darker. "
        f"Keep the eye shape completely unchanged. Natural mascara finish, "
        f"not clumpy or spidery."
    )

def _eyebrow_prompt(d):
    return (
        f"Change the color of this girl's existing eyebrows to {d['shade_name']} "
        f"using {d['brand_name']} brow product. Do not change the shape, thickness, "
        f"or density of her eyebrows. Only change the color."
    )

def _blush_prompt(d):
    return (
        f"Apply {d['brand_name']} {d['shade_name']} blush softly "
        f"to the apples of this girl's cheeks and blend upward toward "
        f"the cheekbones. Keep it natural and well-blended."
    )

def _bronzer_prompt(d):
    return (
        f"Apply {d['brand_name']} {d['shade_name']} bronzer softly "
        f"along this girl's temples and cheekbones in a natural sun-kissed way. "
        f"Blend fully, no harsh lines."
    )

def _highlighter_prompt(d):
    return (
        f"Apply {d['brand_name']} {d['shade_name']} highlighter to "
        f"the very tops of this girl's cheekbones and nose bridge only. "
        f"It should look like a natural glow, not glitter."
    )


# ── Disabled prompts (re-enable after skin tone classifier) ───────

# def _foundation_prompt(d):
#     return f"put the {d['brand_name']} {d['shade_name']} foundation on this girl's face."

# def _concealer_prompt(d):
#     return f"put the {d['brand_name']} {d['shade_name']} concealer under this girl's eyes."

# def _contour_prompt(d, skin_tone="medium"):
#     if skin_tone in ("deep", "rich"):
#         return (
#             f"Apply {d['brand_name']} {d['shade_name']} contour stick "
#             f"to the hollows beneath this girl's cheekbones. "
#             f"Her skin is very dark — use heavy pigmentation so the contour "
#             f"creates a clearly visible deep shadow and defined cheekbone structure. "
#             f"Blend the edges but the contour must be strongly visible."
#         )
#     return (
#         f"Apply {d['brand_name']} {d['shade_name']} contour powder "
#         f"softly to the hollows beneath this girl's cheekbones only. "
#         f"Blend edges completely. Keep it naturally blended but visibly defined."
#     )


# ── Registry ─────────────────────────────────────────────────────

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
    # "foundation":  _foundation_prompt,   ← disabled: needs skin tone classifier
    # "concealer":   _concealer_prompt,    ← disabled: needs skin tone classifier
    # "contour":     _contour_prompt,      ← disabled: too subtle on deep skin
}


# ── Zone definitions ──────────────────────────────────────────────

ZONE_ORDER = {
    "lips":   ["lip-liner", "lipstick", "lip-gloss"],
    "eyes":   ["eyeshadow", "eyeliner", "mascara", "eyebrow"],
    "cheeks": ["blush", "bronzer", "highlighter"],
    # "face": ["foundation", "concealer"],  ← disabled: needs skin tone classifier
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
    "blush":       "blush",
    "bronzer":     "bronzer",
    "highlighter": "highlighter",
    # "foundation":  "foundation",   ← disabled
    # "concealer":   "concealer",    ← disabled
    # "contour":     "contour",      ← disabled
}


# ── Zone layering strategies ──────────────────────────────────────
#
# "layer"  → products build on top of each other (lips: liner → lipstick → gloss)
# "blend"  → products blend in the same area (cheeks: blush + bronzer)
# "region" → products go on different sub-regions (eyes: shadow on lid, liner on lash line)
# "cover"  → first covers, second refines (face: foundation then concealer) — disabled

ZONE_LAYER_STRATEGY = {
    "lips":   "layer",
    "eyes":   "region",
    "cheeks": "blend",
    # "face": "cover",  ← disabled
}

ZONE_CONNECTORS = {
    "layer":  " Then layer on top, ",
    "region": " Then, ",
    "blend":  " Then blend with, ",
    # "cover": " Then, ",  ← disabled
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


# ── Combo prompt ──────────────────────────────────────────────────

def build_combined_prompt(
    steps: list[dict],
    detected_skin_tone: str = "medium",
) -> str:
    """
    Build a zone-aware combined prompt for multiple products.

    Each step must have:
        - category_slug: str
        - product_data: dict with brand_name, shade_name

    Rules:
        - All steps must be in the same zone (validated upstream in main.py)
        - Zone strategy determines how prompts are joined
        - Single step falls back to build_prompt()
        - Cheeks zone is NOT combo-allowed (validated upstream)
    """
    if len(steps) == 1:
        return build_prompt(steps[0]["category_slug"], steps[0]["product_data"], detected_skin_tone)

    zone = CATEGORY_ZONE.get(steps[0]["category_slug"], "unknown")
    strategy = ZONE_LAYER_STRATEGY.get(zone, "layer")
    connector = ZONE_CONNECTORS.get(strategy, " and ")

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