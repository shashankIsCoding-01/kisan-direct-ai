from math import atan2, cos, radians, sin, sqrt
from typing import Protocol


class RoutingProvider(Protocol):
    name: str

    def distance_km(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        ...


class HaversineRoutingProvider:
    name = "haversine_straight_line"

    def distance_km(self, origin: tuple[float, float], destination: tuple[float, float]) -> float:
        radius = 6371.0
        lat1, lon1, lat2, lon2 = map(radians, [origin[0], origin[1], destination[0], destination[1]])
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        return radius * 2 * atan2(sqrt(value), sqrt(1 - value))


def route_distance(stops: list[tuple[float, float]], depot: tuple[float, float], provider: RoutingProvider) -> float:
    points = [depot, *stops, depot]
    return sum(provider.distance_km(points[index], points[index + 1]) for index in range(len(points) - 1))


def nearest_neighbor(stops: list[dict], depot: tuple[float, float], provider: RoutingProvider) -> list[dict]:
    remaining = list(stops)
    ordered = []
    current = depot
    while remaining:
        next_stop = min(remaining, key=lambda stop: provider.distance_km(current, stop["coordinate"]))
        ordered.append(next_stop)
        remaining.remove(next_stop)
        current = next_stop["coordinate"]
    return ordered
