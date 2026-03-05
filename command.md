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
openai>=2.24.0
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
# OpenAI
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=sqlite+aiosqlite:///./glamai.db

# Storage
UPLOAD_DIR=./uploads
RESULTS_DIR=./results
REFERENCES_DIR=./references
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

### NYX (full seed — all 13 categories)
```bash
python brands/nyx/seed_nyx.py
```

### Reference images — all brands
```bash
python brands/seed_references.py
```

### Reference images — specific brand
```bash
python brands/seed_references.py --brand nyx
```

### Reference images — specific product
```bash
python brands/seed_references.py --brand nyx --product nyx-matte-lipstick
```

---

## Reference Images Folder Structure

```
references/
  {brand-slug}/
    {product-slug}/
      {shade-slug}/
        swatch.jpg       ← product color swatch
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

## Adding a New Brand

```bash
# 1. Create brand folder
mkdir brands/{brand-slug}

# 2. Copy NYX seeder as template
cp brands/nyx/seed_nyx.py brands/{brand-slug}/seed_{brand}.py

# 3. Edit seed_{brand}.py — update brand info, products, shades

# 4. Run seeder
python brands/{brand-slug}/seed_{brand}.py

# 5. Add reference images
mkdir -p references/{brand-slug}/{product-slug}/{shade-slug}
# drop your images in there

# 6. Seed references
python brands/seed_references.py --brand {brand-slug}
```

---

## Project Folder Structure

```
glamai/
  main.py                      ← FastAPI app + all endpoints
  db/
    models.py                  ← SQLAlchemy models
  engine/
    generator.py               ← image generation (gpt-image-1)
    prompt_engine.py           ← prompt builder per category
  brands/
    seed_references.py         ← general reference image seeder
    nyx/
      seed_nyx.py              ← NYX seed data
    mac/
      seed_mac.py              ← (future)
  references/                  ← reference images (local storage)
    nyx/
      nyx-matte-lipstick/
        siren/
          model.jpg
          on_skin.jpg
  uploads/                     ← user uploaded photos
  results/                     ← generated results
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
POST /generate                            → generate makeup try-on
GET  /jobs/{job_id}                       → check job status
```

---

## Useful Dev Commands

```bash
# Check OpenAI SDK version
python -c "import openai; print(openai.__version__)"

# Check installed packages
pip list

# Upgrade OpenAI SDK
pip install --upgrade openai

# Check DB contents (SQLite)
sqlite3 glamai.db ".tables"
sqlite3 glamai.db "SELECT name, hex_color, prompt_supplement FROM shades LIMIT 10;"
sqlite3 glamai.db "SELECT COUNT(*) FROM reference_images;"

# Freeze requirements
pip freeze > requirements.txt
```