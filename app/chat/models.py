"""Mapeo de la tabla tickets del script del equipo (no crea tablas en PostgreSQL)."""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.accounts.models import Base

_ID = BigInteger().with_variant(Integer, "sqlite")


class TicketStatus(str, enum.Enum):
    NEW = "NEW"
    IN_DIAGNOSIS = "IN_DIAGNOSIS"
    QUOTED = "QUOTED"
    IN_REPAIR = "IN_REPAIR"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(_ID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    failure_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status_enum", values_callable=lambda s: [v.value for v in s]),
        nullable=False,
        server_default=TicketStatus.NEW.value,
    )
    provisional_diagnosis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
