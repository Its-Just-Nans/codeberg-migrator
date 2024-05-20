from dotenv import load_dotenv
from os import getenv
import requests
from json import dumps

load_dotenv()


def check_env_bool(key):
    envir = getenv(key)
    if envir:
        if envir == "True":
            return True
        elif envir == "False":
            return False
    return None


data = {
    "username": getenv("USERNAME_SITE"),
    "username_next_site": getenv("USERNAME_NEXT_SITE"),
    "site": getenv("SITE"),
    "set_all_private_BOOL": check_env_bool("SET_ALL_PRIVATE_BOOL"),
    "push_private_BOOL": check_env_bool("PUSH_PRIVATE_BOOL"),
    "force_push_BOOL": check_env_bool("FORCE_PUSH_BOOL"),
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


def set_data(key, value):
    data[key] = value


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
        "Content-Type": "application/json",
    }

    json_data = {
        "description": description,
        "name": name,
    }

    if data["site"] == "gitlab.com":
        url = f"/api/v4/projects?private_token={data['token_next_git']}"
        json_data["visibility"] = "private" if private else "public"
    else:
        headers["Authorization"] = f"Bearer {data['token_next_git']}"
        url = "/api/v1/user/repos"
        json_data["private"] = private

    response = requests.post(
        f"https://{data['site'] + url}",
        headers=headers,
        json=json_data,
        timeout=5,
    )
    return response


def make_private(name, state):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    json_data = {}

    if data["site"] == "gitlab.com":
        meth = requests.put
        headers["Authorization"] = f"PRIVATE-TOKEN: {data['token_next_git']}"
        url = (
            f"/api/v4/projects/{data['proj_id']}?private_token={data['token_next_git']}"
        )
        json_data["visibility"] = "private" if state else "enabled"
    else:
        meth = requests.patch
        headers["Authorization"] = f"Bearer {data['token_next_git']}"
        url = f"/api/v1/repos/{data['username_next_site']}/{name}"
        json_data["private"] = state

    response = meth(
        f"https://{data['site']}" + url,
        headers=headers,
        json=json_data,
        timeout=5,
    )
    return response


def delete_repo(name):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    if data["site"] == "gitlab.com":
        url = f"/api/v4/projects/{name}?private_token={data['token_next_git']}"
    else:
        headers["Authorization"] = f"Bearer {data['token_next_git']}"
        url = f"/api/v1/repos/{data['username_next_site']}/{name}"

    response = requests.delete(
        f"https://{data['site']}" + url,
        headers=headers,
        timeout=5,
    )

    return response


def get_repo(name):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    if data["site"] == "gitlab.com":
        url = f"/api/v4/projects/{data['username_next_site']}%2F{name}?private_token={data['token_next_git']}"
    else:
        headers["Authorization"] = f"Bearer {data['token_next_git']}"
        url = f"/api/v1/repos/{data['username_next_site']}/{name}"

    response = requests.get(
        f"https://{data['site']}" + url,
        headers=headers,
        timeout=5,
    )

    return response


def get_private(repo):
    if data["site"] == "gitlab.com":
        if "visibility" not in repo:
            return None
        return repo["visibility"] == "private"
    else:
        if "private" not in repo:
            return None
        return repo["private"]
