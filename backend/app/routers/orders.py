from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.schemas.marketplace import (
    DeliveryCreate,
    DeliveryRead,
    DeliveryStatusUpdate,
    NotificationRead,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
)
from app.services.marketplace_service import MarketplaceService
from app.services.logistics_service import LogisticsService
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED, summary="Create an order")
def create_order(
    payload: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return MarketplaceService(db).create_order(user, payload)


@router.get("/orders/mine", response_model=list[OrderRead], summary="View purchased orders")
def buyer_orders(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderRepository(db).list_buyer_orders(user.id)


@router.get("/orders/incoming", response_model=list[OrderRead], summary="View incoming seller orders")
def incoming_orders(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).seller_orders(user)


@router.get("/orders/ready-for-pickup", response_model=list[OrderRead], summary="View orders ready for pickup")
def ready_for_pickup(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).ready_orders(user)


@router.post("/orders/{order_id}/delivery", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED, summary="Assign a delivery")
def assign_delivery(
    order_id: int,
    payload: DeliveryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return LogisticsService(db).assign(user, order_id, payload)


@router.patch("/deliveries/{delivery_id}/status", response_model=DeliveryRead, summary="Update delivery status")
def update_delivery_status(
    delivery_id: int,
    payload: DeliveryStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return OrderService(db).update_delivery(delivery_id, user, payload.status, payload.current_location)


@router.get("/orders/sales", response_model=list[OrderRead], summary="View seller orders")
def seller_orders(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).seller_orders(user)


@router.get("/orders/notifications", response_model=list[NotificationRead], summary="View seller order notifications")
def order_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    if user.role not in {"FARMER", "FPO"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only sellers have order notifications")
    return OrderRepository(db).list_notifications(user.id)


@router.get("/orders/all", response_model=list[OrderRead], summary="Monitor all orders")
def all_orders(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).all_orders(user)


@router.get("/orders/{order_id}", response_model=OrderRead, summary="View and track an order")
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).get_order_for_user(order_id, user)


@router.delete("/orders/{order_id}", response_model=OrderRead, summary="Cancel an order")
def cancel_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return OrderService(db).cancel_order(order_id, user)


@router.patch("/orders/{order_id}/status", response_model=OrderRead, summary="Update order status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    service = OrderService(db)
    order = service.get_order_for_user(order_id, user)
    return service.update_status(order, user, payload.status)
