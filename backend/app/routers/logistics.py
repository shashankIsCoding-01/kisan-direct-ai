from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.logistics import (
    DeliveryLocationRead,
    LocationCreate,
    LogisticsAssignmentCreate,
    PickupLocationRead,
    RouteOptimizeRequest,
    RouteOptimizationResponse,
    VehicleCreate,
    VehicleRead,
)
from app.schemas.marketplace import DeliveryRead
from app.services.logistics_service import LogisticsService

router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.post("/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED, summary="Register a delivery vehicle")
def create_vehicle(payload: VehicleCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).create_vehicle(user, payload)


@router.get("/vehicles", response_model=list[VehicleRead], summary="List my delivery vehicles")
def list_vehicles(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).list_vehicles(user)


@router.post("/pickup-locations", response_model=PickupLocationRead, status_code=status.HTTP_201_CREATED, summary="Create a pickup location")
def create_pickup_location(payload: LocationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).create_pickup_location(user, payload)


@router.post("/delivery-locations", response_model=DeliveryLocationRead, status_code=status.HTTP_201_CREATED, summary="Create a delivery location")
def create_delivery_location(payload: LocationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).create_delivery_location(user, payload)


@router.post("/assignments/{order_id}", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED, summary="Assign an order for delivery")
def assign_delivery(order_id: int, payload: LogisticsAssignmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).assign(user, order_id, payload)


@router.get("/deliveries", response_model=list[DeliveryRead], summary="List delivery assignments")
def list_deliveries(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).list_deliveries(user)


@router.post("/routes/optimize", response_model=RouteOptimizationResponse, summary="Optimize a delivery route")
def optimize_route(payload: RouteOptimizeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return LogisticsService(db).optimize_route(user, payload)
