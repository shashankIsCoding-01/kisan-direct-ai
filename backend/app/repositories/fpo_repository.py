from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.marketplace import FPO, FPOInventoryAllocation, FPOMember, Order, Product
from app.models.user import User


class FPORepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, fpo_id: int) -> FPO | None:
        return self.db.get(FPO, fpo_id)

    def get_by_owner(self, owner_user_id: int) -> FPO | None:
        return self.db.scalar(select(FPO).where(FPO.owner_user_id == owner_user_id))

    def get_member(self, fpo_id: int, farmer_id: int) -> FPOMember | None:
        return self.db.scalar(select(FPOMember).where(FPOMember.fpo_id == fpo_id, FPOMember.farmer_id == farmer_id))

    def list_members(self, fpo_id: int):
        return self.db.scalars(select(FPOMember).where(FPOMember.fpo_id == fpo_id).order_by(FPOMember.joined_at.asc())).all()

    def list_listings(self, fpo_id: int):
        return self.db.scalars(select(Product).where(Product.fpo_id == fpo_id).order_by(Product.created_at.desc())).all()

    def list_allocations(self, fpo_id: int):
        return self.db.scalars(select(FPOInventoryAllocation).where(FPOInventoryAllocation.fpo_id == fpo_id)).all()

    def list_member_products(self, farmer_ids: list[int]):
        if not farmer_ids:
            return []
        return self.db.scalars(select(Product).where(Product.seller_id.in_(farmer_ids), Product.is_active.is_(True))).all()

    def list_orders(self, owner_user_id: int):
        return self.db.scalars(select(Order).where(Order.seller_id == owner_user_id).order_by(Order.created_at.desc())).all()
