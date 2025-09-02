import csv
import json
import os

from tqdm import tqdm

folder_github_deps = 'resources/github/deps'
file_github_package_versions = 'resources/github/github_package_versions'
file_github_repos_info = 'resources/github/github_repos_info.json'
file_parsed_github_repos_info = 'resources/github/github_repos_info_parsed.json'
file_github_all_deps = 'resources/github/github_all_deps.csv'


# list all the folders in the folder as the repo list
def get_github_repos():
    # list all the folders that do not start with . in the github folder
    return [f for f in os.listdir(folder_github_deps) if
            os.path.isdir(os.path.join(folder_github_deps, f)) and not f.startswith('.')]


def get_github_repo_tags(repo: str):
    # list all the files that end with .json in the repo folder
    files = os.listdir(os.path.join(folder_github_deps, repo))
    tags = []
    for file in files:
        if file.endswith('.json') and file != 'initial.json':
            tags.append(file.removesuffix('.json'))
    return tags


def save_github_repo_tags_to_json():
    repos = get_github_repos()
    repo_tags = {}
    for repo in repos:
        tags = get_github_repo_tags(repo)
        repo_tags[repo] = tags
    with open(f'{file_github_package_versions}.json', 'w') as f:
        json.dump(repo_tags, f)


def print_github_repo_tags_stats():
    with open(f'{file_github_package_versions}.json', 'r') as f:
        repo_tags = json.load(f)
    print('Number of repos:', len(repo_tags))
    print('Number of tags:', sum([len(tags) for tags in repo_tags.values()]))


def print_version_deps_stats():
    with open(f'{file_github_package_versions}.json', 'r') as f:
        repo_tags = json.load(f)

    # calculate the number of all the dependencies
    total_deps = 0
    for repo, tags in repo_tags.items():
        for tag in tags:
            with open(f'{folder_github_deps}/{repo}/{tag}.json', 'r') as f:
                deps = json.load(f)
                total_deps += len(deps)
    print('Number of dependencies:', total_deps)


def get_github_repo_tag_deps(repo: str, tag: str) -> tuple:
    with open(f'{folder_github_deps}/{repo}/{tag}.json', 'r') as f:
        deps = json.load(f)
        for dep in deps:
            package = dep['depname']
            version = dep['version'] if dep['version'] else '*'
            yield package, version


def parse_github_repo_tags_deps():
    with open(f'{file_github_package_versions}.json', 'r') as f:
        repo_tags = json.load(f)

    # use csv to store the dependencies
    with open(file_github_all_deps, 'w', newline='') as csvfile:
        fieldnames = ['Version', 'DependsOn']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for repo, tags in tqdm(repo_tags.items()):
            for tag in tags:
                for package, version in get_github_repo_tag_deps(repo, tag):
                    writer.writerow({'Version': f'{repo}#{tag}', 'DependsOn': f'{package}#{version}'})


def load_github_repos_info():
    with open(file_github_repos_info, 'r') as f:
        return json.load(f)


def print_github_repo_contributors_stat():
    repos_info = load_github_repos_info()
    contributors = list()
    for info in repos_info:
        contributors.extend(info['contributors'])
    print(contributors)
    print('Number of contributors:', len(contributors))
    print('Number of unique contributors:', len(set(contributors)))


def print_github_repo_licenses_stat():
    repos_info = load_github_repos_info()
    licenses = list()
    for info in repos_info:
        licenses.append(info['license']['id'])
    print(licenses)
    print('Number of licenses:', len(licenses))
    print('Number of unique licenses:', len(set(licenses)))


def parse_github_repo_contributors_and_licenses():
    repos_info = load_github_repos_info()
    repos_info_dict = {}
    for info in repos_info:
        [_, repo] = info['repository_url'].rsplit('/', 1)
        contributors = info['contributors']
        license = {'id': info['license']['id'], 'name': info['license']['text']}
        repos_info_dict[repo] = {'contributors': contributors, 'licence': license, 'repository_url': info['repository_url']}
    with open(file_parsed_github_repos_info, 'w') as f:
        json.dump(repos_info_dict, f)


def main():
    # save_github_repo_tags_to_json()
    # print_github_repo_tags_stats()

    # print_version_deps_stats()
    # print_github_repo_contributors_stat()
    # print_github_repo_licenses_stat()

    # parse_github_repo_tags_deps()
    parse_github_repo_contributors_and_licenses()


if __name__ == '__main__':
    main()
