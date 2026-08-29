from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forecast import DemandObservation, ForecastRun


class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_observations(self):
        return self.db.scalars(select(DemandObservation).order_by(DemandObservation.observed_date.asc())).all()

    def create_observation(self, values: dict):
        observation = DemandObservation(**values)
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def create_run(self, values: dict):
        run = ForecastRun(**values)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
