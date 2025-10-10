"""Request models for API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field, validator


class SearchRequest(BaseModel):
    """Request model for search queries."""
    
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    fuzzy_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Custom fuzzy matching threshold"
    )
    max_results: Optional[int] = Field(
        None, ge=1, le=100, description="Maximum number of results to return"
    )
    include_suggestions: bool = Field(
        default=True, description="Whether to include suggestions for no-match queries"
    )

    @validator('query')
    def validate_query(cls, v: str) -> str:
        """Validate and normalize query input."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class BatchSearchRequest(BaseModel):
    """Request model for batch search queries."""
    
    queries: List[str] = Field(..., min_items=1, max_items=100, description="List of search queries")
    fuzzy_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Custom fuzzy matching threshold"
    )
    max_results: Optional[int] = Field(
        None, ge=1, le=100, description="Maximum number of results per query"
    )
    parallel: bool = Field(default=True, description="Whether to process queries in parallel")

    @validator('queries')
    def validate_queries(cls, v: List[str]) -> List[str]:
        """Validate and normalize query list."""
        if not v:
            raise ValueError("Queries list cannot be empty")
        
        normalized_queries = []
        for query in v:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            normalized_queries.append(query.strip())
        
        return normalized_queries


class SetOperationRequest(BaseModel):
    """Request model for set operations."""
    
    words: List[str] = Field(..., min_items=2, max_items=10, description="Words for set operation")
    operation: str = Field(..., description="Operation type: 'intersection' or 'union'")

    @validator('words')
    def validate_words(cls, v: List[str]) -> List[str]:
        """Validate and normalize word list."""
        if not v:
            raise ValueError("Words list cannot be empty")
        
        normalized_words = []
        for word in v:
            if not word or not word.strip():
                raise ValueError("Word cannot be empty")
            normalized_words.append(word.strip())
        
        return normalized_words

    @validator('operation')
    def validate_operation(cls, v: str) -> str:
        """Validate operation type."""
        if v.lower() not in ['intersection', 'union', 'and', 'or']:
            raise ValueError("Operation must be 'intersection', 'union', 'and', or 'or'")
        return v.lower()


class MappingUpdateRequest(BaseModel):
    """Request model for updating word-column mappings."""
    
    word: str = Field(..., min_length=1, max_length=100, description="Word to map")
    columns: List[str] = Field(..., min_items=1, description="Column identifiers")
    operation: str = Field(default="replace", description="Operation: 'add', 'remove', or 'replace'")

    @validator('word')
    def validate_word(cls, v: str) -> str:
        """Validate and normalize word."""
        if not v or not v.strip():
            raise ValueError("Word cannot be empty")
        return v.strip()

    @validator('columns')
    def validate_columns(cls, v: List[str]) -> List[str]:
        """Validate and normalize column list."""
        if not v:
            raise ValueError("Columns list cannot be empty")
        
        normalized_columns = []
        for column in v:
            if not column or not column.strip():
                raise ValueError("Column cannot be empty")
            normalized_columns.append(column.strip())
        
        return normalized_columns

    @validator('operation')
    def validate_operation(cls, v: str) -> str:
        """Validate operation type."""
        if v.lower() not in ['add', 'remove', 'replace']:
            raise ValueError("Operation must be 'add', 'remove', or 'replace'")
        return v.lower()
