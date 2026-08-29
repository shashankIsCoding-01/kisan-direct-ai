# KisanDirect AI — Database Schema

## Overview

- **Database:** PostgreSQL
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Connection:** Async (asyncpg)

---

## Entity Relationship Diagram (Conceptual)

```
users ←(member)→ fpos ←(member)→ users
  │
  └──(owner)──→ products ←──→ orders ←─── users (buyer)
                    │              │
                    └──(seller)─────┘
                      
logistics_assignments ← orders
         ↓
      routes
```

---

## Tables

### 1. users

Primary user table. All roles (farmer, consumer, etc.) are stored here.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hashed password |
| full_name | VARCHAR(100) | NOT NULL | Display name |
| role | ENUM | NOT NULL | farmer, consumer, bulk_buyer, fpo_admin, logistics, admin |
| phone | VARCHAR(20) | | Contact number |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | TIMESTAMP | NOT NULL | Registration time |
| updated_at | TIMESTAMP | NOT NULL | Last update time |

**Indexes:**
- `idx_users_email` on `email`
- `idx_users_role` on `role`

---

### 2. addresses

Stores user addresses and shipping addresses.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → users(id) | Owner (nullable for shipping) |
| address_type | ENUM | NOT NULL | permanent, shipping |
| name | VARCHAR(100) | | Recipient name |
| phone | VARCHAR(20) | | Contact number |
| village | VARCHAR(100) | | Village/Town |
| district | VARCHAR(100) | NOT NULL | District |
| state | VARCHAR(100) | NOT NULL | State |
| pincode | VARCHAR(10) | NOT NULL | PIN code |
| lat | DECIMAL(10,7) | | Latitude (optional) |
| lng | DECIMAL(10,7) | | Longitude (optional) |

---

### 3. fpos (Farmer Producer Organizations)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(255) | NOT NULL | FPO name |
| registration_number | VARCHAR(100) | UNIQUE | Govt registration |
| contact_email | VARCHAR(255) | | Public contact |
| created_by | UUID | FK → users(id) | Admin who created |
| created_at | TIMESTAMP | NOT NULL | Creation time |

---

### 4. fpo_members

Links farmers to FPOs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| fpo_id | UUID | FK → fpos(id) | FPO reference |
| user_id | UUID | FK → users(id) | Farmer member |
| joined_at | TIMESTAMP | NOT NULL | Join date |
| is_active | BOOLEAN | DEFAULT TRUE | Membership status |

**Unique constraint:** `(fpo_id, user_id)`

---

### 5. categories

Product categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Category name |
| parent_id | UUID | FK → categories(id) | Parent (for subcategories) |
| description | TEXT | | Category description |

---

### 6. products

Product listings by farmers and FPOs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| seller_id | UUID | FK → users(id) | Owner (farmer or FPO) |
| fpo_id | UUID | FK → fpos(id) | FPO if aggregated (nullable) |
| category_id | UUID | FK → categories(id) | Product category |
| name | VARCHAR(255) | NOT NULL | Product name |
| description | TEXT | | Product description |
| price_per_unit | DECIMAL(10,2) | NOT NULL | Price per unit |
| unit | VARCHAR(20) | NOT NULL | kg, piece, dozen, etc. |
| stock_quantity | DECIMAL(10,2) | NOT NULL | Available stock |
| harvest_date | DATE | | Harvest date (for produce) |
| is_organic | BOOLEAN | DEFAULT FALSE | Organic certification |
| image_url | VARCHAR(500) | | Product image |
| is_active | BOOLEAN | DEFAULT TRUE | Listing status |
| created_at | TIMESTAMP | NOT NULL | Listing time |
| updated_at | TIMESTAMP | NOT NULL | Last update |

**Indexes:**
- `idx_products_seller` on `seller_id`
- `idx_products_category` on `category_id`
- `idx_products_name` on `name` (GIN trigram for search)

---

### 7. inventory

Tracks stock changes (optional separate table for transaction log).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| product_id | UUID | FK → products(id) | Product reference |
| available_qty | DECIMAL(10,2) | NOT NULL | Current available |
| reserved_qty | DECIMAL(10,2) | DEFAULT 0 | Reserved for orders |
| updated_at | TIMESTAMP | NOT NULL | Last update |

---

### 8. cart_items

Shopping cart items per user.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → users(id) | Cart owner |
| product_id | UUID | FK → products(id) | Product |
| quantity | DECIMAL(10,2) | NOT NULL | Quantity in cart |
| added_at | TIMESTAMP | NOT NULL | Added time |

**Unique constraint:** `(user_id, product_id)`

---

### 9. orders

Main order table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| buyer_id | UUID | FK → users(id) | Purchasing user |
| seller_id | UUID | FK → users(id) | Selling user |
| fpo_id | UUID | FK → fpos(id) | FPO if through FPO |
| status | ENUM | NOT NULL | pending, confirmed, processing, out_for_delivery, delivered, cancelled |
| total_amount | DECIMAL(12,2) | NOT NULL | Total order value |
| shipping_address_id | UUID | FK → addresses(id) | Delivery address |
| shipping_notes | TEXT | | Delivery notes |
| created_at | TIMESTAMP | NOT NULL | Order time |
| updated_at | TIMESTAMP | NOT NULL | Last status update |
| delivered_at | TIMESTAMP | | Delivery time |

**Indexes:**
- `idx_orders_buyer` on `buyer_id`
- `idx_orders_seller` on `seller_id`
- `idx_orders_status` on `status`

---

### 10. order_items

Individual items within an order.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| order_id | UUID | FK → orders(id) | Parent order |
| product_id | UUID | FK → products(id) | Product |
| quantity | DECIMAL(10,2) | NOT NULL | Ordered quantity |
| unit_price | DECIMAL(10,2) | NOT NULL | Price at order time |
| subtotal | DECIMAL(12,2) | NOT NULL | quantity × unit_price |

---

### 11. logistics_assignments

Links orders to logistics operators.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| order_id | UUID | FK → orders(id) | Order reference |
| operator_id | UUID | FK → users(id) | Logistics operator |
| status | ENUM | NOT NULL | assigned, picked_up, in_transit, delivered |
| pickup_location | VARCHAR(500) | | Pickup address |
| delivery_location | VARCHAR(500) | | Delivery address |
| assigned_at | TIMESTAMP | NOT NULL | Assignment time |
| picked_up_at | TIMESTAMP | | Pickup time |
| delivered_at | TIMESTAMP | | Delivery time |

---

### 12. routes

Optimized delivery routes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| logistics_assignment_id | UUID | FK → logistics_assignments(id) | Assignment |
| waypoints | JSONB | NOT NULL | Ordered list of stops |
| total_distance_km | DECIMAL(8,2) | | Total distance |
| estimated_duration_min | INTEGER | | Estimated time |
| optimized_at | TIMESTAMP | NOT NULL | Optimization time |

---

### 13. demand_history

Historical demand data for forecasting.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| product_name | VARCHAR(255) | NOT NULL | Product (denormalized) |
| region | VARCHAR(100) | NOT NULL | Region/state |
| date | DATE | NOT NULL | Date |
| quantity_sold | DECIMAL(10,2) | NOT NULL | Actual quantity |
| avg_price | DECIMAL(10,2) | | Average price |
| recorded_at | TIMESTAMP | NOT NULL | Recording time |

**Unique constraint:** `(product_name, region, date)`

---

### 14. demand_forecasts

Stored forecast results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| product_name | VARCHAR(255) | NOT NULL | Product |
| region | VARCHAR(100) | NOT NULL | Region |
| forecast_date | DATE | NOT NULL | Forecasted date |
| predicted_demand | DECIMAL(10,2) | NOT NULL | Predicted quantity |
| model_used | VARCHAR(50) | NOT NULL | Model name |
| accuracy_mape | DECIMAL(5,2) | | MAPE score |
| generated_at | TIMESTAMP | NOT NULL | Generation time |

---

## Initial Data (Seed)

### Roles
```sql
INSERT INTO roles (name) VALUES 
('farmer'), ('consumer'), ('bulk_buyer'), ('fpo_admin'), ('logistics'), ('admin');
```

### Categories
```sql
INSERT INTO categories (name) VALUES 
('Vegetables'), ('Fruits'), ('Grains'), ('Dairy'), ('Spices'), ('Pulses');
```

---

## Key Relationships

```
users (1) ←→ (N) fpo_members ←→ (N) fpos (1) ←→ (N) fpo_members ←→ (N) users
     │
     └── (1) ←→ (N) products
     │
     └── (1) ←→ (N) orders (as buyer)
     │
     └── (1) ←→ (N) orders (as seller)
     │
     └── (1) ←→ (N) cart_items

products (1) ←→ (N) order_items ←→ (1) orders
     │
     └── (1) ←→ (1) inventory

orders (1) ←→ (N) logistics_assignments
```

---

## Migration Strategy

1. Use **Alembic** for all schema changes
2. Never modify existing migrations — create new ones
3. Seed data in separate migration files
4. Test migrations on a copy before applying to production
