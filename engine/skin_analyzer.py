"""
engine/skin_analyzer.py
Claude-powered skin tone + color season analysis.
Called by POST /analyze-skin in main.py.
"""

import os, json, re, base64
from pathlib import Path
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

MODEL = "claude-sonnet-4-6"

# ── Season palette data ────────────────────────────────────────────

SEASON_CONTEXT = """
Color seasons and their makeup palettes:

SPRING (warm + light):
  Undertone: warm. Best colors: peach, coral, warm beige, golden yellow, light olive.
  Makeup: peachy nudes, warm corals, golden highlights, light bronzers.

SUMMER (cool + light/medium):
  Undertone: cool. Best colors: rose, mauve, dusty pink, lavender, soft berry.
  Makeup: rose-toned nudes, cool pinks, soft mauves, icy highlights.

AUTUMN (warm + deep):
  Undertone: warm. Best colors: terracotta, rust, burnt orange, warm brown, olive.
  Makeup: warm browns, terracotta, brick reds, bronze, gold.

WINTER (cool + deep/high contrast):
  Undertone: cool. Best colors: deep burgundy, true red, plum, navy, pure white.
  Makeup: bold berry lips, cool plums, silver highlights, deep contouring.
"""

ANALYSIS_PROMPT = """
You are an expert makeup artist and color analyst.
Analyze the face in this photo and return ONLY a valid JSON object — no markdown, no explanation, no code fences.

Determine:
1. skin_tone: one of ["fair", "light", "medium", "tan", "deep"]
2. undertone: one of ["warm", "cool", "neutral"]
3. hex: the approximate skin tone as a hex color string (e.g. "#D4A57A")
4. season: one of ["Spring", "Summer", "Autumn", "Winter"] based on the color season system
5. season_description: 1–2 sentences explaining why this season fits this person
6. recommended_colors: an array of exactly 6 objects, 2 per category from ["Lip", "Eye", "Face"].
   Each object must have:
     - name: color name (e.g. "Warm Terracotta")
     - hex: hex code (e.g. "#C45A3A")
     - category: one of ["Lip", "Eye", "Face"]
     - why: one short sentence explaining why this color suits them

Color season reference:
""" + SEASON_CONTEXT + """

Return ONLY this JSON shape:
{
  "skin_tone": "...",
  "undertone": "...",
  "hex": "#......",
  "season": "...",
  "season_description": "...",
  "recommended_colors": [
    { "name": "...", "hex": "#......", "category": "Lip", "why": "..." },
    { "name": "...", "hex": "#......", "category": "Lip", "why": "..." },
    { "name": "...", "hex": "#......", "category": "Eye", "why": "..." },
    { "name": "...", "hex": "#......", "category": "Eye", "why": "..." },
    { "name": "...", "hex": "#......", "category": "Face", "why": "..." },
    { "name": "...", "hex": "#......", "category": "Face", "why": "..." }
  ]
}
"""

# ── Fallback ───────────────────────────────────────────────────────

FALLBACK_RESULT = {
    "skin_tone":          "medium",
    "undertone":          "neutral",
    "hex":                "#C8956A",
    "season":             "Autumn",
    "season_description": "Could not detect clearly from the photo. Autumn is a versatile starting point.",
    "recommended_colors": [
        {"name": "Warm Nude",    "hex": "#C4956A", "category": "Lip",  "why": "Universally flattering warm nude."},
        {"name": "Soft Coral",   "hex": "#E07B54", "category": "Lip",  "why": "Adds warmth without overpowering."},
        {"name": "Warm Brown",   "hex": "#8B5E3C", "category": "Eye",  "why": "Defines eyes with earthy warmth."},
        {"name": "Bronze",       "hex": "#CD7F32", "category": "Eye",  "why": "Adds depth and dimension."},
        {"name": "Peach Blush",  "hex": "#FFAD8A", "category": "Face", "why": "Gives a natural healthy flush."},
        {"name": "Warm Bronzer", "hex": "#A0724A", "category": "Face", "why": "Sculpts and warms the complexion."},
    ],
}


async def analyze_skin_tone(image_path: str) -> dict:
    """
    Send image to Claude, extract skin tone + color season analysis.
    Returns a dict matching SkinAnalysisResult shape.
    Same interface as before — drop-in replacement.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        image_bytes = f.read()

    ext_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = ext_map.get(path.suffix.lower(), "image/jpeg")

    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": media_type,
                            "data":       image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if Claude adds them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            return FALLBACK_RESULT

    # Validate required fields
    required = {"skin_tone", "undertone", "hex", "season", "season_description", "recommended_colors"}
    if not required.issubset(result.keys()):
        return FALLBACK_RESULT

    colors = result.get("recommended_colors", [])
    if len(colors) < 6:
        return FALLBACK_RESULT

    for color in colors:
        for field in ("name", "hex", "category", "why"):
            if field not in color:
                return FALLBACK_RESULT

    return result