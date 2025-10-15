"""Set operations API endpoints."""

import os
import subprocess
import json
import time
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import openai

from ..core.engine import SearchEngine
from ..models.response import SetOperationResponse, ErrorResponse
from ..models.request import SetOperationRequest
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["operations"])
settings = get_settings()

# Import the global search engine instance
from ..engine_instance import search_engine


@router.get(
    "/intersection",
    response_model=SetOperationResponse,
    summary="Find intersection of columns",
    description="Find columns that are common to all specified words (AND operation)"
)
async def intersection_search(
    words: List[str] = Query(..., description="List of words to find intersection for", min_items=2)
) -> SetOperationResponse:
    """
    Find columns that are common to all specified words.
    
    This endpoint performs an intersection operation (AND) to find
    columns that are associated with all the provided words.
    """
    try:
        # Validate input
        if len(words) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 words are required for intersection operation"
            )
        
        # Remove duplicates and empty strings
        words = list(set(word.strip() for word in words if word.strip()))
        
        if len(words) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 valid words are required for intersection operation"
            )
        
        result = search_engine.intersection_search(words)
        
        if result is None:
            return SetOperationResponse(
                query_words=words,
                operation="AND",
                intersection_columns=[],
                total_common_columns=0,
                execution_time_ms=0.0,
                note="No common columns found"
            )
        
        return SetOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Intersection search failed: {str(e)}"
        )


@router.get(
    "/union",
    response_model=SetOperationResponse,
    summary="Find union of columns",
    description="Find all columns associated with any of the specified words (OR operation)"
)
async def union_search(
    words: List[str] = Query(..., description="List of words to find union for", min_items=1)
) -> SetOperationResponse:
    """
    Find all columns associated with any of the specified words.
    
    This endpoint performs a union operation (OR) to find
    all columns that are associated with any of the provided words.
    """
    try:
        # Validate input
        if not words:
            raise HTTPException(
                status_code=400,
                detail="At least 1 word is required for union operation"
            )
        
        # Remove duplicates and empty strings
        words = list(set(word.strip() for word in words if word.strip()))
        
        if not words:
            raise HTTPException(
                status_code=400,
                detail="At least 1 valid word is required for union operation"
            )
        
        result = search_engine.union_search(words)
        
        if result is None:
            return SetOperationResponse(
                query_words=words,
                operation="OR",
                union_columns=[],
                total_unique_columns=0,
                execution_time_ms=0.0,
                note="No columns found for any of the specified words"
            )
        
        return SetOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Union search failed: {str(e)}"
        )


@router.post(
    "/operations",
    response_model=SetOperationResponse,
    summary="Perform set operation with request body",
    description="Perform intersection or union operation using a structured request body"
)
async def set_operation(request: SetOperationRequest) -> SetOperationResponse:
    """
    Perform set operation using a structured request body.
    
    This endpoint accepts a JSON request body to perform either
    intersection or union operations on a set of words.
    """
    try:
        # Determine operation type
        if request.operation in ["intersection", "and"]:
            result = search_engine.intersection_search(request.words)
            operation = "AND"
        elif request.operation in ["union", "or"]:
            result = search_engine.union_search(request.words)
            operation = "OR"
        else:
            raise HTTPException(
                status_code=400,
                detail="Operation must be 'intersection', 'union', 'and', or 'or'"
            )
        
        if result is None:
            # Return empty result based on operation type
            if operation == "AND":
                return SetOperationResponse(
                    query_words=request.words,
                    operation=operation,
                    intersection_columns=[],
                    total_common_columns=0,
                    execution_time_ms=0.0,
                    note="No common columns found"
                )
            else:
                return SetOperationResponse(
                    query_words=request.words,
                    operation=operation,
                    union_columns=[],
                    total_unique_columns=0,
                    execution_time_ms=0.0,
                    note="No columns found for any of the specified words"
                )
        
        # Update operation field
        result["operation"] = operation
        return SetOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Set operation failed: {str(e)}"
        )


@router.get(
    "/operations/stats",
    summary="Get operation statistics",
    description="Get statistics about set operations performed"
)
async def get_operation_stats() -> JSONResponse:
    """
    Get statistics about set operations.
    
    Returns information about the types of operations performed
    and their performance characteristics.
    """
    try:
        stats = search_engine.get_stats()
        
        return JSONResponse(
            status_code=200,
            content={
                "total_queries": stats["total_queries"],
                "exact_matches": stats["exact_matches"],
                "fuzzy_matches": stats["fuzzy_matches"],
                "no_matches": stats["no_matches"],
                "average_execution_time_ms": stats["average_execution_time_ms"],
                "exact_match_rate": stats["exact_match_rate"],
                "fuzzy_match_rate": stats["fuzzy_match_rate"],
                "no_match_rate": stats["no_match_rate"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get operation stats: {str(e)}"
        )


@router.post(
    "/recreate-mappings",
    summary="Recreate mappings from database",
    description="Run the complete process to recreate mappings: get_all_column_names.py -> csv_to_json.py -> reload engine"
)
async def recreate_mappings() -> JSONResponse:
    """
    Recreate mappings by running the complete process:
    1. Run get_all_column_names.py to generate column names from database
    2. Run csv_to_json.py to create mappings JSON
    3. Reload the search engine with new mappings
    """
    try:
        # Get the base directory (word_column_mapper directory)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        results = {
            "status": "success",
            "steps": [],
            "total_time_ms": 0,
            "mappings_loaded": 0
        }
        
        start_time = time.time()
        
        # Step 1: Run get_all_column_names.py
        step1_start = time.time()
        try:
            get_columns_script = os.path.join(base_dir, "get_all_column_names.py")
            result = subprocess.run(
                ["python", get_columns_script],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            step1_time = (time.time() - step1_start) * 1000
            
            if result.returncode == 0:
                results["steps"].append({
                    "step": "get_all_column_names.py",
                    "status": "success",
                    "time_ms": round(step1_time, 2),
                    "output": result.stdout.strip()
                })
            else:
                results["steps"].append({
                    "step": "get_all_column_names.py",
                    "status": "error",
                    "time_ms": round(step1_time, 2),
                    "error": result.stderr.strip()
                })
                raise Exception(f"get_all_column_names.py failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            results["steps"].append({
                "step": "get_all_column_names.py",
                "status": "timeout",
                "time_ms": 300000,
                "error": "Process timed out after 5 minutes"
            })
            raise Exception("get_all_column_names.py timed out")
        except Exception as e:
            results["steps"].append({
                "step": "get_all_column_names.py",
                "status": "error",
                "time_ms": round((time.time() - step1_start) * 1000, 2),
                "error": str(e)
            })
            raise
        
        # Step 2: Run csv_to_json.py
        step2_start = time.time()
        try:
            csv_to_json_script = os.path.join(base_dir, "csv_to_json.py")
            result = subprocess.run(
                ["python", csv_to_json_script],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            step2_time = (time.time() - step2_start) * 1000
            
            if result.returncode == 0:
                results["steps"].append({
                    "step": "csv_to_json.py",
                    "status": "success",
                    "time_ms": round(step2_time, 2),
                    "output": result.stdout.strip()
                })
            else:
                results["steps"].append({
                    "step": "csv_to_json.py",
                    "status": "error",
                    "time_ms": round(step2_time, 2),
                    "error": result.stderr.strip()
                })
                raise Exception(f"csv_to_json.py failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            results["steps"].append({
                "step": "csv_to_json.py",
                "status": "timeout",
                "time_ms": 60000,
                "error": "Process timed out after 1 minute"
            })
            raise Exception("csv_to_json.py timed out")
        except Exception as e:
            results["steps"].append({
                "step": "csv_to_json.py",
                "status": "error",
                "time_ms": round((time.time() - step2_start) * 1000, 2),
                "error": str(e)
            })
            raise
        
        # Step 3: Reload the search engine with new mappings
        step3_start = time.time()
        try:
            mappings_file = os.path.join(base_dir, "sample_mappings2.json")
            
            if not os.path.exists(mappings_file):
                raise Exception("sample_mappings2.json not found after csv_to_json.py")
            
            # Load the new mappings
            with open(mappings_file, 'r', encoding='utf-8') as f:
                new_mappings = json.load(f)
            
            # Reload the search engine
            search_engine.load_mappings(new_mappings)
            
            step3_time = (time.time() - step3_start) * 1000
            results["mappings_loaded"] = len(new_mappings)
            
            results["steps"].append({
                "step": "reload_engine",
                "status": "success",
                "time_ms": round(step3_time, 2),
                "mappings_count": len(new_mappings)
            })
            
        except Exception as e:
            results["steps"].append({
                "step": "reload_engine",
                "status": "error",
                "time_ms": round((time.time() - step3_start) * 1000, 2),
                "error": str(e)
            })
            raise
        
        # Calculate total time
        results["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return JSONResponse(
            status_code=200,
            content=results
        )
        
    except Exception as e:
        # Calculate total time even on error
        if "total_time_ms" not in results:
            results["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        results["status"] = "error"
        results["error"] = str(e)
        
        return JSONResponse(
            status_code=500,
            content=results
        )


@router.post(
    "/get-table-names",
    summary="Get table names from column IDs",
    description="Get array of table names for given column IDs using column_table_mapping.json"
)
async def get_table_names(column_ids: List[str]) -> JSONResponse:
    """
    Get table names for given column IDs.
    
    Takes a list of column IDs and returns the corresponding table names
    from the column_table_mapping.json file.
    """
    try:
        # Get the base directory (word_column_mapper directory)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        mapping_file = os.path.join(base_dir, "column_table_mapping.json")
        
        if not os.path.exists(mapping_file):
            raise Exception("column_table_mapping.json not found")
        
        # Load the column to table mapping
        with open(mapping_file, 'r', encoding='utf-8') as f:
            column_table_mapping = json.load(f)
        
        # Get table names for the provided column IDs (including duplicates)
        table_names = []
        found_columns = []
        not_found_columns = []
        
        for column_id in column_ids:
            if column_id in column_table_mapping:
                table_name = column_table_mapping[column_id]
                table_names.append(table_name)  # Keep duplicates
                found_columns.append(column_id)
            else:
                not_found_columns.append(column_id)
        
        # Get unique table names for counting
        unique_table_names = sorted(list(set(table_names)))
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "column_ids": column_ids,
                "table_names": table_names,  # All table names including duplicates
                "unique_table_names": unique_table_names,  # Unique table names only
                "total_tables": len(table_names),  # Total count including duplicates
                "unique_tables": len(unique_table_names),  # Unique table count
                "found_columns": found_columns,
                "not_found_columns": not_found_columns,
                "total_columns_processed": len(column_ids),
                "columns_found": len(found_columns),
                "columns_not_found": len(not_found_columns)
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "column_ids": column_ids if 'column_ids' in locals() else [],
                "table_names": []
            }
        )


@router.post(
    "/natural-language-query",
    summary="Process natural language query to get columns and tables",
    description="Convert natural language query to relevant words using ChatGPT, then get columns and tables for each word"
)
async def process_natural_language_query(request: dict) -> JSONResponse:
    """
    Process natural language query through ChatGPT to extract relevant words,
    then search for columns and tables for each word.
    
    Flow: Natural Language Query → ChatGPT → Relevant Words → Search Engine → Columns → Tables
    """
    try:
        # Extract query and API key from request
        query = request.get('query', '').strip()
        openai_api_key = request.get('openai_api_key', '').strip()
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Query is required"}
            )
        
        if not openai_api_key:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "OpenAI API key is required"}
            )
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Step 1: Extract relevant words using ChatGPT
        chatgpt_prompt = f"""
        You are a database expert. Given a natural language query, extract the most relevant and essential words that would be needed to write a PostgreSQL query.

        Natural Language Query: "{query}"

        Please return ONLY a JSON array of relevant words. Each word should be:
        - Essential for the database query
        - Related to database fields, tables, or operations
        - Clean and meaningful (no stop words like "the", "and", "or")
        - In singular form when possible
        - Maximum 10 words

        Example format: ["user", "email", "date", "status", "amount"]

        Return only the JSON array, no other text:
        """
        
        chatgpt_start = time.time()
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a database expert who extracts relevant words from natural language queries for PostgreSQL."},
                    {"role": "user", "content": chatgpt_prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            chatgpt_time = (time.time() - chatgpt_start) * 1000
            relevant_words_text = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            try:
                relevant_words = json.loads(relevant_words_text)
                if not isinstance(relevant_words, list):
                    raise ValueError("Response is not a list")
            except (json.JSONDecodeError, ValueError) as e:
                # Fallback: try to extract words from text
                relevant_words = [word.strip().strip('"\'') for word in relevant_words_text.replace('[', '').replace(']', '').split(',')]
                relevant_words = [word for word in relevant_words if word and len(word) > 1]
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": f"ChatGPT API error: {str(e)}",
                    "step": "chatgpt_extraction"
                }
            )
        
        # Step 2: Process each word through search engine
        search_results = []
        all_columns = []
        all_tables = []
        
        for word in relevant_words:
            word_start = time.time()
            try:
                # Search for the word
                search_result = search_engine.search(word, include_suggestions=True)
                word_time = (time.time() - word_start) * 1000
                
                # Get table names for the columns (using all columns including duplicates)
                if search_result and hasattr(search_result, 'total_all_columns') and search_result.total_all_columns:
                    table_start = time.time()
                    try:
                        # Get table names using the existing endpoint logic
                        base_dir = os.path.dirname(os.path.dirname(__file__))
                        mapping_file = os.path.join(base_dir, "column_table_mapping.json")
                        
                        if os.path.exists(mapping_file):
                            with open(mapping_file, 'r', encoding='utf-8') as f:
                                column_table_mapping = json.load(f)
                            
                            word_tables = []
                            for column_id in search_result.total_all_columns:  # Use all columns including duplicates
                                if column_id in column_table_mapping:
                                    word_tables.append(column_table_mapping[column_id])  # Keep duplicate tables
                            
                            table_time = (time.time() - table_start) * 1000
                        else:
                            word_tables = []
                            table_time = 0
                    except Exception as e:
                        word_tables = []
                        table_time = 0
                else:
                    word_tables = []
                    table_time = 0
                
                # Collect results
                word_result = {
                    "word": word,
                    "search_result": {
                        "query": search_result.query if hasattr(search_result, 'query') else word,
                        "total_results": search_result.total_results if hasattr(search_result, 'total_results') else 0,
                        "exact_match": search_result.exact_match if hasattr(search_result, 'exact_match') else False,
                        "execution_time_ms": search_result.execution_time_ms if hasattr(search_result, 'execution_time_ms') else word_time,
                        "total_unique_columns": search_result.total_unique_columns if hasattr(search_result, 'total_unique_columns') else [],
                        "cache_hit": search_result.cache_hit if hasattr(search_result, 'cache_hit') else False,
                        "suggestions": search_result.suggestions if hasattr(search_result, 'suggestions') else None
                    },
                    "columns": search_result.total_all_columns if hasattr(search_result, 'total_all_columns') else [],
                    "tables": word_tables,
                    "search_time_ms": word_time,
                    "table_time_ms": table_time,
                    "total_results": search_result.total_results if hasattr(search_result, 'total_results') else 0
                }
                
                search_results.append(word_result)
                all_columns.extend(search_result.total_all_columns if hasattr(search_result, 'total_all_columns') else [])
                all_tables.extend(word_tables)
                
            except Exception as e:
                search_results.append({
                    "word": word,
                    "error": str(e),
                    "search_time_ms": (time.time() - word_start) * 1000,
                    "columns": [],
                    "tables": [],
                    "total_results": 0
                })
        
        # Keep all columns and tables including duplicates
        # all_columns = list(set(all_columns))  # Removed to keep duplicates
        # all_tables = list(set(all_tables))    # Removed to keep duplicates
        
        # Also provide unique versions for comparison
        unique_columns = list(set(all_columns))
        unique_tables = list(set(all_tables))
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "original_query": query,
                "relevant_words": relevant_words,
                "chatgpt_time_ms": chatgpt_time,
                "search_results": search_results,
                "summary": {
                    "total_words_processed": len(relevant_words),
                    "total_columns_found": len(all_columns),
                    "total_tables_found": len(all_tables),
                    "unique_columns_found": len(unique_columns),
                    "unique_tables_found": len(unique_tables),
                    "all_columns": all_columns,
                    "all_tables": all_tables
                }
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "original_query": query if 'query' in locals() else ""
            }
        )
