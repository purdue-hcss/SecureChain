import csv
import json
import os
import subprocess
from multiprocessing import Pool

import pandas as pd
import pygraphviz as pgv
from tqdm import tqdm

file_conan_references = 'resources/conan/conan_references.json'
folder_conan_deps = 'resources/conan/deps'
folder_conan_metadata = 'resources/conan/metadata'
file_all_deps = 'resources/conan/conan_all_deps.csv'


def dump_conan_references():
    if not os.path.exists('resources'):
        os.makedirs('resources')
    # run the command to dump the conan references
    subprocess.run(f'conan search "*" -r=conancenter --format=json >> {file_conan_references}', shell=True)


def print_conan_references_stats():
    with open(file_conan_references, 'r') as f:
        conan_references = json.load(f)
        references = conan_references["conancenter"].keys()
        recipes = set()
        for ref in references:
            recipes.add(ref.split('/')[0])
        print(f'Total number of Conan recipes: {len(recipes)}')
        print(f'Total number of Conan references: {len(references)}')


def load_conan_references() -> list[str]:
    with open(file_conan_references, 'r') as f:
        conan_references = json.load(f)
        conan_references = conan_references["conancenter"].keys()
    return conan_references


def build_dep_commands(conan_references: list[str]) -> list[str]:
    commands = []
    for recipe in conan_references:
        file_name = recipe.replace('/', '_')
        command = f'conan graph info --require={recipe} -r=conancenter --format=dot > {folder_conan_deps}/{file_name}.dot'
        commands.append(command)
    return commands


def run_command(command):
    print(command)
    subprocess.run(command, shell=True)


def dump_conan_references_deps():
    dump_conan_references()
    print_conan_references_stats()

    conan_references = load_conan_references()
    commands = build_dep_commands(conan_references)

    # create a directory to store the dependencies
    if not os.path.exists(folder_conan_deps):
        os.makedirs(folder_conan_deps)

    # use multiprocessing to extract the dependencies
    pool = Pool(10)
    pool.map(run_command, commands)
    pool.close()
    pool.join()


def get_file_list() -> list[str]:
    dot_files = os.listdir(folder_conan_deps)
    return [f'{folder_conan_deps}/{file}' for file in dot_files if file.endswith('.dot')]


def generate_dependencies(dot_file) -> list[tuple[str, str]]:
    print(f'Processing {dot_file}')

    dependencies = []
    try:
        G = pgv.AGraph(dot_file)
        for edge in G.edges():
            if edge[0] != 'cli':
                dependencies.append((edge[0], edge[1]))
    except:
        print(f'Error reading {dot_file}')
        pass

    # replace the '/' with '#' to avoid issues with the CSV format
    dependencies = [(dep[0].replace('/', '#'), dep[1].replace('/', '#')) for dep in dependencies]
    return dependencies


def dump_all_dependencies():
    files = get_file_list()

    all_deps = set()
    for file in files:
        dependencies = generate_dependencies(file)
        all_deps.update(dependencies)

    with open(file_all_deps, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Version', 'DependsOn'])
        for (version, depends_on) in all_deps:
            writer.writerow([version, depends_on])

    print('Done')


def build_metadata_commands(conan_references: list[str]) -> list[str]:
    commands = []
    for recipe in conan_references:
        [lib_name, _] = recipe.split('/')
        file_name = recipe.replace('/', '_')
        # get the metadata for the reference
        command = f'conan graph info --require={recipe} -r=conancenter --filter=license --filter=author --filter=homepage --filter=url --package-filter="{lib_name}*" --format=json > {folder_conan_metadata}/{file_name}.json'
        commands.append(command)
    return commands


def dump_conan_references_metadata():
    conan_references = load_conan_references()
    commands = build_metadata_commands(conan_references)

    # create a directory to store the dependencies
    if not os.path.exists(folder_conan_metadata):
        os.makedirs(folder_conan_metadata)

    # use multiprocessing to extract the dependencies
    pool = Pool(10)
    pool.map(run_command, commands)
    pool.close()
    pool.join()


def parse_conan_reference_metadata(metadata_file: str) -> tuple:
    with open(metadata_file, 'r') as f:
        try:
            metadata = json.load(f)['graph']['nodes']['1']
        except:
            metadata = {}
        licence = metadata['license'] if 'license' in metadata else ''
        author = metadata['author'] if 'author' in metadata else ''
        homepage = metadata['homepage'] if 'homepage' in metadata else ''
        url = metadata['url'] if 'url' in metadata else ''
    return licence, author, homepage, url


def parse_conan_references_metadata():
    # load the metadata files
    metadata_files = [file for file in os.listdir(folder_conan_metadata) if file.endswith('.json')]
    metadata = []
    for file in tqdm(metadata_files):
        # parse the library name and version from the file name
        [lib_name, version] = file.replace('.json', '').rsplit('_', 1)
        licence, author, homepage, url = parse_conan_reference_metadata(f'{folder_conan_metadata}/{file}')
        metadata.append([lib_name, version, licence, author, homepage, url])
    df = pd.DataFrame(metadata, columns=['Library', 'Version', 'License', 'Author', 'Homepage', 'URL'])
    df.to_csv('resources/conan/conan_all_metadata.csv', index=False)


def agg_without_nan_and_duplicates(x: pd.Series) -> list[str]:
    return x.dropna().unique().tolist()


def group_conan_references_metadata_by_library():
    df = pd.read_csv('resources/conan/conan_all_metadata.csv')
    # group by library, and use sets to remove and duplicates in the columns. When doing aggregation, don't include the nan values
    grouped_df = df.groupby('Library')
    grouped_df = grouped_df.agg(
        {'Version': agg_without_nan_and_duplicates, 'License': agg_without_nan_and_duplicates,
         'Author': agg_without_nan_and_duplicates, 'Homepage': agg_without_nan_and_duplicates,
         'URL': agg_without_nan_and_duplicates})
    grouped_df.reset_index(inplace=True)
    grouped_df['NumLicenses'] = grouped_df['License'].apply(lambda x: len(x))
    grouped_df['NumHomepages'] = grouped_df['Homepage'].apply(lambda x: len(x))
    grouped_df.columns = ['Library', 'Versions', 'Licenses', 'Authors', 'Homepages', 'URLs', 'NumLicenses', 'NumHomepages']
    grouped_df.to_csv('resources/conan/conan_grouped_metadata.csv', index=False)

def filter_conan_recipe_with_github_homepage():
    df = pd.read_csv('resources/conan/conan_grouped_metadata.csv')
    df = df[df['Homepage'].str.contains('github')]
    df.to_csv('resources/conan/conan_github_metadata.csv', index=False)

# def github_contributors(repo_url: str) -> list[str]:
#     # get the contributors from the GitHub API
#     response = requests.get(f'{repo_url}/contributors')
#     if response.status_code == 200:
#         contributors = response.json()
#         return [contributor['login'] for contributor in contributors]
#     return []



def main():
    print_conan_references_stats()

    # dump_conan_references_deps()
    # dump_all_dependencies()
    # dump_conan_references_metadata()
    # parse_conan_references_metadata()
    # group_conan_references_metadata_by_library()
    # group_conan_references_metadata_by_library()


if __name__ == "__main__":
    main()
