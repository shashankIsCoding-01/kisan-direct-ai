from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.marketplace import Delivery
from app.models.user import User
from app.repositories.logistics_repository import LogisticsRepository
from app.schemas.logistics import LocationCreate, LogisticsAssignmentCreate, RouteOptimizeRequest, VehicleCreate
from app.services.order_service import OrderService
from app.services.routing import HaversineRoutingProvider, nearest_neighbor, route_distance


class LogisticsService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LogisticsRepository(db)
        self.routing_provider = HaversineRoutingProvider()

    def create_vehicle(self, user: User, payload: VehicleCreate):
        self._require_logistics(user)
        return self.repository.create_vehicle(user.id, payload.model_dump())

    def list_vehicles(self, user: User):
        self._require_logistics(user)
        return self.repository.list_vehicles(user.id)

    def create_pickup_location(self, user: User, payload: LocationCreate):
        self._require_logistics_or_admin(user)
        return self.repository.create_pickup_location(payload.model_dump())

    def create_delivery_location(self, user: User, payload: LocationCreate):
        self._require_logistics_or_admin(user)
        return self.repository.create_delivery_location(payload.model_dump())

    def assign(self, user: User, order_id: int, payload: LogisticsAssignmentCreate):
        self._require_logistics_or_admin(user)
        if user.role == "LOGISTICS" and payload.logistics_operator_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operators can only assign deliveries to themselves")
        vehicle = self.repository.get_vehicle(payload.vehicle_id) if payload.vehicle_id else None
        if vehicle:
            if vehicle.operator_id != payload.logistics_operator_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vehicle belongs to another operator")
            if not vehicle.is_available:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle is not available")
        pickup = self.repository.get_pickup_location(payload.pickup_location_id) if payload.pickup_location_id else None
        dropoff = self.repository.get_delivery_location(payload.delivery_location_id) if payload.delivery_location_id else None
        if payload.pickup_location_id and not pickup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup location not found")
        if payload.delivery_location_id and not dropoff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery location not found")
        delivery = OrderService(self.db).assign_delivery(order_id, user, payload.logistics_operator_id, payload.vehicle_id, payload.pickup_location_id, payload.delivery_location_id)
        if vehicle:
            vehicle.is_available = False
            self.db.commit()
        return delivery

    def list_deliveries(self, user: User):
        self._require_logistics_or_admin(user)
        return self.repository.list_deliveries(None if user.role == "ADMIN" else user.id)

    def optimize_route(self, user: User, payload: RouteOptimizeRequest):
        self._require_logistics_or_admin(user)
        vehicle = self.repository.get_vehicle(payload.vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        if user.role != "ADMIN" and vehicle.operator_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vehicle belongs to another operator")
        deliveries = [self._delivery_or_404(delivery_id) for delivery_id in payload.delivery_ids]
        stops = []
        total_load = Decimal("0")
        for delivery in deliveries:
            if delivery.vehicle_id not in {None, vehicle.id}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Delivery is assigned to another vehicle")
            if not delivery.delivery_location:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every delivery needs a delivery location")
            quantity = sum((item.quantity for item in delivery.order.items), Decimal("0"))
            total_load += quantity
            stops.append({"delivery_id": delivery.id, "order_id": delivery.order_id, "coordinate": (float(delivery.delivery_location.latitude), float(delivery.delivery_location.longitude)), "quantity": quantity})
        if total_load > vehicle.capacity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vehicle capacity is insufficient for these deliveries")
        depot = (float(payload.depot_latitude), float(payload.depot_longitude))
        baseline_order = [stop["delivery_id"] for stop in stops]
        baseline_distance = route_distance([stop["coordinate"] for stop in stops], depot, self.routing_provider)
        optimized_stops = nearest_neighbor(stops, depot, self.routing_provider)
        optimized_distance = route_distance([stop["coordinate"] for stop in optimized_stops], depot, self.routing_provider)
        travel_minutes = round(optimized_distance / float(payload.average_speed_kmh) * 60)
        utilization = float(total_load / vehicle.capacity * 100)
        optimized_order = [stop["delivery_id"] for stop in optimized_stops]
        route = self.repository.create_route({"vehicle_id": vehicle.id, "waypoint_order": optimized_order, "baseline_waypoint_order": baseline_order, "total_distance_km": round(Decimal(str(optimized_distance)), 2), "estimated_travel_time_min": travel_minutes, "number_of_stops": len(stops), "capacity_utilization_percent": round(Decimal(str(utilization)), 2), "baseline_distance_km": round(Decimal(str(baseline_distance)), 2), "routing_provider": self.routing_provider.name, "is_demo_environment": True})
        return {"route": route, "baseline_distance_km": round(baseline_distance, 2), "optimized_distance_km": round(optimized_distance, 2), "distance_reduction_percent": round((baseline_distance - optimized_distance) / baseline_distance * 100, 2) if baseline_distance else 0, "estimated_travel_time_min": travel_minutes, "number_of_stops": len(stops), "capacity_utilization_percent": round(utilization, 2), "routing_provider": self.routing_provider.name, "optimization_method": "nearest_neighbor", "problem_classification": "single-vehicle capacitated routing heuristic", "demo_environment": self.routing_provider.name == "haversine_straight_line"}

    def _delivery_or_404(self, delivery_id: int) -> Delivery:
        delivery = self.repository.get_delivery(delivery_id)
        if not delivery:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
        return delivery

    @staticmethod
    def _require_logistics(user: User):
        if user.role != "LOGISTICS":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only logistics operators can manage vehicles")

    @staticmethod
    def _require_logistics_or_admin(user: User):
        if user.role not in {"LOGISTICS", "ADMIN"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only logistics operators or admins can manage deliveries")
