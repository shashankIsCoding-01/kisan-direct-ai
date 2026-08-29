"""
test_orders_comprehensive.py
─────────────────────────────
Comprehensive tests for Order placement, state management, and delivery.
"""

import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.core.security import create_access_token, hash_password
from app.models.marketplace import CartItem, Order, Product
from app.models.user import User
from tests.conftest import auth_headers, make_user_in_db, register_user, token_for


def _db(client):
    from app.main import app
    return app.state.session_local()


def _setup_order(client) -> tuple[dict, dict, dict, int]:
    farmer = register_user(client, "ord_farmer@example.com", "FARMER")
    consumer = register_user(client, "ord_consumer@example.com", "CONSUMER")

    product = client.post(
        "/api/v1/products",
        headers=auth_headers(farmer["access_token"]),
        json={"name": "OrderProduct", "category": "Vegetables", "unit": "kg", "price_per_unit": "25", "quantity": "50"},
    ).json()

    client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "10"})
    order = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Test Order Road"}).json()
    return farmer, consumer, product, order["id"]


def _make_logistics(client) -> tuple[User, str]:
    db = _db(client)
    op = User(email="logistics_op@example.com", password_hash=hash_password("SecurePass123!"), full_name="Logistics Op", role="LOGISTICS")
    db.add(op)
    db.commit()
    db.refresh(op)
    db.close()
    return op, create_access_token(str(op.id), "LOGISTICS", op.token_version)


class TestOrderPlacement:
    """BR-ORD-01 through BR-ORD-08"""

    def test_consumer_can_place_order(self, client):
        """BR-ORD-01"""
        farmer = register_user(client, "oplc_farmer@example.com", "FARMER")
        consumer = register_user(client, "oplc_consumer@example.com", "CONSUMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": "30", "quantity": "100"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "5"})
        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Main Road 1"})
        assert resp.status_code == 201
        assert resp.json()["status"] == "PENDING"

    def test_bulk_buyer_can_place_order(self, client):
        """BR-ORD-01"""
        farmer = register_user(client, "oplb_farmer@example.com", "FARMER")
        buyer = register_user(client, "oplb_buyer@example.com", "BULK_BUYER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Wheat", "category": "Grains", "unit": "kg", "price_per_unit": "20", "quantity": "200"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": product["id"], "quantity": "50"})
        resp = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Warehouse Ave 5"})
        assert resp.status_code == 201

    def test_farmer_cannot_place_order(self, client):
        """BR-ORD-01"""
        farmer = register_user(client, "oplf_farmer@example.com", "FARMER")
        resp = client.post("/api/v1/orders", headers=auth_headers(farmer["access_token"]), json={"shipping_address": "Valid Shipping Road"})
        assert resp.status_code == 403

    def test_empty_cart_checkout_fails(self, client):
        """BR-ORD-02"""
        consumer = register_user(client, "empty_cart@example.com", "CONSUMER")
        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Test Road"})
        assert resp.status_code == 400

    def test_mixed_seller_cart_checkout_fails(self, client):
        """BR-ORD-03"""
        farmer1 = register_user(client, "mixedf1@example.com", "FARMER")
        farmer2 = register_user(client, "mixedf2@example.com", "FARMER")
        consumer = register_user(client, "mixedc@example.com", "CONSUMER")

        p1 = client.post("/api/v1/products", headers=auth_headers(farmer1["access_token"]), json={"name": "Tomato", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "50"}).json()
        p2 = client.post("/api/v1/products", headers=auth_headers(farmer2["access_token"]), json={"name": "Onion", "category": "Vegetables", "unit": "kg", "price_per_unit": "18", "quantity": "50"}).json()

        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": p1["id"], "quantity": "2"})
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": p2["id"], "quantity": "2"})

        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Mixed Road"})
        assert resp.status_code == 400

    def test_insufficient_stock_at_checkout_fails(self, client):
        """BR-ORD-04"""
        farmer = register_user(client, "insuf_ord_farmer@example.com", "FARMER")
        consumer = register_user(client, "insuf_ord_consumer@example.com", "CONSUMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Chilli", "category": "Vegetables", "unit": "kg", "price_per_unit": "50", "quantity": "5"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "5"})

        db = _db(client)
        db.get(Product, product["id"]).quantity = 2
        db.commit()
        db.close()

        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Chilli Road"})
        assert resp.status_code == 409

    def test_cart_is_cleared_after_order(self, client):
        """BR-ORD-05"""
        farmer = register_user(client, "cleared_farmer@example.com", "FARMER")
        consumer = register_user(client, "cleared_consumer@example.com", "CONSUMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Brinjal", "category": "Vegetables", "unit": "kg", "price_per_unit": "15", "quantity": "20"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "3"})
        client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Clear Test Road"})
        cart = client.get("/api/v1/cart", headers=auth_headers(consumer["access_token"]))
        assert cart.json()["items"] == []

    def test_duplicate_checkout_fails_empty_cart(self, client):
        """BR-ORD-06"""
        farmer = register_user(client, "dup_ord_farmer@example.com", "FARMER")
        consumer = register_user(client, "dup_ord_consumer@example.com", "CONSUMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Peas", "category": "Vegetables", "unit": "kg", "price_per_unit": "22", "quantity": "10"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "2"})
        client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "First Order Road"})
        duplicate = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Second Order Road"})
        assert duplicate.status_code == 400

    def test_order_total_amount_is_correct(self, client):
        """BR-ORD-07"""
        farmer = register_user(client, "total_farmer@example.com", "FARMER")
        consumer = register_user(client, "total_consumer@example.com", "CONSUMER")
        product = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "CornField", "category": "Grains", "unit": "kg", "price_per_unit": "25", "quantity": "100"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "8"})
        order = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Amount Check Road"}).json()
        assert float(order["total_amount"]) == 8 * 25

    def test_short_shipping_address_rejected(self, client):
        consumer = register_user(client, "short_addr@example.com", "CONSUMER")
        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Hi"})
        assert resp.status_code == 422


class TestOrderStateTransitions:
    """BR-ORD-09 through BR-ORD-13"""

    def test_full_lifecycle_pending_to_delivered(self, client):
        """BR-ORD-09"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])

        assert client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"}).status_code == 200
        assert client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "PREPARING"}).status_code == 200
        assert client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"}).status_code == 200

        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()
        delivery_id = delivery["id"]

        assert client.patch(f"/api/v1/deliveries/{delivery_id}/status", headers=auth_headers(op_token), json={"status": "PICKED_UP"}).status_code == 200
        assert client.patch(f"/api/v1/deliveries/{delivery_id}/status", headers=auth_headers(op_token), json={"status": "DELIVERED"}).status_code == 200

        final_order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(consumer["access_token"])).json()
        assert final_order["status"] == "DELIVERED"

    def test_skip_state_transition_fails(self, client):
        """BR-ORD-10"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(farmer["access_token"]), json={"status": "PREPARING"})
        assert resp.status_code in {403, 409}

    def test_backward_transition_fails(self, client):
        """BR-ORD-10"""
        farmer, consumer, product, order_id = _setup_order(client)
        client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(farmer["access_token"]), json={"status": "CONFIRMED"})
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(farmer["access_token"]), json={"status": "PENDING"})
        assert resp.status_code in {403, 409}

    def test_delivered_order_cannot_be_changed(self, client):
        """BR-ORD-10"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"})
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "PREPARING"})
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"})
        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()
        client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "PICKED_UP"})
        client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "DELIVERED"})
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "CANCELLED"})
        assert resp.status_code in {403, 409}

    def test_cancelled_order_cannot_be_transitioned(self, client):
        """BR-ORD-10"""
        farmer, consumer, product, order_id = _setup_order(client)
        consumer_hdrs = auth_headers(consumer["access_token"])
        client.patch(f"/api/v1/orders/{order_id}/status", headers=consumer_hdrs, json={"status": "CANCELLED"})
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(farmer["access_token"]), json={"status": "CONFIRMED"})
        assert resp.status_code in {403, 409}

    def test_consumer_cannot_confirm_order(self, client):
        """BR-ORD-11"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(consumer["access_token"]), json={"status": "CONFIRMED"})
        assert resp.status_code == 403

    def test_logistics_cannot_confirm_order(self, client):
        """BR-ORD-11"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(op_token), json={"status": "CONFIRMED"})
        assert resp.status_code == 403

    def test_unknown_status_string_is_rejected(self, client):
        """BR-ORD-12"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.patch(f"/api/v1/orders/{order_id}/status", headers=auth_headers(farmer["access_token"]), json={"status": "UNICORN"})
        assert resp.status_code == 422

    def test_only_buyer_can_cancel_order(self, client):
        """BR-ORD-13"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers(farmer["access_token"]))
        assert resp.status_code == 403

    def test_buyer_can_cancel_pending_order(self, client):
        """BR-ORD-13"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.delete(f"/api/v1/orders/{order_id}", headers=auth_headers(consumer["access_token"]))
        assert resp.status_code == 200
        order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(consumer["access_token"])).json()
        assert order["status"] == "CANCELLED"


class TestOrderVisibility:
    """BR-ORD-14 through BR-ORD-16"""

    def test_seller_can_view_own_incoming_orders(self, client):
        """BR-ORD-14"""
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.get("/api/v1/orders/sales", headers=auth_headers(farmer["access_token"]))
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert order_id in ids

    def test_another_seller_cannot_view_incoming_orders(self, client):
        farmer, consumer, product, order_id = _setup_order(client)
        other_farmer = register_user(client, "other_sel@example.com", "FARMER")
        resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(other_farmer["access_token"]))
        assert resp.status_code == 403

    def test_admin_can_view_all_orders(self, client):
        """BR-ORD-16"""
        _setup_order(client)
        db = _db(client)
        admin = User(email="admin_view@example.com", password_hash=hash_password("SecurePass123!"), full_name="Admin", role="ADMIN")
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin_token = create_access_token(str(admin.id), "ADMIN", admin.token_version)
        db.close()
        resp = client.get("/api/v1/orders/all", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_consumer_cannot_view_all_orders(self, client):
        consumer = register_user(client, "consumer_all@example.com", "CONSUMER")
        resp = client.get("/api/v1/orders/all", headers=auth_headers(consumer["access_token"]))
        assert resp.status_code == 403


class TestDeliveryAssignment:
    """BR-ORD-17 through BR-ORD-22"""

    def test_delivery_assigned_to_ready_for_pickup_order(self, client):
        """BR-ORD-17"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"})
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "PREPARING"})
        client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"})

        resp = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id})
        assert resp.status_code == 201
        assert resp.json()["status"] == "ASSIGNED"

    def test_delivery_requires_ready_for_pickup_state(self, client):
        """BR-ORD-17"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        resp = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id})
        assert resp.status_code == 409

    def test_duplicate_delivery_assignment_rejected(self, client):
        """BR-ORD-18"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        for status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": status})
        client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id})
        dup = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id})
        assert dup.status_code == 409

    def test_pickup_sets_order_in_transit(self, client):
        """BR-ORD-19"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        for status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": status})
        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()
        client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "PICKED_UP"})
        order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(consumer["access_token"])).json()
        assert order["status"] == "IN_TRANSIT"

    def test_delivery_completion_sets_order_delivered(self, client):
        """BR-ORD-20"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        for status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": status})
        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()
        client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "PICKED_UP"})
        client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "DELIVERED"})
        order = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers(consumer["access_token"])).json()
        assert order["status"] == "DELIVERED"

    def test_delivery_cancellation_via_status_is_blocked(self, client):
        """BR-ORD-21"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        for status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": status})
        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()
        resp = client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op_token), json={"status": "CANCELLED"})
        assert resp.status_code == 409

    def test_other_operator_cannot_update_delivery(self, client):
        """BR-ORD-22"""
        farmer, consumer, product, order_id = _setup_order(client)
        op, op_token = _make_logistics(client)
        farmer_hdrs = auth_headers(farmer["access_token"])
        for status in ["CONFIRMED", "PREPARING", "READY_FOR_PICKUP"]:
            client.patch(f"/api/v1/orders/{order_id}/status", headers=farmer_hdrs, json={"status": status})
        delivery = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(op_token), json={"logistics_operator_id": op.id}).json()

        db = _db(client)
        op2 = User(email="op2_delivery@example.com", password_hash=hash_password("SecurePass123!"), full_name="Operator 2", role="LOGISTICS")
        db.add(op2)
        db.commit()
        db.refresh(op2)
        op2_token = create_access_token(str(op2.id), "LOGISTICS", op2.token_version)
        db.close()

        resp = client.patch(f"/api/v1/deliveries/{delivery['id']}/status", headers=auth_headers(op2_token), json={"status": "PICKED_UP"})
        assert resp.status_code == 403

    def test_consumer_cannot_assign_delivery(self, client):
        farmer, consumer, product, order_id = _setup_order(client)
        resp = client.post(f"/api/v1/orders/{order_id}/delivery", headers=auth_headers(consumer["access_token"]), json={"logistics_operator_id": 1})
        assert resp.status_code == 403
