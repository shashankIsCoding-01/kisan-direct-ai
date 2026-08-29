from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.marketplace import Product


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def list_active(self, *, search: str | None, category: str | None, sort: str):
        query = select(Product).where(Product.is_active.is_(True), Product.quantity > 0)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        if category:
            query = query.where(Product.category == category)
        if sort == "price_asc":
            query = query.order_by(Product.price_per_unit.asc())
        elif sort == "price_desc":
            query = query.order_by(Product.price_per_unit.desc())
        elif sort == "name":
            query = query.order_by(Product.name.asc())
        else:
            query = query.order_by(Product.created_at.desc())
        return self.db.scalars(query).all()

    def list_by_seller(self, seller_id: int):
        query = select(Product).where(Product.seller_id == seller_id).order_by(Product.created_at.desc())
        return self.db.scalars(query).all()

    def create(self, seller_id: int, values: dict) -> Product:
        product = Product(seller_id=seller_id, **values)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
