"""Health check and monitoring API endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..core.engine import SearchEngine
from ..models.response import HealthResponse, ErrorResponse
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])
settings = get_settings()

# Import the global search engine instance
from ..engine_instance import search_engine

# Track application start time
app_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the search engine service"
)
async def health_check() -> HealthResponse:
    """
    Perform a health check on the search engine service.
    
    This endpoint checks the overall health of the service including
    dependencies and core functionality.
    """
    try:
        # Calculate uptime
        uptime = time.time() - app_start_time
        
        # Check core functionality
        dependencies = {
            "search_engine": "healthy",
            "index_manager": "healthy",
            "fuzzy_matcher": "healthy"
        }
        
        # Test basic functionality
        try:
            # Test search engine
            test_result = search_engine.search("test", max_results=1)
            if test_result is None:
                dependencies["search_engine"] = "degraded"
        except Exception:
            dependencies["search_engine"] = "unhealthy"
        
        # Determine overall status
        if all(status == "healthy" for status in dependencies.values()):
            status = "healthy"
        elif any(status == "unhealthy" for status in dependencies.values()):
            status = "unhealthy"
        else:
            status = "degraded"
        
        return HealthResponse(
            status=status,
            version=settings.app_version,
            uptime=uptime,
            dependencies=dependencies
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests"
)
async def readiness_check() -> JSONResponse:
    """
    Check if the service is ready to accept requests.
    
    This endpoint is used by load balancers and orchestration systems
    to determine if the service is ready to handle traffic.
    """
    try:
        # Check if search engine is initialized and functional
        stats = search_engine.get_stats()
        
        # Service is ready if we can get stats
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "index_stats": stats.get("index_stats", {})
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/health/live",
    summary="Liveness check",
    description="Check if the service is alive and responding"
)
async def liveness_check() -> JSONResponse:
    """
    Check if the service is alive and responding.
    
    This endpoint is used by orchestration systems to determine
    if the service process is still running and responsive.
    """
    try:
        # Simple liveness check - just return current time
        return JSONResponse(
            status_code=200,
            content={
                "status": "alive",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - app_start_time
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/status",
    summary="Service status",
    description="Get detailed status information about the service"
)
async def service_status() -> JSONResponse:
    """
    Get detailed status information about the service.
    
    This endpoint provides comprehensive status information including
    performance metrics, configuration, and system health.
    """
    try:
        # Get engine statistics
        stats = search_engine.get_stats()
        
        # Get configuration info
        config_info = {
            "fuzzy_threshold": settings.fuzzy_threshold,
            "max_results": settings.max_results,
            "max_query_length": settings.max_query_length,
            "enable_cache": settings.enable_cache,
            "debug": settings.debug
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "service": {
                    "name": settings.app_name,
                    "version": settings.app_version,
                    "status": "running",
                    "uptime": time.time() - app_start_time,
                    "start_time": datetime.fromtimestamp(app_start_time).isoformat()
                },
                "configuration": config_info,
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get service status: {str(e)}"
        )
