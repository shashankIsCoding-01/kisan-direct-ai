from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PurchaseRequirement(Base):
    __tablename__ = "purchase_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quality: Mapped[str] = mapped_column(String(30), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_location: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)
    matched_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    matches: Mapped[list["RequirementMatch"]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )


class RequirementMatch(Base):
    __tablename__ = "requirement_matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("purchase_requirements.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    matched_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    requirement: Mapped[PurchaseRequirement] = relationship(back_populates="matches")
