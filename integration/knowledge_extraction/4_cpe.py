import json
import xml.etree.ElementTree as ET

import pandas as pd

file_cpe_dict = 'resources/cpe/official-cpe-dictionary_v2.3.xml'
file_cpe_info_dict = 'resources/cpe/cpe_info_dict.json'
file_cpe_components_dict = 'resources/cpe/cpe_components_dict.json'


def convert_cpe_dict(xml_file=file_cpe_dict, json_info_file=file_cpe_info_dict,
                     json_components_file=file_cpe_components_dict):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    cpe_info_dict = {}
    cpe_components_dict = {}
    for item in root:
        if 'cpe-item' not in item.tag:
            continue
        cpe_id = item.attrib['name']
        print(cpe_id)
        components = cpe_id.removeprefix('cpe:/').split(':')
        cpe_id_components = {
            'part': components[0] if len(components) > 0 else '',
            'vendor': components[1] if len(components) > 1 else '',
            'product': components[2] if len(components) > 2 else '',
            'version': components[3] if len(components) > 3 else '',
            'update': components[4] if len(components) > 4 else '',
            'edition': components[5] if len(components) > 5 else '',
            'language': components[6] if len(components) > 6 else ''
        }
        cpe_title = ''
        cpe_references = []
        for child in item:
            if 'cpe23-item' in child.tag:
                cpe_23 = child.attrib['name']
                cpe_id_components['cpe-23'] = cpe_23
            if 'title' in child.tag:
                cpe_title = child.text
            if 'references' in child.tag:
                for reference in child:
                    cpe_references.append(reference.attrib['href'])
        cpe_components_dict[cpe_id] = cpe_id_components
        cpe_info_dict[cpe_id] = {
            'title': cpe_title,
            'references': cpe_references
        }

    with open(json_info_file, 'w') as f:
        json.dump(cpe_info_dict, f)
    with open(json_components_file, 'w') as f:
        json.dump(cpe_components_dict, f)


def filter_hardware_cpe():
    with open(file_cpe_components_dict, 'r') as f:
        cpe_components_dict = json.load(f)

    # filter the dictionary to only include hardware
    hardware_dict = {k: v for k, v in cpe_components_dict.items() if v['part'] == 'h'}

    hardware_df = pd.DataFrame(hardware_dict.values())
    hardware_df.to_csv('resources/cpe/hardware_cpe_all.csv', index=False)

    # group the hardware by vendor and product
    hardware_df = hardware_df.groupby(['vendor', 'product'])

    # save the vendor and product to a file
    hardware_df = hardware_df.size().reset_index()
    hardware_df.columns = ['vendor', 'product', 'count']
    hardware_df.to_csv('resources/cpe/hardware_cpe.csv', index=False)

    print(f'Total number of hardware products: {len(hardware_df)}')
    print(f'Total number of hardware versions: {len(hardware_dict)}')


def filter_application_cpe():
    with open(file_cpe_components_dict, 'r') as f:
        cpe_components_dict = json.load(f)

    # filter the dictionary to only include hardware
    application_dict = {k: v for k, v in cpe_components_dict.items() if v['part'] == 'a'}

    application_df = pd.DataFrame(application_dict.values())
    application_df.to_csv('resources/cpe/application_cpe_all.csv', index=False)

    # group the hardware by vendor and product
    application_df = application_df.groupby(['vendor', 'product'])

    # save the vendor and product to a file
    application_df = application_df.size().reset_index()
    application_df.columns = ['vendor', 'product', 'count']
    application_df.to_csv('resources/cpe/application_cpe.csv', index=False)

    print(f'Total number of application products: {len(application_df)}')
    print(f'Total number of application versions: {len(application_dict)}')


def filter_os_cpe():
    with open(file_cpe_components_dict, 'r') as f:
        cpe_components_dict = json.load(f)

    # filter the dictionary to only include hardware
    os_dict = {k: v for k, v in cpe_components_dict.items() if v['part'] == 'o'}

    os_df = pd.DataFrame(os_dict.values())
    os_df.to_csv('resources/cpe/os_cpe_all.csv', index=False)

    # group the hardware by vendor and product
    os_df = os_df.groupby(['vendor', 'product'])

    # save the vendor and product to a file
    os_df = os_df.size().reset_index()
    os_df.columns = ['vendor', 'product', 'count']
    os_df.to_csv('resources/cpe/os_cpe.csv', index=False)

    print(f'Total number of os products: {len(os_df)}')
    print(f'Total number of os versions: {len(os_dict)}')


def save_all_vendors():
    with open(file_cpe_components_dict, 'r') as f:
        cpe_components_dict = json.load(f)

    # group the hardware by vendor and product
    df = pd.DataFrame(cpe_components_dict.values())
    df = df.groupby(['vendor'])

    # save the vendor to json
    vendor_df = df.size().reset_index()
    vendor_df.columns = ['vendor', 'count']
    # sort the vendors by count
    vendor_df = vendor_df.sort_values(by='count', ascending=False)
    vendor_df.to_csv('resources/cpe/vendors.csv', index=False)

    print(f'Total number of vendors: {len(df)}')


def main():
    # convert_cpe_dict()
    # filter_hardware_cpe()
    filter_application_cpe()
    filter_os_cpe()
    # save_all_vendors()


if __name__ == '__main__':
    main()
