from datetime import date, timedelta

import pytest

from app.ml.demand_forecasting import predict, train_and_persist, validate_observations


def observations(count=12, source="DEMO"):
    return [
        {
            "observed_date": date(2026, 1, 1) + timedelta(days=index),
            "product": "Tomato",
            "location": "Birbhum",
            "quantity": 10 + index,
            "price": 20,
            "buyer_type": "CONSUMER",
            "source": source,
        }
        for index in range(count)
    ]


def test_validation_rejects_missing_and_invalid_values():
    with pytest.raises(ValueError, match="Missing demand fields"):
        validate_observations([{"product": "Tomato"}])

    invalid = observations(1)
    invalid[0]["quantity"] = -1
    with pytest.raises(ValueError, match="quantity"):
        validate_observations(invalid)


def test_training_compares_baseline_and_persists_selected_model(tmp_path):
    model_path = tmp_path / "demand.joblib"

    result = train_and_persist(observations(), str(model_path))

    assert model_path.exists()
    assert result["training_rows"] == 12
    assert set(result["baseline"]) == {"mae", "rmse", "mape"}
    assert set(result["regression"]) == {"mae", "rmse", "mape"}
    assert result["data_source"] == "DEMO/SYNTHETIC"
    assert result["selected_model"] in {"linear_regression", "historical_mean_baseline"}

    forecast = predict(
        str(model_path),
        {
            "product": "Tomato",
            "location": "Birbhum",
            "buyer_type": "CONSUMER",
            "price": 20,
            "days_ahead": 3,
        },
    )
    assert len(forecast) == 3
    assert all(point["predicted_demand"] >= 0 for point in forecast)


def test_training_rejects_insufficient_data(tmp_path):
    with pytest.raises(ValueError, match="At least 8 observations"):
        train_and_persist(observations(7), str(tmp_path / "demand.joblib"))
