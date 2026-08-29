"""
test_demand_forecasting_comprehensive.py
────────────────────────────────────────
Comprehensive test coverage for Demand Forecasting ML service and APIs.
"""

import os
from datetime import date, timedelta
from pathlib import Path
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.ml.demand_forecasting import model_data_source, predict, train_and_persist, validate_observations
from app.models.user import User
from app.schemas.forecast import DemandForecastRequest, DemandObservationCreate
from app.services.forecast_service import ForecastService
from tests.conftest import auth_headers, make_user_in_db, register_user, token_for


def _db(client):
    from app.main import app
    return app.state.session_local()


def _sample_observations(count: int = 12, product: str = "Tomato", location: str = "Birbhum", source: str = "DEMO") -> list[dict]:
    return [
        {
            "observed_date": date(2026, 1, 1) + timedelta(days=i),
            "product": product,
            "location": location,
            "quantity": 10 + (i * 2),
            "price": 25.0,
            "buyer_type": "BULK_BUYER",
            "source": source,
        }
        for i in range(count)
    ]


class TestForecastMLUnit:
    """BR-FC-05 through BR-FC-08"""

    def test_validation_rejects_missing_fields(self):
        """BR-FC-06"""
        with pytest.raises(ValueError, match="Missing demand fields"):
            validate_observations([{"product": "Tomato", "location": "Birbhum"}])

    def test_validation_rejects_negative_quantity(self):
        """BR-FC-07"""
        obs = _sample_observations(1)
        obs[0]["quantity"] = -5
        with pytest.raises(ValueError, match="quantity"):
            validate_observations(obs)

    def test_validation_rejects_zero_or_negative_price(self):
        """BR-FC-07"""
        obs = _sample_observations(1)
        obs[0]["price"] = 0
        with pytest.raises(ValueError, match="price"):
            validate_observations(obs)

    def test_training_fails_with_insufficient_data(self, tmp_path):
        """BR-FC-05"""
        model_file = str(tmp_path / "underflow.joblib")
        with pytest.raises(ValueError, match="At least 8 observations"):
            train_and_persist(_sample_observations(count=5), model_file)

    def test_training_persists_model_and_calculates_metrics(self, tmp_path):
        """BR-FC-09"""
        model_file = str(tmp_path / "trained_model.joblib")
        result = train_and_persist(_sample_observations(count=15), model_file)
        
        assert Path(model_file).exists()
        assert result["training_rows"] == 15
        assert "mae" in result["regression"]
        assert "rmse" in result["regression"]
        assert "mape" in result["regression"]
        assert result["data_source"] == "DEMO/SYNTHETIC"

        # Predict
        preds = predict(
            model_file,
            {"product": "Tomato", "location": "Birbhum", "buyer_type": "BULK_BUYER", "price": 25.0, "days_ahead": 5},
        )
        assert len(preds) == 5
        assert all(p["predicted_demand"] >= 0 for p in preds)


class TestForecastAPI:
    """BR-FC-01 through BR-FC-04"""

    def test_farmer_cannot_add_observation(self, client):
        """BR-FC-01"""
        farmer = register_user(client, "fc_farmer@example.com", "FARMER")
        resp = client.post(
            "/api/v1/forecast/observations",
            headers=auth_headers(farmer["access_token"]),
            json={"observed_date": "2026-01-01", "product": "Tomato", "location": "Birbhum", "quantity": 10, "price": 20, "buyer_type": "CONSUMER", "source": "IMPORTED"},
        )
        assert resp.status_code == 403

    def test_consumer_cannot_train_model(self, client):
        """BR-FC-02"""
        consumer = register_user(client, "fc_consumer@example.com", "CONSUMER")
        resp = client.post("/api/v1/forecast/train", headers=auth_headers(consumer["access_token"]))
        assert resp.status_code == 403

    def test_farmer_cannot_request_forecast(self, client):
        """BR-FC-03"""
        farmer = register_user(client, "fc_farmer2@example.com", "FARMER")
        resp = client.post(
            "/api/v1/forecast/predict",
            headers=auth_headers(farmer["access_token"]),
            json={"product": "Tomato", "location": "Birbhum", "buyer_type": "BULK_BUYER", "price": 25, "days_ahead": 7},
        )
        assert resp.status_code == 403

    def test_missing_model_file_raises_409(self, client, monkeypatch, tmp_path):
        """BR-FC-04"""
        db = _db(client)
        admin = make_user_in_db(db, "fc_admin@example.com", "ADMIN")
        admin_token = create_access_token(str(admin.id), "ADMIN", admin.token_version)
        db.close()

        monkeypatch.setattr(settings, "forecast_model_path", str(tmp_path / "non_existent_model.joblib"))

        resp = client.post(
            "/api/v1/forecast/predict",
            headers=auth_headers(admin_token),
            json={"product": "Tomato", "location": "Birbhum", "buyer_type": "BULK_BUYER", "price": 25, "days_ahead": 7},
        )
        assert resp.status_code == 409
        assert "Train the demand model" in resp.json()["detail"]

    def test_admin_train_and_bulk_buyer_forecast_flow(self, client, monkeypatch, tmp_path):
        db = _db(client)
        admin = make_user_in_db(db, "flow_admin@example.com", "ADMIN")
        admin_token = create_access_token(str(admin.id), "ADMIN", admin.token_version)
        db.close()

        model_path = str(tmp_path / "flow_model.joblib")
        monkeypatch.setattr(settings, "forecast_model_path", model_path)

        admin_hdrs = auth_headers(admin_token)
        for i in range(10):
            obs_resp = client.post(
                "/api/v1/forecast/observations",
                headers=admin_hdrs,
                json={"observed_date": f"2026-01-{i+1:02d}", "product": "Potato", "location": "Birbhum", "quantity": 10 + i, "price": 20.0, "buyer_type": "BULK_BUYER", "source": "IMPORTED"},
            )
            assert obs_resp.status_code == 201

        train_resp = client.post("/api/v1/forecast/train", headers=admin_hdrs)
        assert train_resp.status_code == 200
        assert train_resp.json()["training_rows"] == 10

        buyer = register_user(client, "flow_buyer@example.com", "BULK_BUYER")
        fc_resp = client.post(
            "/api/v1/forecast/predict",
            headers=auth_headers(buyer["access_token"]),
            json={"product": "Potato", "location": "Birbhum", "buyer_type": "BULK_BUYER", "price": 22.0, "days_ahead": 3},
        )
        assert fc_resp.status_code == 200
        data = fc_resp.json()
        assert len(data["forecast"]) == 3
        assert data["product"] == "Potato"
