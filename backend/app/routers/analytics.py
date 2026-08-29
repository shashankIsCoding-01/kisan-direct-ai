from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsDefinitionsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboardResponse, summary="View operational impact analytics")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return AnalyticsService(db).dashboard(user)


@router.get("/definitions", response_model=AnalyticsDefinitionsResponse, summary="View analytics definitions")
def definitions():
    return AnalyticsService.definitions()
