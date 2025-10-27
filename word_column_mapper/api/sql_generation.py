"""
SQL Query Generation API Endpoint with MCP
Provides endpoints for natural language to SQL query generation
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import structlog

try:
    from ..sql_generator_with_mcp import SQLGeneratorMCP
except ImportError:
    from word_column_mapper.sql_generator_with_mcp import SQLGeneratorMCP

logger = structlog.get_logger()

# Create router
sql_router = APIRouter(prefix="/sql", tags=["SQL Generation"])


def get_schema_path() -> str:
    """
    Get the absolute path to the form_table_schema.json file.
    
    Returns:
        str: Absolute path to the schema file
    """
    import os
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, "form_table_schema.json")


class SQLQueryRequest(BaseModel):
    """Request model for SQL query generation."""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=500)
    max_depth: int = Field(default=2, description="Maximum depth for table relationship traversal", ge=1, le=5)
    auto_export_threshold: int = Field(default=10, description="Threshold for automatic CSV export", ge=1)
    force_csv: bool = Field(default=False, description="Force CSV export regardless of count")
    debug: bool = Field(default=False, description="Enable debug mode")
    dry_run: bool = Field(default=True, description="Only generate SQL without executing (default: True)")


class SQLQueryResponse(BaseModel):
    """Response model for SQL query generation."""
    success: bool
    user_query: str
    relevant_tables: Optional[List[str]] = None
    record_count: Optional[int] = None
    action: Optional[str] = None  # "display_results" or "csv_export"
    message: Optional[str] = None
    sql_queries: Optional[Dict[str, str]] = None
    columns: Optional[List[str]] = None
    data: Optional[List[Any]] = None
    csv_file: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


@sql_router.post(
    "/generate",
    response_model=SQLQueryResponse,
    summary="Generate SQL from natural language query",
    description="""
    Generate PostgreSQL queries from natural language using Claude AI with MCP.
    
    The endpoint:
    1. Analyzes the query to find relevant database tables
    2. Extracts schemas for those tables
    3. Uses Claude AI to generate optimized SQL queries
    4. Executes a COUNT query first
    5. Based on the count:
       - If count > threshold: Exports to CSV file
       - If count <= threshold: Returns data directly
    
    Returns three SQL queries:
    - count_sql: Query to count matching records
    - query_sql: Query to retrieve data (limited)
    - csv_sql: Query for CSV export (unlimited)
    """
)
async def generate_sql_query(request: SQLQueryRequest):
    """
    Generate SQL queries from natural language query.
    
    Args:
        request: SQLQueryRequest with query and configuration
        
    Returns:
        SQLQueryResponse with generated SQL and results
    """
    try:
        logger.info(
            "sql_generation_request",
            query=request.query,
            max_depth=request.max_depth,
            threshold=request.auto_export_threshold,
            force_csv=request.force_csv
        )
        
        # Get the path to form_table_schema.json
        schema_path = get_schema_path()
        
        # Initialize SQL Generator with absolute path
        generator = SQLGeneratorMCP(
            schema_file_path=schema_path,
            debug=request.debug
        )
        
        # Process the query
        result = generator.process_query(
            user_query=request.query,
            max_depth=request.max_depth,
            auto_export_threshold=request.auto_export_threshold,
            force_csv=request.force_csv,
            dry_run=request.dry_run  # Pass dry_run parameter
        )
        
        logger.info(
            "sql_generation_completed",
            success=result.get("success"),
            action=result.get("action"),
            record_count=result.get("record_count")
        )
        
        return SQLQueryResponse(**result)
        
    except ValueError as e:
        logger.error("sql_generation_validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error("sql_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@sql_router.get(
    "/tables",
    summary="Get relevant tables for a query",
    description="Analyze a query and return relevant database tables without generating SQL"
)
async def get_relevant_tables(
    query: str = Query(..., description="Natural language query", min_length=1, max_length=500),
    max_depth: int = Query(default=2, description="Maximum depth for table relationship traversal", ge=1, le=5),
    debug: bool = Query(default=False, description="Enable debug mode")
):
    """
    Get relevant tables for a query without generating SQL.
    
    Args:
        query: Natural language query
        max_depth: Maximum depth for table relationship traversal
        debug: Enable debug mode
        
    Returns:
        Dictionary with relevant tables and their schemas
    """
    try:
        logger.info("table_analysis_request", query=query, max_depth=max_depth)
        
        # Get the path to form_table_schema.json
        schema_path = get_schema_path()
        
        generator = SQLGeneratorMCP(
            schema_file_path=schema_path,
            debug=debug
        )
        
        # Get relevant tables
        relevant_tables = generator._get_relevant_tables(query, max_depth)
        
        # Extract schemas
        table_schemas = generator._extract_table_schemas(relevant_tables)
        
        result = {
            "success": True,
            "query": query,
            "relevant_tables": relevant_tables,
            "table_count": len(relevant_tables),
            "schemas": table_schemas
        }
        
        logger.info("table_analysis_completed", table_count=len(relevant_tables))
        
        return result
        
    except Exception as e:
        logger.error("table_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@sql_router.post(
    "/validate",
    summary="Validate generated SQL",
    description="Validate SQL syntax without executing it"
)
async def validate_sql(
    sql: str = Query(..., description="SQL query to validate"),
    query_type: str = Query(default="SELECT", description="Expected query type (SELECT, COUNT, etc.)")
):
    """
    Validate SQL query syntax.
    
    Args:
        sql: SQL query to validate
        query_type: Expected query type
        
    Returns:
        Validation result
    """
    try:
        import sqlparse
        
        # Parse SQL
        parsed = sqlparse.parse(sql)
        
        if not parsed:
            return {
                "valid": False,
                "error": "Unable to parse SQL query"
            }
        
        statement = parsed[0]
        
        # Check query type
        actual_type = statement.get_type()
        
        result = {
            "valid": True,
            "query_type": actual_type,
            "matches_expected": actual_type.upper() == query_type.upper(),
            "formatted_sql": sqlparse.format(sql, reindent=True, keyword_case='upper')
        }
        
        return result
        
    except Exception as e:
        logger.error("sql_validation_error", error=str(e))
        raise HTTPException(status_code=500, detail="SQL validation failed")


@sql_router.get(
    "/health",
    summary="Check SQL generation service health",
    description="Verify that the SQL generation service is properly configured"
)
async def sql_health_check():
    """
    Health check endpoint for SQL generation service.
    
    Returns:
        Service health status
    """
    try:
        import openai
        from dotenv import load_dotenv
        import os
        
        # Get the path to form_table_schema.json
        schema_path = get_schema_path()
        
        health = {
            "service": "SQL Generation with MCP",
            "status": "healthy",
            "checks": {
                "openai_configured": bool(os.getenv("OPENAI_API_KEY") or openai.api_key),
                "schema_file_exists": os.path.exists(schema_path),
                "database_config": bool(os.getenv("DB_NAME"))
            }
        }
        
        # Overall health
        health["healthy"] = all(health["checks"].values())
        
        if not health["healthy"]:
            missing = [k for k, v in health["checks"].items() if not v]
            health["status"] = "degraded"
            health["message"] = f"Missing configuration: {', '.join(missing)}"
        
        return health
        
    except Exception as e:
        return {
            "service": "SQL Generation with MCP",
            "status": "unhealthy",
            "error": str(e)
        }
