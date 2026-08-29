from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.marketplace import OrderRead, ProductRead


class FPOCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=180)
    registration_number: str | None = Field(default=None, max_length=100)
    address: str = Field(..., min_length=5, max_length=500)


class FPORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    name: str
    registration_number: str | None
    address: str
    created_at: datetime


class FPOMemberCreate(BaseModel):
    farmer_id: int = Field(..., gt=0)


class FPOMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fpo_id: int
    farmer_id: int
    is_active: bool
    joined_at: datetime


class AggregationAllocation(BaseModel):
    source_product_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)


class AggregationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(..., min_length=2, max_length=80)
    unit: str = Field(..., min_length=1, max_length=20)
    price_per_unit: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    location: str | None = Field(default=None, max_length=150)
    image_url: str | None = Field(default=None, max_length=500)
    allocations: list[AggregationAllocation] = Field(..., min_length=1, max_length=100)


class FPOInventoryItem(BaseModel):
    farmer_id: int
    source_product_id: int
    product_name: str
    available_quantity: Decimal
    unit: str


class FPOInventoryRead(BaseModel):
    items: list[FPOInventoryItem]


class FPOAnalytics(BaseModel):
    order_count: int
    fulfilled_order_count: int
    revenue: Decimal


class FPOOverview(BaseModel):
    fpo: FPORead
    members: list[FPOMemberRead]
    listings: list[ProductRead]
    analytics: FPOAnalytics
