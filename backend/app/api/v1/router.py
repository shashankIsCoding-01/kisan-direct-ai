from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.analytics import router as analytics_router
from app.routers.bulk import router as bulk_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
from app.routers.logistics import router as logistics_router
from app.routers.products import router as products_router
from app.routers.fpos import router as fpos_router
from app.routers.forecast import router as forecast_router
from app.routers.users import router as users_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(bulk_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(cart_router)
api_v1_router.include_router(orders_router)
api_v1_router.include_router(logistics_router)
api_v1_router.include_router(fpos_router)
api_v1_router.include_router(forecast_router)
