from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    fpo_id: Mapped[int | None] = mapped_column(ForeignKey("fpos.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    quality: Mapped[str] = mapped_column(String(30), default="STANDARD", nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_aggregated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    delivery: Mapped["Delivery | None"] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    order: Mapped[Order] = relationship(back_populates="items")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FPO(Base):
    __tablename__ = "fpos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    members: Mapped[list["FPOMember"]] = relationship(
        back_populates="fpo", cascade="all, delete-orphan"
    )


class FPOMember(Base):
    __tablename__ = "fpo_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fpo_id: Mapped[int] = mapped_column(ForeignKey("fpos.id"), index=True, nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    fpo: Mapped[FPO] = relationship(back_populates="members")


class FPOInventoryAllocation(Base):
    __tablename__ = "fpo_inventory_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fpo_id: Mapped[int] = mapped_column(ForeignKey("fpos.id"), index=True, nullable=False)
    aggregated_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    logistics_operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ASSIGNED", nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    order: Mapped[Order] = relationship(back_populates="delivery")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    pickup_location_id: Mapped[int | None] = mapped_column(ForeignKey("pickup_locations.id"), nullable=True)
    delivery_location_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_locations.id"), nullable=True)
    vehicle: Mapped["Vehicle | None"] = relationship()
    pickup_location: Mapped["PickupLocation | None"] = relationship(foreign_keys=[pickup_location_id])
    delivery_location: Mapped["DeliveryLocation | None"] = relationship(foreign_keys=[delivery_location_id])


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    registration_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PickupLocation(Base):
    __tablename__ = "pickup_locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)


class DeliveryLocation(Base):
    __tablename__ = "delivery_locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    waypoint_order: Mapped[list] = mapped_column(JSON, nullable=False)
    baseline_waypoint_order: Mapped[list] = mapped_column(JSON, nullable=False)
    total_distance_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_travel_time_min: Mapped[int] = mapped_column(nullable=False)
    number_of_stops: Mapped[int] = mapped_column(nullable=False)
    capacity_utilization_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    baseline_distance_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    routing_provider: Mapped[str] = mapped_column(String(80), default="haversine_straight_line", nullable=False)
    is_demo_environment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    optimized_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
