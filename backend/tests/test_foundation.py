import os

os.environ.setdefault("SECRET_KEY", "test-only-secret")

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.dependencies import get_database
from app.core.database import Base
from app.core.security import create_access_token, decode_access_token, hash_password
from app.models.user import User
from app.schemas.user import UserCreate

client = TestClient(app)


@pytest.fixture()
def auth_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_database():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_database] = override_database
    app.state.test_session_local = session_local
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "not_checked"


def test_jwt_round_trip_contains_subject_and_role():
    token = create_access_token("42", "FARMER")

    claims = decode_access_token(token)

    assert claims is not None
    assert claims["sub"] == "42"
    assert claims["role"] == "FARMER"
    assert claims["token_version"] == 0


def test_registration_schema_rejects_unknown_role():
    try:
        UserCreate(
            email="farmer@example.com",
            password="secure-password",
            full_name="A Farmer",
            role="unknown",
        )
    except ValidationError:
        return

    raise AssertionError("Unknown roles must be rejected by request validation")


def test_auth_flow_register_login_current_user_and_logout(auth_client):
    registration = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "farmer@example.com",
            "password": "secure-password",
            "full_name": "A Farmer",
            "role": "FARMER",
        },
    )

    assert registration.status_code == 201
    assert registration.json()["user"]["role"] == "FARMER"
    token = registration.json()["access_token"]

    current = auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert current.status_code == 200
    assert current.json()["email"] == "farmer@example.com"

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "farmer@example.com", "password": "secure-password"},
    )
    assert login.status_code == 200
    login_token = login.json()["access_token"]

    logout = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert logout.status_code == 200

    revoked = auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert revoked.status_code == 401


def test_auth_rejects_invalid_credentials_and_privileged_self_registration(auth_client):
    invalid_login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "secure-password"},
    )
    assert invalid_login.status_code == 401

    admin_registration = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "secure-password",
            "full_name": "Attempted Admin",
            "role": "ADMIN",
        },
    )
    assert admin_registration.status_code == 403


def test_auth_rejects_missing_token_and_non_admin_role(auth_client):
    missing = auth_client.get("/api/v1/users/me")
    assert missing.status_code == 401

    token = create_access_token("1", "FARMER")
    denied = auth_client.get(
        "/api/v1/users/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403


def test_marketplace_farmer_and_consumer_flow(auth_client):
    farmer_response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "seller@example.com",
            "password": "secure-password",
            "full_name": "A Seller",
            "role": "FARMER",
        },
    )
    farmer_token = farmer_response.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    listing = auth_client.post(
        "/api/v1/products",
        headers=farmer_headers,
        json={
            "name": "Fresh Tomato",
            "description": "Direct from the farm",
            "category": "Vegetables",
            "unit": "kg",
            "price_per_unit": "28.00",
            "quantity": "50",
            "location": "Birbhum",
        },
    )
    assert listing.status_code == 201
    product_id = listing.json()["id"]

    edited = auth_client.patch(
        f"/api/v1/products/{product_id}",
        headers=farmer_headers,
        json={"quantity": "40", "price_per_unit": "30.00"},
    )
    assert edited.status_code == 200
    assert edited.json()["quantity"] == "40.00"

    consumer_response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "buyer@example.com",
            "password": "secure-password",
            "full_name": "A Buyer",
            "role": "CONSUMER",
        },
    )
    consumer_headers = {"Authorization": f"Bearer {consumer_response.json()['access_token']}"}

    browse = auth_client.get("/api/v1/products?search=tomato&category=Vegetables&sort=price_asc")
    assert browse.status_code == 200
    assert browse.json()["total"] == 1

    details = auth_client.get(f"/api/v1/products/{product_id}")
    assert details.status_code == 200
    assert details.json()["name"] == "Fresh Tomato"

    cart = auth_client.post(
        "/api/v1/cart/items",
        headers=consumer_headers,
        json={"product_id": product_id, "quantity": "5"},
    )
    assert cart.status_code == 201

    order = auth_client.post(
        "/api/v1/orders",
        headers=consumer_headers,
        json={"shipping_address": "12 Market Road, Birbhum"},
    )
    assert order.status_code == 201
    assert order.json()["status"] == "PENDING"
    assert order.json()["items"][0]["quantity"] == "5.00"

    farmer_orders = auth_client.get("/api/v1/orders/sales", headers=farmer_headers)
    assert farmer_orders.status_code == 200
    assert len(farmer_orders.json()) == 1

    notifications = auth_client.get("/api/v1/orders/notifications", headers=farmer_headers)
    assert notifications.status_code == 200
    assert notifications.json()[0]["order_id"] == order.json()["id"]

    remaining = auth_client.get(f"/api/v1/products/{product_id}")
    assert remaining.json()["quantity"] == "35.00"


def test_marketplace_prevents_non_owner_listing_changes(auth_client):
    first = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "secure-password", "full_name": "Owner", "role": "FARMER"},
    )
    owner_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    listing = auth_client.post(
        "/api/v1/products",
        headers=owner_headers,
        json={"name": "Potato", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "10"},
    )

    second = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "secure-password", "full_name": "Other", "role": "FARMER"},
    )
    other_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
    response = auth_client.patch(
        f"/api/v1/products/{listing.json()['id']}",
        headers=other_headers,
        json={"quantity": "1"},
    )
    assert response.status_code == 403


def test_order_status_api_enforces_seller_lifecycle(auth_client):
    farmer = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "lifecycle-seller@example.com", "password": "secure-password", "full_name": "Lifecycle Seller", "role": "FARMER"},
    )
    farmer_headers = {"Authorization": f"Bearer {farmer.json()['access_token']}"}
    product = auth_client.post(
        "/api/v1/products",
        headers=farmer_headers,
        json={"name": "Lifecycle Rice", "category": "Grains", "unit": "kg", "price_per_unit": "40", "quantity": "10"},
    )
    buyer = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "lifecycle-buyer@example.com", "password": "secure-password", "full_name": "Lifecycle Buyer", "role": "CONSUMER"},
    )
    buyer_headers = {"Authorization": f"Bearer {buyer.json()['access_token']}"}
    auth_client.post("/api/v1/cart/items", headers=buyer_headers, json={"product_id": product.json()["id"], "quantity": "2"})
    order = auth_client.post("/api/v1/orders", headers=buyer_headers, json={"shipping_address": "1 Farm Road"})
    order_id = order.json()["id"]

    confirmed = auth_client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_headers, json={"status": "CONFIRMED"})
    assert confirmed.status_code == 200
    preparing = auth_client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_headers, json={"status": "PREPARING"})
    assert preparing.status_code == 200
    ready = auth_client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_headers, json={"status": "READY_FOR_PICKUP"})
    assert ready.status_code == 200
    invalid = auth_client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_headers, json={"status": "CONFIRMED"})
    assert invalid.status_code == 409
    unchanged = auth_client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers)
    assert unchanged.json()["status"] == "READY_FOR_PICKUP"

    db = app.state.test_session_local()
    logistics_user = User(email="operator@example.com", password_hash=hash_password("secure-password"), full_name="Operator", role="LOGISTICS")
    db.add(logistics_user)
    db.commit()
    db.refresh(logistics_user)
    logistics_headers = {"Authorization": f"Bearer {create_access_token(str(logistics_user.id), 'LOGISTICS')}"}

    assignment = auth_client.post(
        f"/api/v1/orders/{order_id}/delivery",
        headers=logistics_headers,
        json={"logistics_operator_id": logistics_user.id},
    )
    assert assignment.status_code == 201
    delivery_id = assignment.json()["id"]
    picked_up = auth_client.patch(f"/api/v1/deliveries/{delivery_id}/status", headers=logistics_headers, json={"status": "PICKED_UP"})
    assert picked_up.status_code == 200
    delivered = auth_client.patch(f"/api/v1/deliveries/{delivery_id}/status", headers=logistics_headers, json={"status": "DELIVERED"})
    assert delivered.status_code == 200
    assert auth_client.get(f"/api/v1/orders/{order_id}", headers=buyer_headers).json()["status"] == "DELIVERED"
    db.close()


def test_fpo_aggregation_reserves_and_consumes_supply_once(auth_client):
    fpo = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "fpo@example.com", "password": "secure-password", "full_name": "Village FPO", "role": "FPO"},
    )
    fpo_headers = {"Authorization": f"Bearer {fpo.json()['access_token']}"}
    fpo_profile = auth_client.post(
        "/api/v1/fpos",
        headers=fpo_headers,
        json={"name": "Village Producer Organization", "address": "Market Road, Birbhum"},
    )
    assert fpo_profile.status_code == 201
    fpo_id = fpo_profile.json()["id"]

    farmer_tokens = []
    product_ids = []
    for email, quantity in [("member-one@example.com", "10"), ("member-two@example.com", "7")]:
        farmer = auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "secure-password", "full_name": "Member Farmer", "role": "FARMER"},
        )
        farmer_tokens.append(farmer.json()["user"]["id"])
        headers = {"Authorization": f"Bearer {farmer.json()['access_token']}"}
        product = auth_client.post(
            "/api/v1/products",
            headers=headers,
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "60", "quantity": quantity},
        )
        product_ids.append(product.json()["id"])

    for farmer_id in farmer_tokens:
        membership = auth_client.post(f"/api/v1/fpos/{fpo_id}/members", headers=fpo_headers, json={"farmer_id": farmer_id})
        assert membership.status_code == 201

    inventory = auth_client.get(f"/api/v1/fpos/{fpo_id}/inventory", headers=fpo_headers)
    assert inventory.status_code == 200
    assert sorted(float(item["available_quantity"]) for item in inventory.json()["items"]) == [7.0, 10.0]

    aggregate = auth_client.post(
        f"/api/v1/fpos/{fpo_id}/aggregate",
        headers=fpo_headers,
        json={
            "name": "Mango",
            "category": "Fruits",
            "unit": "kg",
            "price_per_unit": "70",
            "allocations": [
                {"source_product_id": product_ids[0], "quantity": "6"},
                {"source_product_id": product_ids[1], "quantity": "5"},
            ],
        },
    )
    assert aggregate.status_code == 201
    aggregated_product_id = aggregate.json()["id"]
    assert aggregate.json()["quantity"] == "11.00"
    assert auth_client.get(f"/api/v1/products/{product_ids[0]}").json()["quantity"] == "4.00"
    assert auth_client.get(f"/api/v1/products/{product_ids[1]}").json()["quantity"] == "2.00"

    duplicate_source = auth_client.post(
        f"/api/v1/fpos/{fpo_id}/aggregate",
        headers=fpo_headers,
        json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "2"}, {"source_product_id": product_ids[0], "quantity": "2"}]},
    )
    assert duplicate_source.status_code == 400

    over_supply = auth_client.post(
        f"/api/v1/fpos/{fpo_id}/aggregate",
        headers=fpo_headers,
        json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "5"}]},
    )
    assert over_supply.status_code == 409

    buyer = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "fpo-buyer@example.com", "password": "secure-password", "full_name": "Bulk Buyer", "role": "BULK_BUYER"},
    )
    buyer_headers = {"Authorization": f"Bearer {buyer.json()['access_token']}"}
    cart = auth_client.post("/api/v1/cart/items", headers=buyer_headers, json={"product_id": aggregated_product_id, "quantity": "4"})
    assert cart.status_code == 201
    order = auth_client.post("/api/v1/orders", headers=buyer_headers, json={"shipping_address": "FPO Depot Road"})
    assert order.status_code == 201
    aggregate_after_order = auth_client.get(f"/api/v1/products/{aggregated_product_id}")
    assert aggregate_after_order.json()["quantity"] == "7.00"
    analytics = auth_client.get(f"/api/v1/fpos/{fpo_id}/analytics", headers=fpo_headers)
    assert analytics.status_code == 200
    assert analytics.json()["order_count"] == 1
    assert analytics.json()["revenue"] == "280.00"


def test_bulk_requirement_partial_matching_and_insufficient_supply(auth_client):
    farmer = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "bulk-supplier@example.com", "password": "secure-password", "full_name": "Bulk Supplier", "role": "FARMER"},
    )
    farmer_headers = {"Authorization": f"Bearer {farmer.json()['access_token']}"}
    product = auth_client.post(
        "/api/v1/products",
        headers=farmer_headers,
        json={"name": "Wheat", "category": "Grains", "unit": "kg", "quality": "GRADE_A", "price_per_unit": "25", "quantity": "4"},
    )
    buyer = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "bulk-buyer@example.com", "password": "secure-password", "full_name": "Bulk Buyer", "role": "BULK_BUYER"},
    )
    buyer_headers = {"Authorization": f"Bearer {buyer.json()['access_token']}"}

    requirement = auth_client.post(
        "/api/v1/bulk-requirements",
        headers=buyer_headers,
        json={"product_name": "Wheat", "unit": "kg", "required_quantity": "10", "quality": "STANDARD", "max_price": "30", "delivery_location": "Central Warehouse", "delivery_deadline": "2099-01-01T12:00:00"},
    )
    assert requirement.status_code == 201
    requirement_id = requirement.json()["id"]

    match = auth_client.post(f"/api/v1/bulk-requirements/{requirement_id}/match", headers=buyer_headers)
    assert match.status_code == 200
    assert match.json()["required_quantity"] == "10.00"
    assert match.json()["matched_quantity"] == "4.00"
    assert match.json()["remaining_quantity"] == "6.00"
    assert float(match.json()["estimated_cost"]) == 100.0
    assert match.json()["suppliers"][0]["supplier_id"] == farmer.json()["user"]["id"]

    placement = auth_client.post(f"/api/v1/bulk-requirements/{requirement_id}/place-orders", headers=buyer_headers)
    assert placement.status_code == 200
    assert placement.json()["ordered_quantity"] == "4.00"
    assert placement.json()["remaining_quantity"] == "6.00"
    assert placement.json()["status"] == "PARTIALLY_FULFILLED"

    insufficient = auth_client.post(
        "/api/v1/bulk-requirements",
        headers=buyer_headers,
        json={"product_name": "Rice", "unit": "kg", "required_quantity": "2", "quality": "STANDARD", "max_price": "30", "delivery_location": "Central Warehouse", "delivery_deadline": "2099-01-01T12:00:00"},
    )
    insufficient_id = insufficient.json()["id"]
    no_match = auth_client.post(f"/api/v1/bulk-requirements/{insufficient_id}/match", headers=buyer_headers)
    assert no_match.status_code == 200
    assert float(no_match.json()["matched_quantity"]) == 0.0
    assert no_match.json()["remaining_quantity"] == "2.00"
    no_supply_order = auth_client.post(f"/api/v1/bulk-requirements/{insufficient_id}/place-orders", headers=buyer_headers)
    assert no_supply_order.status_code == 409

