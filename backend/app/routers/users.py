from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, summary="Get the authenticated user")
def current_user(user: User = Depends(get_current_user)):
    return user


@router.get("/admin-check", response_model=MessageResponse)
def admin_check(claims: dict = Depends(require_roles("admin"))):
    return MessageResponse(message=f"Admin access granted for user: {claims['sub']}")
