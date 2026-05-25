from fastapi import APIRouter

from app.api.audit import router as audit_router
from app.api.custom_api import router as custom_api_router
from app.api.dashboard import router as dashboard_router
from app.api.datasource import router as datasource_router
from app.api.desensitize import router as desensitize_router
from app.api.metadata import router as metadata_router
from app.api.query import router as query_router
from app.api.user import router as user_router
from app.api.user_mgmt import router as user_mgmt_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dashboard_router)
api_router.include_router(datasource_router)
api_router.include_router(metadata_router)
api_router.include_router(query_router)
api_router.include_router(user_router)
api_router.include_router(user_mgmt_router)
api_router.include_router(audit_router)
api_router.include_router(desensitize_router)
api_router.include_router(custom_api_router)
