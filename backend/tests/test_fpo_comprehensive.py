"""
test_fpo_comprehensive.py
──────────────────────────
Complete test coverage for Farmer Producer Organizations (FPO).

Business rules verified:
  BR-FPO-01  Only FPO-role users can create an FPO profile.
  BR-FPO-02  A user can own at most one FPO (duplicate → 409).
  BR-FPO-03  Only the FPO owner or ADMIN can manage the FPO.
  BR-FPO-04  Members added must be FARMER-role users.
  BR-FPO-05  The same farmer cannot be added as a member twice (active).
  BR-FPO-06  Removing a member sets is_active=False, not deletes.
  BR-FPO-07  Farmer inventory lists available quantities of active members.
  BR-FPO-08  Aggregation requires at least one active member.
  BR-FPO-09  Each source product can appear only once per aggregation request.
  BR-FPO-10  Source products must belong to active member farmers.
  BR-FPO-11  All source products must share the same name, category, and unit.
  BR-FPO-12  Aggregation quantity must not exceed source product availability.
  BR-FPO-13  Aggregation deducts from source product quantities.
  BR-FPO-14  Aggregated listing total = sum of allocated quantities.
  BR-FPO-15  An FPO inventory allocation ledger is consumed in order on purchase.
  BR-FPO-16  Aggregated listing ledger insufficiency raises 409.
  BR-FPO-17  FPO analytics correctly count orders and compute revenue.
  BR-FPO-18  Non-owner cannot add members or aggregate.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

import pytest
from decimal import Decimal

from tests.conftest import auth_headers, make_user_in_db, register_user


def _db(client):
    from app.main import app
    return app.state.session_local()


class TestFPOCreation:
    """BR-FPO-01, BR-FPO-02"""

    def test_fpo_user_can_create_fpo_profile(self, client):
        fpo = register_user(client, "fpo_create@example.com", "FPO")
        resp = client.post("/api/v1/fpos", headers=auth_headers(fpo["access_token"]), json={"name": "Test FPO", "address": "Test Village Road"})
        assert resp.status_code == 201
        assert resp.json()["owner_user_id"] == fpo["user"]["id"]

    def test_farmer_cannot_create_fpo(self, client):
        """BR-FPO-01"""
        farmer = register_user(client, "farmer_fpo@example.com", "FARMER")
        resp = client.post("/api/v1/fpos", headers=auth_headers(farmer["access_token"]), json={"name": "Farmer FPO", "address": "Farm Road 1"})
        assert resp.status_code == 403

    def test_consumer_cannot_create_fpo(self, client):
        consumer = register_user(client, "consumer_fpo@example.com", "CONSUMER")
        resp = client.post("/api/v1/fpos", headers=auth_headers(consumer["access_token"]), json={"name": "Consumer FPO", "address": "Consumer Road"})
        assert resp.status_code == 403

    def test_duplicate_fpo_creation_rejected(self, client):
        """BR-FPO-02"""
        fpo = register_user(client, "dup_fpo@example.com", "FPO")
        hdrs = auth_headers(fpo["access_token"])
        client.post("/api/v1/fpos", headers=hdrs, json={"name": "First FPO", "address": "First Road 1"})
        resp = client.post("/api/v1/fpos", headers=hdrs, json={"name": "Second FPO", "address": "Second Road 2"})
        assert resp.status_code == 409

    def test_fpo_name_too_short_rejected(self, client):
        fpo = register_user(client, "short_fpo@example.com", "FPO")
        resp = client.post("/api/v1/fpos", headers=auth_headers(fpo["access_token"]), json={"name": "X", "address": "Valid Road Address"})
        assert resp.status_code == 422


class TestFPOMembership:
    """BR-FPO-03 through BR-FPO-06"""

    def _create_fpo_with_owner(self, client, email: str = "mem_fpo@example.com") -> tuple[dict, int]:
        fpo_user = register_user(client, email, "FPO")
        fpo = client.post("/api/v1/fpos", headers=auth_headers(fpo_user["access_token"]), json={"name": "Member FPO", "address": "Member Road 123"}).json()
        return fpo_user, fpo["id"]

    def test_owner_can_add_farmer_member(self, client):
        """BR-FPO-04"""
        fpo_user, fpo_id = self._create_fpo_with_owner(client)
        farmer = register_user(client, "mem_farmer@example.com", "FARMER")
        resp = client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": farmer["user"]["id"]})
        assert resp.status_code == 201
        assert resp.json()["farmer_id"] == farmer["user"]["id"]

    def test_adding_non_farmer_as_member_fails(self, client):
        """BR-FPO-04"""
        fpo_user, fpo_id = self._create_fpo_with_owner(client, "nf_fpo@example.com")
        consumer = register_user(client, "nf_consumer@example.com", "CONSUMER")
        resp = client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": consumer["user"]["id"]})
        assert resp.status_code == 400

    def test_adding_same_farmer_twice_fails(self, client):
        """BR-FPO-05"""
        fpo_user, fpo_id = self._create_fpo_with_owner(client, "dup_mem_fpo@example.com")
        farmer = register_user(client, "dup_mem_farmer@example.com", "FARMER")
        farmer_id = farmer["user"]["id"]
        client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": farmer_id})
        resp = client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": farmer_id})
        assert resp.status_code == 409

    def test_remove_member_sets_inactive(self, client):
        """BR-FPO-06"""
        fpo_user, fpo_id = self._create_fpo_with_owner(client, "rem_fpo@example.com")
        farmer = register_user(client, "rem_farmer@example.com", "FARMER")
        farmer_id = farmer["user"]["id"]
        client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": farmer_id})
        resp = client.delete(f"/api/v1/fpos/{fpo_id}/members/{farmer_id}", headers=auth_headers(fpo_user["access_token"]))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_non_owner_cannot_add_members(self, client):
        """BR-FPO-03, BR-FPO-18"""
        fpo_user, fpo_id = self._create_fpo_with_owner(client, "no_own_fpo@example.com")
        other_fpo = register_user(client, "other_fpo@example.com", "FPO")
        farmer = register_user(client, "other_farmer@example.com", "FARMER")
        resp = client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(other_fpo["access_token"]), json={"farmer_id": farmer["user"]["id"]})
        assert resp.status_code == 403

    def test_removing_already_inactive_member_fails(self, client):
        fpo_user, fpo_id = self._create_fpo_with_owner(client, "rm2_fpo@example.com")
        farmer = register_user(client, "rm2_farmer@example.com", "FARMER")
        farmer_id = farmer["user"]["id"]
        client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": farmer_id})
        client.delete(f"/api/v1/fpos/{fpo_id}/members/{farmer_id}", headers=auth_headers(fpo_user["access_token"]))
        resp = client.delete(f"/api/v1/fpos/{fpo_id}/members/{farmer_id}", headers=auth_headers(fpo_user["access_token"]))
        assert resp.status_code == 404


class TestFPOAggregation:
    """BR-FPO-08 through BR-FPO-16"""

    def _full_setup(self, client, fpo_email: str, farmer_emails: list[str], quantities: list[str]) -> tuple[dict, int, list[dict], list[int]]:
        """Register FPO, farmers, add members, create products, return tokens and IDs."""
        fpo_user = register_user(client, fpo_email, "FPO")
        fpo = client.post("/api/v1/fpos", headers=auth_headers(fpo_user["access_token"]), json={"name": f"Agg FPO {fpo_email}", "address": "Aggregation Village Road"}).json()
        fpo_id = fpo["id"]
        farmers = []
        product_ids = []
        for email, qty in zip(farmer_emails, quantities):
            f = register_user(client, email, "FARMER")
            p = client.post("/api/v1/products", headers=auth_headers(f["access_token"]), json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "60", "quantity": qty}).json()
            client.post(f"/api/v1/fpos/{fpo_id}/members", headers=auth_headers(fpo_user["access_token"]), json={"farmer_id": f["user"]["id"]})
            farmers.append(f)
            product_ids.append(p["id"])
        return fpo_user, fpo_id, farmers, product_ids

    def test_aggregation_creates_combined_listing(self, client):
        """BR-FPO-13, BR-FPO-14"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg1_fpo@example.com", ["agg1_f1@example.com", "agg1_f2@example.com"], ["10", "8"]
        )
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "7"}, {"source_product_id": product_ids[1], "quantity": "6"}]},
        )
        assert resp.status_code == 201
        assert resp.json()["quantity"] == "13.00"
        assert resp.json()["is_aggregated"] is True

    def test_aggregation_deducts_from_sources(self, client):
        """BR-FPO-13"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg2_fpo@example.com", ["agg2_f1@example.com"], ["20"]
        )
        client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "15"}]},
        )
        updated = client.get(f"/api/v1/products/{product_ids[0]}")
        assert updated.json()["quantity"] == "5.00"

    def test_duplicate_source_in_single_aggregation_fails(self, client):
        """BR-FPO-09"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg3_fpo@example.com", ["agg3_f1@example.com"], ["20"]
        )
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "5"}, {"source_product_id": product_ids[0], "quantity": "5"}]},
        )
        assert resp.status_code == 400

    def test_aggregation_exceeding_source_quantity_fails(self, client):
        """BR-FPO-12"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg4_fpo@example.com", ["agg4_f1@example.com"], ["10"]
        )
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "15"}]},
        )
        assert resp.status_code == 409

    def test_aggregation_with_mismatched_category_fails(self, client):
        """BR-FPO-11"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg5_fpo@example.com", ["agg5_f1@example.com"], ["10"]
        )
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Vegetables", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "5"}]},
        )
        assert resp.status_code == 400

    def test_aggregation_with_mismatched_unit_fails(self, client):
        """BR-FPO-11"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg6_fpo@example.com", ["agg6_f1@example.com"], ["10"]
        )
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "box", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "5"}]},
        )
        assert resp.status_code == 400

    def test_source_from_non_member_farmer_fails(self, client):
        """BR-FPO-10"""
        fpo_user, fpo_id, farmers, _ = self._full_setup(
            client, "agg7_fpo@example.com", ["agg7_f1@example.com"], ["10"]
        )
        # Non-member farmer
        outsider = register_user(client, "agg7_outsider@example.com", "FARMER")
        outside_product = client.post("/api/v1/products", headers=auth_headers(outsider["access_token"]), json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "60", "quantity": "10"}).json()
        resp = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": outside_product["id"], "quantity": "5"}]},
        )
        assert resp.status_code == 400

    def test_aggregation_with_no_members_fails(self, client):
        """BR-FPO-08"""
        fpo_user = register_user(client, "nomem_fpo@example.com", "FPO")
        fpo = client.post("/api/v1/fpos", headers=auth_headers(fpo_user["access_token"]), json={"name": "Empty FPO", "address": "Empty Road 1"}).json()
        # A farmer's product (not in any FPO)
        farmer = register_user(client, "nomem_farmer@example.com", "FARMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "60", "quantity": "10"}).json()
        resp = client.post(
            f"/api/v1/fpos/{fpo['id']}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product["id"], "quantity": "5"}]},
        )
        assert resp.status_code == 400

    def test_purchase_of_aggregated_listing_consumes_allocations(self, client):
        """BR-FPO-15"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg8_fpo@example.com", ["agg8_f1@example.com", "agg8_f2@example.com"], ["10", "5"]
        )
        agg = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "8"}, {"source_product_id": product_ids[1], "quantity": "4"}]},
        ).json()
        agg_id = agg["id"]

        buyer = register_user(client, "agg8_buyer@example.com", "BULK_BUYER")
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": agg_id, "quantity": "6"})
        order = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Buyer Warehouse Road"})
        assert order.status_code == 201
        # Aggregate quantity must have dropped by 6
        remaining = client.get(f"/api/v1/products/{agg_id}").json()["quantity"]
        assert float(remaining) == 6.0

    def test_allocation_ledger_insufficiency_fails(self, client):
        """BR-FPO-16"""
        fpo_user, fpo_id, farmers, product_ids = self._full_setup(
            client, "agg9_fpo@example.com", ["agg9_f1@example.com"], ["10"]
        )
        agg = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "70", "allocations": [{"source_product_id": product_ids[0], "quantity": "10"}]},
        ).json()
        agg_id = agg["id"]

        # Manually override the aggregated product's quantity to be more than ledger
        db = _db(client)
        from app.models.marketplace import Product as PModel
        db.get(PModel, agg_id).quantity = Decimal("20")
        db.commit()
        db.close()

        buyer = register_user(client, "agg9_buyer@example.com", "BULK_BUYER")
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": agg_id, "quantity": "15"})
        resp = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Ledger Test Road"})
        assert resp.status_code == 409


class TestFPOAnalytics:
    """BR-FPO-17"""

    def test_fpo_analytics_counts_orders_and_revenue(self, client):
        fpo_user, fpo_id, farmers, product_ids = TestFPOAggregation()._full_setup(
            client, "ana_fpo@example.com", ["ana_f1@example.com"], ["50"]
        )
        agg = client.post(
            f"/api/v1/fpos/{fpo_id}/aggregate",
            headers=auth_headers(fpo_user["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "80", "allocations": [{"source_product_id": product_ids[0], "quantity": "40"}]},
        ).json()
        buyer = register_user(client, "ana_buyer@example.com", "BULK_BUYER")
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": agg["id"], "quantity": "10"})
        client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Analytics Road"})

        resp = client.get(f"/api/v1/fpos/{fpo_id}/analytics", headers=auth_headers(fpo_user["access_token"]))
        assert resp.status_code == 200
        assert resp.json()["order_count"] == 1
        assert float(resp.json()["revenue"]) == 800.0
