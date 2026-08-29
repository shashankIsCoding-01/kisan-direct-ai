from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.demand_forecasting import model_data_source, predict, train_and_persist
from app.models.user import User
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.forecast import DemandForecastRequest, DemandObservationCreate


class ForecastService:
    def __init__(self, db: Session):
        self.repository = ForecastRepository(db)

    def add_observation(self, user: User, payload: DemandObservationCreate):
        self._require_admin(user)
        return self.repository.create_observation(payload.model_dump())

    def train(self, user: User):
        self._require_admin(user)
        observations = self.repository.list_observations()
        rows = [{"observed_date": row.observed_date, "product": row.product, "location": row.location, "quantity": row.quantity, "price": row.price, "buyer_type": row.buyer_type, "source": row.source} for row in observations]
        try:
            result = train_and_persist(rows, settings.forecast_model_path)
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        self.repository.create_run({"model_name": result["model_name"], "training_rows": result["training_rows"], "data_source": result["data_source"], "mae": result["regression"]["mae"], "rmse": result["regression"]["rmse"], "mape": result["regression"]["mape"], "baseline_mae": result["baseline"]["mae"]})
        return result

    def forecast(self, user: User, payload: DemandForecastRequest):
        if user.role not in {"ADMIN", "BULK_BUYER"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins and bulk buyers can request forecasts")
        if not Path(settings.forecast_model_path).exists():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Train the demand model before requesting a forecast")
        try:
            points = predict(settings.forecast_model_path, payload.model_dump())
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        return {"model_name": "linear_regression", "product": payload.product, "location": payload.location, "forecast_period": f"{payload.days_ahead} days", "forecast": points, "data_source": model_data_source(settings.forecast_model_path), "uncertainty_supported": False, "limitations": ["Point predictions only; no confidence interval is implemented.", "Accuracy depends on the amount and coverage of historical order data.", "The model does not include weather, holidays, or external market signals."]}

    @staticmethod
    def _require_admin(user: User):
        if user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage forecast training data")
