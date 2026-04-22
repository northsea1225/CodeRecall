from fastapi import APIRouter

from app.api.routes.ai import router as ai_router
from app.api.routes.categories import router as categories_router
from app.api.routes.import_export import router as import_export_router
from app.api.routes.mistakes import router as mistakes_router
from app.api.routes.review import router as review_router
from app.api.routes.stats import router as stats_router
from app.api.routes.problem_import import router as problem_import_router
from app.api.routes.tags import router as tags_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(import_export_router)
api_router.include_router(mistakes_router)
api_router.include_router(categories_router)
api_router.include_router(tags_router)
api_router.include_router(review_router)
api_router.include_router(stats_router)
api_router.include_router(problem_import_router)
