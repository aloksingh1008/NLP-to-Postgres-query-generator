"""Metrics and monitoring API endpoints."""

import psutil
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..core.engine import SearchEngine
from ..models.response import MetricsResponse, ErrorResponse
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["metrics"])
settings = get_settings()

# Import the global search engine instance
from ..engine_instance import search_engine


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get performance metrics",
    description="Get comprehensive performance metrics for the search engine"
)
async def get_metrics() -> MetricsResponse:
    """
    Get comprehensive performance metrics for the search engine.
    
    This endpoint provides detailed performance metrics including
    query statistics, response times, and system resource usage.
    """
    try:
        # Get engine statistics
        stats = search_engine.get_stats()
        
        # Get system memory usage
        memory_info = psutil.virtual_memory()
        memory_usage_mb = memory_info.used / (1024 * 1024)  # Convert to MB
        
        # Calculate metrics
        total_queries = stats.get("total_queries", 0)
        total_execution_time = stats.get("total_execution_time", 0.0)
        exact_matches = stats.get("exact_matches", 0)
        fuzzy_matches = stats.get("fuzzy_matches", 0)
        no_matches = stats.get("no_matches", 0)
        
        # Calculate rates
        if total_queries > 0:
            average_response_time_ms = total_execution_time / total_queries
            error_rate = 0.0  # We don't track errors separately yet
        else:
            average_response_time_ms = 0.0
            error_rate = 0.0
        
        # Cache metrics (placeholder - will be implemented with Redis)
        cache_hit_rate = 0.0
        
        # Active connections (placeholder - will be implemented with connection tracking)
        active_connections = 0
        
        return MetricsResponse(
            total_queries=total_queries,
            average_response_time_ms=average_response_time_ms,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate,
            active_connections=active_connections,
            memory_usage_mb=memory_usage_mb
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get(
    "/metrics/detailed",
    summary="Get detailed metrics",
    description="Get detailed performance metrics including breakdown by operation type"
)
async def get_detailed_metrics() -> JSONResponse:
    """
    Get detailed performance metrics including breakdown by operation type.
    
    This endpoint provides comprehensive metrics including query type
    breakdown, performance percentiles, and system resource usage.
    """
    try:
        # Get engine statistics
        stats = search_engine.get_stats()
        
        # Get system information
        memory_info = psutil.virtual_memory()
        cpu_info = psutil.cpu_percent(interval=1)
        
        # Calculate detailed metrics
        total_queries = stats.get("total_queries", 0)
        
        if total_queries > 0:
            exact_match_rate = stats.get("exact_match_rate", 0.0)
            fuzzy_match_rate = stats.get("fuzzy_match_rate", 0.0)
            no_match_rate = stats.get("no_match_rate", 0.0)
            average_response_time = stats.get("average_execution_time_ms", 0.0)
        else:
            exact_match_rate = 0.0
            fuzzy_match_rate = 0.0
            no_match_rate = 0.0
            average_response_time = 0.0
        
        # Index statistics
        index_stats = stats.get("index_stats", {})
        forward_stats = index_stats.get("forward_index", {})
        reverse_stats = index_stats.get("reverse_index", {})
        
        return JSONResponse(
            status_code=200,
            content={
                "query_metrics": {
                    "total_queries": total_queries,
                    "exact_matches": stats.get("exact_matches", 0),
                    "fuzzy_matches": stats.get("fuzzy_matches", 0),
                    "no_matches": stats.get("no_matches", 0),
                    "exact_match_rate": exact_match_rate,
                    "fuzzy_match_rate": fuzzy_match_rate,
                    "no_match_rate": no_match_rate,
                    "average_response_time_ms": average_response_time,
                    "total_execution_time_ms": stats.get("total_execution_time", 0.0)
                },
                "index_metrics": {
                    "total_words": forward_stats.get("total_words", 0),
                    "total_mappings": forward_stats.get("total_mappings", 0),
                    "total_columns": reverse_stats.get("total_columns", 0),
                    "unique_columns": index_stats.get("total_unique_columns", 0)
                },
                "system_metrics": {
                    "memory_usage_mb": memory_info.used / (1024 * 1024),
                    "memory_usage_percent": memory_info.percent,
                    "cpu_usage_percent": cpu_info,
                    "available_memory_mb": memory_info.available / (1024 * 1024)
                },
                "cache_metrics": {
                    "cache_hits": stats.get("cache_hits", 0),
                    "cache_misses": stats.get("cache_misses", 0),
                    "cache_hit_rate": 0.0  # Will be implemented with Redis
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed metrics: {str(e)}"
        )


@router.get(
    "/metrics/performance",
    summary="Get performance benchmarks",
    description="Get performance benchmark results for different query types"
)
async def get_performance_benchmarks() -> JSONResponse:
    """
    Get performance benchmark results for different query types.
    
    This endpoint provides performance benchmarks for different
    types of queries to help with performance monitoring and optimization.
    """
    try:
        # Get engine statistics
        stats = search_engine.get_stats()
        
        # Calculate performance metrics
        total_queries = stats.get("total_queries", 0)
        total_execution_time = stats.get("total_execution_time", 0.0)
        
        if total_queries > 0:
            average_response_time = total_execution_time / total_queries
            
            # Performance targets from documentation
            performance_targets = {
                "exact_match_target_ms": 1.0,
                "single_typo_target_ms": 10.0,
                "multiple_typo_target_ms": 50.0,
                "cold_start_target_ms": 100.0
            }
            
            # Performance status
            performance_status = {
                "exact_match_performance": "good" if average_response_time < 1.0 else "needs_improvement",
                "fuzzy_match_performance": "good" if average_response_time < 10.0 else "needs_improvement",
                "overall_performance": "good" if average_response_time < 5.0 else "needs_improvement"
            }
        else:
            average_response_time = 0.0
            performance_targets = {}
            performance_status = {
                "exact_match_performance": "no_data",
                "fuzzy_match_performance": "no_data", 
                "overall_performance": "no_data"
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "current_performance": {
                    "average_response_time_ms": average_response_time,
                    "total_queries": total_queries,
                    "total_execution_time_ms": total_execution_time
                },
                "performance_targets": performance_targets,
                "performance_status": performance_status,
                "recommendations": _get_performance_recommendations(average_response_time),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance benchmarks: {str(e)}"
        )


def _get_performance_recommendations(average_response_time: float) -> list[str]:
    """Get performance recommendations based on current metrics."""
    recommendations = []
    
    if average_response_time > 50.0:
        recommendations.append("Consider implementing caching for frequently accessed data")
        recommendations.append("Review fuzzy matching algorithms for optimization opportunities")
        recommendations.append("Consider using more efficient data structures")
    elif average_response_time > 10.0:
        recommendations.append("Consider implementing result caching")
        recommendations.append("Monitor memory usage and optimize if needed")
    elif average_response_time > 5.0:
        recommendations.append("Performance is good, consider monitoring for trends")
    else:
        recommendations.append("Excellent performance! Consider documenting best practices")
    
    return recommendations
