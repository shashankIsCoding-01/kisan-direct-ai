from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.marketplace import FPO, FPOInventoryAllocation, FPOMember, Order, Product
from app.models.user import User
from app.repositories.fpo_repository import FPORepository
from app.schemas.fpo import AggregationRequest, FPOCreate, FPOMemberCreate


class FPOService:
    def __init__(self, db: Session):
        self.db = db
        self.fpos = FPORepository(db)

    def create_fpo(self, user: User, payload: FPOCreate):
        self._require_fpo(user)
        if self.fpos.get_by_owner(user.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This user already owns an FPO")
        fpo = FPO(owner_user_id=user.id, **payload.model_dump())
        self.db.add(fpo)
        self.db.commit()
        self.db.refresh(fpo)
        return fpo

    def my_fpo(self, user: User):
        fpo = self.fpos.get_by_owner(user.id)
        if not fpo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FPO profile not found")
        return fpo

    def get_owned_fpo(self, user: User, fpo_id: int) -> FPO:
        fpo = self.fpos.get_by_id(fpo_id)
        if not fpo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FPO not found")
        if user.role != "ADMIN" and fpo.owner_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not manage this FPO")
        return fpo

    def add_member(self, user: User, fpo_id: int, payload: FPOMemberCreate):
        fpo = self.get_owned_fpo(user, fpo_id)
        farmer = self.db.get(User, payload.farmer_id)
        if not farmer or farmer.role != "FARMER":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member must be a farmer")
        if self.fpos.get_member(fpo.id, farmer.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Farmer is already a member")
        member = FPOMember(fpo_id=fpo.id, farmer_id=farmer.id)
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, user: User, fpo_id: int, farmer_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        member = self.fpos.get_member(fpo.id, farmer_id)
        if not member or not member.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active membership not found")
        member.is_active = False
        self.db.commit()
        return member

    def members(self, user: User, fpo_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        return self.fpos.list_members(fpo.id)

    def farmer_inventory(self, user: User, fpo_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        farmer_ids = [member.farmer_id for member in self.fpos.list_members(fpo.id) if member.is_active]
        products = self.fpos.list_member_products(farmer_ids)
        return [{"farmer_id": p.seller_id, "source_product_id": p.id, "product_name": p.name, "available_quantity": p.quantity, "unit": p.unit} for p in products]

    def aggregate(self, user: User, fpo_id: int, payload: AggregationRequest):
        fpo = self.get_owned_fpo(user, fpo_id)
        active_members = {member.farmer_id for member in self.fpos.list_members(fpo.id) if member.is_active}
        if not active_members:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add active farmer members before aggregating")

        sources: list[tuple[Product, Decimal]] = []
        source_ids: set[int] = set()
        for allocation in payload.allocations:
            if allocation.source_product_id in source_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A source listing can only be allocated once")
            source_ids.add(allocation.source_product_id)
            source = self.db.get(Product, allocation.source_product_id)
            if not source or not source.is_active or source.seller_id not in active_members:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Every source must be an active member farmer listing")
            if source.unit != payload.unit or source.category != payload.category or source.name.lower() != payload.name.lower():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All source listings must describe the same product and unit")
            if allocation.quantity > source.quantity:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Aggregation exceeds available supply for {source.name}")
            sources.append((source, allocation.quantity))

        total_quantity = sum((quantity for _, quantity in sources), Decimal("0"))
        listing = Product(
            seller_id=fpo.owner_user_id,
            fpo_id=fpo.id,
            is_aggregated=True,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            unit=payload.unit,
            price_per_unit=payload.price_per_unit,
            quantity=total_quantity,
            location=payload.location,
            image_url=payload.image_url,
        )
        self.db.add(listing)
        self.db.flush()
        for source, quantity in sources:
            source.quantity -= quantity
            self.db.add(FPOInventoryAllocation(fpo_id=fpo.id, aggregated_product_id=listing.id, source_product_id=source.id, farmer_id=source.seller_id, reserved_quantity=quantity))
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def listings(self, user: User, fpo_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        return self.fpos.list_listings(fpo.id)

    def orders(self, user: User, fpo_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        return self.fpos.list_orders(fpo.owner_user_id)

    def analytics(self, user: User, fpo_id: int):
        fpo = self.get_owned_fpo(user, fpo_id)
        base = select(Order).where(Order.seller_id == fpo.owner_user_id).subquery()
        order_count = self.db.scalar(select(func.count()).select_from(base)) or 0
        fulfilled = self.db.scalar(select(func.count()).select_from(base).where(base.c.status == "DELIVERED")) or 0
        revenue = self.db.scalar(select(func.coalesce(func.sum(base.c.total_amount), 0)).select_from(base)) or Decimal("0")
        return {"order_count": order_count, "fulfilled_order_count": fulfilled, "revenue": revenue}

    @staticmethod
    def _require_fpo(user: User):
        if user.role not in {"FPO", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only FPO users can manage an FPO")
