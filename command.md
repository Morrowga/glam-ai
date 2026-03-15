# GlamAI — Commands & Setup Reference

---

## Python & Virtual Environment

### Requirements
- Python 3.11+
- pip 23+

### Setup venv
```bash
# Create (always from project root)
cd /your/project/root
python3 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate
```

> ⚠️ Always run uvicorn and python commands from the project root directory.
> ⚠️ If venv breaks (bad interpreter error), delete and rebuild:
> ```bash
> rm -rf venv
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

### Install packages
```bash
venv/bin/pip install -r requirements.txt
```

---

## Required Packages (requirements.txt)

```txt
fastapi==0.111.0
uvicorn==0.29.0
sqlalchemy==2.0.30
aiosqlite==0.20.0
openai==1.30.0
python-multipart==0.0.9
pillow==10.3.0
python-dotenv==1.0.1
pydantic==2.7.1
requests==2.31.0
rich==13.7.1
greenlet

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
email-validator==2.1.1

# Gemini (generation + skin analysis)
google-generativeai==0.8.6
google-genai>=0.8.0
googleapis-common-protos==1.73.0
grpcio==1.78.0
grpcio-status==1.62.3
proto-plus==1.27.1
protobuf==4.25.3

# Face validation
mediapipe==0.10.14
opencv-python==4.13.0.92

# Payments
stripe==14.4.1
```

> ⚠️ Do NOT install `opencv-contrib-python` or `opencv-python-headless` alongside `opencv-python` — causes conflicts.
> ⚠️ `protobuf` must stay at `4.25.3` — mediapipe and google-generativeai conflict at 5.x.
> ⚠️ Do NOT pin `bcrypt` — let passlib resolve the version automatically.

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

# Auth
JWT_SECRET=your-random-secret-here
ACCESS_TOKEN_EXPIRE_MINUTES=10080
APP_BASE_URL=http://localhost:3000        # frontend URL (for email verification link)

# Public API protection
PUBLIC_API_TOKEN=your-random-public-token-here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# URLs
BASE_URL=http://localhost:8087            # backend URL (for static file links)
FRONTEND_URL=http://localhost:3000        # frontend URL (for share links)

# Admin + Auth email (shared SMTP config)
ADMIN_EMAIL=admin@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_gmail_app_password        # must be Gmail App Password, not regular password
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8087
NEXT_PUBLIC_API_TOKEN=your-random-public-token-here   # must match backend PUBLIC_API_TOKEN
```

> To generate a Gmail App Password:
> 1. myaccount.google.com → Security → 2-Step Verification (enable first)
> 2. Search "App passwords" → Create for Mail
> 3. Paste the 16-character password into SMTP_PASS

---

## Run Server

```bash
# Development (from project root, with auto-reload)
venv/bin/uvicorn main:app --reload --port 8087

# Production
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8087 --workers 4
```

Swagger UI: http://localhost:8087/docs

> ⚠️ The worker is embedded in `main.py` via `lifespan` — it starts automatically with the server.
> You do NOT need to run a separate worker process.

---

## Database

### Initialize (first time)
```bash
# Auto-created on first server start via lifespan → init_db()
# Or run manually:
venv/bin/python -c "import asyncio; from db.models import init_db; asyncio.run(init_db())"
```

### Reset DB (wipe and recreate)
```bash
rm glamai.db
venv/bin/python -c "import asyncio; from db.models import init_db; asyncio.run(init_db())"
```

### Useful DB queries
```bash
sqlite3 glamai.db ".tables"
sqlite3 glamai.db "SELECT name, hex_color FROM shades LIMIT 10;"
sqlite3 glamai.db "SELECT COUNT(*) FROM reference_images;"
sqlite3 glamai.db "SELECT name, slug FROM categories;"
sqlite3 glamai.db "SELECT id, status, created_at FROM generation_jobs ORDER BY created_at DESC LIMIT 10;"

# Auth
sqlite3 glamai.db "SELECT id, email, is_verified FROM users;"
sqlite3 glamai.db "SELECT token FROM email_verification_tokens ORDER BY created_at DESC LIMIT 1;"

# Credits
sqlite3 glamai.db "SELECT u.email, s.plan_type, s.credits_remaining, s.payg_credits FROM users u JOIN user_subscriptions s ON u.id = s.user_id;"
sqlite3 glamai.db "SELECT * FROM purchase_records ORDER BY created_at DESC LIMIT 10;"
sqlite3 glamai.db "SELECT * FROM plans;"

# Delete a user (also clears tokens and subscription)
sqlite3 glamai.db "DELETE FROM email_verification_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'test@example.com'); DELETE FROM user_subscriptions WHERE user_id = (SELECT id FROM users WHERE email = 'test@example.com'); DELETE FROM users WHERE email = 'test@example.com';"

# Wipe all users
sqlite3 glamai.db "DELETE FROM email_verification_tokens; DELETE FROM user_subscriptions; DELETE FROM users;"

# Manually verify a user (skip email for dev)
sqlite3 glamai.db "UPDATE users SET is_verified = 1 WHERE email = 'test@example.com';"
```

---

## Seeding

### First time — full seed
```bash
venv/bin/python seeds/seed_general.py     # seeds categories + all brands + plans
venv/bin/python seeds/seed_references.py  # seeds all reference images
```

### Plans only
```bash
venv/bin/python seeds/seed_plans.py
```

### NYX brand only
```bash
venv/bin/python seeds/brands/nyx/seed_nyx.py
```

### Reference images — specific brand
```bash
venv/bin/python seeds/seed_references.py --brand nyx
```

### Reference images — specific product
```bash
venv/bin/python seeds/seed_references.py --brand nyx --product nyx-matte-lipstick
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
venv/bin/python seeds/seed_general.py

# 6. Add reference images
mkdir -p references/{brand-slug}/{product-slug}/{shade-slug}
# drop swatch.jpg files in there

# 7. Seed references
venv/bin/python seeds/seed_references.py --brand {brand-slug}
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
Shade name → lowercase, spaces to hyphens, remove apostrophes:
- `Siren` → `siren`
- `Nude Pink` → `nude-pink`
- `Can't Stop` → `cant-stop`

### Skin tone aware references (optional)
Add skin tone suffix — seeder auto-detects:
- `model_fair.jpg` → skin_tone = fair
- `swatch_medium.jpg` → skin_tone = medium
- `model.jpg` → skin_tone = any

---

## Project Folder Structure

```
glamai/
  main.py                          ← FastAPI app + all endpoints + lifespan worker start
  worker.py                        ← job queue worker (called from lifespan, not standalone)
  shared_state.py                  ← cancelled_jobs set shared between main + worker
  Dockerfile
  .dockerignore
  db/
    models.py                      ← all SQLAlchemy models
  engine/
    generator.py                   ← image generation via Gemini image model
    prompt_engine.py               ← prompt builders per category, zone-aware layering, multi-zone
    face_validator.py              ← MediaPipe face validation (local, ~0.1s)
    skin_analyzer.py               ← Gemini vision skin tone + color season analysis (gemini-2.5-flash-lite)
    auth_utils.py                  ← JWT create/decode, password hash, token generator
    auth_email.py                  ← email sender: verification + password reset (SMTP)
    auth_deps.py                   ← FastAPI deps: get_current_user, verify_public_token
    credits.py                     ← credit management: create, grant, deduct, check balance
  routers/
    __init__.py
    auth.py                        ← register, verify-email, login, me, resend, forgot/reset password
    payments.py                    ← plans, my-plan, subscribe, topup, history, Stripe routes
  seeds/
    seed_general.py                ← master seeder: categories + all brands + plans
    seed_plans.py                  ← plan definitions (free/basic/glam/payg)
    seed_references.py             ← reference image seeder
    brands/
      nyx/
        seed_nyx.py            ← NYX: Matte Lipstick, Butter Gloss (40+ shades), Slim Lip Pencil, Ultimate Shadow Palette, Epic Ink Liner, On The Rise Mascara, Micro Brow Pencil, Sweet Cheeks Blush, Matte Bronzer, Born To Glow Highlighter
  references/                      ← reference swatch images (local)
  uploads/                         ← user uploaded photos
  results/                         ← generated result images
  media/
    brands/                        ← brand logo images ({slug}.jpg)
    products/                      ← product images ({slug}.jpg)
  .env
  requirements.txt
```

---

## Features Overview

### 💄 Try On (`/tryon`)
User uploads a face photo → selects brand → product → shade → AI generates a photo with the makeup applied.
- Supports multi-product combos (lips + eyes + cheeks in one generation)
- Zone-aware prompt building (cheeks → eyes → lips application order)
- History sidebar — reload past generations and re-generate
- Share feature — tokenized public link per result

### 🎨 Color Season Analysis (`/skin-analysis`)
User uploads a face photo → AI analyzes skin tone, undertone, and color season.
- Returns: Spring / Summer / Autumn / Winter season + description
- Returns: skin tone (fair→deep), undertone (warm/cool/neutral), hex color
- Returns: 6 personalized makeup color recommendations (2×Lip, 2×Eye, 2×Face)
- Costs 1 credit. Uses `gemini-2.5-flash-lite` vision model.
- Desktop: 2-column layout, typewriter animation on all result text, skeleton during loading

### 👜 Look Preparation (`/look-prep`) — 🔨 Coming
User adds her own makeup products to a "bag" (free text) → selects an occasion → AI checks if her bag is sufficient → generates a look using only her products.
- Basic + Glam plan only

---

## Auth & Credit Flow

```
Register    → verification email sent → 1 free credit granted on verify
Login       → JWT (7 days) stored in Redux + cookie
Buy Basic   → 50 credits, rolling 30-day reset
Buy Glam    → 120 credits, rolling 30-day reset
Buy PAYG    → 5–200 credits, stacks on existing, expires 60 days
Any feature → 1 credit deducted on success (subscription first, then PAYG)
Out of credits → 402 error
```

---

## Useful Dev Commands

```bash
# Verify key packages both work together
venv/bin/python -c "import mediapipe; import google.generativeai; print('both ok')"

# Check installed packages
venv/bin/pip list

# Freeze requirements
venv/bin/pip freeze > requirements.txt

# Get latest verification token (for testing without email)
sqlite3 glamai.db "SELECT token FROM email_verification_tokens ORDER BY created_at DESC LIMIT 1;"
```