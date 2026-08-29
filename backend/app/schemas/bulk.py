from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Quality = Literal["STANDARD", "GRADE_A", "PREMIUM"]


class PurchaseRequirementCreate(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=150)
    unit: str = Field(..., min_length=1, max_length=20)
    required_quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    quality: Quality = "STANDARD"
    max_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    delivery_location: str = Field(..., min_length=5, max_length=500)
    delivery_deadline: datetime


class PurchaseRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    product_name: str
    unit: str
    required_quantity: Decimal
    quality: str
    max_price: Decimal
    delivery_location: str
    delivery_deadline: datetime
    status: str
    matched_quantity: Decimal
    created_at: datetime


class SupplierMatchRead(BaseModel):
    product_id: int
    supplier_id: int
    supplier_name: str
    quality: str
    available_quantity: Decimal
    matched_quantity: Decimal
    unit_price: Decimal
    estimated_cost: Decimal


class BulkMatchRead(BaseModel):
    requirement_id: int
    required_quantity: Decimal
    matched_quantity: Decimal
    remaining_quantity: Decimal
    estimated_cost: Decimal
    delivery_estimate: datetime | None
    suppliers: list[SupplierMatchRead]


class BulkOrderPlacementRead(BaseModel):
    requirement_id: int
    order_ids: list[int]
    ordered_quantity: Decimal
    remaining_quantity: Decimal
    estimated_cost: Decimal
    status: str


class RequirementStatus(BaseModel):
    status: Literal["OPEN", "CANCELLED"]
