import traceback
import tempfile
from dotenv import load_dotenv
from os import getenv, chdir
from git import Repo
import requests
from multiprocessing import Pool
from json import dumps


load_dotenv()

data = {
    "username": getenv("USERNAME_SITE"),
    "username_next_site": getenv("USERNAME_NEXT_SITE"),
    "site": getenv("SITE"),
    "set_all_private_BOOL": True
    if getenv("SET_ALL_PRIVATE_BOOL") and getenv("SET_ALL_PRIVATE") == "True"
    else None,
    "push_private_BOOL": True
    if getenv("PUSH_PRIVATE_BOOL") and getenv("PUSH_PRIVATE") == "True"
    else None,
    "force_push_BOOL": True
    if getenv("FORCE_PUSH_BOOL") and getenv("FORCE_PUSH") == "True"
    else None,
    "token_next_git": getenv("TOKEN"),
    "token_git": getenv("GIT"),
}


def check_data():
    for key, value in data.items():
        if value is None:
            data[key] = input(f"Enter {key}: ")
            if key.endswith("BOOL"):
                data[key] = data[key] == "True"


def get_data():
    return data


def multi_process(repos):
    num_processes = 10
    results = []

    with Pool(processes=num_processes) as pool:
        for result in pool.imap(create_push_repo, repos):
            results.append(result)

    return results


def get_repos():
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {data['token_git']}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    total = []
    res = []
    i = 0
    while True:
        print("Requesting page", i)
        res = requests.get(
            f"https://api.github.com/user/repos?type=owner&per_page=100&page={i}",
            headers=headers,
        ).json()
        total.extend(res)
        if len(res) == 0:
            break
        i += 1

    # make save
    with open("repos.json", "w") as f:
        f.write(dumps(total, indent=4))

    return total


def create_repo(name, description, private):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {data['token_next_git']}",
        "Content-Type": "application/json",
    }

    json_data = {
        "description": description,
        "name": name,
        "private": private,
    }

    response = requests.post(
        f"https://{data['site']}/api/v1/user/repos",
        headers=headers,
        json=json_data,
        timeout=5,
    )
    return response


def make_private(name, state):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {data['token_next_git']}",
        "Content-Type": "application/json",
    }

    json_data = {
        "private": state,
    }

    response = requests.patch(
        f"https://{data['site']}/api/v1/repos/{data['username_next_site']}/{name}",
        headers=headers,
        json=json_data,
        timeout=5,
    )
    return response


def delete_repo(name):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {data['token_next_git']}",
        "Content-Type": "application/json",
    }

    response = requests.delete(
        f"https://{data['site']}/api/v1/repos/{data['username_next_site']}/{name}",
        headers=headers,
        timeout=5,
    )

    return response


def get_repo(name):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {data['token_next_git']}",
        "Content-Type": "application/json",
    }

    json_data = {
        "private": True,
    }

    response = requests.get(
        f"https://{data['site']}/api/v1/repos/{data['username_next_site']}/{name}",
        headers=headers,
        json=json_data,
        timeout=5,
    )

    return response


def create_push_repo(arg):
    try:
        name = arg["name"]
        desc = arg["description"]
        private = arg["private"]
        fork = arg["fork"]
        if fork:
            delete_repo(name)
            print(f"Skipping fork '{name}'")
            return
        if private and not data["push_private_BOOL"]:
            delete_repo(name)
            print(f"Deleted '{name}'")
            return
        if data["set_all_private_BOOL"]:
            private = True
        resp = create_repo(name, desc, private)
        if resp.status_code == 201:
            print(f"Created '{name}'")
            info = resp.json()
        elif resp.status_code == 409:
            print(f"Repo '{name}' already exists")
            info = get_repo(name).json()
        else:
            raise Exception(
                f"Failed to create '{name}' (status code {resp.status_code})"
            )
        if "private" not in info:
            print(f"Failed to get '{name}' info")
            return
        if private != info["private"]:
            print(f"Making '{name}' visibility to {private}")
            resp = make_private(name, private)
            if resp.status_code == 200:
                print(f"Changed '{name}' visibility to {private}")
            else:
                print(
                    f"Failed to change '{name}' visibility to {private} (status code {resp.status_code}, {resp.text})"
                )

        if data["force_push_BOOL"] and info["size"] > 0:
            print(f"Repo '{name}' is not empty - skipping push")
            return
        with tempfile.TemporaryDirectory() as tmpdirname:
            chdir(tmpdirname)
            repo = Repo.clone_from(
                f"git@github.com:{data['username']}/{name}", tmpdirname
            )
            next_repo_url = (
                f"git@{data['site']}:{data['username_next_site']}/{name}.git"
            )
            name_site = data["site"].split(".")[0]
            repo.create_remote(name_site, next_repo_url)
            for ref in repo.refs:
                if ref.path.startswith("refs/heads/") or ref.path.startswith(
                    "refs/tags/"
                ):
                    repo.git.push(name_site, ref.name)
                elif ref.path.startswith("refs/remotes/origin/"):
                    # Skip remote branches
                    continue
                else:
                    print(f"Skipping {ref.path}")
        print(f"Pushed '{name}'")
    except Exception as e:
        print(f"Error: {e}, repo {arg['name']}")
        print(traceback.format_exc())


def main():
    repos_all = get_repos()
    repos = []
    for one_repo in repos_all:
        repos.append(one_repo)
    multi_process(repos)
