# KisanDirect AI — Logistics Architecture

## Overview

The logistics module handles:
- Delivery assignment to logistics operators
- Real-time tracking status updates
- Route optimization for delivery efficiency

The implementation keeps three concerns separate:

1. **Map display:** a frontend visualization concern. It may render stored coordinates and waypoints.
2. **Routing:** a provider calculates distance estimates. The current provider is a Haversine straight-line calculator.
3. **Route optimization:** a deterministic nearest-neighbor method changes the order of stops and compares it with the supplied baseline.

Map display and routing are not AI. The current optimizer is an explainable heuristic, not a machine-learning model.

> **AI Principle:** Route optimization at MVP uses a simple nearest-neighbor heuristic. Results must show measurable improvement over a baseline (random or unoptimized route).

---

## 1. Logistics Flow

```
Order Created (status: pending)
        ↓
   Order Confirmed (status: confirmed)
        ↓
   Logistics Assignment Created
        ↓
   Route Optimized
        ↓
   Operator Picks Up (status: picked_up)
        ↓
   In Transit (status: in_transit)
        ↓
   Out for Delivery (status: out_for_delivery)
        ↓
   Delivered (status: delivered)
```

---

## 2. Core Entities

### logistics_assignments

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| order_id | UUID | FK to orders |
| operator_id | UUID | FK to users (logistics role) |
| status | ENUM | assigned, picked_up, in_transit, out_for_delivery, delivered |
| current_lat | DECIMAL | Current latitude |
| current_lng | DECIMAL | Current longitude |
| assigned_at | TIMESTAMP | Assignment time |
| picked_up_at | TIMESTAMP | Pickup time |
| delivered_at | TIMESTAMP | Delivery time |

### routes

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| assignment_id | UUID | FK to logistics_assignments |
| waypoints | JSONB | Ordered list of stop coordinates |
| waypoint_order | JSONB | Ordered list of order IDs |
| total_distance_km | DECIMAL | Total route distance |
| estimated_duration_min | INTEGER | Estimated time |
| baseline_distance_km | DECIMAL | Distance without optimization |
| optimized_at | TIMESTAMP | Optimization timestamp |

---

## 3. Map Integration

### Technology
- **Leaflet** (JavaScript library)
- **OpenStreetMap** (free tile provider)
- **No API key required** for demo

The backend exposes a provider boundary in `app/services/routing.py`, so a road-network provider can replace the Haversine implementation later without changing the optimizer or API contract.

### Features

| Feature | Implementation |
|---------|----------------|
| Display delivery points | Leaflet Marker |
| Show optimized route | Polyline with waypoints |
| Show current location | Live Marker update |
| Cluster markers | MarkerCluster (when many stops) |

### Frontend Components

```
frontend/src/components/logistics/
├── MapView.jsx         # Main map component
├── RouteDisplay.jsx    # Shows route polyline
├── DeliveryMarker.jsx  # Individual stop marker
└── TrackingPanel.jsx    # Status sidebar
```

---

## 4. Route Optimization (MVP)

### Algorithm: Nearest Neighbor

```python
def nearest_neighbor(stops: List[Stop], depot: Tuple[float, float]) -> List[Stop]:
    """
    Input: List of delivery stops, depot location
    Output: Ordered list of stops minimizing total travel
    
    Algorithm:
    1. Start at depot
    2. Find nearest unvisited stop
    3. Move to that stop, mark as visited
    4. Repeat from current position
    5. Return to depot
    """
    route = []
    current = depot
    unvisited = stops.copy()
    
    while unvisited:
        nearest = min(unvisited, key=lambda s: distance(current, s.location))
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest.location
    
    return route
```

### Distance Calculation

```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lng1, lat2, lng2) -> float:
    """Calculate distance between two points in km"""
    R = 6371  # Earth's radius in km
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c
```

### Baseline Comparison

Every optimization must compare against a baseline:

```python
def evaluate_improvement(optimized_route, stops, depot):
    baseline_distance = sum(
        haversine(depot, stops[0]) + 
        haversine(stops[i], stops[i+1]) for i in range(len(stops)-1) +
        haversine(stops[-1], depot)
    )
    
    optimized_distance = sum(
        haversine(stops[i], stops[i+1]) 
        for i in range(len(stops)-1)
    ) + haversine(depot, stops[0]) + haversine(stops[-1], depot)
    
    improvement = (baseline_distance - optimized_distance) / baseline_distance * 100
    
    return {
        "baseline_km": round(baseline_distance, 2),
        "optimized_km": round(optimized_distance, 2),
        "improvement_percent": round(improvement, 1)
    }
```

---

## 5. API Endpoints

### Logistics Assignments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/logistics/assignments/` | Create assignment |
| GET | `/logistics/assignments/` | List assignments (filtered by role) |
| GET | `/logistics/assignments/{id}` | Get assignment details |
| PUT | `/logistics/assignments/{id}/status` | Update status |
| GET | `/logistics/assignments/my/` | My assigned deliveries |

#### Status Update Flow

```
assigned → picked_up → in_transit → out_for_delivery → delivered
                            ↓
                       cancelled
```

#### `PUT /logistics/assignments/{id}/status`

```json
Request:
{
  "status": "in_transit",
  "current_location": {
    "lat": 23.7955,
    "lng": 87.5867
  },
  "notes": "On the way"
}

Response:
{
  "id": "uuid",
  "status": "in_transit",
  "updated_at": "2026-08-28T10:00:00Z"
}
```

### Route Optimization

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/logistics/optimize/` | Optimize route for assignments |
| GET | `/logistics/routes/{assignment_id}` | Get route details |

Implemented API endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/logistics/vehicles` | Register a vehicle |
| GET | `/api/v1/logistics/vehicles` | List operator vehicles |
| POST | `/api/v1/logistics/pickup-locations` | Create pickup location |
| POST | `/api/v1/logistics/delivery-locations` | Create delivery location |
| POST | `/api/v1/logistics/assignments/{order_id}` | Assign an order |
| GET | `/api/v1/logistics/deliveries` | List assignments |
| POST | `/api/v1/logistics/routes/optimize` | Compare baseline and optimized routes |

The optimization response includes total distance, estimated travel time, stop count, vehicle capacity utilization, baseline distance, optimized distance, reduction percentage, routing provider, and optimization method.

#### `POST /logistics/optimize/`

```json
Request:
{
  "assignment_ids": ["uuid1", "uuid2", "uuid3"]
}

Response:
{
  "route": {
    "waypoints": [
      {"lat": 23.7955, "lng": 87.5867, "order_id": "uuid1"},
      {"lat": 23.8123, "lng": 87.5934, "order_id": "uuid2"},
      {"lat": 23.8234, "lng": 87.6012, "order_id": "uuid3"}
    ],
    "waypoint_order": ["uuid1", "uuid2", "uuid3"],
    "total_distance_km": 15.3,
    "estimated_duration_min": 45
  },
  "baseline_distance_km": 22.1,
  "improvement_percent": 30.8,
  "algorithm": "nearest_neighbor"
}
```

---

## 6. Tracking Updates

### Operator Flow

1. Operator logs in → sees "My Deliveries" list
2. Taps assignment → sees delivery details + map
3. Taps "Start Delivery" → status → `picked_up`
4. While traveling → periodically updates location
5. At each stop → marks as delivered
6. Completes all → status → `delivered`

### Frontend Tracking UI

```
Logistics Dashboard
├── My Assignments (list)
│   ├── Order #1234 → Status: in_transit → [View Map]
│   ├── Order #1235 → Status: assigned → [Start]
│   └── Order #1236 → Status: delivered → [View Route]
├── Active Route Map
│   ├── Showing all stops
│   ├── Current position marker
│   └── Route polyline
└── Route Statistics
    ├── Total distance: 15.3 km
    ├── Deliveries completed: 2/5
    └── Estimated time: 45 min
```

---

## 7. Map Visualization Details

### Route Display

```jsx
// Example Leaflet route display
import { MapContainer, TileLayer, Polyline, Marker } from 'react-leaflet';

function DeliveryRoute({ waypoints, currentLocation }) {
  const positions = waypoints.map(w => [w.lat, w.lng]);
  
  return (
    <MapContainer center={[23.8, 87.6]} zoom={12}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={positions} color="blue" />
      {waypoints.map((w, i) => (
        <Marker key={i} position={[w.lat, w.lng]} />
      ))}
      {currentLocation && (
        <Marker position={[currentLocation.lat, currentLocation.lng]} />
      )}
    </MapContainer>
  );
}
```

---

## 8. Future Logistics Features

| Feature | Description | Priority |
|---------|-------------|----------|
| GPS live tracking | Real-time location via mobile app | Future |
| Time windows | Deliveries within specific time slots | Future |
| Capacity optimization | Group deliveries by vehicle capacity | Future |
| Multi-depot routing | Multiple pickup points | Future |
| Traffic integration | Real-time traffic data | Future |
| Cold chain tracking | Temperature monitoring for perishables | Future |
| Proof of delivery | Photo + signature capture | Future |

---

## 9. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Route optimization time | < 1 second | For ≤ 20 stops |
| Map load time | < 2 seconds | Initial render |
| Status update latency | < 500 ms | API response |
| Distance improvement | > 10% vs baseline | Per route |
| GPS update frequency | Every 30 seconds | When in transit |

---

## 10. Error Handling

| Scenario | Response |
|----------|----------|
| No assignments to optimize | 400: "Need at least 2 stops" |
| Assignment already delivered | 400: "Cannot update delivered order" |
| Invalid coordinates | 422: Validation error |
| Operator not assigned | 403: "Not assigned to this delivery" |
| Route calculation fails | 500: "Optimization failed, try again" |
