import psycopg2
import csv

# ---------- Database Connection ----------
conn = psycopg2.connect(
    host="localhost",     # change
    port="5432",          # change
    database="strategicerp",   # change
    user="db_user",     # change
    password="itacs9"  # change
)
cur = conn.cursor()

# ---------- Get all table ids ----------
cur.execute("SELECT id FROM form_table ORDER BY id;")
all_ids = [row[0] for row in cur.fetchall()]

batch_size = 50   # process 50 tables at a time
results = []

# ---------- Process in Batches ----------
for i in range(0, len(all_ids), batch_size):
    batch_ids = all_ids[i:i+batch_size]
    placeholders = ",".join([str(x) for x in batch_ids])

    query = f"""
    WITH cols AS (
        SELECT 
            table_name, 
            column_name, 
            data_type, 
            character_maximum_length, 
            is_nullable,
            CASE 
                WHEN column_name LIKE 'column%' 
                     AND column_name ~ 'column[0-9]+' 
                THEN regexp_replace(column_name, '^column', '')
                WHEN column_name = 'state'
                THEN 'Status'
                ELSE column_name
            END AS clean_column_name
        FROM information_schema.columns
        WHERE table_name IN (
            SELECT 'table' || id AS table_name 
            FROM form_table
            WHERE id IN ({placeholders})
        ) 
        AND column_name NOT IN (
            'id','created_by','created_date','modified_by',
            'modified_date','additionalfields','active',
            'parentstatereportid','state','stateownerid'
        )
    )
    SELECT 
        c.table_name,
        c.column_name,
        f.field_name
    FROM cols c
    LEFT JOIN form_fields f
        ON (
            (c.clean_column_name ~ '^[0-9]+$' AND f.id::text = c.clean_column_name)
            OR (f.field_name = c.column_name)
        )
        AND (c.table_name = 'table' || f.parent_id OR c.table_name = 'table' || f.relation) WHERE f.field_name is not null;
    """

    cur.execute(query)
    batch_results = cur.fetchall()
    results.extend(batch_results)

    print(f"Processed batch {i//batch_size + 1} / {(len(all_ids)-1)//batch_size + 1}")

# ---------- Write to CSV ----------
with open("form_table_columns.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["table_name","column_name", "field_name"])
    writer.writerows(results)

print("✅ Data saved to form_table_columns.csv")

cur.close()
conn.close()