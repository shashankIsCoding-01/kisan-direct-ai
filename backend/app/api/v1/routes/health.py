from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Check API availability")
def health_check():
    return {"status": "ok", "service": "kisan-direct-ai-backend", "database": "not_checked"}
