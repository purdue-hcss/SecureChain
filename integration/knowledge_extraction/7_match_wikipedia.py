import json
from multiprocessing import Pool

import pandas as pd
import requests


def get_hardware_names_to_search():
    # load the hardware names
    with open('resources/cpe/hardware_cpe.csv', 'r') as f:
        hardware_df = pd.read_csv(f)

    hardware_names = []
    for i, row in hardware_df.iterrows():
        name_product = row['product']
        name_vendor_product = f'{row["vendor"]}_{row["product"]}'
        hardware_names.append([name_product, name_vendor_product])

    return hardware_names


def get_software_names_to_search():
    software_libraries = []

    # load the conan libaries
    with open('resources/conan/conan_references.json', 'r') as f:
        conan_references = json.load(f)
        references = conan_references["conancenter"].keys()
        recipes = set()
        for ref in references:
            recipes.add(ref.split('/')[0])
        print(f'Total number of Conan recipes: {len(recipes)}')
        software_libraries.extend(recipes)

    # load the debian packages
    with open('resources/debian/debian_package_versions_in_cpp.json', 'r') as f:
        debian_packages = json.load(f)
        debian_packages = debian_packages.keys()
        print(f'Total number of Debian packages: {len(debian_packages)}')
        software_libraries.extend(debian_packages)

    # load the github repos
    with open('resources/github/github_package_versions.json', 'r') as f:
        github_packages = json.load(f)
        github_packages = github_packages.keys()
        print(f'Total number of Github repos: {len(github_packages)}')
        software_libraries.extend(github_packages)

    print(f'Total number of software libraries: {len(software_libraries)}')

    software_names = []
    for software in software_libraries:
        software_underscore = software.replace('-', '_')
        if software_underscore == software:
            software_names.append([software])
        else:
            software_names.append([software, software_underscore])

    return software_names


def get_vendor_names_to_search():
    vendors = []
    with open('resources/cpe/vendors.csv', 'r') as f:
        vendor_df = pd.read_csv(f)
        for i, row in vendor_df.iterrows():
            vendors.append(row['vendor'])

    vendor_names = []
    for vendor in vendors:
        vendor_underscore = vendor.replace('-', '_')
        if vendor_underscore == vendor:
            vendor_names.append([vendor])
        else:
            vendor_names.append([vendor, vendor_underscore])

    return vendor_names


def found_name_on_wikipedia(name: str) -> tuple:
    link = f'https://en.wikipedia.org/wiki/{name}'
    # print(f'Checking: {link}')
    if requests.get(link).status_code == 200:
        print(f'Founded: {name}')
        return True, name

    # Convert the underscore to a space and capitalize the letters in the name as a title
    name = name.replace('_', ' ').title()
    link = f'https://en.wikipedia.org/wiki/{name}'
    # print(f'Checking: {link}')
    if requests.get(link).status_code == 200:
        print(f'Founded: {name}')
        return True, name

    return False, ''


def found_names_on_wikipedia(names: list[str]) -> tuple:
    for name in names:
        is_founded, title = found_name_on_wikipedia(name)
        if is_founded:
            return is_founded, title

    return False, ''


def visit_wikipedia(hardware_names) -> list:
    results = []
    p = Pool(20)
    for names in hardware_names:
        results.append((names, p.apply_async(found_names_on_wikipedia, args=(names,))))
    p.close()
    p.join()

    founded = []
    for (names, result) in results:
        is_founded, title = result.get()
        if is_founded:
            founded.append(title)

    print(f'{len(founded)} products on Wikipedia')
    return founded


def get_wiki_data_id(name: str) -> str:
    link = f'https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&redirects=1&titles={name}&format=json'
    response = requests.get(link)
    if response.status_code == 200:
        data = response.json()
        pages = data['query']['pages']
        for page_id in pages:
            return pages[page_id]['pageprops']['wikibase_item']

    return ''


def get_home_page_urls_from_wikidata(wikidata_id: str) -> list:
    link = f'https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json'
    response = requests.get(link)
    if response.status_code == 200:
        data = response.json()
        entities = data['entities']
        for entity in entities:
            claims = entities[entity]['claims']
            if 'P856' in claims:
                urls = []
                for claim in claims['P856']:
                    urls.append(claim['mainsnak']['datavalue']['value'])
                return urls
    return []


def find_hardware_on_wikipedia():
    hardware_names = get_hardware_names_to_search()
    print(f'{len(hardware_names)} hardware products to search on Wikipedia')
    # hardware_names = [['iphone_11', 'apple_iphone_11'], ['watch_ultra_2', 'apple_watch_ultra_2'],
    #                   ['i9-12900k', 'core_i9-12900k']]
    founded = visit_wikipedia(hardware_names)
    # save the founded hardware names
    with open('resources/cpe/hardware_cpe_wikipedia.json', 'w') as f:
        json.dump(founded, f)


def find_software_on_wikipedia():
    software_names = get_software_names_to_search()
    print(f'{len(software_names)} software libraries to search on Wikipedia')
    # software_names = [['Google Chrome'], ['enkits'], ['guetzli'], ['qcustomplot'], ['tiny-utf8', 'tiny_utf8'], ['sobjectizer']]
    founded = visit_wikipedia(software_names)
    # save the founded software names
    with open('resources/cpe/software_libraries_wikipedia.json', 'w') as f:
        json.dump(founded, f)


def find_vendors_on_wikipedia():
    vendor_names = get_vendor_names_to_search()
    print(f'{len(vendor_names)} vendors to search on Wikipedia')
    # print(vendor_names)
    # vendor_names = [['apple'], ['google'], ['microsoft'], ['nvidia'], ['intel']]
    founded = visit_wikipedia(vendor_names)
    # save the founded vendor names
    with open('resources/cpe/vendors_wikipedia.json', 'w') as f:
        json.dump(founded, f)


def get_official_website_of_vendors_on_wikidata():
    with open('resources/cpe/vendors_wikipedia.json', 'r') as f:
        vendors = json.load(f)

    # vendors = ['apple', 'google', 'microsoft', 'nvidia', 'intel']

    vendors_info = []
    for vendor in vendors:
        wiki_data_id = get_wiki_data_id(vendor)
        urls = get_home_page_urls_from_wikidata(wiki_data_id)
        print(vendor, wiki_data_id, urls)
        vendors_info.append((vendor.title(), wiki_data_id, urls))

    # save the vendors info to a csv file
    vendors_df = pd.DataFrame(vendors_info, columns=['vendor', 'wikidata_id', 'urls'])
    vendors_df.to_csv('resources/cpe/vendors_wikipedia_info.csv', index=False)


def filter_official_website_of_vendors_on_wikidata():
    with open('resources/cpe/vendors_wikipedia_info.csv', 'r') as f:
        vendors_df = pd.read_csv(f)
        # filter the vendors with no urls
        vendors_df = vendors_df[vendors_df['urls'].notnull()]
        vendors_df = vendors_df[vendors_df['urls'] != '[]']
        vendors_df.to_csv('resources/cpe/vendors_wikipedia_info_filtered.csv', index=False)


def main():
    find_hardware_on_wikipedia()
    find_software_on_wikipedia()
    find_vendors_on_wikipedia()
    get_official_website_of_vendors_on_wikidata()
    filter_official_website_of_vendors_on_wikidata()


if __name__ == '__main__':
    main()
