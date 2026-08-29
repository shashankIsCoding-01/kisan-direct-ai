from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.marketplace import Delivery, DeliveryLocation, Order, OrderItem, Vehicle
from app.models.user import User
from app.schemas.logistics import RouteOptimizeRequest
from app.services.logistics_service import LogisticsService
from app.services.routing import HaversineRoutingProvider, nearest_neighbor


def test_routing_provider_and_nearest_neighbor_are_separate():
    provider = HaversineRoutingProvider()
    depot = (0.0, 0.0)
    stops = [
        {"delivery_id": 1, "coordinate": (2.0, 0.0)},
        {"delivery_id": 2, "coordinate": (1.0, 0.0)},
    ]

    ordered = nearest_neighbor(stops, depot, provider)

    assert provider.name == "haversine_straight_line"
    assert [stop["delivery_id"] for stop in ordered] == [2, 1]
    assert provider.distance_km(depot, (1.0, 0.0)) > 0


def test_route_optimization_reports_baseline_metrics():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = User(email="route-admin@example.com", password_hash="unused", full_name="Route Admin", role="ADMIN")
    buyer = User(email="route-buyer@example.com", password_hash="unused", full_name="Route Buyer", role="CONSUMER")
    seller = User(email="route-seller@example.com", password_hash="unused", full_name="Route Seller", role="FARMER")
    db.add_all([admin, buyer, seller])
    db.flush()
    vehicle = Vehicle(operator_id=admin.id, registration_number="TEST-ROUTE-1", vehicle_type="Pickup", capacity=100, unit="kg")
    db.add(vehicle)
    db.flush()
    delivery_ids = []
    for index, coordinate in enumerate([(2, 0), (1, 0), (3, 0)]):
        location = DeliveryLocation(name=f"Drop {index}", address="Test address", latitude=coordinate[0], longitude=coordinate[1])
        db.add(location)
        db.flush()
        order = Order(buyer_id=buyer.id, seller_id=seller.id, status="READY_FOR_PICKUP", total_amount=100, shipping_address="Test", items=[])
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=1, product_name="Test crop", quantity=10, unit_price=10, subtotal=100))
        delivery = Delivery(order_id=order.id, logistics_operator_id=admin.id, vehicle_id=vehicle.id, delivery_location_id=location.id)
        db.add(delivery)
        db.flush()
        delivery_ids.append(delivery.id)
    db.commit()

    result = LogisticsService(db).optimize_route(
        admin,
        RouteOptimizeRequest(vehicle_id=vehicle.id, delivery_ids=delivery_ids, depot_latitude=0, depot_longitude=0, average_speed_kmh=30),
    )

    assert result["number_of_stops"] == 3
    assert result["baseline_distance_km"] >= result["optimized_distance_km"]
    assert result["capacity_utilization_percent"] == 30.0
    assert result["routing_provider"] == "haversine_straight_line"
    assert result["optimization_method"] == "nearest_neighbor"
    assert result["problem_classification"] == "single-vehicle capacitated routing heuristic"
    assert result["demo_environment"] is True
    assert result["route"].waypoint_order
    assert result["route"].baseline_waypoint_order == delivery_ids
    db.close()
