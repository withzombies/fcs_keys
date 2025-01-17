#! /usr/bin/env python3

import hashlib
import os
import re
import requests
import shutil
import subprocess
import tempfile

# Check if appledb has an update, if not bail
# Get info on all ipsws
# Download new keys

SUPPORTED_OSES = ["iOS", "iPadOS"]
MIN_BUILD_VER = 22
KEYS_DIR = "keys"


def update_fcs_keys_json():
    for apple_os in ["iOS", "iPadOS", "macOS"]:
        print(f"Updating fcs_keys.json for {apple_os}")
        subprocess.check_call(["ipsw", "dl", "appledb", "--os", apple_os, "--fcs-keys-json", "--latest", "--confirm"])


def download_build_keys(apple_os: str, build: str):
    os_dir = f"{KEYS_DIR}/{apple_os}"
    os.makedirs(os_dir, exist_ok=True)

    key_dir = f"{os_dir}/{build}"

    if os.path.exists(key_dir):
        # Already downloaded/attempted, ignore
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

        for root, _dirs, files in os.walk(tempdir):
            for file in sorted(files):
                if file.endswith(".pem"):
                    os.makedirs(key_dir, exist_ok=True)
                    # The filename that 'ipsw' has used suggests it only applies to a specific
                    # .dmg, but it seems to apply to the entire set. So instead we'll store this
                    # as a hash so that we don't store duplicates and we don't give off the
                    # impression it's only for one file
                    with open(f"{root}/{file}", "rb") as f:
                        new_filename = hashlib.md5(f.read()).hexdigest()
                        shutil.copy(f"{root}/{file}", f"{key_dir}/{new_filename}.pem")

        if os.path.exists(key_dir) is False:
            # There were no keys obtained, create a file to indicate a successful attempt
            open(key_dir, "w").close()


def main():
    r = requests.get("https://api.appledb.dev/ios/index.json")
    r.raise_for_status()

    for entry in r.json():
        apple_os, build = entry.split(";", 1)
        if apple_os in SUPPORTED_OSES:
            match = re.match(r"(\d+)", build)
            if match:
                major = int(match.group(1))
                if major >= MIN_BUILD_VER:
                    download_build_keys(apple_os, build)


if __name__ == "__main__":
    main()
