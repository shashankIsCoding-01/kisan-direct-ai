import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "qa-test-secret")

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.core.dependencies import get_database
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.marketplace import CartItem, Delivery, DeliveryLocation, Order, OrderItem, Product, Vehicle
from app.models.user import User
from app.schemas.forecast import DemandForecastRequest
from app.services.forecast_service import ForecastService
from app.services.logistics_service import LogisticsService
from app.schemas.logistics import RouteOptimizeRequest
from app.services.order_state import validate_transition


@pytest.fixture()
def qa_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_database():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_database] = override_database
    app.state.qa_session_local = session_local
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client, email, role):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "secure-password", "full_name": role, "role": role})
    assert response.status_code == 201
    return response.json()


def test_password_hash_is_not_plaintext_and_wrong_password_fails():
    hashed = hash_password("secure-password")
    assert hashed != "secure-password"
    assert verify_password("secure-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_expired_token_is_rejected():
    token = jwt.encode({"sub": "1", "role": "FARMER", "token_version": 0, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.secret_key, algorithm=settings.algorithm)
    from app.core.security import decode_access_token
    assert decode_access_token(token) is None


def test_consumer_cannot_create_product_and_farmer_cannot_view_admin_analytics(qa_client):
    consumer = register(qa_client, "qa-consumer@example.com", "CONSUMER")
    consumer_headers = {"Authorization": f"Bearer {consumer['access_token']}"}
    product = qa_client.post("/api/v1/products", headers=consumer_headers, json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": 20, "quantity": 2})
    assert product.status_code == 403

    farmer = register(qa_client, "qa-farmer@example.com", "FARMER")
    farmer_headers = {"Authorization": f"Bearer {farmer['access_token']}"}
    analytics = qa_client.get("/api/v1/analytics/dashboard", headers=farmer_headers)
    assert analytics.status_code == 403


def test_order_rejects_stale_insufficient_inventory_and_duplicate_checkout(qa_client):
    farmer = register(qa_client, "stock-farmer@example.com", "FARMER")
    farmer_headers = {"Authorization": f"Bearer {farmer['access_token']}"}
    listing = qa_client.post("/api/v1/products", headers=farmer_headers, json={"name": "Onion", "category": "Vegetables", "unit": "kg", "price_per_unit": 20, "quantity": 2})
    product_id = listing.json()["id"]
    buyer = register(qa_client, "stock-buyer@example.com", "CONSUMER")
    buyer_headers = {"Authorization": f"Bearer {buyer['access_token']}"}
    assert qa_client.post("/api/v1/cart/items", headers=buyer_headers, json={"product_id": product_id, "quantity": 2}).status_code == 201

    db = app.state.qa_session_local()
    db.get(Product, product_id).quantity = 1
    db.commit()
    stale_order = qa_client.post("/api/v1/orders", headers=buyer_headers, json={"shipping_address": "Warehouse Road"})
    assert stale_order.status_code == 409
    db.close()

    db = app.state.qa_session_local()
    db.query(CartItem).filter(CartItem.buyer_id == buyer["user"]["id"], CartItem.product_id == product_id).update({"quantity": 1})
    db.commit()
    db.close()
    order = qa_client.post("/api/v1/orders", headers=buyer_headers, json={"shipping_address": "Warehouse Road"})
    assert order.status_code == 201
    duplicate = qa_client.post("/api/v1/orders", headers=buyer_headers, json={"shipping_address": "Warehouse Road"})
    assert duplicate.status_code == 400


def test_invalid_order_state_transition_does_not_mutate():
    with pytest.raises(Exception):
        validate_transition("DELIVERED", "PENDING", "ADMIN")


def test_route_rejects_missing_location_and_capacity_violation():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    operator = User(email="qa-operator@example.com", password_hash="unused", full_name="Operator", role="ADMIN")
    buyer = User(email="qa-route-buyer@example.com", password_hash="unused", full_name="Buyer", role="CONSUMER")
    seller = User(email="qa-route-seller@example.com", password_hash="unused", full_name="Seller", role="FARMER")
    db.add_all([operator, buyer, seller])
    db.flush()
    vehicle = Vehicle(operator_id=operator.id, registration_number="QA-ROUTE", vehicle_type="Van", capacity=5, unit="kg")
    order = Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=100, shipping_address="Warehouse")
    db.add_all([vehicle, order])
    db.flush()
    db.add(OrderItem(order_id=order.id, product_id=1, product_name="Crop", quantity=10, unit_price=10, subtotal=100))
    delivery = Delivery(order_id=order.id, logistics_operator_id=operator.id, vehicle_id=vehicle.id)
    db.add(delivery)
    db.commit()
    request = RouteOptimizeRequest(vehicle_id=vehicle.id, delivery_ids=[delivery.id], depot_latitude=0, depot_longitude=0)
    with pytest.raises(Exception):
        LogisticsService(db).optimize_route(operator, request)
    db.close()


def test_forecast_requires_trained_model(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    admin = User(email="qa-forecast-admin@example.com", password_hash="unused", full_name="Admin", role="ADMIN")
    db.add(admin)
    db.commit()
    monkeypatch.setattr(settings, "forecast_model_path", str(tmp_path / "missing.model"))
    with pytest.raises(Exception):
        ForecastService(db).forecast(admin, DemandForecastRequest(product="Tomato", location="Birbhum", buyer_type="BULK_BUYER", price=20, days_ahead=7))
    db.close()


def test_analytics_definitions_are_available_without_platform_data(qa_client):
    definitions = qa_client.get("/api/v1/analytics/definitions")
    assert definitions.status_code == 200
    assert "distance_reduction" in definitions.json()["definitions"]
