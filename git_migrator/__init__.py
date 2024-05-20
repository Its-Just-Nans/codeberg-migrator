import traceback
import tempfile
from os import chdir
from git import Repo
from multiprocessing import Pool

from .lib import (
    delete_repo,
    create_repo,
    get_repo,
    get_repos,
    make_private,
    get_data,
    set_data,
    get_private,
)


def multi_process(repos):
    num_processes = 10
    results = []

    with Pool(processes=num_processes) as pool:
        for result in pool.imap(create_push_repo, repos):
            results.append(result)

    return results


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
        if private and not get_data()["push_private_BOOL"]:
            delete_repo(name)
            print(f"Deleted '{name}'")
            return
        if get_data()["set_all_private_BOOL"]:
            private = True
        resp = create_repo(name, desc, private)
        info = resp.json()
        if resp.status_code == 201:
            print(f"Created '{name}'")
        elif resp.status_code == 409 or resp.status_code == 400:
            print(f"Repo '{name}' already exists")
            if "id" in info:
                set_data("proj_id", info["id"])
            info = get_repo(name).json()
        else:
            raise Exception(
                f"Failed to create '{name}' (status code {resp.status_code}), {resp.text}"
            )
        if get_private(info) is None:
            print(f"Failed to get '{name}' info")
            return
        if private != get_private(info):
            print(f"Making '{name}' visibility to {private}")
            resp = make_private(name, private)
            if resp.status_code == 200:
                print(f"Changed '{name}' visibility to {private}")
            else:
                print(
                    f"Failed to change '{name}' visibility to {private} (status code {resp.status_code}, {resp.text})"
                )

        if not get_data()["force_push_BOOL"] and "size" in info and info["size"] > 0:
            print(f"Repo '{name}' is not empty - skipping push")
            return
        with tempfile.TemporaryDirectory() as tmpdirname:
            chdir(tmpdirname)
            repo = Repo.clone_from(
                f"git@github.com:{get_data()['username']}/{name}", tmpdirname
            )
            next_repo_url = f"git@{get_data()['site']}:{get_data()['username_next_site']}/{name}.git"
            name_site = get_data()["site"].split(".")[0]
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
