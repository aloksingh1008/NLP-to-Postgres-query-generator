import csv
import json
import os

# Input files
schema_csv = "form_table_schema.csv"
relationship_json = "relationships.json"
output_file = "form_table_schema.json"

# Load relationship data if available
relationships = {}
if os.path.exists(relationship_json):
    with open(relationship_json, "r", encoding="utf-8") as rel_file:
        relationships = json.load(rel_file)
else:
    print("⚠️ relationships.json not found — continuing without relationships.")

# Final merged data
final_data = {}

# Read schema CSV
with open(schema_csv, mode="r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        table_name = row["table_name"].strip()
        column_name = row["column_name"].strip()
        data_type = row["data_type"].strip()
        char_len = row["character_maximum_length"].strip()
        is_nullable = row["is_nullable"].strip().upper() == "YES"
        alias_name = row["field_name"].strip()

        # Initialize table structure if not present
        if table_name not in final_data:
            final_data[table_name] = {
                "columns": {},
                "relationships": relationships.get(table_name, {
                    "references": [],
                    "referenced_by": []
                })
            }

        # Add column metadata
        final_data[table_name]["columns"][column_name] = {
            "type": data_type,
            "character_maximum_length": char_len,
            "isnullable": is_nullable,
            "alias_name": alias_name
        }

# Save merged JSON
with open(output_file, "w", encoding="utf-8") as out:
    json.dump(final_data, out, indent=4)

print(f"✅ Merged JSON file '{output_file}' created successfully!")
