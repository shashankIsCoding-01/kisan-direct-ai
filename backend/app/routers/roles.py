from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_claims


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(claims: dict = Depends(get_current_claims)) -> dict:
        if claims.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return claims

    return dependency
