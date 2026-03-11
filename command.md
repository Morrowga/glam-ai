# GlamAI — Commands & Setup Reference

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
# Use full path to avoid wrong Python being used
venv/bin/pip install -r requirements.txt
```

---

## Required Packages

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
bcrypt==4.0.1
email-validator==2.1.1

# Gemini
google-generativeai==0.8.6
googleapis-common-protos==1.73.0
grpcio==1.78.0
grpcio-status==1.62.3
proto-plus==1.27.1
protobuf==4.25.3

# Face validation
mediapipe==0.10.14
opencv-python==4.13.0.92
```

> ⚠️ Do NOT install opencv-contrib-python or opencv-python-headless alongside opencv-python — causes conflicts.
> ⚠️ protobuf must stay at 4.25.3 — mediapipe and google-generativeai conflict at 5.x
> ⚠️ bcrypt must be 4.0.1 — newer versions conflict with passlib

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

# Admin + Auth email (shared SMTP config)
ADMIN_EMAIL=admin@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_gmail_app_password        # must be Gmail App Password, not regular password
```

> To generate a Gmail App Password:
> 1. myaccount.google.com → Security → 2-Step Verification (enable first)
> 2. Search "App passwords" → Create for Mail
> 3. Paste the 16-character password into SMTP_PASS

---

## Run Server

```bash
# Development (from project root)
venv/bin/uvicorn main:app --reload --port 8087

# Production (with worker)
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8087 --workers 4
```

Swagger UI: http://localhost:8087/docs

## Run Worker (required for generation)

```bash
# In a separate terminal
venv/bin/python worker.py
```

> Worker polls DB every 3 seconds for pending jobs and calls Gemini.
> Both server and worker must be running for generation to work.

---

## Database

### Initialize (first time)
```bash
# DB is auto-created on first server start via init_db()
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

# Delete a user (also clears verification tokens and subscription)
sqlite3 glamai.db "DELETE FROM email_verification_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'email@example.com'); DELETE FROM user_subscriptions WHERE user_id = (SELECT id FROM users WHERE email = 'email@example.com'); DELETE FROM users WHERE email = 'email@example.com';"

# Wipe all users
sqlite3 glamai.db "DELETE FROM email_verification_tokens; DELETE FROM user_subscriptions; DELETE FROM users;"
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
  worker.py                        ← job queue worker, polls DB, calls Gemini
  Dockerfile                       ← ready for Fargate migration (not used yet)
  .dockerignore                    ← excludes .env, uploads, results, db files
  db/
    models.py                      ← SQLAlchemy models (User, Subscription, Credits, etc.)
  engine/
    generator.py                   ← image generation (gemini-2.0-flash-image-preview)
    prompt_engine.py               ← prompt builder per category + zone-aware layering
    face_validator.py              ← face validation using MediaPipe (local, free, ~0.1s)
    auth_utils.py                  ← JWT create/decode, password hash, token generator
    auth_email.py                  ← verification email sender (reuses SMTP config)
    auth_deps.py                   ← FastAPI dependencies: get_current_user, require_verified_user
    credits.py                     ← credit management: grant, deduct, check balance
  routers/
    __init__.py
    auth.py                        ← register, verify-email, login, me, resend-verification
    payments.py                    ← plans, my-plan, subscribe, topup, purchase history
  seeds/
    __init__.py
    seed_general.py                ← master seeder: categories + all brands + plans
    seed_plans.py                  ← seeds 4 plan definitions (free/basic/glam/payg)
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
# Auth
POST /auth/register                       → create account (sends verification email)
POST /auth/verify-email?token=xxx         → verify email address
POST /auth/login                          → returns JWT access_token
GET  /auth/me                             → current user info (requires Bearer token)
POST /auth/resend-verification            → resend verification email

# Payments & Credits
GET  /payments/plans                      → list all plans + pricing
GET  /payments/my-plan                    → current user's credit balance + plan
POST /payments/subscribe                  → purchase Basic or Glam plan
POST /payments/topup                      → purchase Pay As You Go credits (5–200)
GET  /payments/history                    → user's purchase history

# Catalog
GET  /brands                              → list all brands
GET  /brands/{brand_slug}/categories      → categories for brand
GET  /brands/{brand_slug}/{cat}/products  → products in category
GET  /products/{product_id}/shades        → shades for product

# Generation
POST /upload                              → upload + validate photo (MediaPipe)
POST /generate                            → queue single product try-on → returns job_id
POST /generate-combo                      → queue multi-product combo → returns job_id
GET  /jobs/{job_id}                       → poll job status (pending/processing/complete/failed)

# Static
GET  /results/{filename}                  → serve result image
```

## Generation Flow
```
POST /upload         → validate photo → returns upload_path
POST /generate       → queue job      → returns job_id instantly
GET  /jobs/{job_id}  → poll every 3s  → status: pending → processing → complete
```

## Auth Flow
```
POST /auth/register          → creates user + sends verification email + grants 1 free credit
                               (frontend email link → GET frontend/verify-email?token=xxx)
POST /auth/verify-email      → marks email verified
POST /auth/login             → returns access_token (JWT, 7 days)
GET  /auth/me                → returns user info
All protected routes         → require Authorization: Bearer <token> header
```

## Credit Flow
```
Register           → 1 free credit granted automatically
Buy Basic          → 50 credits, resets monthly (rolling 30 days)
Buy Glam           → 120 credits, resets monthly (rolling 30 days)
Buy PAYG           → 5–200 credits, expires after 2 months, stacks on existing balance
Generation         → deducts 1 credit (subscription first, then PAYG)
Out of credits     → 402 error, must purchase more
```

---

## Plans

| Plan | Price | Credits | Reset | Expiry |
|------|-------|---------|-------|--------|
| Free | $0 | 1 (one-time) | Never | Never |
| Basic | $4.99/mo | 50/mo | Rolling 30 days | Never |
| Glam | $9.99/mo | 120/mo | Rolling 30 days | Never |
| Pay As You Go | $0.18/credit | 5–200 | Never | 2 months |

---

## Useful Dev Commands

```bash
# Verify mediapipe + google-generativeai both work
venv/bin/python -c "import mediapipe; import google.generativeai; print('both ok')"

# Check installed packages
venv/bin/pip list

# Freeze requirements
venv/bin/pip freeze > requirements.txt

# Manually verify a user (skip email for dev)
sqlite3 glamai.db "UPDATE users SET is_verified = 1 WHERE email = 'test@example.com';"

# Get latest verification token
sqlite3 glamai.db "SELECT token FROM email_verification_tokens ORDER BY created_at DESC LIMIT 1;"
```