from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    registration_number: str = Field(..., min_length=2, max_length=40)
    vehicle_type: str = Field(..., min_length=2, max_length=50)
    capacity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(default="kg", min_length=1, max_length=20)


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_id: int
    registration_number: str
    vehicle_type: str
    capacity: Decimal
    unit: str
    is_available: bool


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    address: str = Field(..., min_length=5, max_length=500)
    latitude: Decimal = Field(..., ge=-90, le=90, max_digits=10, decimal_places=7)
    longitude: Decimal = Field(..., ge=-180, le=180, max_digits=10, decimal_places=7)


class PickupLocationRead(LocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DeliveryLocationRead(LocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LogisticsAssignmentCreate(BaseModel):
    logistics_operator_id: int = Field(..., gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    pickup_location_id: int | None = Field(default=None, gt=0)
    delivery_location_id: int | None = Field(default=None, gt=0)


class RouteOptimizeRequest(BaseModel):
    vehicle_id: int = Field(..., gt=0)
    delivery_ids: list[int] = Field(..., min_length=1, max_length=100)
    depot_latitude: Decimal = Field(..., ge=-90, le=90)
    depot_longitude: Decimal = Field(..., ge=-180, le=180)
    average_speed_kmh: Decimal = Field(default=30, gt=0, le=200)


class RouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    waypoint_order: list
    baseline_waypoint_order: list
    total_distance_km: Decimal
    estimated_travel_time_min: int
    number_of_stops: int
    capacity_utilization_percent: Decimal
    baseline_distance_km: Decimal
    optimized_at: datetime


class RouteOptimizationResponse(BaseModel):
    route: RouteRead
    baseline_distance_km: float
    optimized_distance_km: float
    distance_reduction_percent: float
    estimated_travel_time_min: int
    number_of_stops: int
    capacity_utilization_percent: float
    routing_provider: str
    optimization_method: str
    problem_classification: str
    demo_environment: bool
