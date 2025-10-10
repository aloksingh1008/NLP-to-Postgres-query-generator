"""API endpoints for the word column mapper."""

from .search import router as search_router
from .reverse import router as reverse_router
from .operations import router as operations_router
from .health import router as health_router
from .metrics import router as metrics_router

__all__ = [
    "search_router",
    "reverse_router", 
    "operations_router",
    "health_router",
    "metrics_router",
]
