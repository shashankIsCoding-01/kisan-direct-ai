from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.forecast import ForecastRun
from app.models.marketplace import DeliveryLocation, FPO, FPOMember, Order, OrderItem, Product, Route, Vehicle
from app.models.user import User
from app.services.analytics_service import AnalyticsService


def test_dashboard_calculates_actual_demo_and_unavailable_metrics():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = User(email="analytics-admin@example.com", password_hash="unused", full_name="Admin", role="ADMIN", is_active=True)
    farmer = User(email="analytics-farmer@example.com", password_hash="unused", full_name="Farmer", role="FARMER", is_active=True)
    consumer = User(email="analytics-consumer@example.com", password_hash="unused", full_name="Consumer", role="CONSUMER", is_active=True)
    buyer = User(email="analytics-buyer@example.com", password_hash="unused", full_name="Buyer", role="BULK_BUYER", is_active=True)
    fpo_user = User(email="analytics-fpo@example.com", password_hash="unused", full_name="FPO", role="FPO", is_active=True)
    db.add_all([admin, farmer, consumer, buyer, fpo_user])
    db.flush()
    fpo = FPO(owner_user_id=fpo_user.id, name="Analytics FPO", address="Farm Road")
    db.add(fpo)
    db.flush()
    db.add(FPOMember(fpo_id=fpo.id, farmer_id=farmer.id, is_active=True))
    db.add(Product(seller_id=farmer.id, name="Tomato", category="Vegetables", quality="STANDARD", unit="kg", price_per_unit=25, quantity=10, is_active=True))
    db.flush()
    order = Order(buyer_id=consumer.id, seller_id=farmer.id, status="DELIVERED", total_amount=50, shipping_address="Town", items=[])
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, product_id=1, product_name="Tomato", quantity=2, unit_price=25, subtotal=50))
    vehicle = Vehicle(operator_id=admin.id, registration_number="ANALYTICS-1", vehicle_type="Truck", capacity=100, unit="kg")
    db.add(vehicle)
    db.flush()
    db.add(Route(vehicle_id=vehicle.id, waypoint_order=[2, 1], baseline_waypoint_order=[1, 2], total_distance_km=8, estimated_travel_time_min=20, number_of_stops=2, capacity_utilization_percent=20, baseline_distance_km=10, routing_provider="road_provider", is_demo_environment=False))
    db.add(Route(vehicle_id=vehicle.id, waypoint_order=[2, 1], baseline_waypoint_order=[1, 2], total_distance_km=12, estimated_travel_time_min=30, number_of_stops=2, capacity_utilization_percent=20, baseline_distance_km=15, routing_provider="haversine_straight_line", is_demo_environment=True))
    db.add(ForecastRun(model_name="linear_regression", training_rows=20, data_source="DEMO/SYNTHETIC", mae=2, rmse=3, mape=10, baseline_mae=4))
    db.commit()

    dashboard = AnalyticsService(db).dashboard(admin)

    assert dashboard.actual["registered_farmers"].value == 1
    assert dashboard.actual["active_fpos"].value == 1
    assert dashboard.actual["active_buyers"].value == 1
    assert dashboard.actual["active_consumers"].value == 1
    assert dashboard.actual["products_listed"].value == 1
    assert dashboard.actual["orders"].value == 1
    assert dashboard.actual["transaction_value"].value == Decimal("50.00")
    assert dashboard.actual["farmer_realization"].value == Decimal("25.00")
    assert dashboard.actual["consumer_price"].value == Decimal("25.00")
    assert dashboard.actual["optimized_route_distance"].value == Decimal("8.00")
    assert dashboard.actual["baseline_route_distance"].value == Decimal("10.00")
    assert dashboard.demo["optimized_route_distance"].value == Decimal("12.00")
    assert dashboard.demo["distance_reduction"].value == Decimal("20.0000")
    assert dashboard.demo["forecast_mape"].value == Decimal("10.0000")
    assert dashboard.estimates["farmer_income_impact"].value is None
    assert dashboard.actual["transaction_value"].calculation == "SUM total_amount WHERE order status = DELIVERED"
    db.close()
