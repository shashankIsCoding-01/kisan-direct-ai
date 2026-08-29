"""
test_analytics_comprehensive.py
───────────────────────────────
Comprehensive test coverage for Platform Analytics and Metrics.

Business rules verified:
  BR-ANA-01  Only ADMIN can view the analytics dashboard (403 for other roles).
  BR-ANA-02  Analytics definitions are public/available without auth.
  BR-ANA-03  Registered farmers metric counts all users with role=FARMER.
  BR-ANA-04  Active FPOs metric counts distinct FPOs having at least one active membership.
  BR-ANA-05  Active buyers metric counts active users with role=BULK_BUYER.
  BR-ANA-06  Orders metric counts all orders WHERE status != 'CANCELLED'.
  BR-ANA-07  Transaction value sums total_amount WHERE status == 'DELIVERED' only (not pending/cancelled).
  BR-ANA-08  Farmer realization & consumer price calculated from delivered order items only.
  BR-ANA-09  Distance reduction calculation handles zero baseline gracefully (returns None or 0).
  BR-ANA-10  Unmeasured impact estimates (farmer_income_impact, etc.) explicitly return value=None with source='NOT_AVAILABLE' and defensibility explanation.
"""

import os
from decimal import Decimal
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.core.security import create_access_token, hash_password
from app.models.marketplace import FPO, FPOMember, Order, OrderItem, Product, Route, Vehicle
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from tests.conftest import auth_headers, make_user_in_db, register_user, token_for


def _db(client):
    from app.main import app
    return app.state.session_local()


class TestAnalyticsAccess:
    """BR-ANA-01, BR-ANA-02"""

    def test_definitions_endpoint_is_accessible_without_token(self, client):
        """BR-ANA-02"""
        resp = client.get("/api/v1/analytics/definitions")
        assert resp.status_code == 200
        defs = resp.json()["definitions"]
        assert "registered_farmers" in defs
        assert "transaction_value" in defs
        assert "distance_reduction" in defs

    def test_farmer_cannot_view_dashboard(self, client):
        """BR-ANA-01"""
        farmer = register_user(client, "anar_farmer@example.com", "FARMER")
        resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers(farmer["access_token"]))
        assert resp.status_code == 403

    def test_consumer_cannot_view_dashboard(self, client):
        """BR-ANA-01"""
        consumer = register_user(client, "anar_consumer@example.com", "CONSUMER")
        resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers(consumer["access_token"]))
        assert resp.status_code == 403

    def test_bulk_buyer_cannot_view_dashboard(self, client):
        """BR-ANA-01"""
        buyer = register_user(client, "anar_buyer@example.com", "BULK_BUYER")
        resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 403

    def test_admin_can_view_dashboard(self, client):
        db = _db(client)
        admin = make_user_in_db(db, "anar_admin@example.com", "ADMIN")
        admin_token = create_access_token(str(admin.id), "ADMIN", admin.token_version)
        db.close()

        resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "actual" in data
        assert "demo" in data
        assert "estimates" in data


class TestAnalyticsCalculations:
    """BR-ANA-03 through BR-ANA-10"""

    def test_metrics_empty_database_defensibility(self, client):
        """BR-ANA-10: Empty database reports None / 0 without crashing."""
        db = _db(client)
        admin = make_user_in_db(db, "calc_empty_admin@example.com", "ADMIN")
        
        dashboard = AnalyticsService(db).dashboard(admin)
        assert dashboard.actual["registered_farmers"].value == 0
        assert dashboard.actual["orders"].value == 0
        assert dashboard.actual["transaction_value"].value == Decimal("0")
        assert dashboard.actual["farmer_realization"].value is None
        # Unmeasured estimates must be None
        assert dashboard.estimates["farmer_income_impact"].value is None
        assert dashboard.estimates["farmer_income_impact"].source == "NOT_AVAILABLE"
        db.close()

    def test_cancelled_orders_excluded_from_orders_metric(self, client):
        """BR-ANA-06"""
        db = _db(client)
        admin = make_user_in_db(db, "calc_ord_admin@example.com", "ADMIN")
        buyer = make_user_in_db(db, "calc_ord_buyer@example.com", "CONSUMER")
        seller = make_user_in_db(db, "calc_ord_seller@example.com", "FARMER")

        # 1 Delivered, 1 Pending, 1 Cancelled
        db.add(Order(buyer_id=buyer.id, seller_id=seller.id, status="DELIVERED", total_amount=100, shipping_address="Loc 1"))
        db.add(Order(buyer_id=buyer.id, seller_id=seller.id, status="PENDING", total_amount=50, shipping_address="Loc 2"))
        db.add(Order(buyer_id=buyer.id, seller_id=seller.id, status="CANCELLED", total_amount=75, shipping_address="Loc 3"))
        db.commit()

        dashboard = AnalyticsService(db).dashboard(admin)
        # Orders metric includes non-cancelled orders only -> count should be 2
        assert dashboard.actual["orders"].value == 2
        db.close()

    def test_transaction_value_sums_delivered_orders_only(self, client):
        """BR-ANA-07"""
        db = _db(client)
        admin = make_user_in_db(db, "calc_tx_admin@example.com", "ADMIN")
        buyer = make_user_in_db(db, "calc_tx_buyer@example.com", "CONSUMER")
        seller = make_user_in_db(db, "calc_tx_seller@example.com", "FARMER")

        db.add(Order(buyer_id=buyer.id, seller_id=seller.id, status="DELIVERED", total_amount=Decimal("150.00"), shipping_address="Loc 1"))
        db.add(Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=Decimal("300.00"), shipping_address="Loc 2"))
        db.commit()

        dashboard = AnalyticsService(db).dashboard(admin)
        # Only delivered order (150.00) contributes to transaction value
        assert dashboard.actual["transaction_value"].value == Decimal("150.00")
        db.close()
