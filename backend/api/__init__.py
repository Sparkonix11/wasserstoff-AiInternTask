from fastapi import APIRouter
from backend.api.routes import game_routes

router = APIRouter(prefix="/api")

# Remove the additional "/game" prefix to match frontend expectations
router.include_router(game_routes.router, tags=["game"])