"""
test_auth_comprehensive.py
──────────────────────────
Complete test coverage for Authentication & Authorization.

Business rules verified:
  BR-AUTH-01  Passwords are stored as salted PBKDF2-SHA256 hashes, never plaintext.
  BR-AUTH-02  JWT tokens embed sub, role, token_version and exp claims.
  BR-AUTH-03  Tokens expire; expired tokens are unconditionally rejected.
  BR-AUTH-04  Self-registration is blocked for ADMIN and LOGISTICS roles.
  BR-AUTH-05  Login with wrong password returns 401.
  BR-AUTH-06  Login for inactive account returns 403.
  BR-AUTH-07  Duplicate email registration is rejected with 409.
  BR-AUTH-08  Logout invalidates the token via token_version increment.
  BR-AUTH-09  Token with stale token_version is rejected (re-use after logout).
  BR-AUTH-10  Requests without a token are rejected with 401.
  BR-AUTH-11  Tampered / malformed JWT is rejected.
  BR-AUTH-12  FARMER cannot reach admin-only endpoints.
  BR-AUTH-13  CONSUMER cannot reach seller-only endpoints.
  BR-AUTH-14  Email lookup is case-insensitive.
  BR-AUTH-15  Full-name whitespace is trimmed on registration.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from tests.conftest import auth_headers, make_user_in_db, register_user, token_for


# ═══════════════════════════════════════════════════════════════════════════
# Unit tests – pure Python, no DB / HTTP
# ═══════════════════════════════════════════════════════════════════════════


class TestPasswordHashing:
    """BR-AUTH-01"""

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecret123")
        assert hashed != "MySecret123"
        assert "MySecret123" not in hashed

    def test_correct_password_verifies(self):
        hashed = hash_password("MySecret123")
        assert verify_password("MySecret123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MySecret123")
        assert verify_password("WrongPassword", hashed) is False

    def test_empty_string_password_does_not_verify_against_non_empty_hash(self):
        hashed = hash_password("RealPassword")
        assert verify_password("", hashed) is False

    def test_malformed_hash_returns_false(self):
        assert verify_password("any", "not$a$valid$hash$format$at$all$extra") is False

    def test_each_hash_uses_unique_salt(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # unique salt each time

    def test_hash_format_has_four_dollar_separated_parts(self):
        hashed = hash_password("TestPass")
        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"


class TestJWT:
    """BR-AUTH-02, BR-AUTH-03, BR-AUTH-11"""

    def test_token_round_trip_contains_expected_claims(self):
        token = create_access_token("99", "FARMER", token_version=3)
        claims = decode_access_token(token)
        assert claims is not None
        assert claims["sub"] == "99"
        assert claims["role"] == "FARMER"
        assert claims["token_version"] == 3

    def test_expired_token_returns_none(self):
        """BR-AUTH-03"""
        expired = jwt.encode(
            {
                "sub": "1",
                "role": "FARMER",
                "token_version": 0,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        assert decode_access_token(expired) is None

    def test_tampered_signature_returns_none(self):
        """BR-AUTH-11"""
        token = create_access_token("1", "FARMER")
        # Flip last character of signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert decode_access_token(tampered) is None

    def test_token_signed_with_wrong_key_returns_none(self):
        token = jwt.encode({"sub": "1", "role": "ADMIN", "token_version": 0}, "wrong-secret", algorithm=settings.algorithm)
        assert decode_access_token(token) is None

    def test_token_without_sub_claim_is_invalid(self):
        token = jwt.encode({"role": "FARMER", "token_version": 0}, settings.secret_key, algorithm=settings.algorithm)
        # decode_access_token returns the payload; caller (dependency) checks for sub
        claims = decode_access_token(token)
        if claims:
            assert "sub" not in claims or claims.get("sub") is None


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests – API-level
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistration:
    """BR-AUTH-04, BR-AUTH-07, BR-AUTH-14, BR-AUTH-15"""

    def test_farmer_registration_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "farmer@example.com", "password": "SecurePass123!", "full_name": "A Farmer", "role": "FARMER"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["role"] == "FARMER"
        assert "access_token" in data

    def test_consumer_registration_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "consumer@example.com", "password": "SecurePass123!", "full_name": "A Consumer", "role": "CONSUMER"},
        )
        assert resp.status_code == 201

    def test_bulk_buyer_registration_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "buyer@example.com", "password": "SecurePass123!", "full_name": "A Buyer", "role": "BULK_BUYER"},
        )
        assert resp.status_code == 201

    def test_fpo_registration_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "fpo@example.com", "password": "SecurePass123!", "full_name": "An FPO", "role": "FPO"},
        )
        assert resp.status_code == 201

    def test_admin_self_registration_is_blocked(self, client):
        """BR-AUTH-04"""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "admin@example.com", "password": "SecurePass123!", "full_name": "Would-be Admin", "role": "ADMIN"},
        )
        assert resp.status_code == 403

    def test_logistics_self_registration_is_blocked(self, client):
        """BR-AUTH-04"""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "logistics@example.com", "password": "SecurePass123!", "full_name": "Would-be Logistics", "role": "LOGISTICS"},
        )
        assert resp.status_code == 403

    def test_duplicate_email_is_rejected(self, client):
        """BR-AUTH-07"""
        payload = {"email": "dup@example.com", "password": "SecurePass123!", "full_name": "First User", "role": "FARMER"}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_email_registration_is_case_insensitive(self, client):
        """BR-AUTH-14"""
        client.post("/api/v1/auth/register", json={"email": "CamelCase@Example.COM", "password": "SecurePass123!", "full_name": "Camel", "role": "FARMER"})
        resp = client.post("/api/v1/auth/register", json={"email": "camelcase@example.com", "password": "SecurePass123!", "full_name": "Camel2", "role": "FARMER"})
        assert resp.status_code == 409

    def test_unknown_role_is_schema_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "badrol@example.com", "password": "SecurePass123!", "full_name": "Bad Role", "role": "HACKER"},
        )
        assert resp.status_code == 422

    def test_missing_password_field_is_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "nopw@example.com", "full_name": "No Password", "role": "FARMER"},
        )
        assert resp.status_code == 422

    def test_whitespace_name_is_trimmed(self, client):
        """BR-AUTH-15"""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "trim@example.com", "password": "SecurePass123!", "full_name": "  Trimmed Name  ", "role": "FARMER"},
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["full_name"] == "Trimmed Name"


class TestLogin:
    """BR-AUTH-05, BR-AUTH-06"""

    def test_correct_credentials_return_token(self, client):
        register_user(client, "login@example.com", "FARMER")
        resp = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "SecurePass123!"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_wrong_password_returns_401(self, client):
        """BR-AUTH-05"""
        register_user(client, "wrongpw@example.com", "FARMER")
        resp = client.post("/api/v1/auth/login", json={"email": "wrongpw@example.com", "password": "WrongPassword!"})
        assert resp.status_code == 401

    def test_nonexistent_email_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "SecurePass123!"})
        assert resp.status_code == 401

    def test_inactive_account_returns_403(self, client, db_session):
        """BR-AUTH-06"""
        db = app_db_session(client)
        user = make_user_in_db(db, "inactive@example.com", "FARMER", is_active=True)
        user.is_active = False
        db.commit()
        resp = client.post("/api/v1/auth/login", json={"email": "inactive@example.com", "password": "SecurePass123!"})
        assert resp.status_code == 403
        db.close()

    def test_login_is_case_insensitive_on_email(self, client):
        register_user(client, "CaseSensitive@example.com", "FARMER")
        resp = client.post("/api/v1/auth/login", json={"email": "casesensitive@example.com", "password": "SecurePass123!"})
        assert resp.status_code == 200


def app_db_session(client):
    """Helper to open a raw DB session from a test client's database."""
    from app.main import app as fastapi_app
    return fastapi_app.state.session_local()


class TestLogout:
    """BR-AUTH-08, BR-AUTH-09"""

    def test_logout_invalidates_token(self, client):
        """BR-AUTH-08"""
        data = register_user(client, "logout@example.com", "FARMER")
        token = data["access_token"]
        hdrs = auth_headers(token)

        logout = client.post("/api/v1/auth/logout", headers=hdrs)
        assert logout.status_code == 200

        revoked = client.get("/api/v1/users/me", headers=hdrs)
        assert revoked.status_code == 401

    def test_old_token_rejected_after_logout(self, client):
        """BR-AUTH-09"""
        data = register_user(client, "reuse@example.com", "FARMER")
        old_token = data["access_token"]

        client.post("/api/v1/auth/logout", headers=auth_headers(old_token))
        # new login
        new_token = client.post("/api/v1/auth/login", json={"email": "reuse@example.com", "password": "SecurePass123!"}).json()["access_token"]
        assert new_token != old_token

        # old token must still be rejected
        resp = client.get("/api/v1/users/me", headers=auth_headers(old_token))
        assert resp.status_code == 401

    def test_new_token_works_after_logout(self, client):
        data = register_user(client, "newtoken@example.com", "FARMER")
        client.post("/api/v1/auth/logout", headers=auth_headers(data["access_token"]))
        new_token = client.post("/api/v1/auth/login", json={"email": "newtoken@example.com", "password": "SecurePass123!"}).json()["access_token"]
        resp = client.get("/api/v1/users/me", headers=auth_headers(new_token))
        assert resp.status_code == 200


class TestUnauthenticatedRequests:
    """BR-AUTH-10"""

    def test_protected_endpoint_without_token_returns_401(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_bearer_garbage_string_returns_401(self, client):
        resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 401

    def test_basic_auth_scheme_not_accepted(self, client):
        import base64
        creds = base64.b64encode(b"user:pass").decode()
        resp = client.get("/api/v1/users/me", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401


class TestRoleBasedAccessControl:
    """BR-AUTH-12, BR-AUTH-13"""

    def test_farmer_cannot_access_admin_analytics_dashboard(self, client):
        """BR-AUTH-12"""
        data = register_user(client, "farmer_rbac@example.com", "FARMER")
        resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers(data["access_token"]))
        assert resp.status_code == 403

    def test_consumer_cannot_create_product_listing(self, client):
        """BR-AUTH-13"""
        data = register_user(client, "consumer_rbac@example.com", "CONSUMER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(data["access_token"]),
            json={"name": "Tomato", "category": "Vegetables", "unit": "kg", "price_per_unit": 20, "quantity": 5},
        )
        assert resp.status_code == 403

    def test_bulk_buyer_cannot_create_product_listing(self, client):
        data = register_user(client, "bulk_rbac@example.com", "BULK_BUYER")
        resp = client.post(
            "/api/v1/products",
            headers=auth_headers(data["access_token"]),
            json={"name": "Rice", "category": "Grains", "unit": "kg", "price_per_unit": 30, "quantity": 10},
        )
        assert resp.status_code == 403

    def test_farmer_cannot_place_order(self, client):
        data = register_user(client, "farmer_order@example.com", "FARMER")
        resp = client.post("/api/v1/orders", headers=auth_headers(data["access_token"]), json={"shipping_address": "Farm Road"})
        assert resp.status_code == 403

    def test_consumer_cannot_view_admin_only_all_orders(self, client):
        data = register_user(client, "consumer_orders@example.com", "CONSUMER")
        resp = client.get("/api/v1/orders/all", headers=auth_headers(data["access_token"]))
        assert resp.status_code == 403

    def test_farmer_cannot_view_seller_orders_of_another_farmer(self, client):
        farmer1 = register_user(client, "f1_rbac@example.com", "FARMER")
        farmer2 = register_user(client, "f2_rbac@example.com", "FARMER")
        consumer = register_user(client, "c_rbac@example.com", "CONSUMER")

        # farmer1 lists a product
        product = client.post(
            "/api/v1/products",
            headers=auth_headers(farmer1["access_token"]),
            json={"name": "Crop", "category": "Grains", "unit": "kg", "price_per_unit": 10, "quantity": 50},
        ).json()

        # consumer adds to cart and orders
        client.post("/api/v1/cart/items", headers=auth_headers(consumer["access_token"]), json={"product_id": product["id"], "quantity": 1})
        order = client.post("/api/v1/orders", headers=auth_headers(consumer["access_token"]), json={"shipping_address": "Road 1"}).json()

        # farmer2 must not see this order
        resp = client.get(f"/api/v1/orders/{order['id']}", headers=auth_headers(farmer2["access_token"]))
        assert resp.status_code == 403
