from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.marketplace import Delivery, DeliveryLocation, PickupLocation, Route, Vehicle


class LogisticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_vehicle(self, operator_id: int, values: dict):
        vehicle = Vehicle(operator_id=operator_id, **values)
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def list_vehicles(self, operator_id: int):
        return self.db.scalars(select(Vehicle).where(Vehicle.operator_id == operator_id).order_by(Vehicle.id.asc())).all()

    def create_pickup_location(self, values: dict):
        location = PickupLocation(**values)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def create_delivery_location(self, values: dict):
        location = DeliveryLocation(**values)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def get_vehicle(self, vehicle_id: int):
        return self.db.get(Vehicle, vehicle_id)

    def get_pickup_location(self, location_id: int):
        return self.db.get(PickupLocation, location_id)

    def get_delivery_location(self, location_id: int):
        return self.db.get(DeliveryLocation, location_id)

    def get_delivery(self, delivery_id: int):
        return self.db.scalar(
            select(Delivery)
            .options(selectinload(Delivery.order), selectinload(Delivery.delivery_location))
            .where(Delivery.id == delivery_id)
        )

    def list_deliveries(self, operator_id: int | None = None):
        query = select(Delivery).options(selectinload(Delivery.order), selectinload(Delivery.delivery_location))
        if operator_id is not None:
            query = query.where(Delivery.logistics_operator_id == operator_id)
        return self.db.scalars(query.order_by(Delivery.assigned_at.asc())).all()

    def create_route(self, values: dict):
        route = Route(**values)
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route
