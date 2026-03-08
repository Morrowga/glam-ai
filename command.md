# GlamAI — Commands & Setup Reference

## Python & Virtual Environment

### Requirements
- Python 3.11+
- pip 23+

### Setup venv
```bash
# Create
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate
```

### Install packages
```bash
pip install -r requirements.txt
```

---

## Required Packages

```txt
# requirements.txt
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
aiosqlite
alembic
google-genai
pillow
opencv-python
numpy
python-dotenv
httpx
python-multipart
tenacity
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Gemini
GEMINI_API_KEY=...

# Database
DATABASE_URL=sqlite+aiosqlite:///./glamai.db

# Storage
UPLOAD_DIR=./uploads
RESULTS_DIR=./results
REFERENCES_DIR=./references

# Admin email alerts
ADMIN_EMAIL=admin@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_gmail_app_password
```

---

## Run Server

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Swagger UI: http://localhost:8000/docs

---

## Database

### Initialize (first time)
```bash
# DB is auto-created on first server start via init_db()
# Or run manually:
python -c "import asyncio; from db.models import init_db; asyncio.run(init_db())"
```

### Reset DB (wipe and recreate)
```bash
rm glamai.db
python -c "import asyncio; from db.models import init_db; asyncio.run(init_db())"
```

---

## Seeding

### First time — full seed
```bash
python seeds/seed_general.py     # seeds all categories + all brands
python seeds/seed_references.py  # seeds all reference images
```

### Reference images — specific brand
```bash
python seeds/seed_references.py --brand nyx
```

### Reference images — specific product
```bash
python seeds/seed_references.py --brand nyx --product nyx-matte-lipstick
```

---

## Adding a New Brand

```bash
# 1. Create brand folder
mkdir seeds/brands/{brand-slug}

# 2. Copy NYX seeder as template
cp seeds/brands/nyx/seed_nyx.py seeds/brands/{brand-slug}/seed_{brand}.py

# 3. Edit seed_{brand}.py — update brand info, products, shades
#    Do NOT add CATEGORIES — categories live in seed_general.py only

# 4. Register in seed_general.py:
#    from seeds.brands.{brand-slug}.seed_{brand} import seed as seed_{brand}
#    then call: await seed_{brand}() inside seed_all()

# 5. Run seeder
python seeds/seed_general.py

# 6. Add reference images
mkdir -p references/{brand-slug}/{product-slug}/{shade-slug}
# drop swatch.jpg files in there

# 7. Seed references
python seeds/seed_references.py --brand {brand-slug}
```

---

## Reference Images Folder Structure

```
references/
  {brand-slug}/
    {product-slug}/
      {shade-slug}/
        swatch.jpg       ← product color swatch (RGB JPEG, no transparency)
        on_skin.jpg      ← color swatch on skin/arm
        model.jpg        ← person wearing it
```

### Shade slug format
Shade name → lowercase, spaces to hyphens, remove apostrophes
- `Siren` → `siren`
- `Nude Pink` → `nude-pink`
- `Whipped Caviar` → `whipped-caviar`
- `Can't Stop` → `cant-stop`

### Skin tone aware references (optional)
Add skin tone to filename — seeder auto-detects:
- `model_fair.jpg` → skin_tone = fair
- `swatch_medium.jpg` → skin_tone = medium
- `model.jpg` → skin_tone = any

---

## Project Folder Structure

```
glamai/
  main.py                          ← FastAPI app + all endpoints
  db/
    models.py                      ← SQLAlchemy models
  engine/
    generator.py                   ← image generation (gemini-3.1-flash-image-preview)
    prompt_engine.py               ← prompt builder per category + zone-aware layering
  seeds/
    __init__.py
    seed_general.py                ← master seeder: categories + all brands
    seed_references.py             ← reference image seeder
    brands/
      nyx/
        seed_nyx.py                ← NYX products + shades
      mac/
        seed_mac.py                ← (future)
  references/                      ← reference swatch images (local)
    nyx/
      nyx-matte-lipstick/
        siren/
          swatch.jpg
  uploads/                         ← user uploaded photos
  results/                         ← generated results
  .env
  requirements.txt
```

---

## API Endpoints (Quick Reference)

```
GET  /brands                              → list all brands
GET  /brands/{brand_slug}/categories      → categories for brand
GET  /brands/{brand_slug}/{cat}/products  → products in category
GET  /products/{product_id}/shades        → shades for product

POST /upload                              → upload user photo
POST /generate                            → single product try-on
POST /generate-combo                      → multi-product combo try-on
GET  /jobs/{job_id}                       → check job status
```

---

## Useful Dev Commands

```bash
# Check google-genai SDK version
python -c "import google.genai; print(google.genai.__version__)"

# Check installed packages
pip list

# Upgrade google-genai SDK
pip install --upgrade google-genai

# Check DB contents (SQLite)
sqlite3 glamai.db ".tables"
sqlite3 glamai.db "SELECT name, hex_color, prompt_supplement FROM shades LIMIT 10;"
sqlite3 glamai.db "SELECT COUNT(*) FROM reference_images;"
sqlite3 glamai.db "SELECT name, slug FROM categories;"

# Freeze requirements
pip freeze > requirements.txt
```