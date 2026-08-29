from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(..., min_length=2, max_length=80)
    quality: Literal["STANDARD", "GRADE_A", "PREMIUM"] = "STANDARD"
    unit: str = Field(..., min_length=1, max_length=20)
    price_per_unit: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    location: str | None = Field(default=None, max_length=150)
    image_url: str | None = Field(default=None, max_length=500)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    quality: Literal["STANDARD", "GRADE_A", "PREMIUM"] | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    price_per_unit: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    location: str | None = Field(default=None, max_length=150)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    name: str
    description: str | None
    category: str
    quality: str
    unit: str
    price_per_unit: Decimal
    quantity: Decimal
    location: str | None
    image_url: str | None
    is_active: bool
    is_aggregated: bool
    fpo_id: int | None
    created_at: datetime
    updated_at: datetime


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    limit: int


class CartItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: Decimal


class CartRead(BaseModel):
    items: list[CartItemRead]
    total_amount: Decimal


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=5, max_length=500)


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=30)


class DeliveryCreate(BaseModel):
    logistics_operator_id: int = Field(..., gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    pickup_location_id: int | None = Field(default=None, gt=0)
    delivery_location_id: int | None = Field(default=None, gt=0)


class DeliveryStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=30)
    current_location: str | None = Field(default=None, max_length=150)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    seller_id: int
    status: str
    total_amount: Decimal
    shipping_address: str
    created_at: datetime
    items: list[OrderItemRead] = []
    delivery: "DeliveryRead | None" = None


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    logistics_operator_id: int
    status: str
    current_location: str | None
    assigned_at: datetime
    picked_up_at: datetime | None
    delivered_at: datetime | None
    vehicle_id: int | None = None
    pickup_location_id: int | None = None
    delivery_location_id: int | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int | None
    title: str
    message: str
    is_read: bool
    created_at: datetime


SortOption = Literal["newest", "price_asc", "price_desc", "name"]
