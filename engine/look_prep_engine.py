"""
engine/look_prep_engine.py
──────────────────────────
All Gemini text calls for Look Preparation feature.
Uses gemini-2.5-flash-lite (text only — cheap, fast).

Functions:
    validate_product(raw_input)         → is it real? zone? brand/shade extracted?
    check_sufficiency(bag, occasion)    → per-zone score + advice
    select_products(bag, occasion)      → picks best products from bag for generation
"""

import json
import os
import re
from google import genai
from google.genai import types

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL   = "gemini-2.5-flash-lite"


def _clean_json(text: str) -> str:
    """Strip markdown fences if Gemini wraps response in ```json ... ```"""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*",     "", text)
    text = re.sub(r"\s*```$",     "", text)
    return text.strip()


# ── 1. Product Validation ─────────────────────────────────────────────────────

async def validate_product(raw_input: str) -> dict:
    """
    Validates whether user's free-text input is a real cosmetic product.
    Extracts: brand, product_name, shade, zone, hex_color.
    Flags shade_missing if shade could not be determined.

    Returns:
    {
        "valid":         bool,
        "reject_reason": str | None,
        "brand":         str | None,
        "product_name":  str | None,
        "shade":         str | None,
        "shade_missing": bool,
        "zone":          "lip" | "eye" | "cheek" | None,
        "hex_color":     str | None,   # best guess e.g. "#C45A65"
    }
    """
    prompt = f"""You are a professional makeup expert and product database.

A user typed this as one of their makeup products: "{raw_input}"

Analyze this and respond ONLY with a JSON object. No explanation, no markdown, no extra text.

Rules:
- "valid" is true only if this is a real, commercially available makeup product (lipstick, lip gloss, lip liner, eyeshadow, eyeliner, mascara, eyebrow pencil, blush, bronzer, highlighter)
- "valid" is false for skincare, perfume, nail polish, tools, brushes, fake/fictional products, or food
- "zone" must be one of: "lip", "eye", "cheek"
- "shade" should be the color name or shade number if mentioned or if it's well-known (e.g. MAC Ruby Woo is always "Ruby Woo")
- "shade_missing" is true if the product exists but no shade was mentioned AND the shade cannot be inferred
- "hex_color" is your best guess of the shade's color in hex format — null if shade is missing

JSON format:
{{
  "valid":         true or false,
  "reject_reason": null or "reason why invalid",
  "brand":         "Brand Name" or null,
  "product_name":  "Product Name" or null,
  "shade":         "Shade Name" or null,
  "shade_missing": true or false,
  "zone":          "lip" or "eye" or "cheek" or null,
  "hex_color":     "#RRGGBB" or null
}}"""

    response = _client.models.generate_content(
        model    = MODEL,
        contents = prompt,
        config   = types.GenerateContentConfig(
            temperature      = 0.1,
            max_output_tokens = 300,
        ),
    )

    try:
        data = json.loads(_clean_json(response.text))
    except (json.JSONDecodeError, AttributeError):
        return {
            "valid":         False,
            "reject_reason": "Could not analyze product. Please try again.",
            "brand":         None,
            "product_name":  None,
            "shade":         None,
            "shade_missing": False,
            "zone":          None,
            "hex_color":     None,
        }

    # Sanitize
    data.setdefault("valid",         False)
    data.setdefault("reject_reason", None)
    data.setdefault("brand",         None)
    data.setdefault("product_name",  None)
    data.setdefault("shade",         None)
    data.setdefault("shade_missing", False)
    data.setdefault("zone",          None)
    data.setdefault("hex_color",     None)

    return data


# ── 2. Sufficiency Check ──────────────────────────────────────────────────────

async def check_sufficiency(bag: list[dict], occasion: str) -> dict:
    """
    Checks whether a user's bag has enough products for the given occasion.
    Returns per-zone scores and advice.

    bag: list of {brand, product_name, shade, zone, hex_color}
    occasion: e.g. "First Date", "Christmas", "Office", "Party"

    Returns:
    {
        "overall":  "great" | "ok" | "limited",
        "zones": {
            "lip":   { "score": "great"|"ok"|"missing", "count": int, "advice": str },
            "eye":   { ... },
            "cheek": { ... }
        },
        "summary": str,   <- overall advice text shown to user
        "can_generate": bool
    }
    """
    bag_text = "\n".join(
        f"- {p.get('brand','')} {p.get('product_name','')} in {p.get('shade','unknown shade')} [{p.get('zone','')}]"
        for p in bag
    )

    prompt = f"""You are a professional makeup artist reviewing a client's makeup bag for a specific occasion.

Occasion: {occasion}

Their makeup bag:
{bag_text}

Evaluate whether they have enough products for a great {occasion} look.
Assess each zone (lip, eye, cheek) separately.

Respond ONLY with a JSON object. No explanation, no markdown, no extra text.

JSON format:
{{
  "overall": "great" or "ok" or "limited",
  "zones": {{
    "lip":   {{ "score": "great" or "ok" or "missing", "count": <number of lip products>, "advice": "<1 sentence>" }},
    "eye":   {{ "score": "great" or "ok" or "missing", "count": <number of eye products>, "advice": "<1 sentence>" }},
    "cheek": {{ "score": "great" or "ok" or "missing", "count": <number of cheek products>, "advice": "<1 sentence>" }}
  }},
  "summary": "<2-3 sentence overall advice for this occasion>",
  "can_generate": true or false
}}

Rules:
- "great" = 2+ good options for this occasion
- "ok" = 1 product, workable but limited
- "missing" = no products for this zone at all
- "can_generate" = true if at least lip OR eye zone is "ok" or "great"
- Keep advice friendly and specific to the occasion"""

    response = _client.models.generate_content(
        model    = MODEL,
        contents = prompt,
        config   = types.GenerateContentConfig(
            temperature       = 0.2,
            max_output_tokens = 500,
        ),
    )

    try:
        data = json.loads(_clean_json(response.text))
    except (json.JSONDecodeError, AttributeError):
        return {
            "overall": "ok",
            "zones": {
                "lip":   {"score": "ok", "count": 0, "advice": "Unable to analyze."},
                "eye":   {"score": "ok", "count": 0, "advice": "Unable to analyze."},
                "cheek": {"score": "ok", "count": 0, "advice": "Unable to analyze."},
            },
            "summary":      "We couldn't fully analyze your bag. You can still generate a look.",
            "can_generate": True,
        }

    data.setdefault("overall",      "ok")
    data.setdefault("zones",        {})
    data.setdefault("summary",      "")
    data.setdefault("can_generate", True)

    return data


# ── 3. Product Selection for Generation ──────────────────────────────────────

async def select_products_for_occasion(bag: list[dict], occasion: str) -> dict:
    """
    Picks the best products from the user's bag for the occasion.
    Returns a structured selection ready to feed into prompt_engine.

    Returns:
    {
        "selected": [
            {
                "brand":        str,
                "product_name": str,
                "shade":        str,
                "zone":         "lip" | "eye" | "cheek",
                "hex_color":    str | None,
                "reason":       str   <- why this was chosen
            },
            ...
        ],
        "look_description": str   <- e.g. "Soft romantic look with warm coral lips"
    }
    """
    bag_text = "\n".join(
        f"- [{p.get('zone','')}] {p.get('brand','')} {p.get('product_name','')} "
        f"in {p.get('shade','unknown shade')}"
        + (f" ({p.get('hex_color','')})" if p.get("hex_color") else "")
        for p in bag
    )

    prompt = f"""You are a professional makeup artist creating a look for a client.

Occasion: {occasion}

Client's available products:
{bag_text}

Select the best combination of products for a great {occasion} look.
Pick at most 1 product per sub-category (e.g. 1 lipstick, 1 eyeshadow, 1 blush).
Prioritize colors that work well together and suit the occasion.

Respond ONLY with a JSON object. No explanation, no markdown, no extra text.

JSON format:
{{
  "selected": [
    {{
      "brand":        "Brand Name",
      "product_name": "Product Name",
      "shade":        "Shade Name",
      "zone":         "lip" or "eye" or "cheek",
      "hex_color":    "#RRGGBB" or null,
      "reason":       "One sentence why this was chosen"
    }}
  ],
  "look_description": "Brief description of the overall look (1 sentence)"
}}"""

    response = _client.models.generate_content(
        model    = MODEL,
        contents = prompt,
        config   = types.GenerateContentConfig(
            temperature       = 0.3,
            max_output_tokens = 600,
        ),
    )

    try:
        data = json.loads(_clean_json(response.text))
    except (json.JSONDecodeError, AttributeError):
        return {"selected": [], "look_description": ""}

    data.setdefault("selected",          [])
    data.setdefault("look_description",  "")

    return data