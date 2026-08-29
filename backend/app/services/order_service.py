from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.marketplace import Delivery, Notification, Order
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.services.order_state import validate_transition


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)

    def get_order_for_user(self, order_id: int, user: User) -> Order:
        order = self.orders.get_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if user.role == "ADMIN" or user.id in {order.buyer_id, order.seller_id}:
            return order
        if order.delivery and order.delivery.logistics_operator_id == user.id:
            return order
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this order")

    def cancel_order(self, order_id: int, user: User) -> Order:
        order = self.get_order_for_user(order_id, user)
        if user.id != order.buyer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buyer can cancel this order")
        return self.update_status(order, user, "CANCELLED")

    def update_status(self, order: Order, user: User, target_status: str) -> Order:
        validate_transition(order.status, target_status, user.role)
        order.status = target_status
        self.db.add(
            Notification(
                user_id=order.buyer_id,
                order_id=order.id,
                title="Order status updated",
                message=f"Order #{order.id} is now {target_status.replace('_', ' ').lower()}.",
            )
        )
        self.db.commit()
        refreshed = self.orders.get_order(order.id)
        if not refreshed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return refreshed

    def seller_orders(self, user: User):
        if user.role not in {"FARMER", "FPO"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only sellers can view incoming orders")
        return self.orders.list_seller_orders(user.id)

    def assign_delivery(self, order_id: int, operator: User, logistics_operator_id: int, vehicle_id: int | None = None, pickup_location_id: int | None = None, delivery_location_id: int | None = None) -> Delivery:
        if operator.role not in {"LOGISTICS", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only logistics operators can assign deliveries")
        order = self.orders.get_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status != "READY_FOR_PICKUP":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only ready orders can be assigned")
        if self.orders.get_delivery_for_order(order_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This order already has a delivery")
        delivery = Delivery(order_id=order_id, logistics_operator_id=logistics_operator_id, status="ASSIGNED", vehicle_id=vehicle_id, pickup_location_id=pickup_location_id, delivery_location_id=delivery_location_id)
        self.db.add(delivery)
        self.db.add(Notification(user_id=logistics_operator_id, order_id=order.id, title="Delivery assigned", message=f"Delivery for order #{order.id} is assigned to you."))
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def update_delivery(self, delivery_id: int, user: User, target_status: str, current_location: str | None):
        if user.role not in {"LOGISTICS", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only logistics operators can update deliveries")
        delivery = self.orders.get_delivery(delivery_id)
        if not delivery:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
        if user.role != "ADMIN" and delivery.logistics_operator_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This delivery is assigned to another operator")
        allowed_delivery_statuses = {"ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED", "CANCELLED"}
        if target_status not in allowed_delivery_statuses:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown delivery status")
        delivery_order = self.orders.get_order(delivery.order_id)
        if not delivery_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if target_status == "PICKED_UP":
            self.update_status(delivery_order, user, "IN_TRANSIT")
            delivery.picked_up_at = datetime.utcnow()
        elif target_status == "DELIVERED":
            self.update_status(delivery_order, user, "DELIVERED")
            delivery.delivered_at = datetime.utcnow()
        elif target_status == "CANCELLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delivery cancellation is not an order transition")
        delivery.status = target_status
        delivery.current_location = current_location
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def ready_orders(self, user: User):
        if user.role not in {"LOGISTICS", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only logistics can view pickup orders")
        return self.orders.list_ready_orders()

    def all_orders(self, user: User):
        if user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can monitor all orders")
        return self.orders.list_all_orders()
