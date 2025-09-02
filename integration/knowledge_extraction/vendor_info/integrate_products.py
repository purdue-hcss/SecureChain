import csv
import json
import os
import argparse
import re
from pathlib import Path

def normalize_name(name):
    """
    Normalizes a company name for robust matching by making it lowercase and
    removing all spaces and punctuation.
    e.g., "MvPower Technology Co., Ltd." becomes "mvpowertechnologycoltd"
    """
    if not isinstance(name, str):
        return ""
    
    # Convert to lowercase
    name = name.lower()
    # Remove all characters that are not letters or numbers
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def integrate_product_data(csv_input_path, json_dir_path, csv_output_path):
    """
    Reads company data from a CSV, product data from JSON files,
    and integrates the product lists into new hardware/software columns in a new CSV file.

    Args:
        csv_input_path (str): The file path for the input CSV.
        json_dir_path (str): The path to the directory containing JSON files.
        csv_output_path (str): The file path for the output CSV.
    """
    # --- 1. Read the CSV file and group rows by company name ---
    print(f"Reading CSV data from: {csv_input_path}")
    grouped_companies = {} # Structure: { "company_name": [row1, row2, ...] }
    header = []
    try:
        with open(csv_input_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            header = reader.fieldnames
            for row in reader:
                company_name = row.get('name')
                if company_name:
                    row['hardwareProducts'] = row.get('hardwareProducts', '')
                    row['softwareProducts'] = row.get('softwareProducts', '')
                    if company_name not in grouped_companies:
                        grouped_companies[company_name] = []
                    grouped_companies[company_name].append(row)
                else:
                    print(f"Warning: Skipping a row in CSV because it has no 'name' field: {row}")

    except FileNotFoundError:
        print(f"Error: The file {csv_input_path} was not found.")
        return
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return

    if not header:
        print("Error: Could not read header from CSV file.")
        return

    # --- 1.5. Consolidate grouped rows into a single row per company ---
    print("Consolidating duplicate companies into single rows...")
    companies_data = {} # Structure: { "company_name": merged_row }
    for company_name, rows in grouped_companies.items():
        if not rows:
            continue
        
        # Start with a copy of the first row as the base
        base_row = rows[0].copy()

        # Collect all unique vendors from the group
        all_vendors = set(row.get('vendor', '') for row in rows if row.get('vendor'))
        base_row['vendor'] = ';'.join(sorted(list(all_vendors)))

        # Merge product lists from all grouped rows
        all_hw_products = set()
        all_sw_products = set()
        for row in rows:
            hw = row.get('hardwareProducts', '').split(';')
            sw = row.get('softwareProducts', '').split(';')
            all_hw_products.update(p for p in hw if p)
            all_sw_products.update(p for p in sw if p)

        base_row['hardwareProducts'] = ';'.join(sorted(list(all_hw_products)))
        base_row['softwareProducts'] = ';'.join(sorted(list(all_sw_products)))

        companies_data[company_name] = base_row


    # --- 1.6. Create a normalized name mapping for robust matching ---
    print("Creating a normalized name map for matching...")
    normalized_to_original_map = {normalize_name(name): name for name in companies_data.keys()}

    # --- 2. Read all JSON files in the specified directory ---
    print(f"Reading JSON files from directory: {json_dir_path}")
    if not os.path.isdir(json_dir_path):
        print(f"Error: The directory {json_dir_path} does not exist.")
        return

    for filename in os.listdir(json_dir_path):
        if filename.lower().endswith('.json'):
            file_path = os.path.join(json_dir_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    product_info = json.load(f)

                    json_company_name = product_info.get('company')
                    products = product_info.get('products', [])

                    if not json_company_name:
                        print(f"Warning: Skipping JSON file {filename} because it lacks a 'company' key.")
                        continue

                    # --- 3. Match JSON data to CSV data using normalized names ---
                    target_company_key = None
                    
                    # Strategy 1: Match using the 'company' field from JSON content
                    normalized_json_name = normalize_name(json_company_name)
                    if normalized_json_name in normalized_to_original_map:
                        target_company_key = normalized_to_original_map[normalized_json_name]
                        print(f"Found match for '{json_company_name}' as '{target_company_key}'. Integrating products.")
                    
                    # Strategy 2: Fallback to matching using the JSON filename
                    if not target_company_key:
                        filename_stem = Path(filename).stem
                        normalized_filename = normalize_name(filename_stem)
                        if normalized_filename in normalized_to_original_map:
                            target_company_key = normalized_to_original_map[normalized_filename]
                            print(f"Could not match on company name '{json_company_name}'. Found fallback match using filename '{filename}' as '{target_company_key}'.")
                    
                    if not target_company_key:
                         print(f"Warning: No match found in CSV for company '{json_company_name}' or filename '{filename}'.")

                    # If a match was found, integrate the data into the single merged row
                    if target_company_key:
                        hardware_products = [p['name'] for p in products if p.get('type') == 'hardware' and p.get('name')]
                        software_products = [p['name'] for p in products if p.get('type') == 'software' and p.get('name')]

                        # Access the single merged row for the company
                        vendor_row = companies_data[target_company_key]
                        
                        if hardware_products:
                            existing_hw_list = [p for p in vendor_row.get('hardwareProducts', '').split(';') if p]
                            existing_hw_list.extend(hardware_products)
                            vendor_row['hardwareProducts'] = ';'.join(list(dict.fromkeys(existing_hw_list)))
                        
                        if software_products:
                            existing_sw_list = [p for p in vendor_row.get('softwareProducts', '').split(';') if p]
                            existing_sw_list.extend(software_products)
                            vendor_row['softwareProducts'] = ';'.join(list(dict.fromkeys(existing_sw_list)))

            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {filename}. Skipping.")
            except Exception as e:
                print(f"An error occurred while processing {filename}: {e}")

    # --- 4. Write the updated data to a new CSV file ---
    print(f"Writing updated data to: {csv_output_path}")
    
    output_header = [h for h in header if h.lower() != 'relatedproducts']
    if 'hardwareProducts' not in output_header:
        output_header.append('hardwareProducts')
    if 'softwareProducts' not in output_header:
        output_header.append('softwareProducts')

    try:
        Path(csv_output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(csv_output_path, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_header, extrasaction='ignore')
            writer.writeheader()
            # The values of the dictionary are the consolidated rows to be written
            writer.writerows(companies_data.values())
        
        print("\nIntegration complete!")
        print(f"Output saved to {csv_output_path}")

    except Exception as e:
        print(f"An error occurred while writing the new CSV file: {e}")


def create_dummy_files():
    """Creates dummy files for demonstration purposes."""
    print("Creating dummy files for demonstration...")
    
    csv_content = """vendor,name,url,foundingDate,location,isSemiconductor,hardwareProducts,softwareProducts,wikiPageUrl,processedAt
microsoft,Microsoft Corporation,https://www.microsoft.com,1975-04-04,"Redmond, Washington, USA",True,,windows;office,https://en.wikipedia.org/wiki/Microsoft,2025-03-20T18:59:06
msft,Microsoft Corporation,https://www.microsoft.com,1975-04-04,"Redmond, Washington, USA",True,,internet;edge;sharepoint,https://en.wikipedia.org/wiki/Microsoft,2025-03-20T18:59:06
google,Google LLC,https://www.google.com,1998-09-04,"Mountain View, California, USA",True,,android;chrome;tensorflow;v8;asylo,https://en.wikipedia.org/wiki/Google,2025-03-20T18:59:11
apple,Apple Inc.,https://www.apple.com,1976-04-01,"Cupertino, California, USA",True,"iphone;mac",macos;tvos;watchos,https://en.wikipedia.org/wiki/Apple_Inc.,2025-03-20T18:59:25
qualcomm,Qualcomm Incorporated,https://www.qualcomm.com,1985-07-01,"San Diego, California, USA",True,"sd;wcd9380;qca6574au;wsa8830;wsa8835",,https://en.wikipedia.org/wiki/Qualcomm,2025-03-20T19:00:22
samsung,Samsung Electronics,https://www.samsung.com,1969-01-13,"Suwon, South Korea",True,,,https://en.wikipedia.org/wiki/Samsung_Electronics,2025-03-20T19:01:00
mvpower,"MvPower Technology Co., Ltd.",https://www.example.com,2000-01-01,"Shenzhen, China",False,,,https://www.example.com,2025-03-20T19:02:00
"""
    with open("companies.csv", "w") as f:
        f.write(csv_content)

    json_dir = "product_data"
    os.makedirs(json_dir, exist_ok=True)

    json_files = {
        "samsung.json": {
            "company": "Samsung Electronics",
            "products": [
                {"name": "Exynos", "type": "hardware"},
                {"name": "ISOCELL", "type": "hardware"},
                {"name": "SmartThings", "type": "software"}
            ]
        },
        "google_underscore.json": {
            "company": "Google_LLC",
            "products": [
                {"name": "Pixel", "type": "hardware"},
                {"name": "Nest", "type": "hardware"}
            ]
        },
        "microsoft.json": {
            "company": "Microsoft Corporation",
            "products": [
                {"name": "Surface", "type": "hardware"},
                {"name": "Xbox", "type": "hardware"},
                {"name": "VS Code", "type": "software"}
            ]
        },
        "mvpower.json": {
            "company": "MvPower_Technology_Co_Ltd",
            "products": [
                {"name": "PowerBank-1000", "type": "hardware"},
                {"name": "Charger-X", "type": "hardware"}
            ]
        },
        "Apple Inc.json": { # Note the filename matches the CSV name
            "company": "Cupertino Tech Giant", # This internal name will fail to match
            "products": [{"name": "Vision Pro", "type": "hardware"}]
        },
        "unmatched.json": {
            "company": "Some_Random_Company Inc.",
            "products": [{"name": "WidgetA", "type": "hardware"}]
        }
    }

    for filename, content in json_files.items():
        with open(os.path.join(json_dir, filename), "w") as f:
            json.dump(content, f, indent=4)
    
    print("Dummy files created successfully.\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Integrate product data from JSON files into a master CSV file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-c', '--csv_input', 
        default='companies.csv',
        help="Path to the input CSV file.\n(default: companies.csv)"
    )
    parser.add_argument(
        '-j', '--json_dir', 
        default='product_data',
        help="Path to the directory containing JSON files.\n(default: product_data/)"
    )
    parser.add_argument(
        '-o', '--output', 
        default='companies_updated.csv',
        help="Path for the output CSV file.\n(default: companies_updated.csv)"
    )
    parser.add_argument(
        '--create-dummies',
        action='store_true',
        help="If specified, creates dummy input files for demonstration."
    )

    args = parser.parse_args()

    if args.create_dummies:
        create_dummy_files()

    integrate_product_data(args.csv_input, args.json_dir, args.output)
