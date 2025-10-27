"""Main FastAPI application for the Word Column Mapper."""

import json
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from .api import (
    search_router,
    reverse_router,
    operations_router,
    health_router,
    metrics_router,
)
from .api.sql_generation import sql_router
from .config import get_settings
from .engine_instance import search_engine
from .models.response import ErrorResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Word Column Mapper service", version=settings.app_version)
    
    # Load mappings from JSON file
    try:
        json_file_path = os.path.join(os.path.dirname(__file__), "sample_mappings2.json")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            sample_mappings = json.load(f)
        
        search_engine.load_mappings(sample_mappings)
        logger.info("Sample mappings loaded from JSON", total_words=len(sample_mappings))
    except FileNotFoundError:
        logger.warning("sample_mappings.json not found, using fallback data")
        # Fallback to basic sample data
        fallback_mappings = {
            "date": ["column3423", "column5738", "column3846", "column4632"],
            "start_date": ["column5738", "column4632"], 
            "end_date": ["column3423", "column3846"]
        }
        search_engine.load_mappings(fallback_mappings)
        logger.info("Fallback mappings loaded", total_words=len(fallback_mappings))
    except Exception as e:
        logger.error("Failed to load mappings", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Word Column Mapper service")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="High-performance search engine for mapping words to column identifiers",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2)
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle global exceptions."""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            details={"exception": str(exc)} if settings.debug else None
        ).dict()
    )


# Include API routers
app.include_router(search_router)
app.include_router(reverse_router)
app.include_router(operations_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(sql_router)  # SQL Generation with MCP


# Root endpoint
@app.get("/", summary="Root endpoint", description="Get basic information about the API")
async def root() -> dict:
    """Root endpoint with basic API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "High-performance search engine for mapping words to column identifiers",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "status": "running"
    }


# API info endpoint
@app.get("/api", summary="API information", description="Get detailed API information")
async def api_info() -> dict:
    """Get detailed API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "High-performance search engine for mapping words to column identifiers",
        "endpoints": {
            "search": "/api/v1/search/{query}",
            "reverse": "/api/v1/reverse/{column_id}",
            "intersection": "/api/v1/intersection?words=word1,word2",
            "union": "/api/v1/union?words=word1,word2",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics"
        },
        "features": [
            "Exact word matching",
            "Fuzzy matching with typo correction",
            "Case-insensitive searches",
            "Delimiter handling (underscores, hyphens, spaces)",
            "Reverse lookup by column ID",
            "Set operations (intersection/union)",
            "Real-time performance metrics",
            "Comprehensive API documentation"
        ],
        "performance": {
            "exact_match_target_ms": 1.0,
            "fuzzy_match_target_ms": 10.0,
            "max_query_length": settings.max_query_length,
            "max_results": settings.max_results
        }
    }


# Serve static files for frontend
try:
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    app.mount("/dashboard", StaticFiles(directory="frontend", html=True), name="dashboard")
except RuntimeError:
    # Static files not available, skip mounting
    pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "word_column_mapper.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower()
    )
