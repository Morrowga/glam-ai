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

class Brand(Base):
    __tablename__ = "brands"
    id         = Column(String, primary_key=True, default=gen_id)
    name       = Column(String(100), nullable=False)
    slug       = Column(String(100), unique=True, nullable=False)
    country    = Column(String(50))
    tier       = Column(String(20))     # drugstore / mid / luxury
    is_active  = Column(Boolean, default=True)
    products   = relationship("Product", back_populates="brand")

class Category(Base):
    __tablename__ = "categories"
    id               = Column(String, primary_key=True, default=gen_id)
    name             = Column(String(50), nullable=False)
    slug             = Column(String(50), unique=True, nullable=False)
    application_zone = Column(String(50))  # lips/eyes/cheeks/face
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
    finish_type       = Column(String(30))  # matte/glossy/satin/metallic/shimmer
    coverage          = Column(String(20))  # sheer/medium/full
    prompt_supplement = Column(Text)
    is_active         = Column(Boolean, default=True)
    product           = relationship("Product", back_populates="shades")
    references        = relationship("ReferenceImage", back_populates="shade")
    jobs              = relationship("GenerationJob", back_populates="shade")

class ReferenceImage(Base):
    __tablename__ = "reference_images"
    id            = Column(String, primary_key=True, default=gen_id)
    shade_id      = Column(String, ForeignKey("shades.id"), nullable=False)
    skin_tone     = Column(String(20))     # fair/medium/tan/deep/all
    image_path    = Column(Text, nullable=False)
    source        = Column(String(50))
    quality_score = Column(Integer)
    shade         = relationship("Shade", back_populates="references")

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id              = Column(String, primary_key=True, default=gen_id)

    # ── Session / chain tracking (multi-category support) ──────────
    session_id      = Column(String, index=True, nullable=True)   # groups all steps of one /generate request
    chain_order     = Column(Integer, default=0)                  # 0 = first step, 1 = second, etc.
    input_path      = Column(Text)                                # actual image fed in (may be prev result when chaining)
    # ───────────────────────────────────────────────────────────────

    shade_id        = Column(String, ForeignKey("shades.id"), nullable=False)
    upload_path     = Column(Text)                                # always the original user upload
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