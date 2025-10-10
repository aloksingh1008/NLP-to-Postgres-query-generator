import csv
import json


input_file = "form_table_columns.csv"
output_file_1 = "sample_mappings2.json"
output_file_2 = "column_table_mapping.json"

def csv_to_json(csv_file_path, json_file_path=None):
    result = {}

    try:
        # Read CSV file
        with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            print("✅ CSV columns:", reader.fieldnames)

            for row in reader:
                field_name = row['field_name'].strip()
                column_name = row['column_name'].strip()

                # Debug: print current row being processed
                print(f"Processing: {field_name} -> {column_name}")

                # Append column_name under field_name
                if field_name not in result:
                    result[field_name] = []
                result[field_name].append(column_name)

        # Convert to JSON
        json_data = json.dumps(result, indent=2)
        print("\n✅ Final JSON:")
        print(json_data)

        # Save if path provided
        if json_file_path:
            with open(json_file_path, 'w', encoding='utf-8') as json_file:
                json_file.write(json_data)
                print(f"\n💾 JSON saved to: {json_file_path}")

    except Exception as e:
        print("❌ Error:", e)

# Example usage
csv_to_json(input_file, output_file_1)


# Dictionary for column_name → table_name
result = {}

# Read the CSV
with open(input_file, mode="r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        table = row["table_name"].strip()
        column = row["column_name"].strip()
        if table and column:  # Skip empty rows
            result[column] = table

# Write JSON output
with open(output_file_2, "w", encoding="utf-8") as jsonfile:
    json.dump(result, jsonfile, indent=4)

print(f"✅ JSON saved to {output_file_2}")
