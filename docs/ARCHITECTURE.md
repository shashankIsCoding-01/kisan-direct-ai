# KisanDirect AI — Technical Architecture

## 1. Overview

KisanDirect AI is a **monolithic modular** web application designed for a student SIH team. It uses a **React frontend** communicating with a **FastAPI backend**, connected to a **PostgreSQL database**.

> **Why monolithic?**  
> Microservices add complexity (networking, deployment, debugging). For a student team with limited experience, a well-structured monolith with clear module boundaries is simpler to develop, test, and deploy.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│   React SPA (Vite) ←→ REST API ←→ Auth (JWT)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API GATEWAY LAYER                      │
│   FastAPI + CORS + Rate Limiting + Role Middleware          │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   USER MGMT     │ │  MARKETPLACE    │ │  LOGISTICS      │
│   MODULE        │ │  MODULE         │ │  MODULE         │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ • Auth          │ │ • Products      │ │ • Orders        │
│ • Roles         │ │ • Inventory     │ │ • Routes        │
│ • Profiles      │ │ • Cart         │ │ • Tracking      │
│ • FPO Members   │ │ • Orders        │ │ • Optimization  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│   SQLAlchemy ORM + PostgreSQL                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       ML LAYER                              │
│   Demand Forecasting + Route Optimization                   │
│   (Scikit-learn, Pandas, NumPy)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. User Roles & Permissions

| Role | Description | Permissions |
|------|-------------|-------------|
| `farmer` | Individual farmer listing produce | List products, manage own inventory, view orders |
| `fpo` | Farmer Producer Organization | Aggregate inventory, manage member farmers, bulk listing |
| `consumer` | End consumer | Browse, cart, place orders |
| `bulk_buyer` | Retailers, institutions | Bulk orders, demand forecasting |
| `logistics` | Transport operators | Accept delivery assignments, update tracking |
| `admin` | Platform administrator | Full access, analytics, user management |

---

## 4. Module Design

### 4.1 User Management Module (`/api/v1/auth`, `/api/v1/users`)

Handles registration, login, JWT issuance, and role assignment.

**Sub-modules:**
- `auth/` — Login, register, token refresh
- `users/` — Profile CRUD, role management (admin only)

### 4.2 Marketplace Module (`/api/v1/marketplace`)

Handles all buying and selling activities.

**Sub-modules:**
- `products/` — Product listing, search, filtering
- `inventory/` — Stock management per user/FPO
- `cart/` — Shopping cart
- `orders/` — Order placement, status, history
- `payments/` — Payment placeholder (future)

### 4.3 FPO Module (`/api/v1/fpo`)

Handles FPO-specific operations.

**Sub-modules:**
- `fpo/` — FPO creation, member management
- `aggregation/` — Combining farmer inventory into FPO stock

### 4.4 Logistics Module (`/api/v1/logistics`)

Handles delivery and route operations.

**Sub-modules:**
- `routes/` — Route definitions
- `tracking/` — Real-time delivery updates
- `optimization/` — Route optimization engine

### 4.5 Analytics & AI Module (`/api/v1/analytics`, `/api/v1/ai`)

Handles data processing and predictions.

**Sub-modules:**
- `demand/` — Demand forecasting
- `analytics/` — Dashboard statistics
- `reports/` — Export reports (future)

---

## 5. Frontend Architecture

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── common/         # Buttons, inputs, cards
│   │   ├── layout/         # Header, sidebar, footer
│   │   └── marketplace/     # Product cards, cart, etc.
│   ├── pages/              # Route-level pages
│   │   ├── auth/           # Login, register
│   │   ├── farmer/         # Farmer dashboard
│   │   ├── fpo/            # FPO dashboard
│   │   ├── consumer/       # Consumer marketplace
│   │   ├── bulk-buyer/     # Bulk buyer portal
│   │   ├── logistics/      # Logistics dashboard
│   │   └── admin/          # Admin dashboard
│   ├── context/            # React context (auth, cart)
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API client functions
│   ├── utils/              # Helpers, formatters
│   └── App.jsx             # Router + providers
```

---

## 6. Backend Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Settings from environment
│   ├── database.py          # Database connection
│   ├── dependencies.py      # Shared dependencies (auth, db)
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── inventory.py
│   │   ├── order.py
│   │   ├── fpo.py
│   │   └── logistics.py
│   ├── schemas/            # Pydantic schemas
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── ...
│   ├── routers/            # API route modules
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   ├── fpo.py
│   │   └── logistics.py
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── order_service.py
│   │   ├── demand_forecast.py
│   │   └── route_optimizer.py
│   └── ml/                  # ML modules
│       ├── demand_model.py
│       └── route_model.py
├── tests/                  # Unit & integration tests
├── alembic/                # Database migrations
└── requirements.txt
```

---

## 7. Data Flow

### 7.1 Order Placement Flow

```
Consumer browses marketplace
    → Adds to cart
    → Places order
    → FastAPI creates order record (status: "pending")
    → Order routed to farmer/FPO inventory check
    → Logistics operator assigned (or auto-optimized)
    → Delivery tracking updated
    → Order delivered → status: "delivered"
```

### 7.2 FPO Aggregation Flow

```
Individual farmer lists product → linked to FPO
    → FPO aggregates inventory from members
    → FPO creates bulk listing for buyers
    → Bulk buyer places order
    → Revenue distributed to member farmers
```

### 7.3 Demand Forecasting Flow

```
Historical order data → Pandas processing
    → Feature engineering (seasonality, location, price)
    → Scikit-learn model training
    → Demand prediction for next 7/30 days
    → Display on admin dashboard
```

---

## 8. MVP vs Future Features

### MVP (Must Have — SIH Demo)

| Feature | Module | Priority |
|---------|--------|----------|
| User registration + JWT login | Auth | P0 |
| Role-based access (6 roles) | Auth | P0 |
| Product listing (CRUD) | Marketplace | P0 |
| Inventory management | Marketplace | P0 |
| Shopping cart | Marketplace | P0 |
| Order placement + status | Orders | P0 |
| Basic demand data aggregation | Analytics | P1 |
| Delivery tracking (status updates) | Logistics | P1 |
| Admin dashboard (basic stats) | Admin | P1 |
| FPO member management | FPO | P1 |
| Route optimization (simple) | Logistics | P2 |

### Future (Post-SIH)

| Feature | Module | Priority |
|---------|--------|----------|
| Real payment gateway | Payments | Future |
| Push notifications | Notifications | Future |
| Advanced demand forecasting (ML) | AI | Future |
| Real-time chat | Communication | Future |
| Mobile app | Mobile | Future |
| Advanced analytics + charts | Analytics | Future |
| GPS-based live tracking | Logistics | Future |
| Cold chain management | Logistics | Future |
| Weather API integration | External | Future |
| Price prediction | AI | Future |

---

## 9. Security Architecture

```
Authentication: JWT (access + refresh tokens)
Authorization: Role-based middleware on every protected route
Input Validation: Pydantic schemas on all API inputs
Password Hashing: bcrypt via passlib
CORS: Configured per environment (dev vs production)
Rate Limiting: SlowAPI middleware (future)
Database: Parameterized queries (SQLAlchemy prevents SQL injection)
Environment Variables: All secrets loaded from .env
```

---

## 10. Deployment Architecture (Simple)

```
For SIH Demo (Simple):
├── Render.com / Railway.app (Backend API)
├── Vercel / Netlify (Frontend)
└── Neon / Supabase (PostgreSQL)

For Production (Future):
├── Docker containers
├── GitHub Actions CI/CD
├── AWS/GCP Cloud hosting
└── S3 for static assets
```

---

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Monolithic modular | Simpler for student team vs microservices |
| JWT for auth | Stateless, standard, easy to implement |
| SQLAlchemy ORM | Type-safe queries, migration support via Alembic |
| Pydantic for validation | Automatic docs, serialization, validation |
| Leaflet + OpenStreetMap | Free, no API key required for demo |
| Role-based middleware | Clear authorization per endpoint |
| Alembic migrations | Version-controlled schema changes |
| React Context for auth | Simple state without Redux overhead |

---

## 12. Next Step

Once architecture is approved:
1. Set up **backend project structure** (FastAPI + SQLAlchemy)
2. Set up **frontend project structure** (React + Vite)
3. Implement **database models** (defined in DATABASE.md)
4. Build **authentication** (JWT + roles)
5. Build **marketplace APIs** (products, orders)
