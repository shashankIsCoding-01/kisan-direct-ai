from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_claims(
    token: str = Depends(oauth2_scheme),
) -> dict:
    claims = decode_access_token(token)
    if not claims or not claims.get("sub") or "token_version" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def get_database() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
    claims: dict = Depends(get_current_claims),
    db: Session = Depends(get_database),
) -> User:
    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError):
        user_id = None
    user = db.get(User, user_id) if user_id is not None else None
    if not user or not user.is_active or user.token_version != claims["token_version"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(claims: dict = Depends(get_current_claims)) -> dict:
        if claims.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return claims

    return dependency
