# KisanDirect AI QA Test Strategy

## 1. Purpose

This strategy verifies the operational rules of KisanDirect AI across authentication, marketplaces, FPO aggregation, bulk buying, logistics, route optimization, demand forecasting, and analytics. Tests must validate real behavior through services, database sessions, and HTTP endpoints; they must not assert implementation details through incomplete mocks.

## 2. Test Scope

### In scope

- Authentication and token lifecycle
- Role-based authorization
- Product listings and stock behavior
- Orders and state transitions
- FPO membership and aggregation ledger
- Bulk buyer matching and partial fulfillment
- Delivery assignment and status changes
- Route metrics and vehicle capacity
- Forecast data validation, training, persistence, and missing-model behavior
- Analytics calculations, source labels, and unavailable estimates

### Out of scope until implemented

- Payment gateway behavior
- External road-network provider accuracy
- GPS hardware and mobile background tracking
- Push notification delivery
- Production PostgreSQL performance and failover
- Causal claims about farmer income or consumer savings

## 3. Test Levels

### Unit tests

Test pure business rules without HTTP or external services:

- Password hashing and verification
- JWT encoding/decoding and expiry
- Allowed and forbidden order transitions
- Forecast input validation and metrics
- Haversine distance and nearest-neighbor ordering
- Deterministic bulk matching rules

### Service/integration tests

Use an isolated SQLite database with real SQLAlchemy models and services:

- Register users, create listings, place orders, and mutate stock
- FPO membership and source allocation reservation
- Aggregated listing fulfillment and allocation consumption
- Vehicle capacity and delivery assignment
- Analytics formulas across multiple tables
- Forecast run persistence

SQLite is a fast behavioral test database. PostgreSQL-specific migrations, indexes, and query plans require a separate PostgreSQL CI job before production deployment.

### API tests

Use FastAPI `TestClient` against the real application and dependency-overridden isolated database:

- Request validation and response schemas
- HTTP status codes
- Authorization headers
- Route registration
- End-to-end role workflows

### Frontend checks

- `npm run lint`
- `npm run build`
- Manual browser checks for login, protected routes, forms, loading, error, and empty states
- API contract checks against a running backend

## 4. Required Business-Rule Matrix

| Area | Rule | Required test |
|---|---|---|
| Authentication | Passwords are never stored in plaintext | Hash differs from input; correct and incorrect verification |
| Authentication | Expired tokens are rejected | Expired JWT returns invalid-token behavior |
| Authentication | Missing/malformed tokens are rejected | Protected endpoint returns `401` |
| Authorization | Consumers cannot create products | Product API returns `403` |
| Authorization | Non-admins cannot view platform analytics | Analytics API returns `403` |
| Products | Invalid price/quantity/input is rejected | Pydantic validation returns `422` |
| Inventory | Order cannot exceed current stock | Stale cart/order returns `409` |
| Inventory | Stock decreases exactly once after order | Remaining product quantity assertion |
| Orders | Empty cart cannot be checked out | Second checkout returns `400` |
| Orders | Buyer can cancel only permitted orders | Invalid role/state cancellation returns error |
| Orders | Only valid forward transitions are allowed | Full lifecycle transition tests |
| Orders | Terminal orders cannot move backward | `DELIVERED -> PENDING` returns conflict |
| FPO | Only farmer members can be added | Invalid member role returns `400` |
| FPO | Source listing cannot be allocated twice | Duplicate allocation returns `400` |
| FPO | Aggregate cannot exceed source quantity | Over-allocation returns `409` |
| FPO | Reserved source quantity is decremented | Source inventory assertion |
| FPO | Aggregate order consumes allocation ledger once | Allocation and aggregate quantity assertions |
| Bulk buyers | Matching honors product, unit, quality, and price | Candidate filtering test |
| Bulk buyers | Partial supply is reported, not fabricated as full | Required/matched/remaining assertions |
| Bulk buyers | No eligible supply cannot place an order | Placement returns `409` |
| Logistics | Vehicle belongs to operator | Cross-operator assignment returns `403` |
| Logistics | Vehicle capacity cannot be exceeded | Route optimization returns `409` |
| Logistics | Delivery needs coordinates for optimization | Missing location returns `422` |
| Routing | Map display is not called AI | Provider and optimizer are separately identified |
| Routing | Baseline and optimized routes are both returned | Route response assertions |
| Forecasting | Missing fields and invalid values are rejected | Validation tests |
| Forecasting | Insufficient history does not produce accuracy | Training returns an error |
| Forecasting | Metrics come from holdout data | MAE/RMSE/MAPE are returned from training |
| Forecasting | Missing persisted model is handled | Prediction returns `409` |
| Analytics | Every metric has a calculation | Metric schema and definitions endpoint |
| Analytics | Demo and actual data are separated | Source-label assertions |
| Analytics | Unsupported impact estimates are not invented | Estimate values remain `null` |

## 5. Negative and Edge Cases

### Authentication/security

- Duplicate email registration
- Invalid email format
- Password shorter than eight characters
- Wrong password
- Expired, malformed, and revoked JWTs
- User deactivated after token issue
- Privileged self-registration attempts
- Cross-user resource access

### Marketplace/inventory

- Zero and negative quantities
- Decimal quantity precision
- Inactive product purchase
- Concurrent/stale checkout risk
- Duplicate cart item addition
- Empty cart checkout
- Product owner mismatch
- Order stock reduction and rollback on failure

### FPO

- Duplicate membership
- Inactive member source
- Non-farmer member
- Duplicate source allocation in one request
- Allocation greater than available stock
- Mixed product name, unit, or category
- Repeated aggregation after source reservation
- Aggregated listing order exceeding allocation ledger

### Orders/logistics

- Unknown order state
- Same-state transition
- Backward transition
- Cancellation after pickup/delivery
- Assignment before `READY_FOR_PICKUP`
- Duplicate delivery assignment
- Unavailable vehicle
- Wrong operator or vehicle
- Empty route
- Missing delivery location
- Load greater than vehicle capacity
- Zero or invalid average speed

### Forecasting/analytics

- Empty history
- Fewer than minimum training rows
- Invalid dates, negative quantity, zero price
- Missing model artifact
- Unknown forecast category
- No delivered orders
- No routes
- No forecast runs
- Only demo route/forecast records

## 6. Current Automated Test Inventory

- `tests/test_foundation.py`: authentication, marketplace, FPO aggregation, order and delivery workflows
- `tests/test_order_states.py`: direct transition policy tests
- `tests/test_forecasting.py`: validation, training, model persistence, prediction, insufficient data
- `tests/test_logistics.py`: routing provider and route metrics
- `tests/test_analytics.py`: analytics calculations and provenance
- `tests/test_qa_rules.py`: security, authorization, stale inventory, duplicate checkout, capacity, invalid route, missing forecast model, definitions API

Run all backend tests:

```powershell
cd backend
python -m compileall -q app tests
python -m pytest tests -q
```

Run frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## 7. Quality Gates

A change is ready for review when:

1. Focused tests pass.
2. Full backend suite passes.
3. Frontend lint and build pass for frontend changes.
4. New business rules have both valid and invalid cases.
5. No test relies on invented production statistics.
6. Demo/synthetic data is labeled.
7. Security tests cover authentication and resource ownership.
8. Database migrations are added for schema changes before PostgreSQL deployment.

## 8. Known Test Environment Limits

The current local interpreter is Windows ARM64. Tests use SQLite and do not prove a live PostgreSQL connection. Route tests use Haversine straight-line distances, which are demo estimates rather than road travel distances. Existing SQLAlchemy timestamp code emits deprecation warnings for `datetime.utcnow()`; these warnings do not currently fail the suite but should be removed in a maintenance pass.
