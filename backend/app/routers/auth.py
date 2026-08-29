from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterResponse, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_database)):
    user, token = AuthService(db).register(payload)
    return RegisterResponse(
        user=user,
        access_token=token,
        expires_in=AuthService.token_expiry_seconds(),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_database)):
    token = AuthService(db).login(payload)
    return TokenResponse(
        access_token=token,
        expires_in=AuthService.token_expiry_seconds(),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    AuthService(db).logout(user)
    return MessageResponse(message="Logged out successfully")
