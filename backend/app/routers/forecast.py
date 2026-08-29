from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_database
from app.models.user import User
from app.schemas.forecast import DemandForecastRequest, DemandForecastResponse, DemandObservationCreate, DemandObservationRead, ForecastTrainResponse
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["demand forecasting"])


@router.post("/observations", response_model=DemandObservationRead, status_code=status.HTTP_201_CREATED)
def add_observation(payload: DemandObservationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return ForecastService(db).add_observation(user, payload)


@router.post("/train", response_model=ForecastTrainResponse)
def train_model(user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return ForecastService(db).train(user)


@router.post("/predict", response_model=DemandForecastResponse)
def forecast(payload: DemandForecastRequest, user: User = Depends(get_current_user), db: Session = Depends(get_database)):
    return ForecastService(db).forecast(user, payload)
