import json
import os

from tqdm import tqdm

folder_cve = 'resources/cve'
folder_raw_cve_files = 'resources/cve/nvdcve'


def get_cve_files():
    # list all the files that end with .json in the repo folder
    files = os.listdir(folder_raw_cve_files)
    cve_files = []
    for file in files:
        if file.endswith('.json') and file.startswith('CVE-'):
            cve_files.append(file)

    return cve_files


def extract_cpe_items(node):
    cpe_items = []
    for cpe_match in node['cpe_match']:
        cpe_items.append(cpe_match['cpe23Uri'])
    for child in node['children']:
        cpe_items.extend(extract_cpe_items(child))
    return list(set(cpe_items))


def get_cve_affected_cpe_items(cve_id):
    with open(os.path.join(folder_raw_cve_files, f'{cve_id}.json'), 'r') as f:
        cve = json.load(f)

    cpe_items = set()
    for nodes in cve['configurations']['nodes']:
        cpe_items.update(extract_cpe_items(nodes))

    return cve_id, list(cpe_items)


def get_cve_mapped_cwe_ids(cve_id):
    with open(os.path.join(folder_raw_cve_files, f'{cve_id}.json'), 'r') as f:
        cve = json.load(f)

    cwe_ids = set()
    for problemtype_data in cve['cve']['problemtype']['problemtype_data']:
        for description in problemtype_data['description']:
            cwe_value = description['value']
            if cwe_value.startswith('CWE-'):
                cwe_ids.add(cwe_value)

    return cve_id, list(cwe_ids)


def convert_to_all_in_one_file():
    cve_files = get_cve_files()
    cve_ids = [cve_file.removesuffix('.json') for cve_file in cve_files]
    # cve_ids = ['CVE-2016-1195', 'CVE-2016-1206']

    all_cve = []
    for cve_id in tqdm(cve_ids):
        # print(f'Processing {cve_id}')
        _, cwes = get_cve_mapped_cwe_ids(cve_id)
        _, cpe_items = get_cve_affected_cpe_items(cve_id)
        all_cve.append({'cve_id': cve_id, 'cwe_ids': cwes, 'cpe_items': cpe_items})

    # sort the cve items
    all_cve = sorted(all_cve, key=lambda x: x['cve_id'])

    with open(os.path.join(folder_cve, 'all_cve.json'), 'w') as f:
        json.dump(all_cve, f)


def main():
    convert_to_all_in_one_file()


if __name__ == '__main__':
    main()
