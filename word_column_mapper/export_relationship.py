import json
import psycopg2

# ---------- CONFIGURATION ----------
DB_CONFIG = {
    "dbname": "strategicerp",
    "user": "postgres",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}
OUTPUT_FILE = "relationships.json"

# ---------- MAIN QUERY ----------
SQL_QUERY = """
WITH rels AS (
    SELECT
        tc.constraint_name,
        tc.table_name AS fk_table,
        kcu.column_name AS fk_column,
        ccu.table_name AS pk_table,
        ccu.column_name AS pk_column
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.constraint_schema = kcu.constraint_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.constraint_schema = tc.constraint_schema
    WHERE
        tc.constraint_type = 'FOREIGN KEY'
)
SELECT table_name, relation_details
FROM (
    -- for every table, gather its "references" list
    SELECT fk_table AS table_name,
           json_build_object(
               'references', json_agg(
                   json_build_object(
                       'table', pk_table,
                       'foreign_key_column', fk_column,
                       'primary_key_column', pk_column,
                       'constraint_name', constraint_name
                   )
               ),
               'referenced_by', '[]'::json
           ) AS relation_details
    FROM rels
    GROUP BY fk_table

    UNION ALL

    -- for every table, gather its "referenced_by" list
    SELECT pk_table AS table_name,
           json_build_object(
               'references', '[]'::json,
               'referenced_by', json_agg(
                   json_build_object(
                       'table', fk_table,
                       'foreign_key_column', fk_column,
                       'primary_key_column', pk_column,
                       'constraint_name', constraint_name
                   )
               )
           ) AS relation_details
    FROM rels
    GROUP BY pk_table
) combined;
"""

# ---------- MAIN EXECUTION ----------
def export_relationships():
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("Executing SQL query...")
        cursor.execute(SQL_QUERY)

        rows = cursor.fetchall()

        # Merge results into one combined dictionary
        merged = {}
        for table_name, relation_details in rows:
            if table_name not in merged:
                merged[table_name] = {"references": [], "referenced_by": []}

            merged[table_name]["references"].extend(relation_details["references"])
            merged[table_name]["referenced_by"].extend(relation_details["referenced_by"])

        # Write to JSON file
        print(f"Writing output to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)

        print(f"✅ Export complete: {len(merged)} tables found")

    except Exception as e:
        print("❌ Error:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    export_relationships()
