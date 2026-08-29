"""
test_bulk_buyers.py
────────────────────
Comprehensive tests for Bulk Buyer purchase requirements and matching.
"""

import os
import pytest
from decimal import Decimal

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.models.bulk import PurchaseRequirement
from tests.conftest import auth_headers, register_user


FUTURE_DEADLINE = "2099-12-31T12:00:00"
PAST_DEADLINE   = "2000-01-01T12:00:00"


def _db(client):
    from app.main import app
    return app.state.session_local()


def _setup_supply(client, farmer_email: str, product_name: str = "Wheat", qty: str = "100", price: str = "25", quality: str = "GRADE_A") -> tuple[dict, dict]:
    farmer = register_user(client, farmer_email, "FARMER")
    product = client.post(
        "/api/v1/products",
        headers=auth_headers(farmer["access_token"]),
        json={"name": product_name, "category": "Grains", "unit": "kg", "quality": quality, "price_per_unit": price, "quantity": qty},
    ).json()
    return farmer, product


def _create_requirement(client, buyer_token: str, product_name: str = "Wheat", qty: str = "50", quality: str = "STANDARD", max_price: str = "30", deadline: str = FUTURE_DEADLINE) -> dict:
    resp = client.post(
        "/api/v1/bulk-requirements",
        headers=auth_headers(buyer_token),
        json={"product_name": product_name, "unit": "kg", "required_quantity": qty, "quality": quality, "max_price": max_price, "delivery_location": "Central Warehouse", "delivery_deadline": deadline},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


class TestRequirementCreation:
    """BR-BULK-01, BR-BULK-02, BR-BULK-15"""

    def test_bulk_buyer_can_create_requirement(self, client):
        buyer = register_user(client, "bulk_c1@example.com", "BULK_BUYER")
        resp = _create_requirement(client, buyer["access_token"])
        assert resp["status"] == "OPEN"
        assert resp["buyer_id"] == buyer["user"]["id"]

    def test_consumer_cannot_create_requirement(self, client):
        """BR-BULK-01"""
        consumer = register_user(client, "bulk_c2@example.com", "CONSUMER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(consumer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "10", "quality": "STANDARD", "max_price": "30", "delivery_location": "Warehouse", "delivery_deadline": FUTURE_DEADLINE},
        )
        assert resp.status_code == 403

    def test_farmer_cannot_create_requirement(self, client):
        farmer = register_user(client, "bulk_c3@example.com", "FARMER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(farmer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "10", "quality": "STANDARD", "max_price": "30", "delivery_location": "Warehouse", "delivery_deadline": FUTURE_DEADLINE},
        )
        assert resp.status_code == 403

    def test_past_deadline_is_rejected(self, client):
        """BR-BULK-02"""
        buyer = register_user(client, "bulk_c4@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(buyer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "10", "quality": "STANDARD", "max_price": "30", "delivery_location": "Warehouse", "delivery_deadline": PAST_DEADLINE},
        )
        assert resp.status_code == 422

    def test_zero_quantity_is_rejected(self, client):
        """BR-BULK-15"""
        buyer = register_user(client, "bulk_c5@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(buyer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "0", "quality": "STANDARD", "max_price": "30", "delivery_location": "Warehouse", "delivery_deadline": FUTURE_DEADLINE},
        )
        assert resp.status_code == 422

    def test_negative_quantity_is_rejected(self, client):
        """BR-BULK-15"""
        buyer = register_user(client, "bulk_c6@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(buyer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "-10", "quality": "STANDARD", "max_price": "30", "delivery_location": "Warehouse", "delivery_deadline": FUTURE_DEADLINE},
        )
        assert resp.status_code == 422

    def test_negative_max_price_rejected(self, client):
        buyer = register_user(client, "bulk_c7@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/bulk-requirements",
            headers=auth_headers(buyer["access_token"]),
            json={"product_name": "Wheat", "unit": "kg", "required_quantity": "10", "quality": "STANDARD", "max_price": "-5", "delivery_location": "Warehouse", "delivery_deadline": FUTURE_DEADLINE},
        )
        assert resp.status_code == 422


class TestRequirementAccess:
    """BR-BULK-03"""

    def test_owner_can_view_own_requirement(self, client):
        buyer = register_user(client, "bulk_a1@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"])
        resp = client.get(f"/api/v1/bulk-requirements/{req['id']}", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 200

    def test_other_buyer_cannot_view_requirement(self, client):
        """BR-BULK-03"""
        buyer1 = register_user(client, "bulk_a2@example.com", "BULK_BUYER")
        buyer2 = register_user(client, "bulk_a3@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer1["access_token"])
        resp = client.get(f"/api/v1/bulk-requirements/{req['id']}", headers=auth_headers(buyer2["access_token"]))
        assert resp.status_code == 403

    def test_farmer_cannot_view_requirement(self, client):
        buyer = register_user(client, "bulk_a4@example.com", "BULK_BUYER")
        farmer = register_user(client, "bulk_a4f@example.com", "FARMER")
        req = _create_requirement(client, buyer["access_token"])
        resp = client.get(f"/api/v1/bulk-requirements/{req['id']}", headers=auth_headers(farmer["access_token"]))
        assert resp.status_code == 403


class TestBulkMatching:
    """BR-BULK-04, BR-BULK-06 through BR-BULK-09"""

    def test_full_match_when_supply_exceeds_demand(self, client):
        farmer, product = _setup_supply(client, "bulk_m1f@example.com", qty="200")
        buyer = register_user(client, "bulk_m1b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="50")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 200
        assert float(resp.json()["matched_quantity"]) == 50.0
        assert float(resp.json()["remaining_quantity"]) == 0.0

    def test_partial_match_when_supply_is_insufficient(self, client):
        """BR-BULK-06"""
        farmer, product = _setup_supply(client, "bulk_m2f@example.com", qty="30")
        buyer = register_user(client, "bulk_m2b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="80")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 200
        assert float(resp.json()["matched_quantity"]) == 30.0
        assert float(resp.json()["remaining_quantity"]) == 50.0

    def test_no_match_when_no_supply(self, client):
        """BR-BULK-07"""
        buyer = register_user(client, "bulk_m3b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], product_name="SomethingNonExistent")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 200
        assert float(resp.json()["matched_quantity"]) == 0.0

    def test_match_respects_max_price_filter(self, client):
        """BR-BULK-09"""
        farmer, product = _setup_supply(client, "bulk_m4f@example.com", price="40", qty="100")
        buyer = register_user(client, "bulk_m4b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="20", max_price="30")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert float(resp.json()["matched_quantity"]) == 0.0

    def test_match_accepts_higher_quality_for_standard_requirement(self, client):
        """BR-BULK-08"""
        farmer, product = _setup_supply(client, "bulk_m5f@example.com", quality="GRADE_A", qty="50")
        buyer = register_user(client, "bulk_m5b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], quality="STANDARD", qty="30")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert float(resp.json()["matched_quantity"]) > 0

    def test_match_rejects_lower_quality_for_premium_requirement(self, client):
        """BR-BULK-08"""
        farmer, product = _setup_supply(client, "bulk_m6f@example.com", quality="STANDARD", qty="50")
        buyer = register_user(client, "bulk_m6b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], quality="PREMIUM", qty="20")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert float(resp.json()["matched_quantity"]) == 0.0

    def test_cancelled_requirement_cannot_be_matched(self, client):
        """BR-BULK-04"""
        buyer = register_user(client, "bulk_m7b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"])
        
        # Mark cancelled directly in DB
        db = _db(client)
        db_req = db.get(PurchaseRequirement, req["id"])
        db_req.status = "CANCELLED"
        db.commit()
        db.close()

        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 409

    def test_matching_does_not_reserve_inventory(self, client):
        farmer, product = _setup_supply(client, "bulk_m8f@example.com", qty="50")
        buyer = register_user(client, "bulk_m8b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="30")
        client.post(f"/api/v1/bulk-requirements/{req['id']}/match", headers=auth_headers(buyer["access_token"]))
        after = client.get(f"/api/v1/products/{product['id']}").json()
        assert float(after["quantity"]) == 50.0


class TestBulkOrderPlacement:
    """BR-BULK-05, BR-BULK-10 through BR-BULK-14"""

    def test_place_orders_decrements_inventory(self, client):
        """BR-BULK-11"""
        farmer, product = _setup_supply(client, "bulk_op1f@example.com", qty="100")
        buyer = register_user(client, "bulk_op1b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="40")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 200
        after = client.get(f"/api/v1/products/{product['id']}").json()
        assert float(after["quantity"]) == 60.0

    def test_place_orders_fulfilled_status(self, client):
        """BR-BULK-13"""
        farmer, product = _setup_supply(client, "bulk_op2f@example.com", qty="100")
        buyer = register_user(client, "bulk_op2b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="50")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert resp.json()["status"] == "FULFILLED"

    def test_place_orders_partially_fulfilled_status(self, client):
        """BR-BULK-14"""
        farmer, product = _setup_supply(client, "bulk_op3f@example.com", qty="30")
        buyer = register_user(client, "bulk_op3b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="80")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert resp.json()["status"] == "PARTIALLY_FULFILLED"
        assert float(resp.json()["remaining_quantity"]) == 50.0

    def test_no_supply_prevents_order_placement(self, client):
        """BR-BULK-10"""
        buyer = register_user(client, "bulk_op4b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], product_name="UnknownCrop")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 409

    def test_cancelled_requirement_cannot_place_orders(self, client):
        """BR-BULK-05"""
        buyer = register_user(client, "bulk_op5b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"])
        
        db = _db(client)
        db_req = db.get(PurchaseRequirement, req["id"])
        db_req.status = "CANCELLED"
        db.commit()
        db.close()

        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert resp.status_code == 409

    def test_bulk_order_total_is_correct(self, client):
        farmer, product = _setup_supply(client, "bulk_op6f@example.com", qty="100", price="25")
        buyer = register_user(client, "bulk_op6b@example.com", "BULK_BUYER")
        req = _create_requirement(client, buyer["access_token"], qty="20")
        resp = client.post(f"/api/v1/bulk-requirements/{req['id']}/place-orders", headers=auth_headers(buyer["access_token"]))
        assert float(resp.json()["estimated_cost"]) == 20 * 25
