from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bulk import PurchaseRequirement, RequirementMatch
from app.models.marketplace import Notification, Order, OrderItem, Product
from app.models.user import User
from app.repositories.bulk_repository import BulkRepository
from app.services.marketplace_service import MarketplaceService
from app.schemas.bulk import PurchaseRequirementCreate

QUALITY_RANK = {"STANDARD": 1, "GRADE_A": 2, "PREMIUM": 3}


class BulkService:
    def __init__(self, db: Session):
        self.db = db
        self.bulk = BulkRepository(db)

    def create_requirement(self, user: User, payload: PurchaseRequirementCreate):
        self._require_buyer(user)
        if payload.delivery_deadline <= datetime.now(payload.delivery_deadline.tzinfo):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Delivery deadline must be in the future")
        requirement = PurchaseRequirement(buyer_id=user.id, **payload.model_dump())
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get_requirement(self, user: User, requirement_id: int):
        requirement = self.bulk.get_requirement(requirement_id)
        if not requirement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase requirement not found")
        if requirement.buyer_id != user.id and user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this requirement")
        return requirement

    def list_requirements(self, user: User):
        self._require_buyer(user)
        return self.bulk.list_requirements(user.id)

    def match(self, user: User, requirement_id: int):
        requirement = self.get_requirement(user, requirement_id)
        if requirement.status == "CANCELLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled requirements cannot be matched")
        matches = self._compute_matches(requirement)
        self.bulk.clear_matches(requirement.id)
        for product, supplier, matched_quantity in matches:
            self.db.add(RequirementMatch(requirement_id=requirement.id, product_id=product.id, supplier_id=supplier.id, matched_quantity=matched_quantity, unit_price=product.price_per_unit))
        total = sum((quantity for _, _, quantity in matches), Decimal("0"))
        requirement.matched_quantity = total
        requirement.status = "FULFILLED" if total >= requirement.required_quantity else "PARTIALLY_MATCHED" if total > 0 else "OPEN"
        self.db.commit()
        return self._match_response(requirement, matches)

    def place_orders(self, user: User, requirement_id: int):
        requirement = self.get_requirement(user, requirement_id)
        if requirement.status == "CANCELLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cancelled requirements cannot be ordered")
        matches = self._compute_matches(requirement)
        if not matches:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No eligible supply is currently available")

        order_ids: list[int] = []
        ordered_quantity = Decimal("0")
        estimated_cost = Decimal("0")
        for product, supplier, quantity in matches:
            if quantity <= 0:
                continue
            order = Order(buyer_id=user.id, seller_id=supplier.id, status="PENDING", total_amount=quantity * product.price_per_unit, shipping_address=requirement.delivery_location)
            self.db.add(order)
            self.db.flush()
            self.db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, quantity=quantity, unit_price=product.price_per_unit, subtotal=quantity * product.price_per_unit))
            product.quantity -= quantity
            if product.is_aggregated:
                MarketplaceService(self.db)._consume_aggregated_inventory(product.id, quantity)
            self.db.add(Notification(user_id=supplier.id, order_id=order.id, title="New bulk order received", message=f"Bulk requirement #{requirement.id} placed order #{order.id}."))
            order_ids.append(order.id)
            ordered_quantity += quantity
            estimated_cost += quantity * product.price_per_unit
        remaining = max(requirement.required_quantity - ordered_quantity, Decimal("0"))
        requirement.matched_quantity = ordered_quantity
        requirement.status = "FULFILLED" if remaining == 0 else "PARTIALLY_FULFILLED"
        self.db.commit()
        return {"requirement_id": requirement.id, "order_ids": order_ids, "ordered_quantity": ordered_quantity, "remaining_quantity": remaining, "estimated_cost": estimated_cost, "status": requirement.status}

    def _compute_matches(self, requirement: PurchaseRequirement):
        acceptable_grades = [grade for grade, rank in QUALITY_RANK.items() if rank >= QUALITY_RANK[requirement.quality]]
        candidates = self.bulk.candidate_products(requirement.product_name, requirement.unit, acceptable_grades, requirement.max_price)
        remaining = requirement.required_quantity
        matches = []
        for product, supplier in candidates:
            if remaining <= 0:
                break
            quantity = min(product.quantity, remaining)
            matches.append((product, supplier, quantity))
            remaining -= quantity
        return matches

    def _match_response(self, requirement, matches):
        matched_quantity = sum((quantity for _, _, quantity in matches), Decimal("0"))
        estimated_cost = sum((quantity * product.price_per_unit for product, _, quantity in matches), Decimal("0"))
        return {
            "requirement_id": requirement.id,
            "required_quantity": requirement.required_quantity,
            "matched_quantity": matched_quantity,
            "remaining_quantity": max(requirement.required_quantity - matched_quantity, Decimal("0")),
            "estimated_cost": estimated_cost,
            "delivery_estimate": requirement.delivery_deadline if matches else None,
            "suppliers": [
                {"product_id": product.id, "supplier_id": supplier.id, "supplier_name": supplier.full_name, "quality": product.quality, "available_quantity": product.quantity, "matched_quantity": quantity, "unit_price": product.price_per_unit, "estimated_cost": quantity * product.price_per_unit}
                for product, supplier, quantity in matches
            ],
        }

    @staticmethod
    def _require_buyer(user: User):
        if user.role not in {"BULK_BUYER", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only bulk buyers can manage purchase requirements")
