from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.marketplace import CartItemCreate, CartRead
from app.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead, summary="View the current buyer's cart")
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    items, total = MarketplaceService(db).get_cart(user)
    return CartRead(items=items, total_amount=total)


@router.post("/items", status_code=status.HTTP_201_CREATED, summary="Add a product to the cart")
def add_to_cart(
    payload: CartItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return MarketplaceService(db).add_to_cart(user, payload)
