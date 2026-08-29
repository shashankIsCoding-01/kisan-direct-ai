"""
test_products_inventory.py
──────────────────────────
Comprehensive tests for Products and Inventory management.
"""

import os
from decimal import Decimal
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from tests.conftest import auth_headers, make_product, make_user_in_db, register_user, token_for


def _db_session(client):
    from app.main import app as fastapi_app
    return fastapi_app.state.session_local()


class TestProductCreation:
    """BR-PROD-01, BR-PROD-03"""

    def test_farmer_can_create_listing(self, client):
        farmer = register_user(client, "prod_farmer@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Fresh Tomato", "category": "Vegetables", "unit": "kg", "price_per_unit": "28.00", "quantity": "50"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Fresh Tomato"
        assert data["seller_id"] == farmer["user"]["id"]

    def test_fpo_user_can_create_listing(self, client):
        fpo = register_user(client, "prod_fpo@example.com", "FPO")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(fpo["access_token"]),
            json={"name": "Mango", "category": "Fruits", "unit": "kg", "price_per_unit": "60.00", "quantity": "200"},
        )
        assert resp.status_code == 201

    def test_consumer_cannot_create_listing(self, client):
        """BR-PROD-01"""
        consumer = register_user(client, "prod_consumer@example.com", "CONSUMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(consumer["access_token"]),
            json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": "30", "quantity": "10"},
        )
        assert resp.status_code == 403

    def test_bulk_buyer_cannot_create_listing(self, client):
        buyer = register_user(client, "prod_buyer@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(buyer["access_token"]),
            json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": "30", "quantity": "10"},
        )
        assert resp.status_code == 403

    def test_negative_price_is_rejected(self, client):
        """BR-PROD-03"""
        farmer = register_user(client, "neg_price@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Onion", "category": "Vegetables", "unit": "kg", "price_per_unit": "-10", "quantity": "100"},
        )
        assert resp.status_code == 422

    def test_zero_price_is_rejected(self, client):
        farmer = register_user(client, "zero_price@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Potato", "category": "Vegetables", "unit": "kg", "price_per_unit": "0", "quantity": "50"},
        )
        assert resp.status_code == 422

    def test_negative_quantity_is_rejected(self, client):
        farmer = register_user(client, "neg_qty@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Wheat", "category": "Grains", "unit": "kg", "price_per_unit": "20", "quantity": "-5"},
        )
        assert resp.status_code == 422

    def test_invalid_quality_value_is_rejected(self, client):
        farmer = register_user(client, "inv_quality@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": "25", "quantity": "50", "quality": "TRASH"},
        )
        assert resp.status_code == 422

    def test_name_too_short_is_rejected(self, client):
        farmer = register_user(client, "short_name@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "T", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "10"},
        )
        assert resp.status_code == 422


class TestProductUpdate:
    """BR-PROD-02"""

    def test_owner_can_update_own_listing(self, client):
        farmer = register_user(client, "upd_farmer@example.com", "FARMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Potato", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "100"},
        ).json()
        resp = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=auth_headers(farmer["access_token"]),
            json={"price_per_unit": "25", "quantity": "80"},
        )
        assert resp.status_code == 200
        assert float(resp.json()["price_per_unit"]) == 25.0
        assert float(resp.json()["quantity"]) == 80.0

    def test_non_owner_cannot_update_listing(self, client):
        """BR-PROD-02"""
        owner = register_user(client, "owner_farmer@example.com", "FARMER")
        other = register_user(client, "other_farmer@example.com", "FARMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(owner["access_token"]),
            json={"name": "Carrot", "category": "Vegetables", "unit": "kg", "price_per_unit": "15", "quantity": "50"},
        ).json()
        resp = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=auth_headers(other["access_token"]),
            json={"price_per_unit": "5"},
        )
        assert resp.status_code == 403

    def test_consumer_cannot_update_any_listing(self, client):
        farmer = register_user(client, "farmer_upd2@example.com", "FARMER")
        consumer = register_user(client, "consumer_upd@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Spinach", "category": "Vegetables", "unit": "kg", "price_per_unit": "12", "quantity": "30"},
        ).json()
        resp = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=auth_headers(consumer["access_token"]),
            json={"price_per_unit": "5"},
        )
        assert resp.status_code == 403

    def test_nonexistent_product_returns_404(self, client):
        farmer = register_user(client, "farmer_notfound@example.com", "FARMER")
        resp = client.patch(
            "/api/v1/products/99999",
            headers=auth_headers(farmer["access_token"]),
            json={"price_per_unit": "10"},
        )
        assert resp.status_code in {403, 404}


class TestProductDeactivation:
    """BR-PROD-05, BR-PROD-06"""

    def test_deactivating_removes_from_browse(self, client):
        """BR-PROD-05"""
        farmer = register_user(client, "deact_farmer@example.com", "FARMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Broccoli", "category": "Vegetables", "unit": "kg", "price_per_unit": "40", "quantity": "20"},
        ).json()
        browse_before = client.get("/api/v1/products?search=broccoli")
        assert browse_before.json()["total"] == 1

        client.delete(f"/api/v1/products/{product['id']}", headers=auth_headers(farmer["access_token"]))

        browse_after = client.get("/api/v1/products?search=broccoli")
        assert browse_after.json()["total"] == 0


class TestProductBrowsingAndSearch:
    """BR-PROD-07, BR-PROD-08, BR-PROD-15"""

    def test_search_by_name_is_case_insensitive(self, client):
        farmer = register_user(client, "srch_farmer@example.com", "FARMER")
        client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Fresh Spinach", "category": "Vegetables", "unit": "kg", "price_per_unit": "18", "quantity": "40"},
        )
        resp = client.get("/api/v1/products?search=spinach")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_category_filter(self, client):
        farmer = register_user(client, "cat_farmer@example.com", "FARMER")
        client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Apple", "category": "Fruits", "unit": "kg", "price_per_unit": "80", "quantity": "30"})
        client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": "30", "quantity": "100"})

        resp = client.get("/api/v1/products?category=Fruits")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category"] == "Fruits"

    def test_price_asc_sort_returns_cheapest_first(self, client):
        farmer = register_user(client, "sort_farmer@example.com", "FARMER")
        client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "PricedLow", "category": "Vegetables", "unit": "kg", "price_per_unit": "10", "quantity": "5"})
        client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "PricedHigh", "category": "Vegetables", "unit": "kg", "price_per_unit": "100", "quantity": "5"})

        resp = client.get("/api/v1/products?sort=price_asc")
        items = resp.json()["items"]
        prices = [float(i["price_per_unit"]) for i in items]
        assert prices == sorted(prices)

    def test_zero_quantity_product_hidden_from_browse(self, client):
        """BR-PROD-15"""
        farmer = register_user(client, "zero_qty@example.com", "FARMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "EmptyStock", "category": "Grains", "unit": "kg", "price_per_unit": "25", "quantity": "1"},
        ).json()
        db = _db_session(client)
        from app.models.marketplace import Product as PModel
        db_product = db.get(PModel, product["id"])
        db_product.quantity = Decimal("0")
        db.commit()
        db.close()

        resp = client.get("/api/v1/products?search=EmptyStock")
        assert resp.json()["total"] == 0

    def test_pagination_page_2_returns_different_items(self, client):
        """BR-PROD-08"""
        farmer = register_user(client, "page_farmer@example.com", "FARMER")
        for i in range(5):
            client.post(
                "/api/v1/products",
                headers=auth_headers(farmer["access_token"]),
                json={"name": f"PageProduct{i}", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "10"},
            )
        page1 = client.get("/api/v1/products?page=1&limit=3").json()
        page2 = client.get("/api/v1/products?page=2&limit=3").json()
        ids_p1 = {i["id"] for i in page1["items"]}
        ids_p2 = {i["id"] for i in page2["items"]}
        assert ids_p1.isdisjoint(ids_p2)


class TestCart:
    """BR-PROD-09 through BR-PROD-13"""

    def test_consumer_can_add_item_to_cart(self, client):
        farmer = register_user(client, "cart_farmer@example.com", "FARMER")
        consumer = register_user(client, "cart_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Tomato", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "50"},
        ).json()
        resp = client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "5"})
        assert resp.status_code == 201
        assert float(resp.json()["quantity"]) == 5.0

    def test_farmer_cannot_add_to_cart(self, client):
        """BR-PROD-09"""
        farmer = register_user(client, "cartf_farmer@example.com", "FARMER")
        another = register_user(client, "cartf_seller@example.com", "FARMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(another["access_token"]),
            json={"name": "Onion", "category": "Vegetables", "unit": "kg", "price_per_unit": "15", "quantity": "40"},
        ).json()
        resp = client.post("/api/v1/cart/items", headers=auth_headers(farmer["access_token"]), json={"product_id": product["id"], "quantity": "2"})
        assert resp.status_code == 403

    def test_adding_more_than_stock_to_cart_fails(self, client):
        """BR-PROD-10"""
        farmer = register_user(client, "over_farmer@example.com", "FARMER")
        consumer = register_user(client, "over_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Pepper", "category": "Vegetables", "unit": "kg", "price_per_unit": "30", "quantity": "5"},
        ).json()
        resp = client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "10"})
        assert resp.status_code == 409

    def test_same_product_added_twice_accumulates(self, client):
        """BR-PROD-11"""
        farmer = register_user(client, "accum_farmer@example.com", "FARMER")
        consumer = register_user(client, "accum_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Garlic", "category": "Vegetables", "unit": "kg", "price_per_unit": "80", "quantity": "20"},
        ).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "3"})
        resp = client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "4"})
        assert resp.status_code == 201
        assert float(resp.json()["quantity"]) == 7.0

    def test_accumulated_cart_quantity_exceeding_stock_fails(self, client):
        """BR-PROD-12"""
        farmer = register_user(client, "acclim_farmer@example.com", "FARMER")
        consumer = register_user(client, "acclim_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Ginger", "category": "Vegetables", "unit": "kg", "price_per_unit": "100", "quantity": "5"},
        ).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "4"})
        resp = client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "3"})
        assert resp.status_code == 409

    def test_cart_is_private_to_buyer(self, client):
        """BR-PROD-13"""
        farmer = register_user(client, "priv_farmer@example.com", "FARMER")
        buyer1 = register_user(client, "priv_buyer1@example.com", "CONSUMER")
        buyer2 = register_user(client, "priv_buyer2@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "Cabbage", "category": "Vegetables", "unit": "kg", "price_per_unit": "12", "quantity": "30"},
        ).json()
        client.post("/api/v1/cart/items", headers=auth_headers(buyer1["access_token"]), json={"product_id": product["id"], "quantity": "5"})
        cart2 = client.get("/api/v1/cart", headers=auth_headers(buyer2["access_token"]))
        assert cart2.status_code == 200
        assert cart2.json()["items"] == []


class TestInventoryDecrement:
    """BR-PROD-14"""

    def test_order_decrements_product_inventory_exactly(self, client):
        farmer = register_user(client, "inv_farmer@example.com", "FARMER")
        consumer = register_user(client, "inv_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "InventoryProduct", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "30"},
        ).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "10"})
        client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Test Road 1"})
        updated = client.get(f"/api/v1/products/{product['id']}")
        assert float(updated.json()["quantity"]) == 20.0

    def test_insufficient_stock_prevents_order(self, client):
        farmer = register_user(client, "insuf_farmer@example.com", "FARMER")
        consumer = register_user(client, "insuf_consumer@example.com", "CONSUMER")
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "LimitedStock", "category": "Grains", "unit": "kg", "price_per_unit": "25", "quantity": "3"},
        ).json()
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": "3"})

        db = _db_session(client)
        from app.models.marketplace import Product as PModel
        db_p = db.get(PModel, product["id"])
        db_p.quantity = Decimal("1")
        db.commit()
        db.close()

        resp = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Test Road 2"})
        assert resp.status_code == 409
