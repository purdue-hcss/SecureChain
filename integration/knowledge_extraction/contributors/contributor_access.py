# load json file

import csv
import json

import requests
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

from contributors.prompt_utils import find_best_match

GITHUB_FIELDNAMES = [
    "login",
    "name",
    "company",
    "homepage",
    "location",
    "email",
    "bio",
    "twitter",
]


def get_openalex_user_info(name: str):
    url = f"https://api.openalex.org/authors?search={name}"
    while True:
        try:
            response = requests.get(url)
            break
        except Exception as e:
            print(e)
    if response.status_code == 200:
        return parse_openalex_response(response.json())
    else:
        return None


def parse_openalex_response(data: dict, top_n=3) -> list[dict]:
    items = [parse_openalex_author_item(item) for item in data.get("results")]
    items = sorted(items, key=lambda x: x["relevance_score"], reverse=True)[:top_n]
    return items


def parse_openalex_author_item(item: dict) -> dict:
    parsed = {
        "id": item.get("id"),
        "display_name": item.get("display_name"),
        "display_name_alternatives": item.get("display_name_alternatives", []),
        "relevance_score": item.get("relevance_score"),
        "affiliation_names": [
            aff.get("institution", {}).get("display_name")
            for aff in item.get("affiliations", [])
            if aff.get("institution") is not None
        ],
        "topic_names": [topic.get("display_name") for topic in item.get("topics", [])],
    }
    return parsed


def get_github_user_info(login: str):
    url = f"https://api.github.com/users/{login}"
    headers = {"Authorization": "token " + "<your_github_token>"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return parse_github_user_info(response.json())
    else:
        print(f"Failed to fetch user info for {login}")
        return None


def parse_github_user_info(response_dict: dict) -> dict:
    return dict(
        login=response_dict["login"],
        name=response_dict["name"],
        company=response_dict["company"],
        homepage=response_dict["blog"],
        location=response_dict["location"],
        email=response_dict["email"],
        bio=response_dict["bio"],
        twitter=response_dict["twitter_username"],
    )


def get_all_the_github_users() -> list:
    with open("resources/github_repos_info_parsed.json", "r") as f:
        github_repos_info = json.load(f)
    users = set()
    for repo, info in github_repos_info.items():
        if "contributors" in info:
            for contributor in info["contributors"]:
                users.add(contributor)
    return list(users)


def save_github_users_info(users: list):
    users = users[:100]
    init_github_users_info_csv_file()
    user_info_list = thread_map(
        get_github_user_info,
        users,
        max_workers=10,
        chunksize=1,
        desc="Fetching user info",
    )
    with open("resources/github_users_info.csv", "a") as csvfile:
        for user_info in user_info_list:
            if user_info:
                writer = csv.DictWriter(csvfile, fieldnames=user_info.keys())
                writer.writerow(user_info)


def init_github_users_info_csv_file():
    with open("resources/github_users_info.csv", "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=GITHUB_FIELDNAMES)
        writer.writeheader()


def init_openalex_info_csv_file():
    with open("resources/contributors_openalex_info.csv", "w") as csvfile:
        fieldnames = [
            "github_login",
            "github_name",
            "github_company",
            "openalex_id",
            "orcid",
            "display_name",
            "relevance_score",
            "last_known_affiliation",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


def get_contributors_info():
    with open("resources/github_users_info.csv", "r") as f:
        reader = csv.DictReader(f)
        contributors = []
        for row in reader:
            contributors.append(row)
    return contributors


def find_contributor_on_openalex(contributor):
    name = contributor["name"]
    if not name:
        return None

    user_info_list = get_openalex_user_info(name)
    if not user_info_list:
        return None

    print("Contributor:", contributor)
    result = find_best_match(contributor, user_info_list)
    print("Best match:", result)
    return result


def save_contributors_openalex_info(contributors):
    init_openalex_info_csv_file()
    for contributor in tqdm(contributors):
        find_contributor_on_openalex(contributor)


def main():
    # users = get_all_the_github_users()
    # print("Number of users:", len(users))

    # save_github_users_info(users)

    contributors = get_contributors_info()
    save_contributors_openalex_info(contributors)


if __name__ == "__main__":
    main()
