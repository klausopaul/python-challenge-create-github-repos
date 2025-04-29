import os
import sys
import argparse
import subprocess
import json


def cls():
    """
    cls Function that clears the screen, abstracting the underlying OS
    """
    os.system("cls" if os.name == "nt" else "clear")


def add_prefix(repo_name):
    PREFIX = "python-challenge-"
    repo_name = PREFIX + repo_name

    return repo_name


def print_parameters(folder_name, repo_name, repo_desc, repo_visibility):
    print("Data to be used to configure repos locally and remotely: ")
    print(f"   Folder name: {folder_name}")
    print(f"   Repo name: {repo_name}")
    print(f"   Repo desc: {repo_desc}")
    print(f"   Repo visibility: {repo_visibility}", end="\n\n")


def argument_parser():
    """
    argument_parser Validates and process the parameters passed to the script

    Returns:
        folder_name: lowercase folder name passed as parameter
        repo_desc: lowercase description for the repo
        repo_visibility: lowercase visibility of the repo. Values are public (default) or private
        repo_name: lowercased, prefixed, striped of "." repo name, taken from folder name parameter
    """
    parser = argparse.ArgumentParser(
        description="""
                    This script creates and initializes a local repo, and, also 
                    a Github repo and set it as the remote. 
                    """
    )
    parser.add_argument(
        "-f",
        "--folder_name",
        type=str,
        help="Folder will be created and local repo initialize in it",
    )
    parser.add_argument(
        "-rd",
        "--repo_desc",
        type=str,
        help="Description for both local and remote repo. Must be between single or double quotes",
    )
    parser.add_argument(
        "-rv",
        "--repo_visibility",
        type=str,
        help="Repo visibility: Public or Private. Default to Public if not informed",
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)  # Exit with a non-zero code to indicate abnormal usage
    else:
        folder_name = ""
        if args.folder_name is not None:
            folder_name = args.folder_name.lower()

        repo_desc = ""
        if args.repo_desc is not None:
            repo_desc = args.repo_desc[0].title() + args.repo_desc[1:]

        if args.repo_visibility is not None:
            repo_visibility = args.repo_visibility.lower()
        else:
            repo_visibility = "Public".lower()

        repo_name = add_prefix(folder_name.split(".")[1].lower())

    return folder_name, repo_name, repo_desc, repo_visibility


def run_command(cmd, pCWD=None):
    """
    run_command Generic function that takes the command passed and runs it with subprocess.run

    Args:
        cmd (list with the commands to run on OS level): executes the command passed in the OS, using subprocess.run

    Returns:
        boolean: Returns True if execution was successful, otherwise returns False
    """
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=pCWD)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run command {cmd}")
        print(f"Exception: {e}")
        print("STERR", e.stderr)
        print("STOUT", e.stdout)
        return False
    except Exception as ex:
        print(f"❌ Unexpected error while running command {cmd}. Error: {ex}")


def is_logged_to_gh():
    print("▶️  Checking if user is logged to GitHub cli tool...", end="\n\n")
    command = ["gh", "auth", "status"]
    # If run_command returns True, the user is logged into GitHub
    return run_command(command)


def create_gh_repo(repo_name, repo_desc, repo_visibility):
    print(
        f"▶️  Creating GitHub Repo for {repo_name} with visibility as {repo_visibility} and description as '{repo_desc}'",
        end="\n\n",
    )
    command = [
        "gh",
        "repo",
        "create",
        repo_name,
        "--" + repo_visibility,
        "--description",
        repo_desc,
        "--clone",
        "--disable-wiki",
    ]

    if run_command(command):
        # If run_command returns True, the repo was created
        return True
    else:
        return False


def configure_basic_repo_settings(repo_name):
    print(
        f"▶️  Configuring basic repo settings for {repo_name}",
        end="\n\n",
    )
    try:
        cmd = [
            "gh",
            "repo",
            "edit",
            "--enable-projects=false",
            "--delete-branch-on-merge",
        ]

        if run_command(cmd, "./" + repo_name):
            # If run_command returns True, the repo was created
            print("✅ Repository updated successfully", end="\n\n")
            return True
        else:
            return False

    except subprocess.CalledProcessError as e:
        print("❌ Failed to update repository settings.")
        print("STDERR:", e.stderr)
        print("STOUT", e.stdout)
    except Exception as ex:
        print("❌ Unexpected error while updating repository settings:", str(ex))


def set_branch_protection(repo_name):
    print(f"▶️  Setting branch protection for {repo_name}", end="\n\n")
    try:
        # Step 1: Get the owner/name of the current repository
        get_repo_cmd = [
            "gh",
            "repo",
            "view",
            "--json",
            "owner,name",
            "-q",
            '.owner.login + "/" + .name',
        ]
        repo_full_name = subprocess.check_output(
            get_repo_cmd, text=True, cwd="./" + repo_name
        ).strip()

        owner = repo_full_name.split("/")[0]
        repo = repo_full_name.split("/")[1]

        # Step 2: Define the branch protection settings as a Python dictionary
        protection_settings = {
            "required_status_checks": None,
            "enforce_admins": False,
            "required_pull_request_reviews": {"required_approving_review_count": 1},
            "restrictions": None,
            "allow_force_pushes": False,
            "allow_deletions": False,
        }

        # Convert the dictionary to a JSON string
        json_payload = json.dumps(protection_settings)

        # Step 3: Send the PUT request using gh api
        patch_cmd = [
            "gh",
            "api",
            f"repos/{owner}/{repo}/branches/main/protection",
            "--method",
            "PUT",
            "--input",
            "-",  # Read input from stdin
        ]

        # Run the subprocess, sending the JSON payload to stdin
        result = subprocess.run(
            patch_cmd,
            input=json_payload,
            text=True,
            capture_output=True,
            check=True,
            cwd="./" + repo_name,
        )

        print("✅ Branch protection updated successfully", end="\n\n")
        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print("❌ Failed to update branch protection.")
        print("STDERR:", e.stderr)
        print("STOUT", e.stdout)
    except Exception as ex:
        print("❌ Unexpected error while updating branch protection:", str(ex))


def init_repo(repo_name, repo_desc):
    branch_name = "main"
    readme_file = "README.md"

    # Get the owner/name of the current repository
    get_repo_cmd = [
        "gh",
        "repo",
        "view",
        "--json",
        "owner,name",
        "-q",
        '.owner.login + "/" + .name',
    ]

    repo_full_name = subprocess.check_output(
        get_repo_cmd, text=True, cwd="./" + repo_name
    ).strip()

    # Append to README.md
    readme_file_path = "./" + repo_name + "/" + readme_file

    with open(readme_file_path, "a", encoding="utf-8") as f:
        f.write(f"{repo_desc}\n")
    print(f"✅ {readme_file} has been initialized", end="\n\n")

    # Add README.md
    if run_command(["git", "add", readme_file], pCWD="./" + repo_name):
        print(f"✅ {readme_file} has been added to the repo", end="\n\n")

        # Commit changes
        if run_command(
            ["git", "commit", "-m", "Initial commit"], pCWD="./" + repo_name
        ):
            print(f"✅ Initial commit has been completed", end="\n\n")

            # Rename branch to main
            if run_command(["git", "branch", "-M", branch_name], pCWD="./" + repo_name):
                print(f"✅ Branch has been set to {branch_name}", end="\n\n")

                # Push changes to remote
                if run_command(
                    ["git", "push", "origin", "main"], pCWD="./" + repo_name
                ):
                    print(f"✅ Commit has been pushed to remote", end="\n\n")
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return False


def rename_folder(repo_name, folder_name):
    print(f"▶️  Renaming folder from {repo_name} to {folder_name}", end="\n\n")
    cmd = ["mv", repo_name, folder_name]
    if run_command(cmd):
        return True
    else:
        return False


def main():
    folder_name, repo_name, repo_desc, repo_visibility = argument_parser()

    print_parameters(folder_name, repo_name, repo_desc, repo_visibility)

    if is_logged_to_gh():
        print("✅ You are logged into GitHub CLI. Continuing...", end="\n\n")
        if create_gh_repo(
            repo_name=repo_name,
            repo_desc=repo_desc,
            repo_visibility=repo_visibility,
        ):
            if configure_basic_repo_settings(repo_name):
                if init_repo(repo_name, repo_desc):
                    if rename_folder(repo_name, folder_name):
                        print("✅ Done", end="\n\n")
                    # if set_branch_protection(repo_name):
        else:
            print("❌ Something went wrong", end="\n\n")
    else:
        print(
            "❌ You are NOT logged into GitHub CLI. Log via gh first and try again",
            end="\n\n",
        )


if __name__ == "__main__":
    cls()
    main()
