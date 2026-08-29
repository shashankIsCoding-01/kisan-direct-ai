from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def register(self, payload: UserCreate):
        email = payload.email.lower()
        if payload.role in {"ADMIN", "LOGISTICS"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role can only be assigned by an administrator",
            )
        if self.users.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = self.users.create(
            email=email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=payload.role,
        )
        token = create_access_token(str(user.id), user.role, user.token_version)
        return user, token

    def login(self, payload: LoginRequest):
        user = self.users.get_by_email(payload.email.lower())
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive",
            )

        return create_access_token(str(user.id), user.role, user.token_version)

    def logout(self, user):
        self.users.increment_token_version(user)

    @staticmethod
    def token_expiry_seconds() -> int:
        return settings.access_token_expire_minutes * 60
