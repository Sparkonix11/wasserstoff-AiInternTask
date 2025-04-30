"""
API Routes module initialization
"""

from backend.api.routes.game_routes import router as game_router

__all__ = ["game_router"]