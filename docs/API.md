# KisanDirect AI — API Specification

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.kisan-direct.ai/api/v1
```

## Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Auth Module (`/auth`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| POST | `/auth/register` | Register new user | No | — |
| POST | `/auth/login` | Login, receive JWT | No | — |
| POST | `/auth/refresh` | Refresh access token | Yes | any |
| POST | `/auth/logout` | Invalidate token | Yes | any |

#### `POST /auth/register`
```json
Request:
{
  "email": "farmer@example.com",
  "password": "SecurePass123",
  "full_name": "Ramesh Kumar",
  "role": "farmer",
  "phone": "+919876543210",
  "address": {
    "village": "Madhupur",
    "district": "Birbhum",
    "state": "West Bengal",
    "pincode": "731101"
  }
}

Response (201):
{
  "id": "uuid",
  "email": "farmer@example.com",
  "role": "farmer",
  "message": "Registration successful"
}
```

#### `POST /auth/login`
```json
Request:
{
  "email": "farmer@example.com",
  "password": "SecurePass123"
}

Response (200):
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### User Module (`/users`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/users/me` | Get current user profile | Yes | any |
| PUT | `/users/me` | Update current user profile | Yes | any |
| GET | `/users/` | List all users | Yes | admin |
| GET | `/users/{id}` | Get user by ID | Yes | admin |
| PUT | `/users/{id}/role` | Update user role | Yes | admin |

---

### Product Module (`/products`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/products/` | List products (filterable) | No | — |
| GET | `/products/{id}` | Get product details | No | — |
| POST | `/products/` | Create product listing | Yes | farmer, fpo |
| PUT | `/products/{id}` | Update product | Yes | owner, admin |
| DELETE | `/products/{id}` | Delete product | Yes | owner, admin |
| GET | `/products/my/` | Get my products | Yes | farmer, fpo |

#### Query Parameters for `GET /products/`
```
?category=vegetables
?state=west_bengal
?min_price=10
?max_price=100
?search=tomato
?page=1
?limit=20
```

#### `POST /products/`
```json
Request:
{
  "name": "Ripe Tomatoes",
  "category": "vegetables",
  "description": "Fresh organic tomatoes",
  "price_per_unit": 25.00,
  "unit": "kg",
  "stock_quantity": 500,
  "harvest_date": "2026-08-20",
  "location": {
    "village": "Madhupur",
    "district": "Birbhum",
    "state": "West Bengal"
  }
}
```

---

### Inventory Module (`/inventory`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/inventory/` | List all inventory | Yes | admin |
| GET | `/inventory/my/` | Get my inventory | Yes | farmer, fpo |
| PUT | `/inventory/{product_id}` | Update stock | Yes | owner |
| POST | `/inventory/bulk-update` | Bulk stock update | Yes | fpo |

---

### Cart Module (`/cart`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/cart/` | Get my cart | Yes | consumer, bulk_buyer |
| POST | `/cart/items` | Add item to cart | Yes | consumer, bulk_buyer |
| PUT | `/cart/items/{item_id}` | Update cart item qty | Yes | owner |
| DELETE | `/cart/items/{item_id}` | Remove item | Yes | owner |
| DELETE | `/cart/` | Clear cart | Yes | owner |

#### `POST /cart/items`
```json
Request:
{
  "product_id": "uuid",
  "quantity": 10
}
```

---

### Order Module (`/orders`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/orders/` | List orders | Yes | any |
| GET | `/orders/{id}` | Get order details | Yes | owner, admin |
| POST | `/orders/` | Place order from cart | Yes | consumer, bulk_buyer |
| PUT | `/orders/{id}/status` | Update order status | Yes | farmer, fpo, logistics, admin |
| GET | `/orders/my-sales/` | Orders where I'm seller | Yes | farmer, fpo |
| GET | `/orders/my-purchases/` | My purchase orders | Yes | consumer, bulk_buyer |

#### Order Status Flow
```
pending → confirmed → processing → out_for_delivery → delivered
                                        ↓
                                   cancelled
```

#### `POST /orders/`
```json
Request:
{
  "shipping_address": {
    "name": "Amit Sharma",
    "phone": "+919876543210",
    "address": "42 MG Road, Kolkata",
    "city": "Kolkata",
    "pincode": "700001"
  },
  "notes": "Please deliver in morning"
}

Response (201):
{
  "id": "uuid",
  "status": "pending",
  "total_amount": 250.00,
  "items": [...],
  "created_at": "2026-08-28T10:00:00Z"
}
```

---

### FPO Module (`/fpo`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| POST | `/fpo/` | Create FPO | Yes | admin |
| GET | `/fpo/` | List all FPOs | No | — |
| GET | `/fpo/{id}` | Get FPO details | No | — |
| POST | `/fpo/{id}/members` | Add member to FPO | Yes | fpo_admin |
| GET | `/fpo/{id}/members` | List FPO members | Yes | fpo_admin |
| DELETE | `/fpo/{id}/members/{user_id}` | Remove member | Yes | fpo_admin |
| POST | `/fpo/{id}/aggregate` | Aggregate inventory | Yes | fpo_admin |

#### `POST /fpo/`
```json
Request:
{
  "name": "Birbhum Farmers Producer Org",
  "registration_number": "FPO/WB/2024/001",
  "address": {
    "village": "Madhupur",
    "district": "Birbhum",
    "state": "West Bengal"
  },
  "contact_email": "birbhumfpo@example.com"
}
```

---

### Logistics Module (`/logistics`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/logistics/assignments/` | My delivery assignments | Yes | logistics |
| POST | `/logistics/assignments/` | Create assignment | Yes | admin, system |
| PUT | `/logistics/tracking/{order_id}` | Update delivery status | Yes | logistics |
| GET | `/logistics/routes/` | Get optimized route | Yes | logistics |
| POST | `/logistics/optimize/` | Request route optimization | Yes | logistics |

#### `PUT /logistics/tracking/{order_id}`
```json
Request:
{
  "status": "out_for_delivery",
  "current_location": {
    "lat": 23.7955,
    "lng": 87.5867
  },
  "estimated_delivery": "2026-08-28T14:00:00Z",
  "notes": "Traffic delay"
}
```

---

### Analytics Module (`/analytics`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| GET | `/analytics/dashboard/` | Dashboard stats | Yes | admin |
| GET | `/analytics/orders/` | Order statistics | Yes | admin |
| GET | `/analytics/revenue/` | Revenue breakdown | Yes | admin |
| GET | `/analytics/products/` | Product performance | Yes | admin |

#### `GET /analytics/dashboard/`
```json
Response:
{
  "total_users": 150,
  "total_orders": 340,
  "total_revenue": 125000.00,
  "pending_deliveries": 23,
  "active_fpos": 5,
  "top_products": [...]
}
```

---

### AI/ML Module (`/ai`)

| Method | Endpoint | Description | Auth | Role |
|--------|----------|-------------|------|------|
| POST | `/ai/demand-forecast/` | Get demand forecast | Yes | admin, bulk_buyer |
| GET | `/ai/demand-forecast/history` | Past forecasts | Yes | admin |

#### `POST /ai/demand-forecast/`
```json
Request:
{
  "product_name": "tomato",
  "region": "west_bengal",
  "days_ahead": 7
}

Response:
{
  "product": "tomato",
  "region": "west_bengal",
  "forecast": [
    {"date": "2026-08-29", "predicted_demand": 120},
    {"date": "2026-08-30", "predicted_demand": 135},
    ...
  ],
  "model_used": "linear_regression",
  "accuracy_mape": 12.5
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here",
  "code": "ERROR_CODE",
  "timestamp": "2026-08-28T10:00:00Z"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing/invalid token |
| 403 | Forbidden — insufficient role |
| 404 | Not Found — resource doesn't exist |
| 422 | Validation Error — Pydantic validation failed |
| 500 | Internal Server Error |

---

## Pagination

All list endpoints return:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 20,
  "pages": 5
}
```

---

## Rate Limits (Future)

```
100 requests/minute per user
1000 requests/minute per IP (unauthenticated)
```
