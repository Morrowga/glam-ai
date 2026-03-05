"""
NYX Professional Makeup — seed data
Location: brands/nyx/seed_nyx.py
Run: python brands/nyx/seed_nyx.py
"""

import asyncio, sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select
from db.models import init_db, AsyncSessionLocal, Brand, Category, Product, Shade

CATEGORIES = [
    {"name": "Lipstick",    "slug": "lipstick",    "application_zone": "lips"},
    {"name": "Lip Gloss",   "slug": "lip-gloss",   "application_zone": "lips"},
    {"name": "Lip Liner",   "slug": "lip-liner",   "application_zone": "lips"},
    {"name": "Eyeshadow",   "slug": "eyeshadow",   "application_zone": "eyes"},
    {"name": "Eyeliner",    "slug": "eyeliner",    "application_zone": "eyes"},
    {"name": "Mascara",     "slug": "mascara",     "application_zone": "eyes"},
    {"name": "Eyebrow",     "slug": "eyebrow",     "application_zone": "eyes"},
    {"name": "Foundation",  "slug": "foundation",  "application_zone": "face"},
    {"name": "Concealer",   "slug": "concealer",   "application_zone": "face"},
    {"name": "Blush",       "slug": "blush",       "application_zone": "cheeks"},
    {"name": "Bronzer",     "slug": "bronzer",     "application_zone": "cheeks"},
    {"name": "Highlighter", "slug": "highlighter", "application_zone": "cheeks"},
    {"name": "Contour",     "slug": "contour",     "application_zone": "cheeks"},
]

NYX_PRODUCTS = [

    # ── LIPSTICK ──────────────────────────────────────────────────
    {
        "category": "lipstick",
        "name": "Matte Lipstick",
        "slug": "nyx-matte-lipstick",
        "shades": [
            {"name": "Siren",         "hex": "#8B1A1A", "finish": "matte", "coverage": "full", "description": "very dark deep burgundy red, almost vampy, full opaque matte"},
            {"name": "Alabama",       "hex": "#C45A65", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Whipped Caviar","hex": "#2C1A1A", "finish": "matte", "coverage": "full", "description": "extremely dark near-black brown, very deep and moody"},
            {"name": "Nude Pink",     "hex": "#D4977A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Indie Flick",   "hex": "#A0522D", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Strawberry Milk","hex": "#F4A7A7","finish": "matte", "coverage": "full", "description": "very sheer soft pink, barely-there tint, milky finish"},
            {"name": "Chic Red",      "hex": "#C0392B", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Cocoa",         "hex": "#5C3317", "finish": "matte", "coverage": "full", "description": "deep warm chocolate brown, rich and earthy"},
        ]
    },

    # ── LIP GLOSS ─────────────────────────────────────────────────
     {
        "category": "lip-gloss",
        "name": "Butter Gloss",
        "slug": "nyx-lip-gloss",
        "shades": [

            # ── NUDES / NEUTRALS ──────────────────────────────────────
            {
                "name": "Creme Brulee",
                "hex": "#E8C49A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "warm beige nude, natural lip enhancer with golden undertone, sheer glossy wash",
            },
            {
                "name": "Praline",
                "hex": "#C9956A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "medium warm tan nude, caramel-toned gloss, flattering on medium skin tones",
            },
            {
                "name": "Sugar Cookie",
                "hex": "#F5DEB3",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "very sheer pale cream gloss, barely visible tint, almost clear with a hint of warmth",
            },
            {
                "name": "Maple Blondie",
                "hex": "#D4956A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "soft honey-caramel nude, warm golden undertone, sheer and natural-looking",
            },
            {
                "name": "Tiramisu",
                "hex": "#7B5B3A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "nude brown with pink undertones, buildable from sheer wash to medium coverage, warm mocha tone",
            },
            {
                "name": "Angel Food Cake",
                "hex": "#E8AABA",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "true mauve pink, soft dusty rose gloss, feminine and wearable everyday shade",
            },
            {
                "name": "Madeleine",
                "hex": "#DCAB8A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "light peachy nude, warm biscuit tone, barely-there tint for a natural look",
            },
            {
                "name": "Fortune Cookie",
                "hex": "#C8906A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "soft warm nude peach, golden-beige tone, lightweight sheer gloss",
            },
            {
                "name": "Vanilla Creme Pie",
                "hex": "#F0D5B0",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "pale vanilla cream, very light sheer tint, almost translucent warm nude",
            },

            # ── PINKS ─────────────────────────────────────────────────
            {
                "name": "Strawberry Parfait",
                "hex": "#FF6B8A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "bright strawberry pink, fresh and playful, sheer glossy pop of cool pink",
            },
            {
                "name": "Strawberry Cheesecake",
                "hex": "#E85080",
                "finish": "glossy",
                "coverage": "medium",
                "description": "vivid bubblegum pink, medium pigmentation, bright and eye-catching glossy pink",
            },
            {
                "name": "Marshmallow",
                "hex": "#F5C5D0",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "very soft baby pink, airy and barely-there tint, sheer glassy finish",
            },
            {
                "name": "Ginger Snap",
                "hex": "#D4785A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "warm coral-pink, spiced peachy tone, sheer and flattering on warm complexions",
            },
            {
                "name": "Sorbet",
                "hex": "#FF8FAB",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "cool-toned candy pink, bright and fresh, sheer wash of sherbet colour",
            },
            {
                "name": "Summer Fruit",
                "hex": "#D45870",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep berry-pink, medium pigment, rich juicy tone between raspberry and rose",
            },

            # ── PEACHES / CORALS ──────────────────────────────────────
            {
                "name": "Peach Cobbler",
                "hex": "#FFAB76",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "warm peachy orange, soft coral tint, sheer and sun-kissed looking",
            },
            {
                "name": "Orangesicle",
                "hex": "#FF7043",
                "finish": "glossy",
                "coverage": "medium",
                "description": "vivid orange-coral, bold citrusy tone, medium coverage bright orange gloss",
            },
            {
                "name": "Bit of Honey",
                "hex": "#E8A060",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "golden honey peach, warm amber tint, sheer and luminous on lips",
            },

            # ── REDS ──────────────────────────────────────────────────
            {
                "name": "Red Velvet",
                "hex": "#8B0000",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep red with high shine, rich glossy finish, luxurious vampy red with gloss sheen",
            },
            {
                "name": "Apple Crisp",
                "hex": "#C0392B",
                "finish": "glossy",
                "coverage": "medium",
                "description": "true red with blue undertone, classic red gloss, glossy and bold",
            },
            {
                "name": "Cranberry Pie",
                "hex": "#9B1B30",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep cranberry red, rich berry-red tone, medium coverage with high shine",
            },
            {
                "name": "Devil's Food Cake",
                "hex": "#6B1A1A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "very dark chocolate red, deep moody red-brown gloss, dramatic and intense",
            },

            # ── BERRIES / PLUMS ───────────────────────────────────────
            {
                "name": "Blueberry Tart",
                "hex": "#4A2C8A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep blue-toned berry, vivid purple-plum gloss, bold and statement-making",
            },
            {
                "name": "Raspberry Tart",
                "hex": "#9B2D6A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "vivid true purple, sheer-to-medium pigment, bright berry-purple gloss",
            },

            # ── BROWNS / TOFFEES ──────────────────────────────────────
            {
                "name": "Rocky Road",
                "hex": "#5C3020",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep chocolate brown gloss, rich and creamy-looking, medium pigmented warm brown",
            },
            {
                "name": "Sugar High",
                "hex": "#C8805A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "warm peachy-brown nude, perfect for deeper skin tones, sheer glossy coverage",
            },
            {
                "name": "Butterscotch",
                "hex": "#D4906A",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "golden butterscotch nude, warm honey-brown tone, designed to flatter medium to tan skin",
            },
            {
                "name": "Spiked Toffee",
                "hex": "#A0603A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "rich toffee brown, medium warm brown gloss, flattering on tan to deep skin tones",
            },
            {
                "name": "Cinnamon Roll",
                "hex": "#8B4A28",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep cinnamon brown, spiced warm brown gloss, rich pigment for deeper skin tones",
            },
            {
                "name": "Fudge Me",
                "hex": "#6B3820",
                "finish": "glossy",
                "coverage": "medium",
                "description": "dark fudge brown, deep warm brown gloss, high shine on rich and deep complexions",
            },
            {
                "name": "Caramelt",
                "hex": "#B87040",
                "finish": "glossy",
                "coverage": "medium",
                "description": "caramel brown with warm orange undertone, glossy and pigmented for medium-deep skin",
            },
            {
                "name": "Brownie Drip",
                "hex": "#7B4030",
                "finish": "glossy",
                "coverage": "medium",
                "description": "deep brownie brown-red, rich muted brick-brown gloss, flattering on deep skin tones",
            },
            {
                "name": "Lava Cake",
                "hex": "#4A2010",
                "finish": "glossy",
                "coverage": "medium",
                "description": "very deep dark chocolate brown, almost black-brown gloss, dramatic on all skin tones",
            },

            # ── CLEAR / SPECIAL ───────────────────────────────────────
            {
                "name": "Sugar Glass",
                "hex": "#F8F8F8",
                "finish": "glossy",
                "coverage": "sheer",
                "description": "crystal clear gloss with no tint, pure high-shine transparent lip gloss, glass-like finish",
            },
            {
                "name": "Licorice",
                "hex": "#1A0A1A",
                "finish": "glossy",
                "coverage": "medium",
                "description": "near-black deep plum gloss, very dark with high shine, bold gothic-inspired shade",
            },

            # ── BLINGY / SHIMMER SHADES ───────────────────────────────
            {
                "name": "Glazen Eye",
                "hex": "#FFD9A0",
                "finish": "metallic",
                "coverage": "sheer",
                "description": "golden champagne shimmer gloss, blinding metallic particles on a sheer base, bling finish",
            },
            {
                "name": "Diamonds & Rubies",
                "hex": "#CC4466",
                "finish": "metallic",
                "coverage": "medium",
                "description": "hot pink-red metallic gloss, intense sparkle with a jewel-toned pink-red base",
            },
            {
                "name": "Sprinkle Me",
                "hex": "#F0A0C0",
                "finish": "metallic",
                "coverage": "sheer",
                "description": "sheer pink with rainbow iridescent glitter particles, multi-dimensional sparkle effect",
            },
            {
                "name": "Peach Bling",
                "hex": "#F4B090",
                "finish": "metallic",
                "coverage": "sheer",
                "description": "peachy-nude base with gold shimmer, warm glitter gloss, flattering metallic peach",
            },
            {
                "name": "Cherry Bomb",
                "hex": "#CC2244",
                "finish": "metallic",
                "coverage": "medium",
                "description": "vivid cherry red with metallic shimmer particles, bold bling red gloss",
            },
            {
                "name": "Bronze Bling",
                "hex": "#B87840",
                "finish": "metallic",
                "coverage": "medium",
                "description": "warm bronze base with intense metallic shimmer, rich glitter-gloss in copper-bronze tone",
            },
            {
                "name": "Berry Bling",
                "hex": "#882060",
                "finish": "metallic",
                "coverage": "medium",
                "description": "deep berry base with silver and purple shimmer particles, dark jewel-toned metallic gloss",
            },
            {
                "name": "Nude Bling",
                "hex": "#C89070",
                "finish": "metallic",
                "coverage": "sheer",
                "description": "neutral nude base with gold shimmer, wearable everyday metallic gloss, warm blingy nude",
            },
        ],
    },

    # ── LIP LINER ─────────────────────────────────────────────────
    {
        "category": "lip-liner",
        "name": "Slim Lip Pencil",
        "slug": "nyx-lip-liner",
        "shades": [
            {"name": "Natural",  "hex": "#C68642", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Nude Pink","hex": "#D4977A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Berry",    "hex": "#7B2D8B", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Red",      "hex": "#CC0000", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Plum",     "hex": "#580F41", "finish": "matte", "coverage": "full", "description": "very dark purple-black plum, intense and dramatic"},
            {"name": "Espresso", "hex": "#3B1C0A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Mauve",    "hex": "#B07D8A", "finish": "matte", "coverage": "full", "description": ""},
        ]
    },

    # ── EYESHADOW ─────────────────────────────────────────────────
    {
        "category": "eyeshadow",
        "name": "Ultimate Shadow Palette",
        "slug": "nyx-ultimate-shadow-palette",
        "shades": [
            {"name": "Brunch Me",    "hex": "#C19A6B", "finish": "matte",    "coverage": "full", "description": ""},
            {"name": "Taupe",        "hex": "#8B7765", "finish": "matte",    "coverage": "full", "description": ""},
            {"name": "Chocolate",    "hex": "#4A2C2A", "finish": "matte",    "coverage": "full", "description": ""},
            {"name": "Rose Gold",    "hex": "#B76E79", "finish": "shimmer",  "coverage": "full", "description": "warm pink with gold shimmer particles, reflects light"},
            {"name": "Champagne",    "hex": "#F7E7CE", "finish": "shimmer",  "coverage": "full", "description": "very pale champagne shimmer, subtle and glowy"},
            {"name": "Bronze",       "hex": "#CD7F32", "finish": "metallic", "coverage": "full", "description": "rich metallic bronze, highly reflective foil finish"},
            {"name": "Deep Plum",    "hex": "#4B0082", "finish": "matte",    "coverage": "full", "description": "very dark purple, intense pigment"},
            {"name": "Smoky Black",  "hex": "#1C1C1C", "finish": "matte",    "coverage": "full", "description": "pure matte black, highly pigmented for smoky eye"},
            {"name": "Forest Green", "hex": "#228B22", "finish": "shimmer",  "coverage": "full", "description": "deep green with shimmer, jewel toned"},
            {"name": "Navy",         "hex": "#000080", "finish": "shimmer",  "coverage": "full", "description": "deep navy blue with shimmer, bold and dramatic"},
        ]
    },

    # ── EYELINER ──────────────────────────────────────────────────
    {
        "category": "eyeliner",
        "name": "Epic Ink Liner",
        "slug": "nyx-epic-ink-liner",
        "shades": [
            {"name": "Black", "hex": "#000000", "finish": "matte", "coverage": "full", "description": "jet black liquid liner, precise thin line"},
            {"name": "Brown", "hex": "#3B1C0A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "White", "hex": "#F5F5F5", "finish": "matte", "coverage": "full", "description": "bright white liner, stark and bold"},
            {"name": "Blue",  "hex": "#003399", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Green", "hex": "#006400", "finish": "matte", "coverage": "full", "description": ""},
        ]
    },

    # ── MASCARA ───────────────────────────────────────────────────
    {
        "category": "mascara",
        "name": "Worth The Hype Mascara",
        "slug": "nyx-worth-the-hype-mascara",
        "shades": [
            {"name": "Black",         "hex": "#000000", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Brownish Black","hex": "#1C0A00",  "finish": "matte", "coverage": "full", "description": ""},
        ]
    },

    # ── EYEBROW ───────────────────────────────────────────────────
    {
        "category": "eyebrow",
        "name": "Micro Brow Pencil",
        "slug": "nyx-micro-brow-pencil",
        "shades": [
            {"name": "Blonde",       "hex": "#C8A882", "finish": "matte", "coverage": "full", "description": "very light blonde, almost invisible on fair brows"},
            {"name": "Taupe",        "hex": "#8B7765", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Soft Brown",   "hex": "#7B5B3A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Medium Brown", "hex": "#5C3D1E", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Espresso",     "hex": "#2C1A0A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Black",        "hex": "#0A0A0A",  "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Brunette",     "hex": "#3D2314", "finish": "matte", "coverage": "full", "description": ""},
        ]
    },

    # ── FOUNDATION ────────────────────────────────────────────────
    {
        "category": "foundation",
        "name": "Can't Stop Won't Stop Foundation",
        "slug": "nyx-csws-foundation",
        "shades": [
            {"name": "Pale",         "hex": "#F5E6D3", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Fair",         "hex": "#F0D5B8", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Light",        "hex": "#E8C9A0", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Light Medium", "hex": "#DFB98A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Medium",       "hex": "#C99A6B", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Medium Olive", "hex": "#B8895A", "finish": "matte", "coverage": "full", "description": "warm olive undertone, not pink or neutral"},
            {"name": "Warm Honey",   "hex": "#A0714F", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Caramel",      "hex": "#8B5E3C", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Mahogany",     "hex": "#6B3A2A", "finish": "matte", "coverage": "full", "description": ""},
            {"name": "Deep Ebony",   "hex": "#3C1F0F", "finish": "matte", "coverage": "full", "description": "very deep dark brown, rich ebony tone"},
        ]
    },

    # ── BLUSH ─────────────────────────────────────────────────────
    {
        "category": "blush",
        "name": "Sweet Cheeks Blush",
        "slug": "nyx-sweet-cheeks-blush",
        "shades": [
            {"name": "Citrine Rose",  "hex": "#E8919A", "finish": "matte",   "coverage": "medium", "description": ""},
            {"name": "Summer Breeze", "hex": "#F4A460", "finish": "matte",   "coverage": "medium", "description": ""},
            {"name": "Boho Chic",     "hex": "#C17A8A", "finish": "shimmer", "coverage": "medium", "description": "dusty mauve pink with subtle shimmer"},
            {"name": "Peach Perfect", "hex": "#FFAD8A", "finish": "matte",   "coverage": "medium", "description": ""},
            {"name": "Pink Linen",    "hex": "#FFB6C1", "finish": "matte",   "coverage": "light",  "description": "very sheer baby pink, light wash of color"},
            {"name": "Berry Twist",   "hex": "#8B2252", "finish": "matte",   "coverage": "medium", "description": "deep berry, bold and pigmented for blush"},
            {"name": "Mauve",         "hex": "#B07D8A", "finish": "shimmer", "coverage": "medium", "description": ""},
        ]
    },

    # ── BRONZER ───────────────────────────────────────────────────
    {
        "category": "bronzer",
        "name": "Matte Bronzer",
        "slug": "nyx-matte-bronzer",
        "shades": [
            {"name": "Light", "hex": "#C8956C", "finish": "matte", "coverage": "medium", "description": ""},
            {"name": "Medium","hex": "#A0714F", "finish": "matte", "coverage": "medium", "description": ""},
            {"name": "Dark",  "hex": "#7B4F2E", "finish": "matte", "coverage": "medium", "description": ""},
            {"name": "Deep",  "hex": "#5C3317", "finish": "matte", "coverage": "medium", "description": "very deep bronzer for deep skin tones"},
        ]
    },

    # ── HIGHLIGHTER ───────────────────────────────────────────────
    {
        "category": "highlighter",
        "name": "Born To Glow Highlighter",
        "slug": "nyx-born-to-glow-highlighter",
        "shades": [
            {"name": "Synthetica",   "hex": "#FFD700", "finish": "metallic", "coverage": "light", "description": "intense gold metallic, very blinding highlight"},
            {"name": "Narcissistic", "hex": "#FFC0CB", "finish": "shimmer",  "coverage": "light", "description": "soft pink shimmer highlight, glowy and feminine"},
            {"name": "Immortal",     "hex": "#F5F5DC", "finish": "shimmer",  "coverage": "light", "description": ""},
            {"name": "Crystal",      "hex": "#E8E8E8", "finish": "shimmer",  "coverage": "light", "description": "icy silver shimmer, cool toned glow"},
            {"name": "Copper",       "hex": "#B87333", "finish": "metallic", "coverage": "light", "description": "warm copper metallic, rich and glowy"},
            {"name": "Magic",        "hex": "#C8A2C8", "finish": "shimmer",  "coverage": "light", "description": "soft lavender shimmer, ethereal glow"},
        ]
    },

    # ── CONTOUR ───────────────────────────────────────────────────
    {
        "category": "contour",
        "name": "Ombre Blush & Contour",
        "slug": "nyx-ombre-blush-contour",
        "shades": [
            {"name": "Light",  "hex": "#C4956A", "finish": "matte", "coverage": "medium", "description": ""},
            {"name": "Medium", "hex": "#9B6E4A", "finish": "matte", "coverage": "medium", "description": ""},
            {"name": "Dark",   "hex": "#6B4226", "finish": "matte", "coverage": "medium", "description": ""},
        ]
    },
]


async def seed():
    await init_db()

    async with AsyncSessionLocal() as db:

        # Upsert NYX brand
        result = await db.execute(select(Brand).where(Brand.slug == "nyx"))
        nyx = result.scalar_one_or_none()
        if not nyx:
            nyx = Brand(name="NYX Professional Makeup", slug="nyx",
                        country="US", tier="drugstore", is_active=True)
            db.add(nyx)
            await db.commit()
            print(f"Created brand: {nyx.name}")
        else:
            print(f"Found brand: {nyx.name}")

        # Upsert categories
        cat_map = {}
        for c in CATEGORIES:
            result = await db.execute(select(Category).where(Category.slug == c["slug"]))
            cat = result.scalar_one_or_none()
            if not cat:
                cat = Category(name=c["name"], slug=c["slug"],
                               application_zone=c["application_zone"])
                db.add(cat)
                print(f"  + Category: {cat.name}")
            cat_map[c["slug"]] = cat
        await db.commit()

        # Seed products + shades
        total_products = 0
        total_shades   = 0

        for p_data in NYX_PRODUCTS:
            cat = cat_map[p_data["category"]]

            result = await db.execute(select(Product).where(Product.slug == p_data["slug"]))
            product = result.scalar_one_or_none()
            if not product:
                product = Product(name=p_data["name"], slug=p_data["slug"],
                                  brand_id=nyx.id, category_id=cat.id, is_active=True)
                db.add(product)
                await db.commit()
                print(f"  + Product: {product.name} [{cat.slug}]")
                total_products += 1

            for s_data in p_data["shades"]:
                result = await db.execute(
                    select(Shade).where(Shade.product_id == product.id,
                                       Shade.name == s_data["name"])
                )
                shade = result.scalar_one_or_none()
                if not shade:
                    shade = Shade(
                        name              = s_data["name"],
                        hex_color         = s_data["hex"],
                        finish_type       = s_data["finish"],
                        coverage          = s_data["coverage"],
                        prompt_supplement = s_data.get("description", ""),
                        product_id        = product.id,
                        is_active         = True,
                    )
                    db.add(shade)
                    total_shades += 1
                else:
                    # Update description if changed
                    new_desc = s_data.get("description", "")
                    if shade.prompt_supplement != new_desc:
                        shade.prompt_supplement = new_desc

            await db.commit()

        print(f"\nNYX seed complete!")
        print(f"  Products: {total_products}")
        print(f"  Shades:   {total_shades}")


if __name__ == "__main__":
    asyncio.run(seed())