# KisanDirect AI Test Strategy

## 1. Purpose and quality objectives

This strategy defines how KisanDirect AI is tested across the implemented FastAPI
backend and React frontend. It is a living test design, not only a list of
happy-path checks. Every important business rule has a positive, negative, and
boundary test where applicable.

The release must demonstrate:

- Correct authentication, authorization, ownership, and tenant isolation.
- Atomic inventory and order behavior, including failure and retry behavior.
- A valid order state machine with no illegal transitions.
- Correct FPO aggregation and allocation-ledger accounting.
- Correct bulk matching and partial-fulfilment reporting.
- Safe logistics assignment, capacity enforcement, and route validation.
- Honest demand forecasts and analytics, including unavailable-data responses.
- Stable API contracts and usable frontend loading, error, and empty states.

The source-of-truth implementation surfaces are the routers under
`backend/app/routers`, services under `backend/app/services`, SQLAlchemy models,
and the API and domain documents in `docs/`.

## 2. Scope

### In scope

Authentication, role authorization, users, products, inventory, cart and orders,
FPOs, bulk buyers, logistics, route optimization, demand forecasting, analytics,
database consistency, API contracts, frontend integration, and security.

### Out of scope until implemented

Payment-provider settlement, real road-network accuracy, GPS hardware and
background tracking, push notification delivery, production PostgreSQL failover
and query-plan benchmarking, and causal claims about farmer income or savings.
These still require contract tests or explicit feature flags when introduced.

## 3. Test pyramid and responsibilities

### Unit tests

Fast tests with no HTTP or external services. Cover password hashing and JWT
validation, Pydantic constraints, order transition policy, inventory and money
calculations, bulk matching, FPO allocation arithmetic, Haversine distance and
nearest-neighbor ordering, forecast validation/metrics, and analytics formulas.
Use table-driven tests for every allowed and forbidden state/role combination.

### Service and database integration tests

Use the real services, repositories, models, and an isolated database per test
or test class. Verify transactions and persisted state, not just returned
objects. SQLite is suitable for fast behavior tests; a PostgreSQL CI job is
required for migrations, constraints, indexes, locking, numeric behavior, and
concurrency before production.

### API tests

Use FastAPI `TestClient` with the real application and an overridden isolated
database. Assert endpoint registration, request validation, response schemas,
status codes, error bodies, authentication headers, ownership checks, and
end-to-end workflows. Each protected endpoint must have anonymous, valid-role,
and invalid-role cases.

### Frontend tests and checks

Run `npm run lint` and `npm run build`. Add component/integration tests when a
browser test runner is introduced. Until then, manually verify login, protected
route redirects, role-based navigation, form validation, API loading/error/empty
states, pagination/filtering, and order/logistics status refresh against a
running backend.

### Contract, smoke, and operational tests

On every merge, run health, auth, product browse, order checkout, and one
logistics/forecast smoke flow. Validate OpenAPI response shapes and documented
error codes. Run migration-up/migration-down checks and seed-data checks in
PostgreSQL CI. Do not use synthetic demo records as evidence of production
impact; every analytics and forecast record must expose its provenance.

## 4. Test data and isolation

Use factory fixtures for:

- Users: `CONSUMER`, `FARMER`, `FPO`, `BULK_BUYER`, `LOGISTICS`, `ADMIN`;
  active, inactive, revoked-token, and cross-tenant users.
- Products: active/inactive, owner/FPO listings, integer and decimal quantities,
  multiple categories/units/quality grades, zero and low stock.
- Orders: one and many items, each state, delivered/cancelled orders, duplicate
  request identifiers where supported, and orders owned by another user.
- FPOs: owner, active/inactive members, source listings, allocations and
  aggregated listings.
- Vehicles and locations: exact-capacity, under-capacity, over-capacity,
  unavailable, cross-operator, missing, boundary, and invalid coordinates.
- Forecasts and analytics: empty history, minimum history, noisy history,
  missing model artifact, demo-only records, and actual delivered orders.

Reset database state between tests. Avoid shared mutable fixtures. Freeze time
for expiry, order timestamps, forecast dates, and analytics windows. Use decimal
assertions for prices and quantities rather than binary floating-point equality.

## 5. Business-rule traceability matrix

The IDs below are required tests. `U` means unit, `I` service/database
integration, `A` API, `N` negative/edge, and `S` security.

### Authentication and authorization

| ID | Rule and test |
|---|---|
| AUTH-01 U/I | Passwords are hashed with a salt; plaintext is never persisted; correct password verifies and wrong/empty password fails. |
| AUTH-02 A/N | Registration trims permitted text, validates email, rejects malformed email and password shorter than eight characters with `422`. |
| AUTH-03 A/N | Duplicate email registration is rejected without creating a second user. |
| AUTH-04 A/S | Self-registration cannot create `ADMIN`, `LOGISTICS`, or other privileged roles by payload override. |
| AUTH-05 A | Login returns a bearer token and expiry for valid credentials; nonexistent email and wrong password return the same `401` shape. |
| AUTH-06 U/A/N | Missing, malformed, expired, tampered, wrong-signing-key, missing-subject, and unsupported-algorithm tokens return `401` with `WWW-Authenticate`. |
| AUTH-07 I/A | Logout increments token version; the old token cannot access a protected endpoint while a newly issued token can. |
| AUTH-08 I/A | Inactive/deleted users and tokens with stale token versions are rejected. |
| AUTH-09 A/S | Every protected endpoint denies anonymous access; role checks return `403`, never data. |
| AUTH-10 A/S | Cross-user and cross-tenant IDs cannot read or mutate users, products, carts, orders, FPOs, requirements, vehicles, or forecasts. |
| AUTH-11 A/N | Very long names, emails, headers, and bearer values are rejected or safely bounded without a server error. |

### Products and inventory

| ID | Rule and test |
|---|---|
| PROD-01 U/A | Product name, category, unit, price, and quantity constraints reject missing, blank, negative, zero-invalid, and over-precision values. |
| PROD-02 A | Only permitted seller roles create listings; consumers, bulk buyers, logistics users, and admins follow the documented policy. |
| PROD-03 I/A/S | A seller can edit/deactivate only its own listing; another seller receives `403`/`404` and state is unchanged. |
| PROD-04 A | Browse returns only active products, honors search/category/sort, and enforces page >= 1 and limit 1..100. |
| PROD-05 I/A | Cart rejects inactive/nonexistent products, invalid quantities, and duplicate cart lines according to the merge/reject rule. |
| INV-01 I/A | Checkout succeeds when requested quantity is exactly available and decrements stock exactly once. |
| INV-02 I/A/N | Insufficient inventory returns `409`; no order, payment-like side effect, or partial stock decrement remains. |
| INV-03 I/A/N | Zero, negative, fractional-invalid, and excessive quantities are rejected; decimal quantities retain configured precision. |
| INV-04 I/A/N | Two concurrent/stale checkouts cannot oversell; one fails cleanly and final stock equals initial stock minus committed quantity. |
| INV-05 I/A | Empty cart cannot be checked out; retrying a successful checkout cannot create a duplicate order or decrement stock twice. |
| INV-06 I/A | A multi-item checkout is atomic: if any line fails, all order lines and inventory changes roll back. |
| INV-07 I/A | Inventory aggregation equals the sum of active eligible source quantities, excludes inactive/duplicate sources, and never double-counts after repeat reads. |
| INV-08 S | SQL injection in search/category and XSS in product text are treated as data; no query escape or executable markup is possible. |

### Orders

| ID | Rule and test |
|---|---|
| ORD-01 A | Only buyer roles can place orders; seller/logistics/admin role behavior matches policy and invalid roles are denied. |
| ORD-02 I/A | Created orders contain the correct buyer, seller/FPO, item snapshot, totals, quantity, and initial `PENDING` state. |
| ORD-03 U/A | Test every allowed transition: `PENDING->CONFIRMED/CANCELLED`, `CONFIRMED->PREPARING/CANCELLED`, `PREPARING->READY_FOR_PICKUP/CANCELLED`, `READY_FOR_PICKUP->IN_TRANSIT`, and `IN_TRANSIT->DELIVERED`. |
| ORD-04 U/A/N | Reject same-state, skipped, backward, unknown, and terminal-state transitions with the documented `403`, `409`, or `422`; state never mutates. |
| ORD-05 A/S | Consumer cancellation is limited to owned orders and permitted states; sellers/logistics cannot cancel another user's order. |
| ORD-06 A/S | Buyer, seller, FPO, logistics operator, and admin order lists expose only their authorized scope; IDOR attempts are denied. |
| ORD-07 I/A | Delivery assignment is allowed only at `READY_FOR_PICKUP`, cannot be duplicated, and status updates follow their own valid lifecycle. |
| ORD-08 I/A/N | Delivery completion records current location when required, sets order delivered once, and rejects invalid locations or repeated completion. |
| ORD-09 A/N | Unknown order IDs, malformed path IDs, missing address, short address, empty cart, and oversized payloads return stable client errors. |

### FPO

| ID | Rule and test |
|---|---|
| FPO-01 A | Only an eligible role creates an FPO; name and required fields validate boundaries. |
| FPO-02 A/S | Only the FPO owner can list/add/remove members and manage FPO resources; non-owner and unrelated users are denied. |
| FPO-03 I/A/N | Only farmer users can be members; duplicate membership, inactive members, unknown farmers, and removing an absent member fail without mutation. |
| FPO-04 I/A | Aggregation accepts only active member source listings with matching product/category/unit/quality rules. |
| FPO-05 I/A/N | Duplicate source IDs in one request, non-member sources, inactive sources, mixed categories/units, and quantities above available stock are rejected. |
| FPO-06 I/A | Reservation decrements source inventory once and creates an allocation-ledger entry whose total equals the aggregate listing quantity. |
| FPO-07 I/A/N | Allocation-ledger insufficiency returns `409`; repeated aggregation or repeated order fulfillment cannot reserve/consume the same source twice. |
| FPO-08 I/A | Orders against an aggregate listing consume the ledger across sources exactly once; remaining allocations and source stock reconcile. |
| FPO-09 A/S | FPO inventory, listings, orders, and analytics cannot be viewed through another FPO's ID. |
| FPO-10 I/A | FPO analytics count only authorized delivered orders and compute revenue from the correct order state and seller scope. |

### Bulk buyers

| ID | Rule and test |
|---|---|
| BULK-01 A | Only `BULK_BUYER` can create/list/view its requirements; other roles and another buyer's IDs are denied. |
| BULK-02 U/A/N | Requirement validates product, quantity, unit, quality, max price, and delivery fields; zero/negative/over-precision values fail. |
| BULK-03 U/I | Matching filters by product, unit, quality compatibility, active supply, seller eligibility, and max price deterministically. |
| BULK-04 I/A | Matching is read-only: it does not reserve or decrement inventory and reports candidate quantities accurately. |
| BULK-05 I/A | Partial supply reports required, matched, and remaining quantities; it never fabricates full fulfilment. |
| BULK-06 I/A/N | No eligible supply and insufficient supply prevent placement with `409`; no partial order set or stock mutation remains. |
| BULK-07 I/A | Placed orders have correct line totals and seller allocation; repeating placement cannot duplicate orders for the same live match. |
| BULK-08 N | Stale match, inactive product, changed price, and changed inventory are revalidated at placement. |

### Logistics and route optimization

| ID | Rule and test |
|---|---|
| LOG-01 A/S | Only logistics operators can create/list vehicles and assignments; operators cannot access another operator's vehicle or delivery. |
| LOG-02 U/A/N | Vehicle capacity, registration, availability, speed, and location fields validate zero, negative, blank, and maximum boundaries. |
| LOG-03 I/A | Pickup/delivery locations persist correct coordinates and ownership; invalid latitude/longitude and missing required location fail. |
| LOG-04 I/A | Assignment requires an eligible order state, valid operator/vehicle, required pickup/delivery locations, and an available vehicle. |
| LOG-05 I/A/N | Vehicle capacity is enforced at exact capacity and rejects any load above capacity; rejected assignment leaves vehicle/order unchanged. |
| LOG-06 I/A/N | Duplicate assignment, unavailable vehicle, wrong operator, unknown order, and assignment before pickup readiness fail safely. |
| ROUTE-01 U | Haversine distance is correct for known coordinates, identical points are zero, and depot round-trip includes both depot legs. |
| ROUTE-02 U/I | Nearest-neighbor returns each stop exactly once, is deterministic for ties, and does not mutate input stops. |
| ROUTE-03 A/N | Empty stops, duplicate/invalid coordinates, invalid depot, zero/negative speed, and impossible capacity return client errors. |
| ROUTE-04 I/A | Optimized response contains valid baseline and optimized metrics, route order, total distance, duration, provider identity, and capacity checks. |
| ROUTE-05 S | Route and delivery IDs cannot be used to inspect or alter another operator's data. |

### Demand forecasting

| ID | Rule and test |
|---|---|
| FORE-01 U/A | Observation requires valid date, category/product, positive quantity, and positive price; missing, malformed, duplicate, and future dates follow policy. |
| FORE-02 A/S | Only authorized roles add observations/train/request forecasts; invalid role access returns `403`. |
| FORE-03 U/I | Training rejects empty or fewer-than-minimum history with a clear error and writes no misleading model or metrics. |
| FORE-04 U/I | Training uses a time-ordered holdout, returns MAE/RMSE/MAPE, persists the selected model and metadata, and is reproducible for fixed data. |
| FORE-05 I/A/N | Missing/corrupt model artifact, unknown product/category, and insufficient prediction data return `409`/`422` without a fabricated forecast. |
| FORE-06 I/A | Forecast horizon, dates, non-negative predictions, confidence bounds, and model metadata satisfy schema and domain constraints. |
| FORE-07 I/A | New training replaces or versions artifacts consistently; concurrent training does not leave a partially written model. |

### Analytics

| ID | Rule and test |
|---|---|
| AN-01 A/S | Dashboard is restricted to the documented admin/platform role; definitions are public only if that is the intended contract. |
| AN-02 U/I | Orders, revenue, fulfilment, inventory, route, and forecast metrics use the documented filters and aggregation formulas. |
| AN-03 I/A | Cancelled/pending orders are excluded from delivered/revenue metrics; only delivered orders contribute to transaction value. |
| AN-04 I/A/N | Empty database, no delivered orders, no routes, no forecast runs, and demo-only data return valid zero/null/unavailable values rather than exceptions. |
| AN-05 A | Every metric includes a definition, unit, source/provenance label, and consistent numeric type; demo and actual values are never silently combined. |
| AN-06 S | Analytics cannot leak other tenants' farmer, buyer, FPO, order, inventory, or forecast details through filters or error messages. |

## 6. Negative, edge, and security campaign

Run these as a separate regression tag as well as alongside feature tests:

- Authentication: credential enumeration, token replay after logout, token tampering,
  `alg=none`, wrong issuer/audience if configured, inactive users, oversized
  headers, and rate-limit behavior when rate limiting is implemented.
- Authorization: every endpoint with no token, each wrong role, wrong owner,
  cross-FPO/cross-operator IDOR, altered path/query/body IDs, and privilege
  escalation through registration or mass assignment.
- Input safety: SQL injection strings, XSS/HTML, Unicode/whitespace normalization,
  boundary numeric values, malformed JSON, duplicate keys, unknown fields, and
  oversized arrays/payloads.
- Consistency: concurrent checkout, repeated POST/retry, rollback after a later
  line fails, duplicate webhook/status delivery, and process interruption during
  inventory or ledger updates.
- AI/data integrity: missing forecast data, missing/corrupt artifact, leakage of
  future observations into training, impossible negative forecasts, and
  analytics that treat demo records as real outcomes.

Use dependency and secret scanning in CI, TLS in deployed environments, secure
cookie/header configuration where applicable, and verify that logs redact
passwords, bearer tokens, and sensitive personal data.

## 7. Automation layout and naming

Keep backend tests under `backend/tests` and organize markers by level:
`unit`, `integration`, `api`, `security`, `slow`, and `postgres`. Recommended
files are:

- `test_auth_unit.py`, `test_authorization_api.py`
- `test_products_inventory.py`, `test_orders_api.py`, `test_order_states.py`
- `test_fpo.py`, `test_bulk_buyers.py`
- `test_logistics.py`, `test_logistics_routing.py`
- `test_forecasting.py`, `test_analytics.py`
- `test_security_edge_cases.py`, `test_contracts.py`

Use names containing the matrix ID, for example
`test_INV_02_insufficient_inventory_is_atomic`. A failing test must identify
the rule, actor, request, expected status, and persistence assertion.

## 8. Execution plan

Local fast feedback:

```powershell
cd backend
python -m compileall -q app tests
python -m pytest tests -q -m "unit or api"
```

Full backend regression:

```powershell
cd backend
python -m pytest tests -q
```

Frontend validation:

```powershell
cd frontend
npm run lint
npm run build
```

Before release, also run the PostgreSQL migration/constraint/concurrency job,
security campaign, API contract tests, and smoke flow against a deployed-like
environment. Capture test reports, coverage, response-time percentiles, and
database logs as CI artifacts.

## 9. Coverage, quality gates, and exit criteria

Coverage targets are guidance, not a substitute for the rule matrix:

- 90%+ line and branch coverage for pure business-rule modules.
- 80%+ service coverage, including failure paths and transaction rollback.
- 100% of matrix IDs automated or explicitly accepted as a documented gap.
- 100% of protected routes covered by anonymous and invalid-role authorization
  tests.

A release candidate is acceptable only when:

1. All focused and full backend tests pass.
2. Frontend lint and build pass.
3. No open critical/high security or data-integrity defect remains.
4. Insufficient inventory, duplicate orders, unauthorized access, invalid roles,
   invalid transitions, aggregation errors, capacity violations, invalid routes,
   and missing forecast data have passing regression tests.
5. PostgreSQL migrations and constraints pass in CI.
6. Test data provenance, model version, and analytics source labels are verified.
7. Known warnings and environment limitations are recorded with an owner and
   remediation plan.

## 10. Current repository baseline and known limits

The repository already contains backend coverage for foundation flows,
authentication, orders, FPO, bulk buyers, logistics/routing, forecasting,
analytics, and security edge cases under `backend/tests`. The suite should be
mapped to the IDs above and any uncovered IDs added before claiming complete
coverage. The frontend currently exposes lint/build scripts but no test runner.

Local tests use SQLite and therefore do not prove PostgreSQL locking, migration,
index, or numeric behavior. Route optimization currently uses a Haversine
straight-line provider and nearest-neighbor heuristic; it must not be reported
as road-distance or globally optimal routing. External integrations remain
contract-test boundaries until implemented.
