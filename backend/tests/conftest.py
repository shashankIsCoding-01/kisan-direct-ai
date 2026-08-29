"""
conftest.py – Shared pytest fixtures for the KisanDirect AI test suite.

Every test module imports from this file via pytest's automatic conftest
discovery.  All tests use an in-memory SQLite database so no external
services are required.
"""

import os

# Must be set before any app import so that pydantic-settings can parse it.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_database
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.marketplace import (
    CartItem,
    Delivery,
    DeliveryLocation,
    FPO,
    FPOMember,
    FPOInventoryAllocation,
    Order,
    OrderItem,
    PickupLocation,
    Product,
    Route,
    Vehicle,
)
from app.models.user import User

# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    """Isolated in-memory SQLite engine per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    """Bare SQLAlchemy session – useful for service-layer unit tests."""
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def client(db_engine):
    """
    FastAPI TestClient wired to the isolated in-memory database.

    The ``app.state.session_local`` attribute is set so that individual
    tests can open their own session to perform direct DB manipulation.
    """
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_database] = override_db
    app.state.session_local = factory
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper functions (not fixtures – imported directly in tests)
# ---------------------------------------------------------------------------


def register_user(client: TestClient, email: str, role: str, password: str = "SecurePass123!") -> dict:
    """Register a user via the API and return the full response JSON."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"Test {role.title()}",
            "role": role,
        },
    )
    assert resp.status_code == 201, f"Registration failed for {role}: {resp.json()}"
    return resp.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_user_in_db(db: Session, email: str, role: str, is_active: bool = True) -> User:
    """Insert a user directly into the DB – useful for privileged roles."""
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        full_name=f"DB {role.title()}",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def token_for(user: User) -> str:
    return create_access_token(str(user.id), user.role, user.token_version)


def make_product(db: Session, seller: User, name: str = "Tomato", quantity: float = 100.0, price: float = 20.0, category: str = "Vegetables", quality: str = "STANDARD", unit: str = "kg", is_active: bool = True) -> Product:
    p = Product(
        seller_id=seller.id,
        name=name,
        category=category,
        quality=quality,
        unit=unit,
        price_per_unit=price,
        quantity=quantity,
        is_active=is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_vehicle(db: Session, operator: User, capacity: float = 500.0, registration: str = "TEST-VH-01") -> Vehicle:
    v = Vehicle(
        operator_id=operator.id,
        registration_number=registration,
        vehicle_type="Pickup Truck",
        capacity=capacity,
        unit="kg",
        is_available=True,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def make_delivery_location(db: Session, lat: float = 12.97, lon: float = 77.59, name: str = "Drop Point") -> DeliveryLocation:
    loc = DeliveryLocation(name=name, address="123 Test Road", latitude=lat, longitude=lon)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def make_order_with_delivery(db: Session, buyer: User, seller: User, vehicle: Vehicle, operator: User, location: DeliveryLocation, quantity: float = 10.0, status: str = "READY_FOR_PICKUP") -> tuple[Order, Delivery]:
    """Create an order and a delivery record directly in the DB."""
    order = Order(
        buyer_id=buyer.id,
        seller_id=seller.id,
        status=status,
        total_amount=quantity * 20,
        shipping_address="Test Shipping Address",
    )
    db.add(order)
    db.flush()
    product = make_product(db, seller, quantity=quantity)
    db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, quantity=quantity, unit_price=20.0, subtotal=quantity * 20))
    delivery = Delivery(
        order_id=order.id,
        logistics_operator_id=operator.id,
        vehicle_id=vehicle.id,
        delivery_location_id=location.id,
        status="ASSIGNED",
    )
    db.add(delivery)
    db.commit()
    db.refresh(order)
    db.refresh(delivery)
    return order, delivery
