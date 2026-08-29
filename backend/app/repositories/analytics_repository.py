from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bulk import PurchaseRequirement
from app.models.forecast import ForecastRun
from app.models.marketplace import FPO, FPOInventoryAllocation, FPOMember, Order, OrderItem, Product, Route
from app.models.user import User


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_users(self, role: str, active_only: bool = False) -> int:
        query = select(func.count(User.id)).where(User.role == role)
        if active_only:
            query = query.where(User.is_active.is_(True))
        return int(self.db.scalar(query) or 0)

    def count_active_fpos(self) -> int:
        query = select(func.count(func.distinct(FPOMember.fpo_id))).where(FPOMember.is_active.is_(True))
        return int(self.db.scalar(query) or 0)

    def count_products(self) -> int:
        return int(self.db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0)

    def orders(self):
        return self.db.scalars(select(Order)).all()

    def delivered_order_items(self):
        return self.db.execute(
            select(OrderItem, Order).join(Order, Order.id == OrderItem.order_id).where(Order.status == "DELIVERED")
        ).all()

    def routes(self, demo: bool):
        return self.db.scalars(select(Route).where(Route.is_demo_environment.is_(demo))).all()

    def latest_forecast_run(self, source: str):
        return self.db.scalar(select(ForecastRun).where(ForecastRun.data_source == source).order_by(ForecastRun.created_at.desc()))
