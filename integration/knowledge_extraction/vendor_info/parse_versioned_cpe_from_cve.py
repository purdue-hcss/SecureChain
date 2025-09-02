import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm

CVE_FOLDER_PATH = "vendor_info/resources/nvdcve"


def process_json_file(filepath: str) -> Optional[Tuple[str, Dict]]:
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            cve_meta = data.get("cve", {}).get("CVE_data_meta", {})
            if not (cve_id := cve_meta.get("ID")):
                print(f"Missing CVE ID in file: {filepath}")
                return None
            return cve_id, data.get("configurations", {})
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error processing {filepath}: {str(e)}")
        return None


def extract_versioned_entries(configurations: Dict) -> List[Tuple[str, str, Dict]]:
    """Extract vendor, product and version constraints from CPE data"""
    entries = []

    def process_node(node: Dict):
        for match in node.get("cpe_match", []):
            if not match.get("vulnerable", False):
                continue

            uri = match.get("cpe23Uri", "")
            parts = uri.split(":")
            if len(parts) < 6 or parts[0] != "cpe" or parts[1] != "2.3":
                continue

            vendor = parts[3].lower()
            product = parts[4].lower()
            cpe_version = parts[5]

            # 提取版本约束条件
            constraints = {
                "cpe_version": cpe_version,
                "versionStartIncluding": match.get("versionStartIncluding"),
                "versionEndIncluding": match.get("versionEndIncluding"),
                "versionStartExcluding": match.get("versionStartExcluding"),
                "versionEndExcluding": match.get("versionEndExcluding"),
            }

            entries.append((vendor, product, constraints))

        for child in node.get("children", []):
            process_node(child)

    for node in configurations.get("nodes", []):
        process_node(node)

    return entries


def build_versioned_groups(directory: str) -> Dict[str, Dict]:
    """构建包含版本约束的分组结构"""
    vendor_groups = defaultdict(
        lambda: {
            "products": defaultdict(
                lambda: defaultdict(
                    lambda: {"constraints": {}, "cves": set(), "cve_count": 0}
                )
            ),
            "cves": set(),
            "product_count": 0,
            "total_cves": 0,
        }
    )

    for filename in tqdm(os.listdir(directory), desc="Processing CVEs"):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(directory, filename)
        if (result := process_json_file(filepath)) is None:
            continue

        cve_id, configurations = result
        entries = extract_versioned_entries(configurations)

        for vendor, product, constraints in entries:
            group = vendor_groups[vendor]
            group["cves"].add(cve_id)

            # 生成唯一的版本约束标识
            version_key = json.dumps(constraints, sort_keys=True)
            product_group = group["products"][product]

            # 初始化或更新版本条目
            if not product_group[version_key]["constraints"]:
                product_group[version_key]["constraints"] = constraints
            product_group[version_key]["cves"].add(cve_id)
            product_group[version_key]["cve_count"] = len(
                product_group[version_key]["cves"]
            )

    # 转换为最终输出格式
    formatted_groups = {}
    for vendor, data in vendor_groups.items():
        products = []
        for product_name, versions in data["products"].items():
            version_list = []
            for ver in versions.values():
                version_list.append(
                    {
                        "constraints": ver["constraints"],
                        "cves": sorted(ver["cves"]),
                        "cve_count": ver["cve_count"],
                    }
                )

            # 按CVE数量降序排序版本
            version_list.sort(
                key=lambda x: (
                    -x["cve_count"],
                    json.dumps(x["constraints"], sort_keys=True),
                )
            )

            products.append(
                {
                    "name": product_name,
                    "versions": version_list,
                    "total_cves": sum(v["cve_count"] for v in version_list),
                }
            )

        # 按产品总CVE数排序
        products.sort(key=lambda x: (-x["total_cves"], x["name"]))

        formatted_groups[vendor] = {
            "products": products,
            "product_count": len(products),
            "total_cves": len(data["cves"]),
            "cves": sorted(data["cves"]),
        }

    return formatted_groups


def save_vendor_groups_to_json(groups: Dict, output_path: str) -> None:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sorted_vendors = sorted(
        groups.items(), key=lambda item: (-item[1]["total_cves"], item[0])
    )

    structured_data = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_vendors": len(groups),
            "total_products": sum(v["product_count"] for v in groups.values()),
            "total_cves": sum(v["total_cves"] for v in groups.values()),
            "data_source": "NVD CVE Records",
        },
        "vendors": [
            {
                "vendor": vendor,
                "product_count": data["product_count"],
                "total_cves": data["total_cves"],
                "products": [
                    {
                        "name": p["name"],
                        "total_cves": p["total_cves"],
                        "versions": [
                            {
                                "constraints": v["constraints"],
                                "cve_count": v["cve_count"],
                                "cves": v["cves"],
                            }
                            for v in p["versions"]
                        ],
                    }
                    for p in data["products"]
                ],
                "cves": data["cves"],
            }
            for vendor, data in sorted_vendors
        ],
    }

    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {output_file}")
    except IOError as e:
        print(f"Error saving data: {str(e)}")


if __name__ == "__main__":
    versioned_groups = build_versioned_groups(CVE_FOLDER_PATH)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"vendor_info/cve_analysis/versioned_groups_{timestamp}.json"
    save_vendor_groups_to_json(versioned_groups, output_path)
