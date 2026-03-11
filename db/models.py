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

class Plan(Base):
    """
    Master plan definitions — seeded once, not user-specific.
    plan_type: free | basic | glam | payg

    Pricing is stored in 3 currencies:
    - price_usd: default / all other countries
    - price_thb: Thailand
    - price_mmk: Myanmar
    For PAYG: price_per_credit_usd / price_per_credit_thb / price_per_credit_mmk
    """
    __tablename__ = "plans"

    id               = Column(String,  primary_key=True, default=gen_id)
    name             = Column(String(50),  nullable=False)
    plan_type        = Column(String(20),  nullable=False, unique=True)
    credits          = Column(Integer, nullable=False)
    is_subscription  = Column(Boolean, default=False)
    is_active        = Column(Boolean, default=True)

    # Subscription prices (monthly)
    price_usd        = Column(Float, nullable=False, default=0.0)
    price_thb        = Column(Float, nullable=True)   # Thailand Baht
    price_mmk        = Column(Float, nullable=True)   # Myanmar Kyat

    # PAYG-specific
    min_credits          = Column(Integer, nullable=True)
    max_credits          = Column(Integer, nullable=True)
    price_per_credit     = Column(Float,   nullable=True)   # USD per credit
    price_per_credit_thb = Column(Float,   nullable=True)   # THB per credit
    price_per_credit_mmk = Column(Float,   nullable=True)   # MMK per credit


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
    amount_local      = Column(Float,   nullable=True)   # amount in local currency
    currency          = Column(String(10), nullable=True) # THB / MMK / USD
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

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id              = Column(String, primary_key=True, default=gen_id)
    session_id      = Column(String, index=True, nullable=True)
    chain_order     = Column(Integer, default=0)
    input_path      = Column(Text)
    shade_id        = Column(String, ForeignKey("shades.id"), nullable=False)
    upload_path     = Column(Text)
    result_path     = Column(Text)
    prompt_used     = Column(Text)
    status          = Column(String(20), default="pending")
    cached          = Column(Boolean, default=False)
    error_message   = Column(Text)
    generation_time = Column(Float)
    created_at      = Column(DateTime, server_default=func.now())
    completed_at    = Column(DateTime)
    shade           = relationship("Shade", back_populates="jobs")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session