"""
test_security_edge_cases.py
───────────────────────────
Deep security tests, negative tests, and edge cases across KisanDirect AI.
"""

import os
from decimal import Decimal
import pytest
from jose import jwt

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.marketplace import CartItem, Product
from app.models.user import User
from app.services.order_state import ORDER_STATES, ALLOWED_TRANSITIONS, ROLE_TRANSITIONS, validate_transition
from tests.conftest import auth_headers, make_user_in_db, register_user, token_for


def _db(client):
    from app.main import app
    return app.state.session_local()


class TestSecurityTokenAttacks:
    """SEC-01, SEC-02, SEC-03"""

    def test_forged_admin_token_is_rejected(self, client):
        """SEC-01: User crafts JWT signed with a different key."""
        fake_token = jwt.encode(
            {"sub": "999", "role": "ADMIN", "token_version": 0},
            "attacker-secret-key-12345",
            algorithm="HS256",
        )
        resp = client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {fake_token}"})
        assert resp.status_code == 401

    def test_none_algorithm_jwt_attack(self, client):
        """SEC-01: Unsigned token or algorithm='none' attack."""
        fake_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIiwicm9sZSI6IkFETUlOIiwidG9rZW5fdmVyc2lvbiI6MH0."
        resp = client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {fake_token}"})
        assert resp.status_code == 401

    def test_privilege_escalation_via_registration_role_override(self, client):
        """SEC-03: Malicious user sends 'ADMIN' or 'LOGISTICS' in registration payload."""
        resp_admin = client.post(
            "/api/v1/auth/register",
            json={"email": "attacker_admin@example.com", "password": "Pass123!Password", "full_name": "Attacker", "role": "ADMIN"},
        )
        assert resp_admin.status_code == 403

        resp_log = client.post(
            "/api/v1/auth/register",
            json={"email": "attacker_log@example.com", "password": "Pass123!Password", "full_name": "Attacker", "role": "LOGISTICS"},
        )
        assert resp_log.status_code == 403

    def test_token_revocation_on_password_change_or_logout(self, client):
        """SEC-02: Revoked token cannot be used again."""
        user = register_user(client, "revoke_sec@example.com", "FARMER")
        token = user["access_token"]
        
        assert client.get("/api/v1/users/me", headers=auth_headers(token)).status_code == 200
        client.post("/api/v1/auth/logout", headers=auth_headers(token))
        assert client.get("/api/v1/users/me", headers=auth_headers(token)).status_code == 401


class TestCrossTenantIDOR:
    """SEC-04"""

    def test_farmer_cannot_modify_another_farmers_product(self, client):
        f1 = register_user(client, "f1_idor@example.com", "FARMER")
        f2 = register_user(client, "f2_idor@example.com", "FARMER")
        
        p = client.post(
            "/api/v1/products",
            headers=auth_headers(f1["access_token"]),
            json={"name": "Farmer1 Crop", "category": "Grains", "unit": "kg", "price_per_unit": "20", "quantity": "50"},
        ).json()

        patch_resp = client.patch(
            f"/api/v1/products/{p['id']}",
            headers=auth_headers(f2["access_token"]),
            json={"price_per_unit": "1.00"},
        )
        assert patch_resp.status_code == 403

        del_resp = client.delete(
            f"/api/v1/products/{p['id']}",
            headers=auth_headers(f2["access_token"]),
        )
        assert del_resp.status_code == 403

    def test_consumer_cannot_cancel_another_consumers_order(self, client):
        farmer = register_user(client, "idor_sf@example.com", "FARMER")
        c1 = register_user(client, "idor_c1@example.com", "CONSUMER")
        c2 = register_user(client, "idor_c2@example.com", "CONSUMER")

        p = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Veg", "category": "Vegetables", "unit": "kg", "price_per_unit": "10", "quantity": "50"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(c1["access_token"]), json={"product_id": p["id"], "quantity": "5"})
        order = client.post("/api/v1/orders", headers=auth_headers(c1["access_token"]), json={"shipping_address": "C1 Home"}).json()

        cancel_resp = client.delete(f"/api/v1/orders/{order['id']}", headers=auth_headers(c2["access_token"]))
        assert cancel_resp.status_code == 403

        view_resp = client.get(f"/api/v1/orders/{order['id']}", headers=auth_headers(c2["access_token"]))
        assert view_resp.status_code == 403


class TestInputValidationAndSQLI:
    """SEC-05, SEC-06"""

    def test_sql_injection_in_search_query_handled_safely(self, client):
        """SEC-05: SQL injection string in query parameter returns empty/safe list without error."""
        resp = client.get("/api/v1/products?search=' OR 1=1; --")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_xss_script_tags_in_product_name(self, client):
        farmer = register_user(client, "xss_farmer@example.com", "FARMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer["access_token"]),
            json={"name": "<script>alert(1)</script>", "category": "Vegetables", "unit": "kg", "price_per_unit": "20", "quantity": "10"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "<script>alert(1)</script>"


class TestExhaustiveStateTransitions:
    """SEC-08"""

    def test_all_invalid_state_leaps_rejected(self):
        """Test exhaustive invalid state combinations."""
        for state_from in ORDER_STATES:
            for state_to in ORDER_STATES:
                allowed_targets = ALLOWED_TRANSITIONS.get(state_from, set())
                if state_to not in allowed_targets:
                    with pytest.raises(Exception):
                        validate_transition(state_from, state_to, "ADMIN")
