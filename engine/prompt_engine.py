"""
GlamAI Prompt Engine v7
- build_prompt()          — single category, unchanged from v4
- build_combined_prompt() — NEW: merges multiple categories into one prompt (one API call)
- build_combo_prompt()    — kept for reference, no longer used by /generate-combo
"""

def _hex_to_color_description(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    brightness = (r + g + b) / 3

    if r > 2*g and r > 2*b:
        if brightness < 70:    return "very dark deep burgundy red"
        elif brightness < 120: return "dark rich red"
        elif brightness < 170: return "medium red"
        else:                  return "bright vivid red"
    elif r > g and b > g and abs(r-b) < 40:
        if brightness < 80:    return "very dark plum purple"
        else:                  return "mauve rose purple"
    elif b > r and b > g:
        if brightness < 80:    return "very dark navy blue"
        else:                  return "medium blue"
    elif r > 200 and g > 150 and b > 130 and brightness > 170:
        return "light nude pink"
    elif r > 160 and g > 110 and b > 80 and brightness > 140:
        return "medium nude beige"
    elif r > g*1.4 and b > g*1.4:
        return "deep berry wine"
    elif r < 60 and g < 60 and b < 60:
        return "black"
    elif r > 200 and g > 190 and b > 190:
        return "very light pale pink"
    elif r > 200 and g > 180 and b > 150:
        return "warm champagne"
    elif r > 150 and g > 100 and b < 80:
        return "warm coral orange"
    elif r > 100 and g > 60 and b < 50:
        return "warm brown"
    elif r > 150 and g > 120 and b < 100:
        return "warm peach"
    elif r > 180 and g > 150 and b > 100:
        return "golden bronze"
    else:
        return "dark neutral"


# ── Skin texture restoration block ───────────────────────────────────────────

SKIN_TEXTURE = (
    "After applying the makeup, adjust the image processing to restore natural skin texture: "
    "reduce any skin smoothing or softening that was applied, "
    "add subtle natural noise and grain back into the skin to restore visible pores and imperfections, "
    "ensure redness, acne, blemishes and uneven skin tone are preserved exactly as in the original photo, "
    "the skin must not look retouched, filtered, or artificially perfected — "
    "only the makeup zones should differ from the original, everything else must match the raw unedited original photo."
)


# ── Individual prompt builders ────────────────────────────────────────────────

def _lipstick_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#cc0000"))
    return (
        f"Apply {color} {d['finish_type']} lipstick to the lips only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _lipgloss_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#ff9999"))
    return (
        f"Apply {color} glossy lip gloss to the lips only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _lipliner_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#cc0000"))
    return (
        f"Draw a thin precise {color} lip liner line strictly along the outer edge and border of the lips only. "
        f"Do NOT fill the lips. Do NOT color inside the lips. Only outline the lip perimeter like tracing with a pencil. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _eyeshadow_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#996633"))
    return (
        f"Apply {color} {d['finish_type']} eyeshadow to the eyelids only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _eyeliner_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#000000"))
    return (
        f"Apply {color} eyeliner along the upper lash line only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _mascara_prompt(d):
    return (
        f"Apply dark mascara to the eyelashes only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _eyebrow_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#4a3728"))
    return (
        f"Fill in the eyebrows with {color} brow product following the existing brow shape exactly. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _foundation_prompt(d):
    return (
        f"Apply {d['coverage']} coverage {d['finish_type']} foundation evenly across the face. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _concealer_prompt(d):
    return (
        f"Apply concealer under the eyes only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _blush_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#ff9999"))
    return (
        f"Apply {color} {d['finish_type']} blush to the cheeks only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _bronzer_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#a0714f"))
    return (
        f"Apply {color} {d['finish_type']} bronzer to the cheekbones and temples only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _highlighter_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#ffd700"))
    return (
        f"Apply {color} {d['finish_type']} highlighter to the tops of cheekbones and nose bridge only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )

def _contour_prompt(d):
    color = _hex_to_color_description(d.get("hex_color", "#9b6e4a"))
    return (
        f"Apply {color} contour under the cheekbones only. "
        f"Shade: {d['shade_name']} by {d['brand_name']}. "
        f"{d.get('prompt_supplement', '')}"
    )


# ── Registry ──────────────────────────────────────────────────────────────────

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

SKIN_TONE_NOTES = {
    "fair":   "The person has fair/porcelain skin.",
    "light":  "The person has light skin.",
    "medium": "The person has medium skin.",
    "tan":    "The person has tan skin.",
    "deep":   "The person has deep skin.",
    "rich":   "The person has rich/ebony skin.",
}


def build_prompt(category_slug: str, product_data: dict, detected_skin_tone: str = "medium") -> str:
    """Single category prompt — unchanged from v4."""
    builder = PROMPT_BUILDERS.get(category_slug)
    if not builder:
        raise ValueError(f"No prompt builder for '{category_slug}'. Available: {list(PROMPT_BUILDERS.keys())}")
    skin_note = SKIN_TONE_NOTES.get(detected_skin_tone, "")
    base = builder(product_data)
    return f"{skin_note} {base} {SKIN_TEXTURE}".strip()

def get_supported_categories():
    return list(PROMPT_BUILDERS.keys())


# ═════════════════════════════════════════════════════════════════════════════
# COMBO SUPPORT — v7: single API call, one combined prompt
# ═════════════════════════════════════════════════════════════════════════════

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
    """Sort category slugs by correct application order within their zone."""
    order_map = {}
    for zone, cats in ZONE_ORDER.items():
        for i, cat in enumerate(cats):
            order_map[cat] = i
    known   = [c for c in category_slugs if c in order_map]
    unknown = [c for c in category_slugs if c not in order_map]
    known.sort(key=lambda c: order_map[c])
    return known + unknown


def build_combined_prompt(
    steps: list[dict],           # [{"category_slug": ..., "product_data": ...}, ...]
    detected_skin_tone: str = "medium",
) -> str:
    """
    Builds ONE prompt that applies ALL combo products in a single API call.

    Each step is numbered and clearly separated so gpt-image-1 knows
    exactly what to apply to which zone, with no overlap or conflict.

    steps must already be sorted in application order.
    """
    skin_note = SKIN_TONE_NOTES.get(detected_skin_tone, "")

    intro = (
        f"{skin_note} "
        f"Apply ALL of the following makeup products to this face photo simultaneously. "
        f"Each product applies to its own specific zone only — do not let them overlap or interfere. "
        f"Apply each one precisely and completely:"
    )

    instructions = []
    for i, step in enumerate(steps, 1):
        builder = PROMPT_BUILDERS.get(step["category_slug"])
        if not builder:
            raise ValueError(f"No prompt builder for '{step['category_slug']}'.")
        instruction = builder(step["product_data"]).strip()
        instructions.append(f"[{i}] {instruction}")

    combined = "\n".join(instructions)

    return f"{intro}\n{combined}\n{SKIN_TEXTURE}".strip()