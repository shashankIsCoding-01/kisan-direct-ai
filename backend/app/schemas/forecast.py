from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BuyerType = Literal["FARMER", "FPO", "CONSUMER", "BULK_BUYER", "LOGISTICS", "ADMIN"]


class DemandObservationCreate(BaseModel):
    observed_date: date
    product: str = Field(..., min_length=2, max_length=150)
    location: str = Field(..., min_length=2, max_length=150)
    quantity: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    buyer_type: BuyerType
    source: Literal["ORDER", "IMPORTED", "DEMO"] = "IMPORTED"


class DemandObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    observed_date: date
    product: str
    location: str
    quantity: Decimal
    price: Decimal
    buyer_type: str
    source: str


class ForecastTrainResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    training_rows: int
    data_source: str
    baseline: dict[str, float]
    regression: dict[str, float]
    selected_model: str


class DemandForecastRequest(BaseModel):
    product: str = Field(..., min_length=2, max_length=150)
    location: str = Field(..., min_length=2, max_length=150)
    buyer_type: BuyerType
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    start_date: date | None = None
    days_ahead: int = Field(default=7, ge=1, le=30)


class DemandForecastPoint(BaseModel):
    date: date
    predicted_demand: float


class DemandForecastResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    product: str
    location: str
    forecast_period: str
    forecast: list[DemandForecastPoint]
    data_source: str
    uncertainty_supported: bool = False
    limitations: list[str]
