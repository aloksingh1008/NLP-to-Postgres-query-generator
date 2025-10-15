"""Response models for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Individual search result."""
    
    word: str = Field(..., description="The matched word")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    match_type: str = Field(..., description="Type of match (exact, fuzzy_levenshtein, etc.)")
    columns: List[str] = Field(..., description="Array of column identifiers")
    edit_distance: Optional[int] = Field(None, description="Edit distance for fuzzy matches")
    changes: Optional[str] = Field(None, description="Description of changes made")


class SearchResponse(BaseModel):
    """Response for search queries."""
    
    query: str = Field(..., description="Original search query")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    exact_match: bool = Field(..., description="Whether an exact match was found")
    total_results: int = Field(..., description="Total number of results")
    results: List[SearchResult] = Field(..., description="Search results")
    total_unique_columns: List[str] = Field(..., description="All unique columns from results")
    total_all_columns: List[str] = Field(..., description="All columns from results including duplicates")
    cache_hit: bool = Field(..., description="Whether result was served from cache")
    suggestions: Optional[List[str]] = Field(None, description="Alternative suggestions if no match")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ReverseLookupResponse(BaseModel):
    """Response for reverse lookup queries."""
    
    column_id: str = Field(..., description="The column identifier")
    words: List[str] = Field(..., description="Words that map to this column")
    total_mappings: int = Field(..., description="Total number of word mappings")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SetOperationResponse(BaseModel):
    """Response for set operation queries (union/intersection)."""
    
    query_words: List[str] = Field(..., description="Input words for the operation")
    operation: str = Field(..., description="Type of operation (AND/OR)")
    intersection_columns: Optional[List[str]] = Field(None, description="Columns for intersection")
    union_columns: Optional[List[str]] = Field(None, description="Columns for union")
    total_common_columns: Optional[int] = Field(None, description="Count of common columns")
    total_unique_columns: Optional[int] = Field(None, description="Count of unique columns")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    note: Optional[str] = Field(None, description="Additional information about the result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class MetricsResponse(BaseModel):
    """Performance metrics response."""
    
    total_queries: int = Field(..., description="Total queries processed")
    average_response_time_ms: float = Field(..., description="Average response time")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    error_rate: float = Field(..., description="Error rate percentage")
    active_connections: int = Field(..., description="Active connections")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
