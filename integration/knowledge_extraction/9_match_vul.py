# Try to map the recipes from Conan to CPEs

import json

file_conan_references = 'resources/conan/conan_references.json'
file_debian_packages = 'resources/debian/debian_package_versions_in_cpp.json'
file_github_packages = 'resources/github/github_package_versions.json'
file_software_version_map = 'resources/software/software_version_map.json'


def get_conan_software_version_map() -> dict:
    with open(file_conan_references, 'r') as f:
        conan_references = json.load(f)
        references = conan_references["conancenter"].keys()
        conan_software_version_map = {}
        for ref in references:
            recipe = ref.split('/')[0]
            version = ref.split('/')[1]
            if recipe not in conan_software_version_map:
                conan_software_version_map[recipe] = [version]
            else:
                conan_software_version_map[recipe].append(version)
    return conan_software_version_map


def get_debian_software_version_map() -> dict:
    with open('resources/debian/debian_package_versions_in_cpp.json', 'r') as f:
        debian_software_version_map = json.load(f)
    return debian_software_version_map


def get_github_software_version_map() -> dict:
    with open('resources/github/github_package_versions.json', 'r') as f:
        github_software_version_map = json.load(f)

    # if the first character of the version in the versions list, remove the first character
    github_software_version_map = {k: [v[1:] if v[0] == 'v' else v for v in versions] for k, versions in
                                   github_software_version_map.items()}
    return github_software_version_map


def get_software_version_map() -> dict:
    conan_software_version_map = get_conan_software_version_map()
    debian_software_version_map = get_debian_software_version_map()
    github_software_version_map = get_github_software_version_map()

    # merge the dictionaries, if there are duplicated keys, append the values
    software_version_map = conan_software_version_map

    for key, value in debian_software_version_map.items():
        if key not in software_version_map:
            software_version_map[key] = value
        else:
            software_version_map[key] = list(set(software_version_map[key] + value))

    for key, value in github_software_version_map.items():
        if key not in software_version_map:
            software_version_map[key] = value
        else:
            software_version_map[key] = list(set(software_version_map[key] + value))

    return software_version_map


def dump_software_version_map():
    software_version_map = get_software_version_map()
    with open(file_software_version_map, 'w') as f:
        json.dump(software_version_map, f)

    print(f'Total number of software libraries: {len(software_version_map.keys())}')
    print(f'Total number of software versions: {sum([len(versions) for versions in software_version_map.values()])}')


def get_cpe_components_dict() -> dict:
    with open('resources/cpe/cpe_components_dict.json', 'r') as f:
        cpe_components_dict = json.load(f)
    return cpe_components_dict


def build_cpe_products_dict(cpe_components_dict: dict) -> dict:
    cpe_products = {}
    for cpe_id, components in cpe_components_dict.items():
        product = components['product']
        version = components['version']
        cpe_23 = components['cpe-23']
        if product not in cpe_products:
            cpe_products[product] = {version: [cpe_23]}
        elif version not in cpe_products[product]:
            cpe_products[product][version] = [cpe_23]
        else:
            cpe_products[product][version].append(cpe_23)
    return cpe_products


def getVersionToMatch(version):
    index = next((i for i, c in enumerate(version) if not c.isdigit() and c != '.'), None)
    if index is not None:
        version = version[:index]
    return version


def compare_versions(version1, version2):
    version1 = getVersionToMatch(version1)
    version2 = getVersionToMatch(version2)
    return version1 == version2 and version1 != ''


def map_software_to_cpe():
    software_version_map = get_software_version_map()
    cpe_components_dict = get_cpe_components_dict()

    cpe_products_dict = build_cpe_products_dict(cpe_components_dict)
    mapped_software = {}
    mapped_cpe_ids = []
    mapped_cpe_versions = {}

    for software_name in software_version_map.keys():
        if software_name in cpe_products_dict.keys():
            versions_of_software = software_version_map[software_name]
            versions_of_cpe = cpe_products_dict[software_name]

            # find the references that are in the versions
            mapped_software_versions = []
            for software_version in versions_of_software:
                for cpe_version in versions_of_cpe.keys():
                    if compare_versions(software_version, cpe_version):
                        print(f'{software_name} {software_version} == {cpe_version}')
                        mapped_software_versions.append(software_version)
                        cpe_23_ids = versions_of_cpe[cpe_version]
                        mapped_cpe_ids.extend(cpe_23_ids)
                        for cpe_23_id in cpe_23_ids:
                            if cpe_23_id not in mapped_cpe_versions:
                                mapped_cpe_versions[cpe_23_id] = [software_name + '/' + software_version]
                            else:
                                mapped_cpe_versions[cpe_23_id].append(software_name + '/' + software_version)

            mapped_software[software_name] = mapped_software_versions

        # if recipe in cpe_vendors:
        #     # # use get_close_matches to find the closest match
        #     #     print(recipe)
        #     #     close_matches = difflib.get_close_matches(recipe, cpe_vendors)
        #     #     if len(close_matches) > 0:
        #     #         conan_mapped_recipes[recipe] = close_matches
        #     conan_mapped_recipes_2.append(recipe)

    # print the size of the mapped software
    print(f'Mapped software: {len(mapped_software.keys())}')

    # print the size of the mapped cpe ids
    print(f'Mapped CPE IDs: {len(mapped_cpe_ids)}')

    # count the number of mapped software versions
    mapped_references = sum([len(software_versions) for software_versions in mapped_software.values()])
    print(f'Mapped software versions: {mapped_references}')

    # print(conan_mapped_recipes_2)
    # print(len(conan_mapped_recipes_2))
    #
    # # print the difference between the two sets
    # print(set(conan_mapped_recipes_2) - set(conan_mapped_recipes))

    # Save the mapped recipes
    with open('resources/software/mapped_software.json', 'w') as f:
        json.dump(mapped_software, f)

    # Save the mapped cpe ids
    with open('resources/software/mapped_cpe_ids.json', 'w') as f:
        json.dump(mapped_cpe_ids, f)

    with open('resources/software/mapped_cpe_versions.json', 'w') as f:
        json.dump(mapped_cpe_versions, f)


def match_cve_to_software_versions():
    with open('resources/cve/all_cve.json', 'r') as f:
        cves = json.load(f)

    cve_software_versions_map = {}
    with open('resources/software/mapped_cpe_versions.json', 'r') as f:
        cpe_versions = json.load(f)

    for cve in cves:
        cve_id = cve['cve_id']
        cpe_items = cve['cpe_items']
        software_versions = set()
        for cpe_item in cpe_items:
            if cpe_item in cpe_versions:
                software_versions.update(cpe_versions[cpe_item])
        if len(software_versions) > 0:
            cve_software_versions_map[cve_id] = list(software_versions)

    with open('resources/cve/cve_software_versions.json', 'w') as f:
        json.dump(cve_software_versions_map, f)

    print(f'Mapped CVEs: {len(cve_software_versions_map.keys())}')
    print(
        f'Mapped software versions: {sum([len(software_versions) for software_versions in cve_software_versions_map.values()])}')


def convert_cpe_to_hardware_version(cpe):
    cpe = cpe.split(':')
    hardware_name = cpe[4]
    hardware_version = cpe[5]
    return hardware_name + '/' + hardware_version


def match_cve_to_hardware_versions():
    with open('resources/cve/all_cve.json', 'r') as f:
        cves = json.load(f)

    cve_hardware_versions_map = {}
    for cve in cves:
        cve_id = cve['cve_id']
        cpe_items = cve['cpe_items']
        cpe_items = [cpe_item for cpe_item in cpe_items if cpe_item.startswith('cpe:2.3:h')]
        if len(cpe_items) > 0:
            cpe_items = [convert_cpe_to_hardware_version(cpe_item) for cpe_item in cpe_items]
            cve_hardware_versions_map[cve_id] = list(set(cpe_items))

    with open('resources/cve/cve_hardware_versions.json', 'w') as f:
        json.dump(cve_hardware_versions_map, f)

    print(f'Mapped CVEs: {len(cve_hardware_versions_map.keys())}')
    print(
        f'Mapped hardware versions: {sum([len(hardware_versions) for hardware_versions in cve_hardware_versions_map.values()])}')


def match_cve_to_cwe():
    with open('resources/cve/all_cve.json', 'r') as f:
        cves = json.load(f)

    cve_cwe_map = {}
    for cve in cves:
        cve_id = cve['cve_id']
        cwe = cve['cwe']
        cve_cwe_map[cve_id] = cwe

    with open('resources/cve/cve_cwe.json', 'w') as f:
        json.dump(cve_cwe_map, f)

    print(f'Mapped CVEs: {len(cve_cwe_map.keys())}')


def main():
    # dump_software_version_map()
    # map_software_to_cpe()
    # match_cve_to_software_versions()
    match_cve_to_hardware_versions()


if __name__ == '__main__':
    main()
