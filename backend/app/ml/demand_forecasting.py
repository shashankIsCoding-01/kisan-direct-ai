import math
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path

MIN_TRAINING_ROWS = 8


def validate_observations(rows: list[dict]) -> list[dict]:
    required = {"observed_date", "product", "location", "quantity", "price", "buyer_type"}
    if not rows:
        raise ValueError("At least one demand observation is required")
    validated = []
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"Missing demand fields: {', '.join(sorted(missing))}")
        try:
            observed_date = row["observed_date"] if isinstance(row["observed_date"], date) else date.fromisoformat(str(row["observed_date"]))
            quantity = float(row["quantity"])
            price = float(row["price"])
        except (TypeError, ValueError) as error:
            raise ValueError("Demand dates, quantities, and prices must be valid") from error
        if not all(str(row[field]).strip() for field in ["product", "location", "buyer_type"]):
            raise ValueError("Product, location, and buyer type are required")
        if quantity < 0 or price <= 0:
            raise ValueError("quantity must be non-negative and price must be positive")
        validated.append({**row, "observed_date": observed_date, "quantity": quantity, "price": price})
    return sorted(validated, key=lambda row: row["observed_date"])


def _features(row: dict, origin: date) -> tuple[float, float, float, float, float]:
    observed_date = row["observed_date"]
    return (float((observed_date - origin).days), float(row["price"]), float(observed_date.weekday()), float(observed_date.day), float(observed_date.month))


def _fit_linear(rows: list[dict], origin: date) -> tuple[float, ...]:
    # Coordinate-wise least squares keeps this MVP dependency-free and explainable.
    features = [_features(row, origin) for row in rows]
    means = [sum(values[index] for values in features) / len(features) for index in range(5)]
    target_mean = sum(row["quantity"] for row in rows) / len(rows)
    coefficients = []
    for index in range(5):
        numerator = sum((values[index] - means[index]) * (row["quantity"] - target_mean) for values, row in zip(features, rows))
        denominator = sum((values[index] - means[index]) ** 2 for values in features)
        coefficients.append(numerator / denominator if denominator else 0.0)
    intercept = target_mean - sum(coefficient * mean for coefficient, mean in zip(coefficients, means))
    return (intercept, *coefficients)


def _predict_row(row: dict, origin: date, coefficients: tuple[float, ...]) -> float:
    intercept, *slopes = coefficients
    return max(0.0, intercept + sum(slope * value for slope, value in zip(slopes, _features(row, origin))))


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    errors = [actual_value - predicted_value for actual_value, predicted_value in zip(actual, predicted)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mape = sum(abs(error) / (actual_value if actual_value else 1.0) for error, actual_value in zip(errors, actual)) / len(errors) * 100
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 4)}


def train_and_persist(rows: list[dict], model_path: str) -> dict:
    validated = validate_observations(rows)
    if len(validated) < MIN_TRAINING_ROWS:
        raise ValueError(f"At least {MIN_TRAINING_ROWS} observations are required; received {len(validated)}")
    split = max(1, len(validated) // 5)
    train_rows, test_rows = validated[:-split], validated[-split:]
    origin = validated[0]["observed_date"]
    coefficients = _fit_linear(train_rows, origin)
    actual = [row["quantity"] for row in test_rows]
    regression = [_predict_row(row, origin, coefficients) for row in test_rows]
    mean_value = sum(row["quantity"] for row in train_rows) / len(train_rows)
    baseline = [mean_value] * len(test_rows)
    baseline_metrics = _metrics(actual, baseline)
    regression_metrics = _metrics(actual, regression)
    selected_model = "linear_regression" if regression_metrics["mae"] <= baseline_metrics["mae"] else "historical_mean_baseline"
    sources = {row.get("source", "REAL/ORDER_DATA") for row in validated}
    data_source = "DEMO/SYNTHETIC" if sources == {"DEMO"} else "REAL/ORDER_DATA"
    artifact = {"coefficients": coefficients, "baseline": sum(row["quantity"] for row in validated) / len(validated), "origin": origin, "last_date": validated[-1]["observed_date"], "selected_model": selected_model, "data_source": data_source}
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(model_path).open("wb") as model_file:
        pickle.dump(artifact, model_file)
    return {"model_name": "linear_regression", "training_rows": len(validated), "data_source": data_source, "baseline": baseline_metrics, "regression": regression_metrics, "selected_model": selected_model}


def predict(model_path: str, request: dict) -> list[dict]:
    with Path(model_path).open("rb") as model_file:
        artifact = pickle.load(model_file)
    if request.get("price") is None:
        raise ValueError("price is required for regression prediction")
    start = request.get("start_date") or (artifact["last_date"] + timedelta(days=1))
    if isinstance(start, str):
        start = date.fromisoformat(start)
    points = []
    for index in range(request["days_ahead"]):
        forecast_date = start + timedelta(days=index)
        row = {"observed_date": forecast_date, "product": request["product"], "location": request["location"], "price": float(request["price"]), "buyer_type": request["buyer_type"]}
        predicted = artifact["baseline"] if artifact["selected_model"] == "historical_mean_baseline" else _predict_row(row, artifact["origin"], artifact["coefficients"])
        points.append({"date": forecast_date, "predicted_demand": round(predicted, 2)})
    return points


def model_data_source(model_path: str) -> str:
    with Path(model_path).open("rb") as model_file:
        return pickle.load(model_file)["data_source"]
