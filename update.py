#! /usr/bin/env python3

import os
import requests
import shutil
import subprocess
import tempfile
import traceback

# Check if appledb has an update, if not bail
# Get info on all ipsws
# Download new keys

REPO_OWNER = "littlebyteorg"
REPO_NAME = "appledb"
SUPPORTED_OSES = ["iOS", "iPadOS"]
MIN_BUILD_VER = 22
KEYS_DIR = "keys"


def get_last_known_commit() -> str:
    try:
        with open("last_commit", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def set_last_known_commit(commit: str):
    with open("last_known_commit", "w") as f:
        f.write(commit)


def query_current_commit():
    r = requests.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/main")
    r.raise_for_status()

    return r.json()["sha"]


def process_update():
    # First get ipsw to download appledb
    subprocess.check_output(
        [
            "ipsw",
            "dl",
            "appledb",
            "--os",
            "iOS",
            "--latest",
            "--urls",
        ]
    )

    # Then look at the repo it downloaded to get the build identifiers
    repo_dir = f"{os.environ['HOME']}/.config/ipsw/appledb"

    for apple_os in SUPPORTED_OSES:
        versions_dir = f"{repo_dir}/osFiles/{apple_os}/"
        for version in sorted(os.listdir(versions_dir)):
            major = int(version.split("x", 1)[0])
            if major >= MIN_BUILD_VER:
                process_build(apple_os, f"{versions_dir}/{version}")


def process_build(apple_os: str, version_dir: str):
    for version in sorted(os.listdir(version_dir)):
        if version.endswith(".json"):
            build = version.rsplit(".", 1)[0]

            try:
                download_build_keys(apple_os, build)
            except subprocess.CalledProcessError:
                traceback.print_exc()


def download_build_keys(apple_os: str, build: str):
    key_dir = f"{KEYS_DIR}/{apple_os}/{build}"

    if os.path.exists(key_dir):
        # Already downloaded, ignore
        return

    with tempfile.TemporaryDirectory() as tempdir:
        print(f"Build {build}")
        subprocess.check_call(
            [
                "ipsw",
                "dl",
                "appledb",
                "--os",
                apple_os,
                "--build",
                build,
                "--fcs-keys",
                "--output",
                tempdir,
                "--confirm",
            ]
        )

        os.makedirs(key_dir, exist_ok=True)
        for root, _dirs, files in os.walk(tempdir):
            for file in sorted(files):
                if file.endswith(".pem"):
                    shutil.copy(f"{root}/{file}", key_dir)


def main():
    current_commit = query_current_commit()
    last_known_commit = get_last_known_commit()

    if current_commit != last_known_commit:
        process_update()

        set_last_known_commit(current_commit)
    else:
        print("No new updates")


if __name__ == "__main__":
    main()
