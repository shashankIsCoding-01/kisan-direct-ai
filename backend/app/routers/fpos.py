from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.fpo import (
    AggregationRequest,
    FPOAnalytics,
    FPOCreate,
    FPOInventoryRead,
    FPOMemberCreate,
    FPOMemberRead,
    FPORead,
)
from app.schemas.marketplace import OrderRead, ProductRead
from app.services.fpo_service import FPOService

router = APIRouter(prefix="/fpos", tags=["fpos"])


@router.post("", response_model=FPORead, status_code=status.HTTP_201_CREATED, summary="Create an FPO profile")
def create_fpo(payload: FPOCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).create_fpo(user, payload)


@router.get("/mine", response_model=FPORead, summary="View the current user's FPO profile")
def my_fpo(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).my_fpo(user)


@router.get("/{fpo_id}/members", response_model=list[FPOMemberRead], summary="List FPO members")
def list_members(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).members(user, fpo_id)


@router.post("/{fpo_id}/members", response_model=FPOMemberRead, status_code=status.HTTP_201_CREATED, summary="Add a farmer member")
def add_member(fpo_id: int, payload: FPOMemberCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).add_member(user, fpo_id, payload)


@router.delete("/{fpo_id}/members/{farmer_id}", response_model=FPOMemberRead, summary="Deactivate a farmer membership")
def remove_member(fpo_id: int, farmer_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).remove_member(user, fpo_id, farmer_id)


@router.get("/{fpo_id}/inventory", response_model=FPOInventoryRead, summary="View active member inventory")
def member_inventory(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOInventoryRead(items=FPOService(db).farmer_inventory(user, fpo_id))


@router.post("/{fpo_id}/aggregate", response_model=ProductRead, status_code=status.HTTP_201_CREATED, summary="Reserve member produce into an aggregated listing")
def aggregate_produce(fpo_id: int, payload: AggregationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).aggregate(user, fpo_id, payload)


@router.get("/{fpo_id}/listings", response_model=list[ProductRead], summary="View aggregated listings")
def aggregated_listings(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).listings(user, fpo_id)


@router.get("/{fpo_id}/orders", response_model=list[OrderRead], summary="Manage FPO bulk orders")
def fpo_orders(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).orders(user, fpo_id)


@router.get("/{fpo_id}/analytics", response_model=FPOAnalytics, summary="View FPO revenue analytics")
def fpo_analytics(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).analytics(user, fpo_id)


@router.get("/{fpo_id}", response_model=FPORead, summary="View an FPO profile")
def fpo_details(fpo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return FPOService(db).get_owned_fpo(user, fpo_id)
