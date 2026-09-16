"""
API v1 Router aggregator for Land Stack India.
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.public import router as public_router
from app.api.v1.citizen import router as citizen_router
from app.api.v1.government import router as government_router
from app.api.v1.gis import router as gis_router
from app.api.v1.documents import router as documents_router
from app.api.v1.integration import router as integration_router
from app.api.v1.ai import router as ai_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(public_router)
api_v1_router.include_router(citizen_router)
api_v1_router.include_router(government_router)
api_v1_router.include_router(gis_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(integration_router)
api_v1_router.include_router(ai_router)

__all__ = ["api_v1_router"]
