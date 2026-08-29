# KisanDirect AI — AI/ML Architecture

## Overview

The AI layer handles **demand forecasting** and **route optimization**. Both are designed to be explainable and measurable.

> **AI Principle (per project rules):**  
> Do not call an algorithm "AI" merely for marketing. Clearly distinguish ML from statistical forecasting, optimization, and rule-based logic.

---

## 1. Demand Forecasting

### Problem

Predict future demand for agricultural products per region to help:
- Farmers decide what to grow
- FPOs plan aggregation
- Bulk buyers plan purchases
- Admins plan logistics

### Data Sources

| Source | Data |
|--------|------|
| Order history | Quantities sold per product per day |
| Seasonality | Calendar features (month, day of week) |
| Price | Average selling price per product |
| Location | Region/state from address |

### Feature Engineering

```python
features = [
    "product_name",        # Categorical → one-hot encoded
    "region",              # Categorical → one-hot encoded
    "day_of_week",         # 0-6 (Monday-Sunday)
    "day_of_month",        # 1-31
    "month",               # 1-12
    "is_holiday",          # Boolean
    "price_lag_7",         # Price 7 days ago
    "demand_lag_7",        # Demand 7 days ago
    "demand_lag_14",       # Demand 14 days ago
    "rolling_mean_7",      # 7-day rolling average
    "rolling_std_7",      # 7-day rolling std
]
```

### Models (MVP → Future)

#### MVP: Historical Mean + Linear Regression
```
Baseline: Historical mean demand
Model: Linear regression over date, price, product, location, and buyer type
Why: Both are interpretable and provide a measurable baseline comparison
Input: Validated order-derived observations
Output: Demand quantity for each day
Evaluation: MAE, RMSE, and MAPE on a chronological hold-out
```

The current implementation uses a small standard-library pipeline so it can run on
the Windows ARM64 development environment without native scientific Python wheels.
It persists the selected model with `pickle`. Pandas/scikit-learn or a time-series
library can be evaluated later when the dataset justifies the additional dependency.

#### Future: Random Forest / XGBoost
```
Why: Handles non-linear relationships, feature importance
When: More training data available
```

#### Future: Prophet (Facebook)
```
Why: Built-in seasonality handling
When: Time series patterns are complex
```

### Evaluation Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| MAPE | mean(\|actual - predicted\| / actual) × 100 | < 20% for MVP |
| MAE | mean(\|actual - predicted\|) | Context-dependent |
| RMSE | sqrt(mean((actual - predicted)²)) | Context-dependent |

> **Important:** Demand forecasting must be evaluated using appropriate metrics. We use MAPE as the primary metric since it is scale-independent and commonly used in demand forecasting.

### API Endpoint

```
POST /api/v1/ai/demand-forecast/
Request: { product_name, region, days_ahead }
Response: { forecast: [{date, predicted_demand}], model_used, data_source, limitations }
```

### Implementation Path

```
1. Collect historical order data (MVP can use synthetic data)
2. Engineer features using Pandas
3. Train Linear Regression with Scikit-learn
4. Evaluate with MAPE on hold-out set
5. Expose via FastAPI endpoint
6. Display on admin dashboard
```

---

## 2. Route Optimization

### Problem

Optimize delivery routes for logistics operators to:
- Minimize total travel distance
- Reduce fuel costs
- Speed up deliveries
- Improve farmer and buyer satisfaction

### Approach

#### MVP: Nearest Neighbor Heuristic
```
Algorithm: 
1. Start at depot
2. Find nearest unvisited stop → go there
3. Repeat until all stops visited
4. Return to depot

Why: Simple, fast, acceptable for small number of stops
Limitation: Not guaranteed to be optimal
```

#### Future: Traveling Salesman Problem (Held-Karp)
```
Algorithm: Dynamic programming solution
Benefit: Optimal solution for small instances (≤15 stops)
When: Pilot phase with limited deliveries
```

#### Future: Vehicle Routing Problem (VPR)
```
Algorithm: OR-Tools or custom implementation
Benefit: Handles capacity constraints, time windows
When: Scaled operations
```

### Data Model

```python
Stop:
    - order_id: UUID
    - location: (lat, lng)
    - priority: int (1 = highest)
    - time_window: (start, end)  # Future

Route:
    - stops: List[Stop]
    - total_distance_km: float
    - estimated_duration_min: int
    - waypoint_order: List[UUID]  # Stop IDs in order
```

### Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Total distance (baseline) | Sum of distances without optimization | Record |
| Total distance (optimized) | Sum after optimization | 10-30% reduction |
| Distance reduction % | (baseline - optimized) / baseline × 100 | > 10% |
| Computation time | Time to generate route | < 1 second |

> **Important:** Route optimization must show measurable baseline-versus-optimized results. The MVP will compare nearest-neighbor against random route ordering.

### API Endpoint

```
POST /api/v1/logistics/optimize/
Request: { assignment_ids: [uuid, uuid, ...] }
Response: { 
    route: { waypoints: [...], total_distance_km, estimated_minutes },
    baseline_distance_km,
    improvement_percent 
}
```

### Map Visualization

- Use **Leaflet + OpenStreetMap** (no API key needed)
- Display route as polyline
- Show markers for each stop with order info
- Highlight optimized vs original route

---

## 3. AI Module Structure

```
backend/app/
├── ml/
│   ├── __init__.py
│   ├── demand_model.py      # Demand forecasting
│   │   ├── prepare_features()
│   │   ├── train_model()
│   │   ├── predict()
│   │   └── evaluate()
│   └── route_optimizer.py   # Route optimization
│       ├── nearest_neighbor()
│       ├── calculate_distance()
│       └── optimize()
├── services/
│   ├── demand_forecast.py   # API service layer
│   └── route_service.py     # API service layer
└── routers/
    └── ai.py                 # API routes
```

---

## 4. Data Requirements

### For Demand Forecasting MVP

| Data | Source | Required |
|------|--------|----------|
| Historical orders | orders table | Yes |
| Product categories | categories table | Yes |
| Region/location | addresses table | Yes |
| Price per order | order_items table | Yes |
| Date/time | orders.created_at | Yes |

> **Note:** If historical data is insufficient (early stage), use **synthetic data** for training and clearly label it as synthetic in the UI. Never present synthetic data as real data.

### For Route Optimization

| Data | Source | Required |
|------|--------|----------|
| Delivery addresses | addresses table | Yes |
| Coordinates | addresses (lat/lng) | Yes |
| Order priorities | orders table | Optional |
| Time windows | N/A | Future |

---

## 5. Synthetic Data Strategy

For MVP demo, generate synthetic order history:

```python
# Example: Generate 90 days of synthetic demand
import pandas as pd
import numpy as np

dates = pd.date_range("2026-05-01", periods=90, freq="D")
for product in ["tomato", "potato", "onion", "wheat", "rice"]:
    base_demand = np.random.randint(50, 200)
    seasonality = 1 + 0.2 * np.sin(2 * np.pi * dates.dayofyear / 365)
    noise = np.random.normal(1, 0.1, 90)
    demand = base_demand * seasonality * noise
```

> **Critical:** Clearly label synthetic data in UI with a badge "Demo Data" and in API responses with `"is_synthetic": true`.

---

## 6. Future AI Features

| Feature | Description | Priority |
|---------|-------------|----------|
| Price prediction | Predict future prices based on supply | Future |
| Crop suggestion | Recommend crops based on soil + weather | Future |
| Quality classification | Image-based quality grading | Future |
| Churn prediction | Identify at-risk farmers/buyers | Future |
| Fraud detection | Anomaly detection in orders | Future |

---

## 7. Model Deployment

### MVP (SIH Demo)
```
Training: Offline in Python script
Storage:  Pickle files in /models/
Loading:  Load on FastAPI startup
Updates:  Manual retraining
```

### Future (Production)
```
Training: Scheduled retraining (weekly/monthly)
Storage:  Model registry (MLflow, DVC)
Serving:  FastAPI + background tasks
Monitoring: Track prediction accuracy over time
```

---

## 8. Explainability

Every ML prediction must include:

1. **Model name** — Which algorithm was used
2. **Confidence** — Accuracy metric (MAPE for forecasting)
3. **Features used** — Top contributing features
4. **Data period** — Training data range
5. **Synthetic flag** — Whether training data was synthetic

```json
{
  "prediction": 135,
  "model_used": "linear_regression",
  "accuracy_mape": 12.5,
  "confidence": "medium",
  "features_top_3": ["demand_lag_7", "month", "price_lag_7"],
  "training_data_days": 90,
  "is_synthetic": false
}
```
