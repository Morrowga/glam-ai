"""
GlamAI Brand DNA — every brand has a unique makeup signature.
This ensures NYX looks like NYX, Charlotte Tilbury looks like CT,
Fenty looks like Fenty. Not generic AI slop.
"""

BRAND_DNA = {

    # ── LUXURY ────────────────────────────────────────────────────

    "mac": {
        "persona": "professional editorial makeup artist",
        "finish_signature": "pigment-rich, high-impact, buildable intensity with a fashion-forward edge",
        "texture_language": "creamy yet long-wearing, second-skin adhesion",
        "application_style": "precise placement, clean edges, professional artistry",
        "skin_tone_approach": "MAC is formulated for ALL skin tones equally — deep shades are saturated and opaque, not ashy or washed out",
        "lighting_quality": "studio editorial lighting, sharp definition",
        "realism_anchor": "looks like a MAC counter makeover, not a filter",
    },

    "charlotte-tilbury": {
        "persona": "luxury red carpet glam artist",
        "finish_signature": "soft-focus airbrushed glow, Hollywood glamour, never harsh",
        "texture_language": "velvet-smooth, blurred skin effect, luminous without being glittery",
        "application_style": "seamlessly blended, diffused edges, sculpted but soft",
        "skin_tone_approach": "warm golden undertones favored — results look lit-from-within on light to medium skin, rich and radiant on deeper skin",
        "lighting_quality": "warm golden hour light, soft shadows",
        "realism_anchor": "looks like a Charlotte Tilbury editorial ad, skin looks expensive",
    },

    "nars": {
        "persona": "French minimalist beauty artist",
        "finish_signature": "effortless Parisian cool, skin still visible through product, undone perfection",
        "texture_language": "lightweight veil, natural skin texture preserved underneath",
        "application_style": "strategic placement, barely-there yet impactful",
        "skin_tone_approach": "neutral to cool undertones, works across all skin tones with natural skin showing through",
        "lighting_quality": "natural daylight, matte cool tones",
        "realism_anchor": "looks like NARS campaign photography — raw, real, confident",
    },

    "dior": {
        "persona": "haute couture beauty house",
        "finish_signature": "ultra-refined, couture precision, timeless elegance",
        "texture_language": "micro-fine particles, featherweight, imperceptible texture",
        "application_style": "artisan-precise, flawless coverage, zero excess",
        "skin_tone_approach": "cool porcelain to warm caramel spectrum, sophisticated neutrals",
        "lighting_quality": "soft studio light, no harsh shadows",
        "realism_anchor": "looks like a Dior Beauty campaign — pristine, polished, editorial",
    },

    "chanel": {
        "persona": "quintessential Parisian luxury",
        "finish_signature": "understated opulence, quiet luxury, refined restraint",
        "texture_language": "satin-smooth, weightless, skin-fusing",
        "application_style": "effortlessly blended, never overdone, chic precision",
        "skin_tone_approach": "classic French complexion tones favored, but universally elegant",
        "lighting_quality": "elegant diffused light, Chanel black and white aesthetic",
        "realism_anchor": "looks like a Chanel ad — less is more, everything is intentional",
    },

    "ysl": {
        "persona": "bold Parisian fashion house",
        "finish_signature": "high-fashion drama, statement color, unapologetic boldness",
        "texture_language": "rich saturated pigment, velvety smooth, long-wearing",
        "application_style": "confident bold placement, sharp definition where needed",
        "skin_tone_approach": "dramatic pigment payoff across all skin tones, deep shades are intense not muddy",
        "lighting_quality": "high contrast fashion photography lighting",
        "realism_anchor": "looks like YSL Beauté campaign — bold, sexy, deliberate",
    },

    "fenty-beauty": {
        "persona": "inclusive beauty pioneer",
        "finish_signature": "skin-matching perfection across 50 shades, second-skin realism",
        "texture_language": "weightless but full-coverage capable, breathable finish",
        "application_style": "seamless blending, skin texture preserved, never cakey",
        "skin_tone_approach": "CRITICAL: Fenty is built for deep and dark skin tones — deep shades must look rich, radiant, perfectly matched — NEVER ashy, grey or washed out. Light shades equally precise.",
        "lighting_quality": "natural diverse lighting showing true skin tone",
        "realism_anchor": "looks like Fenty Beauty campaign — diverse, real, skin looks incredible",
    },

    "huda-beauty": {
        "persona": "full-glam maximalist artist",
        "finish_signature": "full glam, high intensity, heavily pigmented, Instagram-perfect",
        "texture_language": "ultra-pigmented, opaque, dramatic finish",
        "application_style": "full coverage, high definition, every feature enhanced",
        "skin_tone_approach": "warm olive and golden undertones, Middle Eastern and South Asian beauty aesthetic, rich pigments on all skin tones",
        "lighting_quality": "beauty influencer ring light, high definition",
        "realism_anchor": "looks like a Huda Beauty tutorial — full glam, flawless, dramatic",
    },

    "too-faced": {
        "persona": "playful feminine glam",
        "finish_signature": "feminine, flirty, pretty-girl glam — wearable but polished",
        "texture_language": "soft creamy pigments, flattering warm tones, comfortable wear",
        "application_style": "blended softly, romantic and approachable finish",
        "skin_tone_approach": "warm peach and rose tones, flattering on light to medium skin, adjusted warmth for deeper tones",
        "lighting_quality": "soft warm flattering light, pink tones",
        "realism_anchor": "looks like Too Faced campaign — cute, feminine, wearable glam",
    },

    "urban-decay": {
        "persona": "edgy rebellious beauty",
        "finish_signature": "bold, moody, alternative aesthetic — not mainstream pretty",
        "texture_language": "intense pigment, grungy finishes, unexpected color combinations",
        "application_style": "deliberate edginess, smoky diffusion, no-rules application",
        "skin_tone_approach": "deep jewel tones and dark shades are a specialty — looks intentionally dramatic on all skin tones",
        "lighting_quality": "moody low key lighting, contrast shadows",
        "realism_anchor": "looks like Urban Decay campaign — dark, cool, intentionally edgy",
    },

    "benefit": {
        "persona": "fun retro San Francisco glam",
        "finish_signature": "cheek and brow specialist — fresh, flushed, arched perfection",
        "texture_language": "airy buildable powders, silky cheek products, defined but natural brows",
        "application_style": "fresh-faced placement, lifted arched brows, rosy flush",
        "skin_tone_approach": "fresh rosy tones on light skin, warm berry on medium, deep wine on dark skin",
        "lighting_quality": "bright natural daylight, fresh-faced",
        "realism_anchor": "looks like Benefit campaign — cute, girly, effortlessly pretty",
    },

    "rare-beauty": {
        "persona": "mental wellness meets dewy beauty",
        "finish_signature": "dewy lit-from-within glow, effortless and healthy-looking",
        "texture_language": "liquid-light, buildable sheer to medium, skin still breathes",
        "application_style": "tapped and blended, no harsh lines, natural movement",
        "skin_tone_approach": "Rare Beauty is for ALL skin tones — deep shades are warm and rich, light shades are bright and fresh, never washed out on any tone",
        "lighting_quality": "soft natural dewy light",
        "realism_anchor": "looks like Rare Beauty campaign — real skin, real glow, healthy",
    },

    "nyx": {
        "persona": "accessible professional makeup artist",
        "finish_signature": "professional quality at drugstore price — punchy color, reliable finish",
        "texture_language": "creamy pigmented formulas, smooth application, stays put",
        "application_style": "clean professional application, color-true results",
        "skin_tone_approach": "wide shade range covering all skin tones — colors read true on all complexions",
        "lighting_quality": "clean bright professional lighting",
        "realism_anchor": "looks like NYX professional campaign — clean, color-accurate, wearable",
    },

    "maybelline": {
        "persona": "everyday accessible glam",
        "finish_signature": "reliable everyday wear, classic looks, universally flattering",
        "texture_language": "smooth comfortable formulas, easy-blend",
        "application_style": "effortless everyday application, natural to medium coverage",
        "skin_tone_approach": "classic neutral tones, wide range — designed for everyday wearability",
        "lighting_quality": "everyday natural lighting",
        "realism_anchor": "looks like Maybelline ad — fresh, real, accessible beauty",
    },

    "loreal": {
        "persona": "science-backed beauty authority",
        "finish_signature": "clinically refined, long-wearing, performance-driven results",
        "texture_language": "smooth engineered formulas, precise pigment dispersion",
        "application_style": "even application, consistent coverage",
        "skin_tone_approach": "broad shade range with scientific precision",
        "lighting_quality": "clean clinical beauty photography",
        "realism_anchor": "looks like L'Oréal campaign — refined, confident, because you're worth it",
    },

    "elf": {
        "persona": "budget-savvy beauty enthusiast",
        "finish_signature": "surprisingly good results at minimal cost — punchy and wearable",
        "texture_language": "lightweight accessible formulas",
        "application_style": "clean simple application",
        "skin_tone_approach": "inclusive range, clean color payoff",
        "lighting_quality": "bright accessible lighting",
        "realism_anchor": "looks like e.l.f. campaign — fun, affordable, real",
    },

    "3ce": {
        "persona": "Korean minimalist cool-girl",
        "finish_signature": "K-beauty aesthetic — clean, modern, slightly muted tones with cool undertones",
        "texture_language": "lightweight silky textures, skin-like finish, trendy cool-toned palette",
        "application_style": "minimal precise application, clean and graphic",
        "skin_tone_approach": "designed for East Asian skin tones — cool pink and beige undertones, porcelain to warm yellow spectrum",
        "lighting_quality": "clean white Korean studio lighting",
        "realism_anchor": "looks like 3CE Stylenanda campaign — cool, minimal, K-beauty aesthetic",
    },

    "romand": {
        "persona": "K-beauty soft romantic aesthetic",
        "finish_signature": "soft blurred lips and cheeks, romantic Korean ulzzang look",
        "texture_language": "lightweight tinted formulas, velvet matte on lips, soft wash of color",
        "application_style": "gradient lip technique, blurred inner-lip to outer effect",
        "skin_tone_approach": "warm peach and rosy tones for Korean beauty aesthetic, porcelain to light tan spectrum",
        "lighting_quality": "soft pastel Korean photography lighting",
        "realism_anchor": "looks like ROMAND campaign — soft, cute, Korean romantic beauty",
    },

    "etude-house": {
        "persona": "playful K-beauty princess aesthetic",
        "finish_signature": "cute, youthful, sweet K-beauty — pinks and peaches dominate",
        "texture_language": "light playful textures, sweet color palette",
        "application_style": "doll-like soft application, youthful finish",
        "skin_tone_approach": "designed for Korean beauty standards — light rosy skin, cool pink undertones",
        "lighting_quality": "bright pastel pink Korean studio lighting",
        "realism_anchor": "looks like Etude House campaign — cute, girly, Korean pop aesthetic",
    },

    "srichand": {
        "persona": "Thai beauty icon",
        "finish_signature": "lightweight coverage for humid tropical climates, translucent-to-light coverage",
        "texture_language": "ultra-light, shine-control, comfortable in heat",
        "application_style": "light natural application, skin-forward",
        "skin_tone_approach": "designed for Southeast Asian skin — warm golden yellow undertones, medium to tan complexions, NEVER ashy on warm skin",
        "lighting_quality": "bright tropical natural lighting",
        "realism_anchor": "looks like Srichand Thai beauty campaign — light, natural, Southeast Asian aesthetic",
    },

    "mistine": {
        "persona": "Thai mass-market beauty leader",
        "finish_signature": "heat-resistant, long-wearing for tropical Southeast Asian climate",
        "texture_language": "reliable formulas, comfortable tropical wear",
        "application_style": "everyday natural application",
        "skin_tone_approach": "warm golden Southeast Asian complexions, medium coverage that flatters warm undertones",
        "lighting_quality": "bright natural Thai beauty photography",
        "realism_anchor": "looks like Mistine campaign — fresh, natural, Southeast Asian beauty",
    },
}


def get_brand_dna(brand_slug: str) -> dict:
    """Get brand DNA or return a sensible generic fallback."""
    return BRAND_DNA.get(brand_slug, {
        "persona": "professional makeup artist",
        "finish_signature": "natural, well-blended, professional finish",
        "texture_language": "smooth, even application",
        "application_style": "clean professional technique",
        "skin_tone_approach": "flattering on all skin tones",
        "lighting_quality": "natural beauty photography lighting",
        "realism_anchor": "realistic makeup photography result",
    })