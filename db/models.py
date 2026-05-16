from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, DateTime, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv
import uuid, os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./glamai.db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

def gen_id():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id             = Column(String,  primary_key=True, default=gen_id)
    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=False)
    display_name   = Column(String(100), nullable=True)
    is_verified    = Column(Boolean, default=False)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, server_default=func.now())
    last_login_at  = Column(DateTime, nullable=True)

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id         = Column(String,  primary_key=True, default=gen_id)
    user_id    = Column(String,  ForeignKey("users.id"), nullable=False)
    token      = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id         = Column(String,  primary_key=True, default=gen_id)
    user_id    = Column(String,  ForeignKey("users.id"), nullable=False)
    token      = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    user       = relationship("User")

class Plan(Base):
    __tablename__ = "plans"
    id               = Column(String,  primary_key=True, default=gen_id)
    name             = Column(String(50),  nullable=False)
    plan_type        = Column(String(20),  nullable=False, unique=True)
    credits          = Column(Integer, nullable=False)
    is_subscription  = Column(Boolean, default=False)
    is_active        = Column(Boolean, default=True)
    price_usd        = Column(Float, nullable=False, default=0.0)
    price_thb        = Column(Float, nullable=True)
    price_mmk        = Column(Float, nullable=True)
    min_credits          = Column(Integer, nullable=True)
    max_credits          = Column(Integer, nullable=True)
    price_per_credit     = Column(Float,   nullable=True)
    price_per_credit_thb = Column(Float,   nullable=True)
    price_per_credit_mmk = Column(Float,   nullable=True)

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id                   = Column(String,  primary_key=True, default=gen_id)
    user_id              = Column(String,  ForeignKey("users.id"), nullable=False, unique=True)
    plan_type            = Column(String(20), nullable=False, default="free")
    credits_total        = Column(Integer, nullable=False, default=1)
    credits_used         = Column(Integer, nullable=False, default=0)
    credits_remaining    = Column(Integer, nullable=False, default=1)
    payg_credits         = Column(Integer, nullable=False, default=0)
    payg_expires_at      = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end   = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())
    user                 = relationship("User")

class PurchaseRecord(Base):
    __tablename__ = "purchase_records"
    id                = Column(String,  primary_key=True, default=gen_id)
    user_id           = Column(String,  ForeignKey("users.id"), nullable=False)
    plan_type         = Column(String(20), nullable=False)
    credits_purchased = Column(Integer, nullable=False)
    amount_usd        = Column(Float,   nullable=False)
    amount_local      = Column(Float,   nullable=True)
    currency          = Column(String(10), nullable=True)
    payment_intent_id = Column(String,  nullable=True)
    status            = Column(String(20), default="completed")
    created_at        = Column(DateTime, server_default=func.now())
    user              = relationship("User")

class Brand(Base):
    __tablename__ = "brands"
    id         = Column(String, primary_key=True, default=gen_id)
    name       = Column(String(100), nullable=False)
    slug       = Column(String(100), unique=True, nullable=False)
    country    = Column(String(50))
    tier       = Column(String(20))
    is_active  = Column(Boolean, default=True)
    products   = relationship("Product", back_populates="brand")

class Category(Base):
    __tablename__ = "categories"
    id               = Column(String, primary_key=True, default=gen_id)
    name             = Column(String(50), nullable=False)
    slug             = Column(String(50), unique=True, nullable=False)
    application_zone = Column(String(50))
    products         = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id          = Column(String, primary_key=True, default=gen_id)
    brand_id    = Column(String, ForeignKey("brands.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=False)
    name        = Column(String(150), nullable=False)
    slug        = Column(String(150), nullable=False)
    description = Column(Text)
    is_active   = Column(Boolean, default=True)
    brand       = relationship("Brand", back_populates="products")
    category    = relationship("Category", back_populates="products")
    shades      = relationship("Shade", back_populates="product")

class Shade(Base):
    __tablename__ = "shades"
    id                = Column(String, primary_key=True, default=gen_id)
    product_id        = Column(String, ForeignKey("products.id"), nullable=False)
    name              = Column(String(100), nullable=False)
    hex_color         = Column(String(7))
    finish_type       = Column(String(30))
    coverage          = Column(String(20))
    prompt_supplement = Column(Text)
    is_active         = Column(Boolean, default=True)
    product           = relationship("Product", back_populates="shades")
    references        = relationship("ReferenceImage", back_populates="shade")
    jobs              = relationship("GenerationJob", back_populates="shade")

class ReferenceImage(Base):
    __tablename__ = "reference_images"
    id            = Column(String, primary_key=True, default=gen_id)
    shade_id      = Column(String, ForeignKey("shades.id"), nullable=False)
    skin_tone     = Column(String(20))
    image_path    = Column(Text, nullable=False)
    source        = Column(String(50))
    quality_score = Column(Integer)
    shade         = relationship("Shade", back_populates="references")

# ── ADD THESE TWO MODELS TO db/models.py ─────────────────────────
# Add after the GenerationJobItem class
# Also add to init_db() — it already calls Base.metadata.create_all so no change needed there

class UserProfile(Base):
    """
    One row per user.
    Stores default face photo path for Look Preparation.
    Created lazily on first photo upload.
    """
    __tablename__ = "user_profiles"

    id                   = Column(String,  primary_key=True, default=gen_id)
    user_id              = Column(String,  ForeignKey("users.id"), nullable=False, unique=True)
    default_photo_path   = Column(Text,    nullable=True)   # absolute path, validated by face_validator
    default_photo_url    = Column(Text,    nullable=True)   # BASE_URL + /uploads/filename for display
    created_at           = Column(DateTime, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")


class UserProduct(Base):
    """
    One row per cosmetic product in a user's bag.
    Created after Gemini validates the product text.
    """
    __tablename__ = "user_products"

    id           = Column(String,  primary_key=True, default=gen_id)
    user_id      = Column(String,  ForeignKey("users.id"), nullable=False, index=True)
    raw_input    = Column(Text,    nullable=False)          # exactly what the user typed
    brand        = Column(String(150), nullable=True)       # extracted by Gemini
    product_name = Column(String(150), nullable=True)       # extracted by Gemini
    shade        = Column(String(100), nullable=True)       # extracted or asked
    zone         = Column(String(20),  nullable=False)      # lip | eye | cheek
    hex_color    = Column(String(7),   nullable=True)       # best-guess hex from Gemini
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, server_default=func.now())

    user = relationship("User")

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id              = Column(String, primary_key=True, default=gen_id)
    user_id         = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    session_id      = Column(String, index=True, nullable=True)
    chain_order     = Column(Integer, default=0)
    input_path      = Column(Text)
    shade_id        = Column(String, ForeignKey("shades.id"), nullable=False)
    upload_path     = Column(Text)
    result_path     = Column(Text)
    prompt_used     = Column(Text)
    zone            = Column(String(20), nullable=True)  # 'lip' | 'eye' | 'cheek'
    status          = Column(String(20), default="pending")
    cached          = Column(Boolean, default=False)
    error_message   = Column(Text)
    generation_time = Column(Float)
    created_at      = Column(DateTime, server_default=func.now())
    completed_at    = Column(DateTime)
    # ── Share ──────────────────────────────────────────────────────
    share_token     = Column(String(64), unique=True, nullable=True, index=True)
    is_shared       = Column(Boolean, default=False, nullable=False)
    look_meta       = Column(Text, nullable=True)  

    # ──────────────────────────────────────────────────────────────
    shade           = relationship("Shade", back_populates="jobs")
    user            = relationship("User")
    items           = relationship("GenerationJobItem", back_populates="job", cascade="all, delete-orphan")


class GenerationJobItem(Base):
    """One row per product+shade used in a generation job."""
    __tablename__ = "generation_job_items"

    id         = Column(String, primary_key=True, default=gen_id)
    job_id     = Column(String, ForeignKey("generation_jobs.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"),        nullable=False)
    shade_id   = Column(String, ForeignKey("shades.id"),          nullable=False)

    job     = relationship("GenerationJob", back_populates="items")
    product = relationship("Product")
    shade   = relationship("Shade")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session