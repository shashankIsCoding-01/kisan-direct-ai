from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.marketplace import ProductCreate, ProductList, ProductRead, ProductUpdate, SortOption
from app.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductList, summary="Browse active products")
def browse_products(
    search: str | None = Query(default=None, min_length=1, max_length=80),
    category: str | None = Query(default=None, min_length=1, max_length=80),
    sort: SortOption = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_database),
):
    items, total = MarketplaceService(db).list_products(
        search=search, category=category, sort=sort, page=page, limit=limit
    )
    return ProductList(items=items, total=total, page=page, limit=limit)


@router.get("/mine", response_model=list[ProductRead], summary="View the current seller's listings")
def own_products(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return MarketplaceService(db).list_own_products(user)


@router.get("/{product_id}", response_model=ProductRead, summary="View product details")
def product_details(product_id: int, db: Session = Depends(get_database)):
    return MarketplaceService(db).get_product(product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED, summary="Create a product listing")
def create_product(
    payload: ProductCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return MarketplaceService(db).create_product(user, payload)


@router.patch("/{product_id}", response_model=ProductRead, summary="Edit a product listing")
def update_product(
    product_id: int,
    payload: ProductUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return MarketplaceService(db).update_product(user, product_id, payload)


@router.delete("/{product_id}", response_model=ProductRead, summary="Deactivate a product listing")
def deactivate_product(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    return MarketplaceService(db).deactivate_product(user, product_id)
