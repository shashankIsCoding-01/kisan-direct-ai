from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forecast import DemandObservation
from app.models.marketplace import CartItem, FPOInventoryAllocation, Notification, Order, OrderItem, Product
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.marketplace import CartItemCreate, OrderCreate, ProductCreate, ProductUpdate


class MarketplaceService:
    def __init__(self, db: Session):
        self.db = db
        self.products = ProductRepository(db)
        self.orders = OrderRepository(db)

    def create_product(self, user: User, payload: ProductCreate):
        self._require_seller(user)
        return self.products.create(user.id, payload.model_dump())

    def update_product(self, user: User, product_id: int, payload: ProductUpdate):
        self._require_seller(user)
        product = self._owned_product(user, product_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            if value is not None:
                setattr(product, field, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def deactivate_product(self, user: User, product_id: int):
        self._require_seller(user)
        product = self._owned_product(user, product_id)
        product.is_active = False
        self.db.commit()
        return product

    def list_products(self, *, search: str | None, category: str | None, sort: str, page: int, limit: int):
        products = self.products.list_active(search=search, category=category, sort=sort)
        start = (page - 1) * limit
        return products[start : start + limit], len(products)

    def list_own_products(self, user: User):
        self._require_seller(user)
        return self.products.list_by_seller(user.id)

    def get_product(self, product_id: int, include_inactive: bool = False):
        product = self.products.get(product_id)
        if not product or (not include_inactive and (not product.is_active or product.quantity <= 0)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product

    def add_to_cart(self, user: User, payload: CartItemCreate):
        if user.role not in {"CONSUMER", "BULK_BUYER"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyers can use a cart")
        product = self.get_product(payload.product_id)
        if payload.quantity > product.quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested quantity exceeds available stock")
        item = self.db.scalar(select(CartItem).where(CartItem.buyer_id == user.id, CartItem.product_id == product.id))
        if item:
            if item.quantity + payload.quantity > product.quantity:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cart quantity exceeds available stock")
            item.quantity += payload.quantity
        else:
            item = CartItem(buyer_id=user.id, product_id=product.id, quantity=payload.quantity)
            self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_cart(self, user: User):
        items = self.orders.get_cart(user.id)
        total = Decimal("0")
        for item in items:
            product = self.products.get(item.product_id)
            if product:
                total += item.quantity * product.price_per_unit
        return items, total

    def create_order(self, user: User, payload: OrderCreate):
        if user.role not in {"CONSUMER", "BULK_BUYER"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyers can place orders")
        cart = self.orders.get_cart(user.id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        products = [self.get_product(item.product_id) for item in cart]
        seller_ids = {product.seller_id for product in products}
        if len(seller_ids) != 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart items must come from one seller")

        total = Decimal("0")
        order = Order(buyer_id=user.id, seller_id=products[0].seller_id, total_amount=0, shipping_address=payload.shipping_address)
        self.db.add(order)
        self.db.flush()
        for item, product in zip(cart, products):
            if item.quantity > product.quantity:
                self.db.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Insufficient stock for {product.name}")
            subtotal = item.quantity * product.price_per_unit
            total += subtotal
            product.quantity -= item.quantity
            if product.is_aggregated:
                self._consume_aggregated_inventory(product.id, item.quantity)
            self.db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, quantity=item.quantity, unit_price=product.price_per_unit, subtotal=subtotal))
            self.db.add(DemandObservation(observed_date=order.created_at.date(), product=product.name, location=order.shipping_address, quantity=item.quantity, price=product.price_per_unit, buyer_type=user.role, source="ORDER"))
            self.db.delete(item)
        order.total_amount = total
        self.db.add(Notification(user_id=order.seller_id, order_id=order.id, title="New order received", message=f"Order #{order.id} has been placed."))
        self.db.commit()
        return self.orders.get_order(order.id)

    def _consume_aggregated_inventory(self, aggregated_product_id: int, quantity: Decimal):
        allocations = self.db.scalars(
            select(FPOInventoryAllocation)
            .where(FPOInventoryAllocation.aggregated_product_id == aggregated_product_id)
            .order_by(FPOInventoryAllocation.id.asc())
        ).all()
        remaining = quantity
        for allocation in allocations:
            available = allocation.reserved_quantity - allocation.consumed_quantity
            if available <= 0:
                continue
            consumed = min(available, remaining)
            allocation.consumed_quantity += consumed
            remaining -= consumed
            if remaining <= 0:
                break
        if remaining > 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Aggregated allocation ledger is insufficient")

    def _owned_product(self, user: User, product_id: int):
        product = self.get_product(product_id, include_inactive=True)
        if product.seller_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this listing")
        return product

    @staticmethod
    def _require_seller(user: User):
        if user.role not in {"FARMER", "FPO"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only farmers and FPOs can manage listings")
