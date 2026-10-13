"""Mapping of the users table from the team script (creacion_tablas_sin_inserciones.sql).

The script creates the schema in PostgreSQL; this module only maps it. create_all is used only in
SQLite tests.
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    # BIGINT in PostgreSQL; INTEGER in SQLite so autoincrement works in the tests.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role_enum", values_callable=lambda roles: [r.value for r in roles]),
        nullable=False,
        server_default=Role.CUSTOMER.value,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecoveryToken(Base):
    """recovery_tokens table. The token column stores the SHA-256 hash, never the link token."""

    __tablename__ = "recovery_tokens"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
