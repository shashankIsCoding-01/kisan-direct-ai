"""
test_logistics_routing_comprehensive.py
───────────────────────────────────────
Comprehensive test coverage for Logistics Management and Route Optimization.
"""

import os
from decimal import Decimal
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-never-use-in-prod")

from app.core.security import create_access_token, hash_password
from app.models.marketplace import Delivery, DeliveryLocation, Order, OrderItem, PickupLocation, Vehicle
from app.models.user import User
from app.schemas.logistics import RouteOptimizeRequest
from app.services.logistics_service import LogisticsService
from app.services.routing import HaversineRoutingProvider, nearest_neighbor, route_distance
from tests.conftest import auth_headers, make_delivery_location, make_product, make_user_in_db, make_vehicle, register_user, token_for


def _db(client):
    from app.main import app
    return app.state.session_local()


def _create_logistics_user(client, email: str = "log_op@example.com") -> tuple[User, str]:
    db = _db(client)
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        full_name="Logistics Specialist",
        role="LOGISTICS",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), "LOGISTICS", user.token_version)
    db.close()
    return user, token


def _create_admin_user(client, email: str = "log_admin@example.com") -> tuple[User, str]:
    db = _db(client)
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        full_name="Logistics Admin",
        role="ADMIN",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), "ADMIN", user.token_version)
    db.close()
    return user, token


class TestRoutingUnit:
    """BR-LOG-13, BR-LOG-14"""

    def test_haversine_provider_name_and_zero_distance(self):
        provider = HaversineRoutingProvider()
        assert provider.name == "haversine_straight_line"
        dist = provider.distance_km((12.9716, 77.5946), (12.9716, 77.5946))
        assert dist == 0.0

    def test_haversine_distance_known_coordinates(self):
        provider = HaversineRoutingProvider()
        dist = provider.distance_km((12.9716, 77.5946), (12.2958, 76.6394))
        assert 120 < dist < 150

    def test_route_distance_includes_depot_roundtrip(self):
        provider = HaversineRoutingProvider()
        depot = (0.0, 0.0)
        stops = [(1.0, 0.0), (2.0, 0.0)]
        total_dist = route_distance(stops, depot, provider)
        assert total_dist > 0

    def test_nearest_neighbor_ordering(self):
        provider = HaversineRoutingProvider()
        depot = (0.0, 0.0)
        stops = [
            {"delivery_id": 1, "coordinate": (10.0, 0.0)},
            {"delivery_id": 2, "coordinate": (1.0, 0.0)},
            {"delivery_id": 3, "coordinate": (5.0, 0.0)},
        ]
        ordered = nearest_neighbor(stops, depot, provider)
        order_ids = [s["delivery_id"] for s in ordered]
        assert order_ids == [2, 3, 1]


class TestVehicleManagement:
    """BR-LOG-01"""

    def test_logistics_operator_can_create_vehicle(self, client):
        op, token = _create_logistics_user(client, "veh_op1@example.com")
        resp = client.post(
            "/api/v1/logistics/vehicles",
            headers=auth_headers(token),
            json={"registration_number": "KA-01-AB-1234", "vehicle_type": "Mini Truck", "capacity": "1500.00", "unit": "kg"},
        )
        assert resp.status_code == 201
        assert resp.json()["operator_id"] == op.id
        assert resp.json()["is_available"] is True

    def test_consumer_cannot_create_vehicle(self, client):
        """BR-LOG-01"""
        consumer = register_user(client, "veh_consumer@example.com", "CONSUMER")
        resp = client.post(
            "/api/v1/logistics/vehicles",
            headers=auth_headers(consumer["access_token"]),
            json={"registration_number": "KA-01-AB-9999", "vehicle_type": "Van", "capacity": "500.00"},
        )
        assert resp.status_code == 403

    def test_farmer_cannot_create_vehicle(self, client):
        farmer = register_user(client, "veh_farmer@example.com", "FARMER")
        resp = client.post(
            "/api/v1/logistics/vehicles",
            headers=auth_headers(farmer["access_token"]),
            json={"registration_number": "KA-01-AB-8888", "vehicle_type": "Van", "capacity": "500.00"},
        )
        assert resp.status_code == 403


class TestLogisticsAssignment:
    """BR-LOG-04 through BR-LOG-08"""

    def test_create_pickup_and_delivery_locations(self, client):
        """BR-LOG-02"""
        op, token = _create_logistics_user(client, "loc_op@example.com")
        pickup = client.post(
            "/api/v1/logistics/pickup-locations",
            headers=auth_headers(token),
            json={"name": "Kolar Mandi Pickup", "address": "Kolar Market Yard", "latitude": "13.1367", "longitude": "78.1291"},
        )
        assert pickup.status_code == 201
        assert pickup.json()["name"] == "Kolar Mandi Pickup"

        dropoff = client.post(
            "/api/v1/logistics/delivery-locations",
            headers=auth_headers(token),
            json={"name": "Bangalore Distribution Hub", "address": "Electronic City", "latitude": "12.8452", "longitude": "77.6602"},
        )
        assert dropoff.status_code == 201

    def test_logistics_operator_cannot_assign_to_another_operator(self, client):
        """BR-LOG-04"""
        op1, token1 = _create_logistics_user(client, "asgn_op1@example.com")
        op2, token2 = _create_logistics_user(client, "asgn_op2@example.com")
        
        farmer = register_user(client, "asgn_farmer@example.com", "FARMER")
        buyer = register_user(client, "asgn_buyer@example.com", "CONSUMER")
        p = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Beans", "category": "Vegetables", "unit": "kg", "price_per_unit": "30", "quantity": "100"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": p["id"], "quantity": "10"})
        order = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Hub Address"}).json()
        
        farmer_hdrs = auth_headers(farmer["access_token"])
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "PREPARING"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"})

        # op1 attempts to assign delivery to op2
        resp = client.post(
            f"/api/v1/logistics/assignments/{order['id']}",
            headers=auth_headers(token1),
            json={"logistics_operator_id": op2.id},
        )
        assert resp.status_code == 403

    def test_assignment_with_another_operators_vehicle_fails(self, client):
        """BR-LOG-05"""
        op1, token1 = _create_logistics_user(client, "vehown_op1@example.com")
        op2, token2 = _create_logistics_user(client, "vehown_op2@example.com")
        
        veh2 = client.post(
            "/api/v1/logistics/vehicles",
            headers=auth_headers(token2),
            json={"registration_number": "KA-51-OP2-VEH", "vehicle_type": "Truck", "capacity": "1000", "unit": "kg"},
        ).json()

        farmer = register_user(client, "vehown_farmer@example.com", "FARMER")
        buyer = register_user(client, "vehown_buyer@example.com", "CONSUMER")
        p = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Cabbage", "category": "Vegetables", "unit": "kg", "price_per_unit": "15", "quantity": "100"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": p["id"], "quantity": "10"})
        order = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Hub Address"}).json()
        
        farmer_hdrs = auth_headers(farmer["access_token"])
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "PREPARING"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"})

        # op1 assigns to self but with op2's vehicle
        resp = client.post(
            f"/api/v1/logistics/assignments/{order['id']}",
            headers=auth_headers(token1),
            json={"logistics_operator_id": op1.id, "vehicle_id": veh2["id"]},
        )
        assert resp.status_code == 403

    def test_assignment_marks_vehicle_unavailable(self, client):
        """BR-LOG-07"""
        op, token = _create_logistics_user(client, "unavail_op@example.com")
        veh = client.post("/api/v1/logistics/vehicles", headers=auth_headers(token), json={"registration_number": "KA-01-BUSY-1", "vehicle_type": "Van", "capacity": "500", "unit": "kg"}).json()

        farmer = register_user(client, "unavail_farmer@example.com", "FARMER")
        buyer = register_user(client, "unavail_buyer@example.com", "CONSUMER")
        p = client.post("/api/v1/products", headers=auth_headers(farmer["access_token"]), json={"name": "Radish", "category": "Vegetables", "unit": "kg", "price_per_unit": "10", "quantity": "100"}).json()
        client.post("/api/v1/cart/items", headers=auth_headers(buyer["access_token"]), json={"product_id": p["id"], "quantity": "10"})
        order = client.post("/api/v1/orders", headers=auth_headers(buyer["access_token"]), json={"shipping_address": "Hub Address"}).json()
        
        farmer_hdrs = auth_headers(farmer["access_token"])
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "CONFIRMED"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "PREPARING"})
        client.patch(f"/api/v1/orders/{order['id']}/status", headers=farmer_hdrs, json={"status": "READY_FOR_PICKUP"})

        resp = client.post(
            f"/api/v1/logistics/assignments/{order['id']}",
            headers=auth_headers(token),
            json={"logistics_operator_id": op.id, "vehicle_id": veh["id"]},
        )
        assert resp.status_code == 201

        vehicles = client.get("/api/v1/logistics/vehicles", headers=auth_headers(token)).json()
        target_veh = next(v for v in vehicles if v["id"] == veh["id"])
        assert target_veh["is_available"] is False


class TestRouteOptimization:
    """BR-LOG-09 through BR-LOG-16"""

    def test_vehicle_capacity_violation_fails(self, client):
        """BR-LOG-09, BR-LOG-10"""
        db = _db(client)
        admin = make_user_in_db(db, "cap_admin@example.com", "ADMIN")
        buyer = make_user_in_db(db, "cap_buyer@example.com", "CONSUMER")
        seller = make_user_in_db(db, "cap_seller@example.com", "FARMER")
        
        vehicle = make_vehicle(db, admin, capacity=50.0, registration="CAP-VEH-1")
        loc = make_delivery_location(db, lat=12.97, lon=77.59, name="Drop 1")
        
        order = Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=1000, shipping_address="Drop 1")
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=1, product_name="Grain", quantity=100, unit_price=10, subtotal=1000))
        delivery = Delivery(order_id=order.id, logistics_operator_id=admin.id, vehicle_id=vehicle.id, delivery_location_id=loc.id)
        db.add(delivery)
        db.commit()

        request = RouteOptimizeRequest(vehicle_id=vehicle.id, delivery_ids=[delivery.id], depot_latitude=Decimal("12.9000"), depot_longitude=Decimal("77.5000"))
        
        with pytest.raises(Exception) as excinfo:
            LogisticsService(db).optimize_route(admin, request)
        assert "capacity is insufficient" in str(excinfo.value)
        db.close()

    def test_delivery_without_location_fails(self, client):
        """BR-LOG-12"""
        db = _db(client)
        admin = make_user_in_db(db, "nolocation_admin@example.com", "ADMIN")
        buyer = make_user_in_db(db, "nolocation_buyer@example.com", "CONSUMER")
        seller = make_user_in_db(db, "nolocation_seller@example.com", "FARMER")
        
        vehicle = make_vehicle(db, admin, capacity=500.0, registration="NOLOC-VEH")
        order = Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=200, shipping_address="Somewhere")
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=1, product_name="Grain", quantity=10, unit_price=20, subtotal=200))
        
        delivery = Delivery(order_id=order.id, logistics_operator_id=admin.id, vehicle_id=vehicle.id, delivery_location_id=None)
        db.add(delivery)
        db.commit()

        request = RouteOptimizeRequest(vehicle_id=vehicle.id, delivery_ids=[delivery.id], depot_latitude=Decimal("12.90"), depot_longitude=Decimal("77.50"))
        
        with pytest.raises(Exception) as excinfo:
            LogisticsService(db).optimize_route(admin, request)
        assert "delivery location" in str(excinfo.value).lower()
        db.close()

    def test_delivery_assigned_to_another_vehicle_fails(self, client):
        """BR-LOG-11"""
        db = _db(client)
        admin = make_user_in_db(db, "othveh_admin@example.com", "ADMIN")
        buyer = make_user_in_db(db, "othveh_buyer@example.com", "CONSUMER")
        seller = make_user_in_db(db, "othveh_seller@example.com", "FARMER")
        
        veh1 = make_vehicle(db, admin, capacity=500.0, registration="VEH-1-ASSIGNED")
        veh2 = make_vehicle(db, admin, capacity=500.0, registration="VEH-2-TARGET")
        loc = make_delivery_location(db)

        order = Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=200, shipping_address="Loc")
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=1, product_name="Crop", quantity=10, unit_price=20, subtotal=200))
        delivery = Delivery(order_id=order.id, logistics_operator_id=admin.id, vehicle_id=veh1.id, delivery_location_id=loc.id)
        db.add(delivery)
        db.commit()

        request = RouteOptimizeRequest(vehicle_id=veh2.id, delivery_ids=[delivery.id], depot_latitude=Decimal("12.90"), depot_longitude=Decimal("77.50"))
        with pytest.raises(Exception) as excinfo:
            LogisticsService(db).optimize_route(admin, request)
        assert "assigned to another vehicle" in str(excinfo.value)
        db.close()

    def test_invalid_depot_coordinates_rejected_by_schema(self, client):
        """BR-LOG-16"""
        op, token = _create_logistics_user(client, "badcoord_op@example.com")
        resp = client.post(
            "/api/v1/logistics/routes/optimize",
            headers=auth_headers(token),
            json={"vehicle_id": 1, "delivery_ids": [1], "depot_latitude": 95.0, "depot_longitude": 77.0},
        )
        assert resp.status_code == 422
