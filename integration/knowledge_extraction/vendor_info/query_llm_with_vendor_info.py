import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel
from tqdm.contrib.concurrent import thread_map


class Response(BaseModel):
    """响应数据模型"""
    name: str
    url: str
    foundingDate: Optional[str]
    wikiPageUrl: Optional[str]
    location: str
    isSemiconductor: bool


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("analysis.log"),
        logging.StreamHandler()
    ]
)

# 配置路径
INPUT_JSON = "./cve_analysis/vendor_groups_20250320_175315.json"
OUTPUT_DIR = "vendor_info_results_bak"

PROMPTS_JSONL = os.path.join(OUTPUT_DIR, "prompts.jsonl")
RESPONSES_JSONL = os.path.join(OUTPUT_DIR, "responses.jsonl")
PARSED_JSONL = os.path.join(OUTPUT_DIR, "parsed_results.jsonl")

# 创建目录
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# 加载配置
api_key = "<your_api_key>"
client = OpenAI(api_key=api_key)


def load_vendor_data(file_path: str) -> List[Dict]:
    """加载vendor分组数据"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data['vendors']
    except Exception as e:
        logging.error(f"Loading vendor data failed: {str(e)}")
        raise


def generate_prompt(vendor_data: Dict) -> str:
    """生成LLM提示"""
    vendor = vendor_data['vendor']
    products = [p['name'] for p in vendor_data['products'][:5]]

    example = """Example for 'MediaTek':
{
  "name": "MediaTek Inc.",
  "url": "https://www.mediatek.com",
  "foundingDate": "1997-05-28",
  "wikipediaUrl": "https://en.wikipedia.org/wiki/MediaTek",
  "location": "Hsinchu, Taiwan",
  "isSemiconductor": true
}"""

    return f"""Please provide information about the company or organization "{vendor}" in JSON format：
    
**Requirements**
1. Validate {vendor} is a real corporate entity
2. Focus on products related to: {", ".join(products)}
3. For semiconductor judgment, consider:
   - Chip design/IP cores
   - Semiconductor manufacturing
   - Hardware security modules
   - CPU/GPU/ASIC development
4. If uncertain about any field, return null for that field
5. Use only verified official sources
6. Strictly follow this format:

{example.strip()}

**Response Format**
{{
  "name": "(Official legal name)",
  "url": "(Official website URL starting with http)",
  "foundingDate": "(ISO 8601 date format like 1968-07-18)",
  "wikiPageUrl": "(Full Wikipedia page URL)",
  "location": "(Headquarters city and country)",
  "isSemiconductor": "(True if involved in semiconductor/chip design/manufacturing, else False)"
}}
"""


def query_llm(prompt: str, max_retries=3) -> Optional[Dict]:
    """调用OpenAI API"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(max_retries):
        try:
            resp = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=Response
            )
            # if resp.choices and resp.choices[0].message:
            #     logging.info(f"API call successful: {resp.choices[0].message.content}")
            return json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"API call failed: {str(e)}")
            return None
    return None


def validate_response(data: Dict) -> bool:
    """验证响应数据结构"""
    required_fields = {
        "name": str,
        "url": str,
        "foundingDate": (str, type(None)),
        "wikiPageUrl": (str, type(None)),
        "location": str,
        "isSemiconductor": bool
    }

    for field, ftype in required_fields.items():
        if field not in data:
            return False
        if not isinstance(data[field], ftype) if not isinstance(ftype, tuple) \
                else not isinstance(data[field], ftype):
            return False
    return True


def process_vendor(vendor_data: Dict) -> Optional[Dict]:
    """处理单个vendor的完整流程"""
    vendor_name = vendor_data['vendor']

    # 生成prompt
    prompt = generate_prompt(vendor_data)

    with open(PROMPTS_JSONL, 'a', encoding='utf-8') as f:
        json.dump({"vendor": vendor_name, "prompt": prompt}, f, ensure_ascii=False)
        f.write('\n')

    # 调用API
    raw_response = query_llm(prompt)
    if not raw_response:
        return None

    # 保存原始响应
    with open(RESPONSES_JSONL, 'a', encoding='utf-8') as f:
        json.dump({
            "vendor": vendor_name,
            "response": raw_response,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }, f, ensure_ascii=False)
        f.write('\n')

    # 验证响应
    if not validate_response(raw_response):
        logging.error(f"{vendor_name} 响应验证失败")
        return None

    # 标准化数据
    processed = {
        "vendor": vendor_name,
        "name": raw_response.get("name"),
        "url": raw_response.get("url"),
        "foundingDate": raw_response.get("foundingDate"),
        "wikiPageUrl": raw_response.get("wikiPageUrl"),
        "location": raw_response.get("location"),
        "isSemiconductor": bool(raw_response.get("isSemiconductor", False)),
        "relatedProducts": [p['name'] for p in vendor_data['products'][:5]],
        "processedAt": time.strftime("%Y-%m-%dT%H:%M:%S")
    }

    # 保存解析结果
    with open(PARSED_JSONL, 'a', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False)
        f.write('\n')

    return processed


def save_semiconductor_vendors_to_csv():
    """Filter semiconductor vendors and save to CSV"""
    semiconductor_vendors = []

    # Read from the parsed results file
    with open(PARSED_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            vendor_data = json.loads(line)
            if vendor_data.get('isSemiconductor'):
                semiconductor_vendors.append(vendor_data)

    # Save to CSV
    csv_output = os.path.join(OUTPUT_DIR, "semiconductor_vendors.csv")

    if semiconductor_vendors:
        # Define CSV headers based on the first entry's keys
        headers = list(semiconductor_vendors[0].keys())

        with open(csv_output, 'w', encoding='utf-8') as f:
            # Write header
            f.write(','.join(f'"{h}"' for h in headers) + '\n')

            # Write data rows
            for vendor in semiconductor_vendors:
                row_values = []
                for key in headers:
                    value = vendor.get(key, '')
                    # Handle lists and special characters for CSV
                    if isinstance(value, list):
                        value = ';'.join(str(item) for item in value)
                    if isinstance(value, str) and (',' in value or '"' in value):
                        value = f'"{value.replace("\"", "\"\"")}"'
                    row_values.append(str(value))
                f.write(','.join(row_values) + '\n')

        logging.info(f"Saved {len(semiconductor_vendors)} semiconductor vendors to {csv_output}")
    else:
        logging.warning("No semiconductor vendors found to save")


def main():
    for file in [PROMPTS_JSONL, RESPONSES_JSONL, PARSED_JSONL]:
        if os.path.exists(file):
            os.remove(file)

    # 加载数据
    vendors = load_vendor_data(INPUT_JSON)
    # sample vendors for testing
    # vendors = vendors[:10]
    logging.info(f"成功加载 {len(vendors)} 个vendor")

    # Process vendors in parallel using thread_map
    processed_vendors = thread_map(
        process_vendor,
        vendors,
        max_workers=50,  # Adjust based on API rate limits
        desc="Processing vendors",
        total=len(vendors)
    )

    # Filter out None results and add to results list
    results = [result for result in processed_vendors if result]

    # 保存最终汇总
    final_output = os.path.join(OUTPUT_DIR, "final_results.json")
    with open(final_output, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logging.info(f"处理完成！有效结果：{len(results)}/{len(vendors)}")


if __name__ == "__main__":
    # main()
    save_semiconductor_vendors_to_csv()
