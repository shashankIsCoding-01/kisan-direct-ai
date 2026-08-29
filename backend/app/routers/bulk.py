from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.bulk import BulkMatchRead, BulkOrderPlacementRead, PurchaseRequirementCreate, PurchaseRequirementRead
from app.services.bulk_service import BulkService

router = APIRouter(prefix="/bulk-requirements", tags=["bulk buyer"])


@router.post("", response_model=PurchaseRequirementRead, status_code=status.HTTP_201_CREATED, summary="Create a bulk purchase requirement")
def create_requirement(payload: PurchaseRequirementCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return BulkService(db).create_requirement(user, payload)


@router.get("", response_model=list[PurchaseRequirementRead], summary="View purchase requirements")
def list_requirements(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return BulkService(db).list_requirements(user)


@router.get("/{requirement_id}", response_model=PurchaseRequirementRead, summary="View a purchase requirement")
def get_requirement(requirement_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return BulkService(db).get_requirement(user, requirement_id)


@router.post("/{requirement_id}/match", response_model=BulkMatchRead, summary="Match a requirement with live supply")
def match_requirement(requirement_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return BulkService(db).match(user, requirement_id)


@router.post("/{requirement_id}/place-orders", response_model=BulkOrderPlacementRead, summary="Place orders for the current live match")
def place_orders(requirement_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return BulkService(db).place_orders(user, requirement_id)
