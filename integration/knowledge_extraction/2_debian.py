import csv
import json
from multiprocessing import Pool

import pandas as pd
import psycopg2
import requests
from tqdm import tqdm

folder_debian = 'resources/debian'
file_debian_package_versions = 'debian_package_versions'
file_debian_package_infos = 'debian_package_infos'
file_debian_package_versions_in_cpp = 'debian_package_versions_in_cpp'
file_package_versions_in_cpp_info_from_db = 'debian_package_versions_in_cpp_info_from_db'
file_debian_all_deps = 'debian_all_deps'

QUERY = """
SELECT packages.package,
        packages.version,
        packages.architecture,
        packages.maintainer,
        packages.maintainer_name,
        packages.maintainer_email,
        packages.description,
        packages.depends,
        packages.homepage
       FROM packages
    UNION ALL
     SELECT ubuntu_packages.package,
        ubuntu_packages.version,
        ubuntu_packages.architecture,
        ubuntu_packages.maintainer,
        ubuntu_packages.maintainer_name,
        ubuntu_packages.maintainer_email,
        ubuntu_packages.description,
        ubuntu_packages.depends,
        ubuntu_packages.homepage
       FROM ubuntu_packages
    UNION ALL
     SELECT derivatives_packages.package,
        derivatives_packages.version,
        derivatives_packages.architecture,
        derivatives_packages.maintainer,
        derivatives_packages.maintainer_name,
        derivatives_packages.maintainer_email,
        derivatives_packages.description,
        derivatives_packages.depends,
        derivatives_packages.homepage
       FROM derivatives_packages
    UNION ALL
     SELECT archived_packages.package,
        archived_packages.version,
        archived_packages.architecture,
        archived_packages.maintainer,
        archived_packages.maintainer_name,
        archived_packages.maintainer_email,
        archived_packages.description,
        archived_packages.depends,
        archived_packages.homepage
       FROM archived_packages
    UNION ALL
     SELECT ports_packages.package,
        ports_packages.version,
        ports_packages.architecture,
        ports_packages.maintainer,
        ports_packages.maintainer_name,
        ports_packages.maintainer_email,
        ports_packages.description,
        ports_packages.depends,
        ports_packages.homepage
       FROM ports_packages
    UNION ALL
     SELECT unofficial_packages.package,
        unofficial_packages.version,
        unofficial_packages.architecture,
        unofficial_packages.maintainer,
        unofficial_packages.maintainer_name,
        unofficial_packages.maintainer_email,
        unofficial_packages.description,
        unofficial_packages.depends,
        unofficial_packages.homepage
       FROM unofficial_packages
"""


def get_debian_packages_names() -> list:
    url = "https://sources.debian.org/api/list/"
    response = requests.get(url)
    data = response.json()
    package_names = [package["name"] for package in data["packages"]]
    return package_names


def get_debian_package_versions(package_name: str) -> list:
    url = f"https://sources.debian.org/api/src/{package_name}/"
    try:
        response = requests.get(url)
        data = response.json()
        versions = [version["version"] for version in data["versions"]]
    except:
        versions = []

    # append the results to jsonl file
    with open(f'{folder_debian}/{file_debian_package_versions}.jsonl', 'a') as f:
        f.write(json.dumps({package_name: versions}) + '\n')

    print(f'{package_name}: {len(versions)}')
    return versions


def get_debian_package_version_info(package_name: str, version: str) -> dict:
    url = f"https://sources.debian.org/api/src/{package_name}/{version}/"
    # get the pts_link and sloc in its package info
    try:
        response = requests.get(url)
        data = response.json()
        pkg_infos = data['pkg_infos']
        filtered = {'pts_link': pkg_infos['pts_link'], 'sloc': pkg_infos['sloc']}
    except:
        filtered = {}

    # append the results to jsonl file
    with open(f'{folder_debian}/{file_debian_package_infos}.jsonl', 'a') as f:
        f.write(json.dumps({package_name: filtered}) + '\n')

    print(f'{package_name} {version}: {filtered}')
    return filtered


def save_to_json(data, file_name):
    with open(f'{folder_debian}/{file_name}.json', 'w') as f:
        json.dump(data, f)


def append_row_to_csv(data, file_name):
    with open(f'{folder_debian}/{file_name}.csv', 'a') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(data)


def append_rows_to_csv(data, file_name):
    with open(f'{folder_debian}/{file_name}.csv', 'a') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(data)


def save_debian_package_versions():
    # get all debian package names
    package_names = get_debian_packages_names()
    save_to_json(package_names, 'debian_packages')
    print(len(package_names))

    # get all versions for each package
    package_versions = {}
    p = Pool(20)
    for package_name in package_names:
        versions_res = p.apply_async(get_debian_package_versions, args=(package_name,))
        package_versions[package_name] = versions_res
    p.close()
    p.join()
    for package_name, versions_res in package_versions.items():
        try:
            package_versions[package_name] = versions_res.get()
        except:
            package_versions[package_name] = []

    # for package_name in package_names but not in package_versions, add empty list
    for package_name in package_names:
        if package_name not in package_versions:
            package_versions[package_name] = []

    save_to_json(package_versions, file_debian_package_versions)


def save_debian_package_info():
    # load debian package versions
    with open(f'{folder_debian}/{file_debian_package_versions}.json', 'r') as f:
        package_versions = json.load(f)

    # for first version of each package, get the pts_link and sloc in its package info
    package_info = {}
    p = Pool(20)
    for package_name, versions in package_versions.items():
        if len(versions) > 0:
            version = versions[0]
            info_res = p.apply_async(get_debian_package_version_info, args=(package_name, version))
            package_info[package_name] = info_res
    p.close()
    p.join()

    for package_name, info_res in package_info.items():
        try:
            package_info[package_name] = info_res.get()
        except:
            package_info[package_name] = {}

    # for package_name in package_versions but not in package_info, add empty dict
    for package_name in package_versions:
        if package_name not in package_info:
            package_info[package_name] = {}

    save_to_json(package_info, file_debian_package_infos)


def filter_debian_package_versions_written_in_cpp():
    # load debian package versions
    with open(f'{folder_debian}/{file_debian_package_versions}.json', 'r') as f:
        package_versions = json.load(f)

    # load debian package versions
    with open(f'{folder_debian}/{file_debian_package_infos}.json', 'r') as f:
        package_infos = json.load(f)

    # filter packages that are written in C++
    package_versions_in_cpp = {}
    for package_name, versions in package_versions.items():
        if package_name in package_infos:
            sloc = package_infos[package_name]['sloc']
            for lang, loc in sloc:
                if lang == 'cpp':
                    package_versions_in_cpp[package_name] = versions
                    break

    save_to_json(package_versions_in_cpp, file_debian_package_versions_in_cpp)
    print(len(package_versions_in_cpp))


def print_debian_package_versions_in_cpp_stats():
    with open(f'{folder_debian}/{file_debian_package_versions_in_cpp}.json', 'r') as f:
        package_versions = json.load(f)

    print(f'Total number of Debian packages: {len(package_versions)}')
    total_versions = sum([len(versions) for versions in package_versions.values()])
    print(f'Total number of Debian package versions: {total_versions}')


def get_connection_to_debian_db():
    conn = psycopg2.connect(
        host="udd-mirror.debian.net",
        database="udd",
        user="udd-mirror",
        password="udd-mirror"
    )
    return conn


def get_debian_package_info_column_names_from_db(cur):
    # get the column names of the all_packages table
    cur.execute(f"SELECT * FROM ({QUERY}) AS all_package_tables WHERE false")
    column_names = [desc[0] for desc in cur.description]
    return column_names


def get_debian_package_info_from_db(cur, package_name: str):
    # get the package info records from the database
    cur.execute(f"SELECT * FROM ({QUERY}) AS all_package_tables WHERE package = '{package_name}'")
    records = cur.fetchall()
    print(f'{package_name}: {len(records)}')
    return records


def save_debian_package_info_from_db():
    conn = get_connection_to_debian_db()
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()

    # save column names as the csv header
    column_names = get_debian_package_info_column_names_from_db(cur)
    append_row_to_csv(column_names, file_package_versions_in_cpp_info_from_db)

    # load debian package versions in C++
    with open(f'{folder_debian}/{file_debian_package_versions_in_cpp}.json', 'r') as f:
        package_versions_in_cpp = json.load(f)

    # get the package info records from the database
    for package_name in tqdm(package_versions_in_cpp.keys()):
        records = get_debian_package_info_from_db(cur, package_name)
        append_rows_to_csv(records, file_package_versions_in_cpp_info_from_db)

    cur.close()
    conn.close()


def split_depends(depends_str: str) -> list:
    depends = depends_str.split(',')
    depends_version_map = {}

    # if the dependency has a "|" in it, add all the dependencies to the list
    depends = [dep.split('|') for dep in depends]
    depends = [item for sublist in depends for item in sublist]

    for dependency in depends:
        if '(' in dependency:
            [package, version] = dependency.split('(')
            version = version.strip().removesuffix(')')
        else:
            package = dependency
            version = '*'

        package = package.strip()
        version = version.strip()

        if version.startswith('='):
            version = version[1:].strip()

        if package in depends_version_map:
            depends_version_map[package].append(version)
        else:
            depends_version_map[package] = [version]

    # convert version list to string and concatenate with the package name in the format "package#version"
    return [f'{package}#{"&".join(versions)}' for package, versions in depends_version_map.items()]


def parse_debian_package_version_deps():
    df = pd.read_csv(f'{folder_debian}/{file_package_versions_in_cpp_info_from_db}.csv')
    # keep only the columns of interest
    df = df[['package', 'version', 'depends']]
    df = df.drop_duplicates()
    df = df.dropna(subset=['depends'])
    df = df[df['depends'] != '']
    # split the dependencies by comma, for each one of them, only keep the package name
    df['depends'] = df['depends'].apply(split_depends)
    # group by package and version
    df = df.groupby(['package', 'version'])
    # for each group, keep the longest list of dependencies
    df = df['depends'].apply(lambda x: max(x, key=len))
    df = df.reset_index()
    df['num_deps'] = df['depends'].apply(lambda x: len(x))

    # create a new dataframe with the concatenation of package and version, and each dependency
    df = df.explode('depends')
    # rename the depends column to DependsOn
    df = df.rename(columns={'depends': 'DependsOn'})
    # concatenate the package and version
    df['Version'] = df['package'] + '#' + df['version']
    # drop the other columns
    df = df[['Version', 'DependsOn']]

    # print the number of all dependencies
    print(f'Total number of dependencies: {df["DependsOn"]}')

    # save the results
    df.to_csv(f'{folder_debian}/{file_debian_all_deps}.csv', index=False)


def main():
    # save_debian_package_versions()
    # save_debian_package_info()

    # filter_debian_package_versions_written_in_cpp()
    print_debian_package_versions_in_cpp_stats()

    # save_debian_package_info_from_db()
    # parse_debian_package_version_deps()


if __name__ == "__main__":
    main()
