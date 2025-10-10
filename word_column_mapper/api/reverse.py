"""Reverse lookup API endpoints."""

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse

from ..core.engine import SearchEngine
from ..models.response import ReverseLookupResponse, ErrorResponse
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["reverse"])
settings = get_settings()

# Import the global search engine instance
from ..engine_instance import search_engine


@router.get(
    "/reverse/{column_id}",
    response_model=ReverseLookupResponse,
    summary="Reverse lookup by column ID",
    description="Find all words that map to a specific column identifier"
)
async def reverse_lookup(
    column_id: str = Path(..., description="The column identifier to search for")
) -> ReverseLookupResponse:
    """
    Find all words that map to a specific column identifier.
    
    This endpoint performs a reverse lookup to find all words
    that are associated with a given column ID.
    """
    try:
        result = search_engine.reverse_search(column_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Column '{column_id}' not found in index"
            )
        
        return ReverseLookupResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reverse lookup failed: {str(e)}"
        )


@router.get(
    "/columns",
    response_model=list[str],
    summary="Get all column IDs",
    description="Get a list of all column identifiers currently indexed"
)
async def get_all_columns() -> list[str]:
    """
    Get all column identifiers currently indexed in the search engine.
    
    This endpoint is useful for debugging, monitoring, or building
    client-side functionality that needs to know all available columns.
    """
    try:
        columns = search_engine.index_manager.reverse_index.get_all_columns()
        return sorted(columns)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get columns: {str(e)}"
        )


@router.get(
    "/columns/stats",
    summary="Get column statistics",
    description="Get statistics about columns in the index"
)
async def get_column_stats() -> JSONResponse:
    """
    Get statistics about columns in the index.
    
    Returns information about the number of columns, mappings,
    and other useful metrics for monitoring the system.
    """
    try:
        stats = search_engine.index_manager.get_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "total_columns": stats["total_unique_columns"],
                "total_mappings": stats["reverse_index"]["total_mappings"],
                "index_stats": stats
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get column stats: {str(e)}"
        )
