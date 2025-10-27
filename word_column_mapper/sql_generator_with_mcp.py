"""
SQL Generator with MCP (Model Context Protocol)
This script:
1. Gets relevant tables from table_relationship_traversal
2. Extracts schemas for those tables from form_table_schema.json
3. Sends to Claude AI with user query + schemas
4. Claude generates 3 SQLs: COUNT, ACTUAL QUERY, and DOWNLOAD (CSV)
5. Executes COUNT SQL first:
   - If count > 10: Offers CSV download option
   - If count <= 10: Executes and shows results directly
"""

import json
import os
import psycopg2
import csv
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv
import re

try:
    from .table_relationship_traversal import TableRelationshipTraversal
    from .table_frequency_ranker import TableFrequencyRanker
    from .config.settings import get_settings
except ImportError:
    from table_relationship_traversal import TableRelationshipTraversal
    from table_frequency_ranker import TableFrequencyRanker
    try:
        from config.settings import get_settings
    except ImportError:
        get_settings = None

# Load environment variables
load_dotenv()


class SQLGeneratorMCP:
    """
    SQL Generator with Model Context Protocol (MCP) integration.
    Generates intelligent SQL queries using Claude AI with relevant table schemas.
    """
    
    def __init__(
        self,
        schema_file_path: str = "form_table_schema.json",
        db_config: Optional[Dict[str, str]] = None,
        anthropic_api_key: Optional[str] = None,
        debug: bool = False
    ):
        """
        Initialize the SQL Generator with MCP.
        
        Args:
            schema_file_path: Path to the table schema JSON file
            db_config: Database configuration dictionary
            anthropic_api_key: Anthropic API key (or from environment)
            debug: Enable debug mode with detailed logging
        """
        self.schema_file_path = schema_file_path
        self.debug = debug
        
        # If relative path, make it absolute from the word_column_mapper directory
        if not os.path.isabs(self.schema_file_path):
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.schema_file_path = os.path.join(script_dir, schema_file_path)
        
        self.schema = self._load_schema()
        
        # Load settings if available
        self.settings = get_settings() if get_settings else None
        
        # Database configuration (priority: parameter > settings > environment)
        if db_config:
            self.db_config = db_config
        elif self.settings:
            self.db_config = {
                "host": self.settings.db_host,
                "port": self.settings.db_port,
                "database": self.settings.db_name,
                "user": self.settings.db_user,
                "password": self.settings.db_password
            }
        else:
            self.db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DB_NAME", "strategicerp"),
                "user": os.getenv("DB_USER", "db_user"),
                "password": os.getenv("DB_PASSWORD")
            }
            
            if not self.db_config["password"]:
                raise ValueError("Database password is required. Set DB_PASSWORD in environment or pass db_config parameter.")        
        
        # Anthropic configuration (priority: parameter > settings > environment)
        anthropic_key = None
        if anthropic_api_key:
            anthropic_key = anthropic_api_key
        elif self.settings and self.settings.anthropic_api_key:
            anthropic_key = self.settings.anthropic_api_key
        else:
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize Anthropic client
        if not anthropic_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY in environment, settings, or pass as parameter.")
        
        self.anthropic_client = Anthropic(api_key=anthropic_key)
        
        # SQL Security settings from config
        self.allowed_operations = self.settings.allowed_sql_operations if self.settings else ["SELECT"]
        self.prohibited_keywords = self.settings.prohibited_sql_keywords if self.settings else [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", 
            "INSERT", "UPDATE", "GRANT", "REVOKE", "EXEC", 
            "EXECUTE", "MERGE", "REPLACE"
        ]
        self.enable_sql_validation = self.settings.enable_sql_validation if self.settings else True
        
        # Initialize traversal components (without debug for TableFrequencyRanker)
        self.traversal = TableRelationshipTraversal(self.schema_file_path, debug=debug)
        self.ranker = TableFrequencyRanker()  # No debug parameter
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"SQL GENERATOR WITH MCP INITIALIZED")
            print(f"{'='*80}")
            print(f"Schema File: {schema_file_path}")
            print(f"Database: {self.db_config['database']}@{self.db_config['host']}")
            print(f"AI Provider: CLAUDE (Anthropic)")
            print(f"Allowed Operations: {', '.join(self.allowed_operations)}")
            print(f"Prohibited Keywords: {', '.join(self.prohibited_keywords)}")
            print(f"SQL Validation: {'ENABLED' if self.enable_sql_validation else 'DISABLED'}")
            print(f"Debug Mode: {'ENABLED' if debug else 'DISABLED'}")
            print(f"{'='*80}\n")
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load the table schema from JSON file."""
        try:
            with open(self.schema_file_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                if self.debug:
                    print(f"Schema loaded successfully: {len(schema)} tables found")
                return schema
        except FileNotFoundError:
            print(f"ERROR: Schema file '{self.schema_file_path}' not found!")
            return {}
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON - {e}")
            return {}
    
    def _get_relevant_tables(self, user_query: str, max_depth: int = 2) -> List[str]:
        """
        Get relevant tables based on user query using frequency ranking and traversal.
        
        Args:
            user_query: Natural language query from user
            max_depth: Maximum depth for table relationship traversal
            
        Returns:
            List of relevant table names
        """
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔍 STEP 1: FINDING RELEVANT TABLES")
            print(f"{'='*80}")
            print(f"📝 User Query: \"{user_query}\"")
            print(f"📊 Max Depth: {max_depth}")
            print(f"{'='*80}\n")
        
        # Extract keywords from user query
        keywords = user_query.lower().split()
        
        # Rank tables by matching keywords in column aliases
        table_frequencies = {}
        
        for table_name, table_data in self.schema.items():
            columns = table_data.get('columns', {})
            frequency = 0
            
            # Check each column's alias for keyword matches
            for col_id, col_info in columns.items():
                alias = col_info.get('alias_name', '').lower()
                for keyword in keywords:
                    if keyword in alias:
                        frequency += 1
            
            if frequency > 0:
                table_frequencies[table_name] = frequency
        
        if self.debug:
            print(f"\n📊 Table Frequency Ranking:")
            for table, freq in sorted(table_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  • {table}: {freq} matches")
            print()
        
        # If no tables found by keyword matching, return all tables
        if not table_frequencies:
            if self.debug:
                print(f"⚠️  No tables matched keywords. Using all tables.")
            table_frequencies = {table: 1 for table in self.schema.keys()}
        
        # Traverse relationships to get all relevant tables
        relevant_tables = self.traversal.traverse_relationships(table_frequencies, max_depth)
        
        if self.debug:
            print(f"\n✅ Relevant Tables Found: {len(relevant_tables)}")
            print(f"📋 Tables: {relevant_tables}\n")
        
        return relevant_tables
    
    def _extract_table_schemas(self, table_names: List[str]) -> Dict[str, Any]:
        """
        Extract schemas for specified tables from the loaded schema.
        
        Args:
            table_names: List of table names to extract schemas for
            
        Returns:
            Dictionary mapping table names to their schemas
        """
        if self.debug:
            print(f"\n{'='*80}")
            print(f"📚 STEP 2: EXTRACTING TABLE SCHEMAS")
            print(f"{'='*80}\n")
        
        extracted_schemas = {}
        
        for table_name in table_names:
            if table_name in self.schema:
                extracted_schemas[table_name] = self.schema[table_name]
                if self.debug:
                    columns = self.schema[table_name].get('columns', {})
                    print(f"✅ {table_name}: {len(columns)} columns")
            else:
                if self.debug:
                    print(f"⚠️  {table_name}: NOT FOUND in schema")
        
        if self.debug:
            print(f"\n📊 Total Schemas Extracted: {len(extracted_schemas)}")
            print(f"{'='*80}\n")
        
        return extracted_schemas
    
    def _validate_sql_security(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for security issues.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enable_sql_validation:
            return True, None
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔒 VALIDATING SQL SECURITY")
            print(f"{'='*80}")
            print(f"📊 SQL: {sql[:100]}...")
        
        sql_upper = sql.upper()
        
        # Check for prohibited keywords
        for keyword in self.prohibited_keywords:
            # Use word boundary regex to avoid false positives
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_upper):
                error = f"Prohibited SQL keyword detected: {keyword}"
                if self.debug:
                    print(f"❌ {error}")
                    print(f"{'='*80}\n")
                return False, error
        
        # Check if query starts with allowed operation
        sql_trimmed = sql_upper.strip()
        is_allowed = any(sql_trimmed.startswith(op) for op in self.allowed_operations)
        
        if not is_allowed:
            error = f"SQL must start with one of: {', '.join(self.allowed_operations)}"
            if self.debug:
                print(f"❌ {error}")
                print(f"{'='*80}\n")
            return False, error
        
        # Check for SQL injection patterns
        dangerous_patterns = [
            r';.*DROP',
            r';.*DELETE',
            r';.*INSERT',
            r';.*UPDATE',
            r'--.*DROP',
            r'/\*.*\*/',  # Block comments
            r'UNION.*SELECT.*FROM',  # Basic UNION injection check
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_upper):
                error = f"Potentially dangerous SQL pattern detected"
                if self.debug:
                    print(f"❌ {error}")
                    print(f"{'='*80}\n")
                return False, error
        
        if self.debug:
            print(f"✅ SQL Security Validation Passed")
            print(f"{'='*80}\n")
        
        return True, None
    
    def _generate_sql_with_chatgpt(
        self,
        user_query: str,
        table_schemas: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate SQL queries using Claude AI with provided table schemas.
        
        Args:
            user_query: Original user query in natural language
            table_schemas: Dictionary of relevant table schemas
            
        Returns:
            Dictionary with 'count_sql', 'query_sql', and 'csv_sql' keys
        """
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🤖 STEP 3: GENERATING SQL WITH CLAUDE")
            print(f"{'='*80}\n")
        
        # Prepare schema context for Claude
        schema_context = json.dumps(table_schemas, indent=2)
        
        # Get max rows from settings
        max_rows = self.settings.max_sql_result_rows if self.settings else 10
        
        system_prompt = f"""You are an expert PostgreSQL database query generator with deep knowledge of database design and SQL optimization. 
You will be provided with:
1. A natural language query from the user
2. Relevant table schemas with column information

Your task is to generate THREE SQL queries:
1. **count_sql**: A COUNT query to determine how many records match the criteria
2. **query_sql**: The actual SELECT query to retrieve the data (limit to {max_rows} rows for preview)
3. **csv_sql**: A query suitable for CSV export (without LIMIT, for full data export)

CRITICAL SECURITY RULES:
- Generate ONLY SELECT queries
- DO NOT use: {', '.join(self.prohibited_keywords)}
- DO NOT use multiple statements
- DO NOT use comments or block comments
- Use ONLY the tables and columns provided in the schema

COLUMN REFERENCE RULES (CRITICAL):
- **ALWAYS verify which table each column belongs to before using it**
- Each column is defined under a specific table in the schema
- When using JOINs, ensure you reference columns from the correct table
- If a column like "column37572" exists in table424, use t424.column37572 (NOT t425.column37572)
- Double-check the "columns" section of each table to confirm column existence
- Use the correct table alias for each column (e.g., t424.column_name for table424, t425.column_name for table425)

POSTGRESQL SYNTAX RULES (IMPORTANT):
- Use proper PostgreSQL data types and functions
- For date/time operations:
  * Use INTERVAL with valid units: '1 day', '1 week', '1 month', '1 year'
  * NEVER use INTERVAL '1 quarter' - use INTERVAL '3 months' instead
  * Use date_trunc() for date truncation: date_trunc('day', column), date_trunc('month', column), date_trunc('year', column)
  * For quarters: Use date_trunc('quarter', column) but INTERVAL '3 months' for quarter arithmetic
  * Use CURRENT_DATE, CURRENT_TIMESTAMP, NOW() for current date/time
- For string operations:
  * Use || for concatenation (NOT +)
  * Use ILIKE for case-insensitive matching
  * Use LOWER() or UPPER() for case conversion
- For NULL handling:
  * Use IS NULL or IS NOT NULL (NOT = NULL)
  * Use COALESCE(column, default_value) for NULL defaults
- For aggregations:
  * Always include non-aggregated columns in GROUP BY
  * Use HAVING for filtering after GROUP BY
- For ordering:
  * Use ORDER BY column ASC or ORDER BY column DESC
  * Specify NULLS FIRST or NULLS LAST if needed
- For casting:
  * Use column::type or CAST(column AS type)
  * Common types: INTEGER, BIGINT, NUMERIC, TEXT, TIMESTAMP, DATE, BOOLEAN

QUERY GENERATION RULES:
- Generate valid PostgreSQL syntax
- Use table aliases (e.g., t424, t425) for clarity
- Include appropriate JOINs based on relationships in the schema
- Use WHERE clauses to filter data according to the user's intent
- For count_sql: Use COUNT(*) or COUNT(DISTINCT column) appropriately
- For query_sql: Add "LIMIT {max_rows}" at the end
- For csv_sql: Do NOT add LIMIT (full data)
- **IMPORTANT**: Each SQL query MUST end with a semicolon (;)
- Handle edge cases: NULL values, empty strings, date ranges, numeric precision
- Return ONLY valid JSON with exactly these three keys: count_sql, query_sql, csv_sql
- Do NOT include any explanatory text, comments, or markdown - ONLY the JSON object

Table Schemas:
{schema_context}
"""

        user_prompt = f"""User Query: "{user_query}"

Task: Generate THREE PostgreSQL queries based on the user query and table schemas provided above.

CRITICAL VERIFICATION STEPS:
1. Identify relevant columns by searching for keywords from the user query in the column alias names
2. Verify which table each column belongs to by checking the "columns" section of each table
3. Use the correct table alias when referencing columns (e.g., if column37572 is in table424, use t424.column37572)
4. Include appropriate JOINs if data from multiple tables is needed

Output Format (MUST be valid JSON with NO additional text):
{{
  "count_sql": "SELECT COUNT(*) FROM ... WHERE ... ;",
  "query_sql": "SELECT columns FROM ... WHERE ... LIMIT {max_rows};",
  "csv_sql": "SELECT columns FROM ... WHERE ... ;"
}}

Remember: Each query MUST end with a semicolon (;)
"""

        if self.debug:
            print(f"\n{'='*80}")
            print(f"FULL PROMPT DETAILS")
            print(f"{'='*80}\n")
            
            print(f"[SYSTEM PROMPT - {len(system_prompt)} characters]")
            print(f"{'-'*80}")
            print(system_prompt)
            print(f"{'-'*80}\n")
            
            print(f"[USER PROMPT]")
            print(f"{'-'*80}")
            print(user_prompt)
            print(f"{'-'*80}\n")
            
            print(f"[TABLE SCHEMAS INCLUDED]")
            print(f"{'-'*80}")
            for table_name, table_info in table_schemas.items():
                column_count = len(table_info.get('columns', {}))
                print(f"Table: {table_name} ({column_count} columns)")
                if 'columns' in table_info:
                    print(f"  Sample columns (first 5):")
                    for col_name, col_info in list(table_info['columns'].items())[:5]:
                        alias = col_info.get('alias_name', 'N/A')
                        col_type = col_info.get('type', 'N/A')
                        print(f"    - {col_name}: '{alias}' ({col_type})")
                    if column_count > 5:
                        print(f"    ... and {column_count - 5} more columns")
                print()
            print(f"{'-'*80}\n")
            
            print(f"Sending request to Claude API...")
            print(f"Model: {self.settings.anthropic_model if self.settings else 'claude-3-5-sonnet-20241022'}")
            print()
        
        try:
            # Anthropic API call
            model = self.settings.anthropic_model if self.settings else "claude-3-5-sonnet-20241022"
            temperature = self.settings.anthropic_temperature if self.settings else 0.3
            max_tokens = self.settings.anthropic_max_tokens if self.settings else 4096
            
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            response_text = response.content[0].text
            
            if self.debug:
                print(f"✅ Claude Response Received")
                print(f"Raw response length: {len(response_text)} characters")
                print(f"First 500 chars: {response_text[:500]}\n")
            
            # Clean the response text - remove control characters and escape sequences
            import re
            # Remove control characters except newlines and tabs
            response_text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', response_text)
            # Also remove escaped control characters
            response_text = response_text.replace('\\n', ' ').replace('\\t', ' ').replace('\\r', '')
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                # Try to parse with strict=False to handle more edge cases
                sql_queries = json.loads(json_str, strict=False)
            else:
                # If no JSON found, try parsing the whole response
                sql_queries = json.loads(response_text, strict=False)
            
            if self.debug:
                print(f"📊 COUNT SQL:")
                print(f"   {sql_queries.get('count_sql', 'N/A')}\n")
                print(f"📊 QUERY SQL:")
                print(f"   {sql_queries.get('query_sql', 'N/A')}\n")
                print(f"📊 CSV SQL:")
                print(f"   {sql_queries.get('csv_sql', 'N/A')}\n")
            
            # Validate all generated SQL queries for security
            for query_type, query_sql in sql_queries.items():
                is_valid, error_msg = self._validate_sql_security(query_sql)
                if not is_valid:
                    raise ValueError(f"Security validation failed for {query_type}: {error_msg}")
            
            if self.debug:
                print(f"✅ All SQL queries passed security validation")
                print(f"{'='*80}\n")
            
            return sql_queries
            
        except Exception as e:
            print(f"❌ Error generating SQL with ChatGPT: {e}")
            raise
    
    def _execute_count_query(self, count_sql: str) -> int:
        """
        Execute the COUNT query and return the count.
        
        Args:
            count_sql: SQL query to count records
            
        Returns:
            Count of records
        """
        # Validate SQL before execution
        is_valid, error_msg = self._validate_sql_security(count_sql)
        if not is_valid:
            raise ValueError(f"SQL validation failed: {error_msg}")
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔢 STEP 4: EXECUTING COUNT QUERY")
            print(f"{'='*80}")
            print(f"📊 SQL: {count_sql}\n")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(count_sql)
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            if self.debug:
                print(f"✅ Count Result: {count} records")
                print(f"{'='*80}\n")
            
            return count
            
        except Exception as e:
            print(f"❌ Error executing count query: {e}")
            raise
    
    def _execute_query(self, sql: str) -> List[Tuple]:
        """
        Execute a SELECT query and return results.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            List of result tuples
        """
        # Validate SQL before execution
        is_valid, error_msg = self._validate_sql_security(sql)
        if not is_valid:
            raise ValueError(f"SQL validation failed: {error_msg}")
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔍 STEP 5: EXECUTING ACTUAL QUERY")
            print(f"{'='*80}")
            print(f"📊 SQL: {sql}\n")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(sql)
            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            cur.close()
            conn.close()
            
            if self.debug:
                print(f"✅ Query Executed Successfully")
                print(f"📊 Columns: {columns}")
                print(f"📊 Rows Retrieved: {len(results)}")
                print(f"{'='*80}\n")
            
            return results, columns
            
        except Exception as e:
            print(f"❌ Error executing query: {e}")
            raise
    
    def _export_to_csv(self, sql: str, output_file: str = None) -> str:
        """
        Execute query and export results to CSV file.
        
        Args:
            sql: SQL query to execute
            output_file: Path to output CSV file (auto-generated if None)
            
        Returns:
            Path to the created CSV file
        """
        # Validate SQL before execution
        is_valid, error_msg = self._validate_sql_security(sql)
        if not is_valid:
            raise ValueError(f"SQL validation failed: {error_msg}")
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"query_results_{timestamp}.csv"
        
        if self.debug:
            print(f"\n{'='*80}")
            print(f"📥 STEP 6: EXPORTING TO CSV")
            print(f"{'='*80}")
            print(f"📄 Output File: {output_file}")
            print(f"📊 SQL: {sql}\n")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(sql)
            
            # Get column names
            columns = [desc[0] for desc in cur.description]
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(cur.fetchall())
            
            cur.close()
            conn.close()
            
            if self.debug:
                print(f"✅ CSV Export Completed")
                print(f"📄 File: {output_file}")
                print(f"{'='*80}\n")
            
            return output_file
            
        except Exception as e:
            print(f"❌ Error exporting to CSV: {e}")
            raise
    
    def process_query(
        self,
        user_query: str,
        max_depth: Optional[int] = None,
        auto_export_threshold: Optional[int] = None,
        force_csv: bool = False,
        dry_run: bool = True  # Default to dry run (no DB execution)
    ) -> Dict[str, Any]:
        """
        Main method to process user query through the complete MCP pipeline.
        
        Args:
            user_query: Natural language query from user
            max_depth: Maximum depth for table relationship traversal (from settings if None)
            auto_export_threshold: Threshold for automatic CSV export (from settings if None)
            force_csv: Force CSV export regardless of count
            dry_run: If True, only generate SQL without executing (default: True)
            
        Returns:
            Dictionary with results, metadata, and SQL queries
        """
        # Use settings defaults if not provided
        if max_depth is None:
            max_depth = self.settings.max_table_depth if self.settings else 2
        if auto_export_threshold is None:
            auto_export_threshold = self.settings.csv_export_threshold if self.settings else 10
        
        if self.debug:
            print(f"\n{'#'*80}")
            print(f"{'#'*80}")
            print(f"##  SQL GENERATOR WITH MCP - PROCESSING STARTED")
            print(f"{'#'*80}")
            print(f"{'#'*80}\n")
            print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📝 User Query: \"{user_query}\"")
            print(f"⚙️  Max Depth: {max_depth} {'(from settings)' if max_depth == self.settings.max_table_depth else ''}")
            print(f"📊 Auto Export Threshold: {auto_export_threshold} {'(from settings)' if auto_export_threshold == self.settings.csv_export_threshold else ''}")
            print(f"🔒 SQL Validation: {'ENABLED' if self.enable_sql_validation else 'DISABLED'}")
            print(f"🔧 Mode: {'DRY RUN (No DB execution)' if dry_run else 'FULL EXECUTION'}")
            print(f"{'='*80}\n")
        
        try:
            # Step 1: Get relevant tables
            relevant_tables = self._get_relevant_tables(user_query, max_depth)
            
            if not relevant_tables:
                return {
                    "success": False,
                    "error": "No relevant tables found for the query",
                    "user_query": user_query
                }
            
            # Step 2: Extract table schemas
            table_schemas = self._extract_table_schemas(relevant_tables)
            
            if not table_schemas:
                return {
                    "success": False,
                    "error": "No table schemas could be extracted",
                    "user_query": user_query,
                    "relevant_tables": relevant_tables
                }
            
            # Step 3: Generate SQL with ChatGPT
            sql_queries = self._generate_sql_with_chatgpt(user_query, table_schemas)
            
            result = {
                "success": True,
                "user_query": user_query,
                "relevant_tables": relevant_tables,
                "table_schemas": {table: {"column_count": len(schema.get("columns", {}))} for table, schema in table_schemas.items()},
                "sql_queries": sql_queries,
                "timestamp": datetime.now().isoformat(),
                "mode": "dry_run" if dry_run else "execution"
            }
            
            # If dry run, skip database execution
            if dry_run:
                if self.debug:
                    print(f"\n{'='*80}")
                    print(f"🔧 DRY RUN MODE: Skipping database execution")
                    print(f"📊 Returning generated SQL queries only")
                    print(f"{'='*80}\n")
                
                result["action"] = "sql_generated"
                result["message"] = "SQL queries generated successfully. Database execution skipped (dry run mode)."
                
                if self.debug:
                    print(f"\n{'#'*80}")
                    print(f"##  ✅ DRY RUN COMPLETED SUCCESSFULLY")
                    print(f"{'#'*80}\n")
                
                return result
            
            # Step 4: Execute count query (only if not dry run)
            count = self._execute_count_query(sql_queries['count_sql'])
            
            result["record_count"] = count
            
            # Step 5: Decide action based on count
            if force_csv or count > auto_export_threshold:
                if self.debug:
                    print(f"\n{'='*80}")
                    print(f"📊 DECISION: Export to CSV")
                    print(f"   Reason: {'Force CSV' if force_csv else f'Count ({count}) > Threshold ({auto_export_threshold})'}")
                    print(f"{'='*80}\n")
                
                csv_file = self._export_to_csv(sql_queries['csv_sql'])
                result["action"] = "csv_export"
                result["csv_file"] = csv_file
                result["message"] = f"Query returned {count} records. Data exported to {csv_file}"
                
            else:
                if self.debug:
                    print(f"\n{'='*80}")
                    print(f"📊 DECISION: Execute and Display")
                    print(f"   Reason: Count ({count}) <= Threshold ({auto_export_threshold})")
                    print(f"{'='*80}\n")
                
                results, columns = self._execute_query(sql_queries['query_sql'])
                result["action"] = "display_results"
                result["columns"] = columns
                result["data"] = results
                result["message"] = f"Query returned {count} records. Showing first {len(results)} rows."
            
            if self.debug:
                print(f"\n{'#'*80}")
                print(f"##  ✅ PROCESSING COMPLETED SUCCESSFULLY")
                print(f"{'#'*80}\n")
            
            return result
            
        except Exception as e:
            if self.debug:
                print(f"\n{'#'*80}")
                print(f"##  ❌ PROCESSING FAILED")
                print(f"{'#'*80}")
                print(f"Error: {e}\n")
            
            return {
                "success": False,
                "error": str(e),
                "user_query": user_query
            }


def main():
    """Example usage of SQL Generator with MCP."""
    
    # Example 1: Simple query with debug mode
    print("="*80)
    print("EXAMPLE 1: Simple Query with Debug Mode")
    print("="*80)
    
    generator = SQLGeneratorMCP(debug=True)
    
    result = generator.process_query(
        user_query="Show me all employees who joined in 2023",
        max_depth=2,
        auto_export_threshold=10
    )
    
    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    
    # Example 2: Query likely to have many results (force CSV)
    print("\n\n" + "="*80)
    print("EXAMPLE 2: Large Result Set (Force CSV)")
    print("="*80)
    
    result2 = generator.process_query(
        user_query="Get all sales transactions",
        max_depth=2,
        force_csv=True
    )
    
    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print(json.dumps(result2, indent=2, default=str))


if __name__ == "__main__":
    main()
