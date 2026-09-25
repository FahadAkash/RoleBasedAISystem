"""SQLite database models and setup using SQLAlchemy."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from backend.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


# ─── Models ──────────────────────────────────────────────────────────────────


class User(Base):
    """All users (admin, staff, user) share this table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # admin | staff | user
    department = Column(String(50), default="general")
    phone = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Staff can be assigned to users
    assigned_staff_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_staff = relationship("User", remote_side=[id], backref="assigned_users")

    # Chat history
    chat_messages = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class ChatMessage(Base):
    """Chat message history per user."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    tool_used = Column(String(50), nullable=True)
    access_decision = Column(String(200), nullable=True)  # Jev decision log
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chat_messages")


class Document(Base):
    """Knowledge base documents tracked for RAG."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="general")  # general | policy | technical
    access_level = Column(
        String(20), default="all"
    )  # all | staff | admin  (minimum role to read)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Audit trail for access control decisions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(200), nullable=False)
    decision = Column(String(20), nullable=False)  # allowed | denied
    jev_probability = Column(String(10), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Product(Base):
    """E-Commerce Product."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), index=True)
    description = Column(Text, default="")
    price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    category = Column(String(50), default="general")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Order(Base):
    """E-Commerce Order."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    total_price = Column(Float, default=0.0)
    order_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default="in_cart") # in_cart, processing, shipped, delivered, returned
    delivery_date = Column(DateTime, nullable=True)


# ─── Engine & Session ────────────────────────────────────────────────────────

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency for FastAPI – yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
