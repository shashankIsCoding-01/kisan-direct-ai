from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsDefinitionsResponse, MetricValue


class AnalyticsService:
    def __init__(self, db: Session):
        self.repository = AnalyticsRepository(db)

    def dashboard(self, user: User) -> AnalyticsDashboardResponse:
        self._require_admin(user)
        orders = self.repository.orders()
        non_cancelled = [order for order in orders if order.status != "CANCELLED"]
        completed_items = self.repository.delivered_order_items()
        completed_value = sum((order.total_amount for order in orders if order.status == "DELIVERED"), Decimal("0"))
        total_quantity = sum((item.quantity for item, _ in completed_items), Decimal("0"))
        total_revenue = sum((item.subtotal for item, _ in completed_items), Decimal("0"))
        routes_demo = self.repository.routes(True)
        routes_actual = self.repository.routes(False)
        latest_actual_forecast = self.repository.latest_forecast_run("REAL/ORDER_DATA")
        latest_demo_forecast = self.repository.latest_forecast_run("DEMO/SYNTHETIC")

        actual = {
            "registered_farmers": self._metric(self.repository.count_users("FARMER"), "users", "COUNT users WHERE role = FARMER"),
            "active_fpos": self._metric(self.repository.count_active_fpos(), "FPOs", "COUNT DISTINCT FPOs with at least one active farmer membership"),
            "active_buyers": self._metric(self.repository.count_users("BULK_BUYER", True), "users", "COUNT active users WHERE role = BULK_BUYER"),
            "active_consumers": self._metric(self.repository.count_users("CONSUMER", True), "users", "COUNT active users WHERE role = CONSUMER"),
            "products_listed": self._metric(self.repository.count_products(), "products", "COUNT products WHERE is_active = true"),
            "orders": self._metric(len(non_cancelled), "orders", "COUNT orders WHERE status != CANCELLED"),
            "transaction_value": self._metric(completed_value, "currency", "SUM total_amount WHERE order status = DELIVERED"),
            "farmer_realization": self._metric(total_revenue / total_quantity if total_quantity else None, "currency per unit", "SUM delivered order-item subtotals / SUM delivered order-item quantities"),
            "consumer_price": self._metric(total_revenue / total_quantity if total_quantity else None, "currency per unit", "Average paid unit price across delivered order items"),
            "logistics_distance": self._route_metric(routes_actual, "total_distance_km", "km", "SUM optimized route distance for non-demo routes", "REAL/ROAD_DATA"),
            "baseline_route_distance": self._route_metric(routes_actual, "baseline_distance_km", "km", "SUM baseline distance for non-demo routes", "REAL/ROAD_DATA"),
            "optimized_route_distance": self._route_metric(routes_actual, "total_distance_km", "km", "SUM optimized distance for non-demo routes", "REAL/ROAD_DATA"),
            "distance_reduction": self._distance_reduction(routes_actual, "REAL/ROAD_DATA"),
            "forecast_mae": self._forecast_metric(latest_actual_forecast, "mae", "units", "Latest persisted MAE from REAL/ORDER_DATA forecast holdout"),
            "forecast_rmse": self._forecast_metric(latest_actual_forecast, "rmse", "units", "Latest persisted RMSE from REAL/ORDER_DATA forecast holdout"),
            "forecast_mape": self._forecast_metric(latest_actual_forecast, "mape", "%", "Latest persisted MAPE from REAL/ORDER_DATA forecast holdout"),
        }
        demo = {
            "logistics_distance": self._route_metric(routes_demo, "total_distance_km", "km", "SUM optimized route distance for demo straight-line routes", "DEMO/HAVERSINE"),
            "baseline_route_distance": self._route_metric(routes_demo, "baseline_distance_km", "km", "SUM baseline distance for demo straight-line routes", "DEMO/HAVERSINE"),
            "optimized_route_distance": self._route_metric(routes_demo, "total_distance_km", "km", "SUM optimized distance for demo straight-line routes", "DEMO/HAVERSINE"),
            "distance_reduction": self._distance_reduction(routes_demo, "DEMO/HAVERSINE"),
            "forecast_mae": self._forecast_metric(latest_demo_forecast, "mae", "units", "Latest persisted MAE from DEMO/SYNTHETIC holdout"),
            "forecast_rmse": self._forecast_metric(latest_demo_forecast, "rmse", "units", "Latest persisted RMSE from DEMO/SYNTHETIC holdout"),
            "forecast_mape": self._forecast_metric(latest_demo_forecast, "mape", "%", "Latest persisted MAPE from DEMO/SYNTHETIC holdout"),
        }
        estimates = {name: MetricValue(value=None, unit=None, source="NOT_AVAILABLE", calculation="No defensible estimate input exists in the repository") for name in ["farmer_income_impact", "consumer_price_reduction", "intermediaries_reduced", "fuel_cost_savings"]}
        return AnalyticsDashboardResponse(actual=actual, demo=demo, estimates=estimates, generated_at=datetime.now(timezone.utc).isoformat(), limitations=["Farmer realization and consumer price are paid delivered-order unit prices; no external market-price baseline exists.", "Non-demo road-network route metrics are unavailable unless a road routing provider is configured.", "No causal impact estimate is calculated from platform data.", "Empty metrics mean the repository has no qualifying records, not zero real-world impact."])

    @staticmethod
    def definitions() -> AnalyticsDefinitionsResponse:
        return AnalyticsDefinitionsResponse(definitions={
            "registered_farmers": "All users with role FARMER.",
            "active_fpos": "Distinct FPOs with at least one active membership.",
            "active_buyers": "Active users with role BULK_BUYER.",
            "active_consumers": "Active users with role CONSUMER.",
            "products_listed": "Active product listings.",
            "orders": "Orders excluding CANCELLED orders.",
            "transaction_value": "Delivered order total value.",
            "farmer_realization": "Delivered item revenue divided by delivered quantity; not a market-price comparison.",
            "consumer_price": "Average paid unit price on delivered items; not a consumer savings estimate.",
            "logistics_distance": "Sum of optimized route distance, separated by actual or demo provenance.",
            "distance_reduction": "(Baseline route distance - optimized route distance) / baseline route distance * 100.",
            "forecast_metrics": "Latest persisted MAE, RMSE, and MAPE from a chronological holdout.",
        })

    @staticmethod
    def _metric(value, unit, calculation, source="ACTUAL/PLATFORM_DATA"):
        return MetricValue(value=value, unit=unit, source=source, calculation=calculation)

    def _route_metric(self, routes, field, unit, calculation, source):
        value = sum((getattr(route, field) for route in routes), Decimal("0"))
        return self._metric(value if routes else None, unit, calculation, source)

    def _distance_reduction(self, routes, source):
        if not routes:
            return self._metric(None, "%", source, "No qualifying routes")
        baseline = sum((route.baseline_distance_km for route in routes), Decimal("0"))
        optimized = sum((route.total_distance_km for route in routes), Decimal("0"))
        value = (baseline - optimized) / baseline * 100 if baseline else Decimal("0")
        return self._metric(value, "%", "(SUM baseline - SUM optimized) / SUM baseline * 100", source)

    def _forecast_metric(self, run, field, unit, calculation):
        return self._metric(getattr(run, field) if run else None, unit, calculation, run.data_source if run else "NOT_AVAILABLE")

    @staticmethod
    def _require_admin(user: User):
        if user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view platform analytics")
