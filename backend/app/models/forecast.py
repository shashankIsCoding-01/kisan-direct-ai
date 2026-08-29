from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DemandObservation(Base):
    __tablename__ = "demand_observations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    observed_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    product: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    buyer_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="ORDER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    training_rows: Mapped[int] = mapped_column(nullable=False)
    data_source: Mapped[str] = mapped_column(String(30), nullable=False)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    baseline_mae: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
