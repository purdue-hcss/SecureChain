import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Tuple, Optional, DefaultDict

from tqdm import tqdm

# Type aliases for better readability
VendorGroup = Dict[str, Dict]

CVE_FOLDER_PATH = 'resources/nvdcve'


def process_json_file(filepath: str) -> Optional[Tuple[str, Dict]]:
    """Load and validate JSON file, return CVE ID and configurations"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            cve_meta = data.get('cve', {}).get('CVE_data_meta', {})
            if not (cve_id := cve_meta.get('ID')):
                print(f"Missing CVE ID in file: {filepath}")
                return None
            return cve_id, data.get('configurations', {})
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error processing {filepath}: {str(e)}")
        return None


def extract_vendor_products(configurations: Dict) -> Dict[str, Set[str]]:
    """Extract CPE keys from configurations data"""
    vendor_products: DefaultDict[str, Set[str]] = defaultdict(set)

    def process_node(node: Dict):
        for match in node.get("cpe_match", []):
            if match.get("vulnerable", False):
                if uri := match.get("cpe23Uri"):
                    parts = uri.split(':')
                    if len(parts) >= 5 and parts[0] == 'cpe' and parts[1] == '2.3':
                        vendor = parts[3].lower()
                        product = parts[4].split('_')[0].lower()
                        vendor_products[vendor].add(product)

        for child in node.get("children", []):
            process_node(child)

    for node in configurations.get("nodes", []):
        process_node(node)

    return dict(vendor_products)


def build_vendor_groups(directory: str) -> Dict[str, Dict]:
    vendor_groups: DefaultDict[str, Dict] = defaultdict(lambda: {
        'products': defaultdict(set),
        'cves': set()
    })

    for filename in tqdm(os.listdir(directory), desc="Processing files"):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(directory, filename)
        if (result := process_json_file(filepath)) is None:
            continue

        cve_id, configurations = result

        vendor_products = extract_vendor_products(configurations)

        for vendor, products in vendor_products.items():
            group = vendor_groups[vendor]
            group['cves'].add(cve_id)
            for product in products:
                group['products'][product].add(cve_id)

    return {
        vendor: {
            'products': sorted(
                [
                    {
                        'name': product,
                        'cve_count': len(cves),
                        'cves': sorted(cves)
                    }
                    for product, cves in data['products'].items()
                ],
                key=lambda x: (-x['cve_count'], x['name'])  # 先按数量降序，再按名称升序
            ),
            'product_count': len(data['products']),
            'total_cves': len(data['cves']),
            'cves': sorted(data['cves'])
        }
        for vendor, data in vendor_groups.items()
    }


def save_vendor_groups_to_json(groups: Dict, output_path: str) -> None:
    """保存vendor分组结果"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sorted_vendors = sorted(
        groups.items(),
        key=lambda item: (-item[1]['total_cves'], item[0])
    )

    structured_data = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_vendors": len(groups),
            "total_products": sum(v['product_count'] for v in groups.values()),
            "total_cves": sum(v['total_cves'] for v in groups.values()),
            "data_source": "NVD CVE Records"
        },
        "vendors": [
            {
                "vendor": vendor,
                "product_count": data['product_count'],
                "total_cves": data['total_cves'],
                "products": data['products'],
                "cves": data['cves']
            }
            for vendor, data in sorted_vendors
        ]
    }

    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {output_file}")
    except IOError as e:
        print(f"Error saving data to {output_file}: {str(e)}")


# Usage example
if __name__ == "__main__":
    vendor_groups = build_vendor_groups(CVE_FOLDER_PATH)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"./cve_analysis/vendor_groups_{timestamp}.json"
    save_vendor_groups_to_json(vendor_groups, output_path)
