"""Search API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from ..core.engine import SearchEngine
from ..models.response import SearchResponse, ErrorResponse
from ..models.request import SearchRequest, BatchSearchRequest
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["search"])
settings = get_settings()

# Import the global search engine instance
from ..engine_instance import search_engine


@router.get(
    "/search/{query}",
    response_model=SearchResponse,
    summary="Search for columns by word",
    description="Search for column identifiers that match a given word with fuzzy matching support"
)
async def search_word(
    query: str = Path(..., description="The word to search for", min_length=1, max_length=100),
    fuzzy_threshold: Optional[float] = Query(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Custom fuzzy matching threshold (0.0-1.0)"
    ),
    max_results: Optional[int] = Query(
        None, 
        ge=1, 
        le=100, 
        description="Maximum number of results to return"
    ),
    include_suggestions: bool = Query(
        True, 
        description="Whether to include suggestions for no-match queries"
    )
) -> SearchResponse:
    """
    Search for columns matching a word query.
    
    Supports exact matching and fuzzy matching with typo correction.
    Returns detailed results including confidence scores and match types.
    """
    try:
        # Validate query length
        if len(query) > settings.max_query_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query too long. Maximum length is {settings.max_query_length} characters"
            )
        
        # Perform search
        result = search_engine.search(
            query=query,
            fuzzy_threshold=fuzzy_threshold,
            max_results=max_results or settings.max_results,
            include_suggestions=include_suggestions
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search with request body",
    description="Search for columns using a structured request body"
)
async def search_with_body(request: SearchRequest) -> SearchResponse:
    """
    Search for columns using a structured request body.
    
    This endpoint accepts a JSON request body with additional options
    for fine-tuning the search behavior.
    """
    try:
        result = search_engine.search(
            query=request.query,
            fuzzy_threshold=request.fuzzy_threshold,
            max_results=request.max_results or settings.max_results,
            include_suggestions=request.include_suggestions
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post(
    "/search/batch",
    response_model=list[SearchResponse],
    summary="Batch search",
    description="Search multiple queries in a single request"
)
async def batch_search(request: BatchSearchRequest) -> list[SearchResponse]:
    """
    Perform batch search for multiple queries.
    
    This endpoint allows you to search multiple words in a single request,
    which is more efficient than making multiple individual requests.
    """
    try:
        results = []
        
        for query in request.queries:
            result = search_engine.search(
                query=query,
                fuzzy_threshold=request.fuzzy_threshold,
                max_results=request.max_results or settings.max_results,
                include_suggestions=True
            )
            results.append(result)
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch search failed: {str(e)}"
        )


@router.get(
    "/suggestions/{query}",
    response_model=list[str],
    summary="Get search suggestions",
    description="Get word suggestions for a partial or misspelled query"
)
async def get_suggestions(
    query: str = Path(..., description="The query to get suggestions for", min_length=1),
    max_suggestions: int = Query(5, ge=1, le=20, description="Maximum number of suggestions")
) -> list[str]:
    """
    Get suggestions for a query.
    
    Useful for autocomplete functionality or when users need help
    finding the right word to search for.
    """
    try:
        # Get all words from the index
        all_words = search_engine.index_manager.forward_index.get_all_words()
        
        # Use fuzzy matcher to get suggestions
        suggestions = search_engine.fuzzy_matcher.suggest_corrections(
            query, all_words, max_suggestions
        )
        
        return suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get(
    "/words",
    response_model=list[str],
    summary="Get all indexed words",
    description="Get a list of all words currently indexed in the search engine"
)
async def get_all_words() -> list[str]:
    """
    Get all words currently indexed in the search engine.
    
    This endpoint is useful for debugging, monitoring, or building
    client-side autocomplete functionality.
    """
    try:
        words = search_engine.index_manager.forward_index.get_all_words()
        return sorted(words)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get words: {str(e)}"
        )


@router.post(
    "/mappings",
    summary="Load word-column mappings",
    description="Load or update word-to-column mappings in the search engine"
)
async def load_mappings(mappings: dict[str, list[str]]) -> JSONResponse:
    """
    Load word-to-column mappings into the search engine.
    
    This endpoint allows you to bulk load or update the mappings
    that the search engine uses for lookups.
    """
    try:
        search_engine.load_mappings(mappings)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Mappings loaded successfully",
                "total_words": len(mappings),
                "total_mappings": sum(len(columns) for columns in mappings.values())
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load mappings: {str(e)}"
        )


@router.delete(
    "/mappings/{word}",
    summary="Remove word mapping",
    description="Remove a specific word mapping from the search engine"
)
async def remove_mapping(
    word: str = Path(..., description="The word to remove from the index")
) -> JSONResponse:
    """
    Remove a word mapping from the search engine.
    
    This endpoint allows you to remove specific word mappings
    from the search engine's index.
    """
    try:
        success = search_engine.index_manager.remove_mapping(word)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"message": f"Mapping for '{word}' removed successfully"}
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Word '{word}' not found in index"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove mapping: {str(e)}"
        )
