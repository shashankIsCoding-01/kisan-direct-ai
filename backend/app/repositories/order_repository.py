from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.marketplace import CartItem, Delivery, Notification, Order


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_cart(self, buyer_id: int):
        return self.db.scalars(select(CartItem).where(CartItem.buyer_id == buyer_id)).all()

    def get_order(self, order_id: int) -> Order | None:
        return self.db.scalar(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )

    def list_buyer_orders(self, buyer_id: int):
        return self.db.scalars(
            select(Order).options(selectinload(Order.items)).where(Order.buyer_id == buyer_id).order_by(Order.created_at.desc())
        ).all()

    def list_seller_orders(self, seller_id: int):
        return self.db.scalars(
            select(Order).options(selectinload(Order.items)).where(Order.seller_id == seller_id).order_by(Order.created_at.desc())
        ).all()

    def list_notifications(self, user_id: int):
        return self.db.scalars(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
        ).all()

    def list_all_orders(self):
        return self.db.scalars(
            select(Order).options(selectinload(Order.items), selectinload(Order.delivery)).order_by(Order.created_at.desc())
        ).all()

    def get_delivery(self, delivery_id: int) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)

    def get_delivery_for_order(self, order_id: int) -> Delivery | None:
        return self.db.scalar(select(Delivery).where(Delivery.order_id == order_id))

    def list_ready_orders(self):
        return self.db.scalars(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.delivery))
            .where(Order.status == "READY_FOR_PICKUP")
            .order_by(Order.created_at.asc())
        ).all()
