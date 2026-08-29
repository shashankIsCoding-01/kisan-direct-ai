from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.bulk import PurchaseRequirement, RequirementMatch
from app.models.marketplace import Product
from app.models.user import User


class BulkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_requirement(self, requirement_id: int) -> PurchaseRequirement | None:
        return self.db.get(PurchaseRequirement, requirement_id)

    def list_requirements(self, buyer_id: int):
        return self.db.scalars(select(PurchaseRequirement).where(PurchaseRequirement.buyer_id == buyer_id).order_by(PurchaseRequirement.created_at.desc())).all()

    def list_matches(self, requirement_id: int):
        return self.db.scalars(select(RequirementMatch).where(RequirementMatch.requirement_id == requirement_id).order_by(RequirementMatch.unit_price.asc())).all()

    def clear_matches(self, requirement_id: int):
        self.db.execute(delete(RequirementMatch).where(RequirementMatch.requirement_id == requirement_id))

    def candidate_products(self, product_name: str, unit: str, quality_grades: list[str], max_price):
        return self.db.execute(
            select(Product, User)
            .join(User, User.id == Product.seller_id)
            .where(
                Product.is_active.is_(True),
                Product.quantity > 0,
                Product.name.ilike(product_name),
                Product.unit == unit,
                Product.quality.in_(quality_grades),
                Product.price_per_unit <= max_price,
                User.role.in_(["FARMER", "FPO"]),
            )
            .order_by(Product.price_per_unit.asc(), Product.created_at.asc(), Product.id.asc())
        ).all()
