#!/usr/bin/env python3
"""
Script to install or update an RPM package from github
"""

from pathlib import Path
import requests
import tempfile
import subprocess
import sys
import argparse
import shlex
from packaging.version import Version

parser = argparse.ArgumentParser(
                    prog='update-rpm-github',
                    description='Fetch the latest release RPM of a package from Github. Install it.',)
parser.add_argument("repo", help="Owner and repository name. Example: 'lapce/lapce'", type=str)
parser.add_argument("-f", "--file_selector", help="A substring to be found in the release file name. Example: ", default=".rpm", type=str, required=False)
parser.add_argument("-d", "--redownload", help="Whether to redownload the RPM if it is already downloaded", default=False, action="store_true")
parser.add_argument("-i", "--reinstall", help="Whether to reinstall if the same package version is already installed", default=False, action="store_true")

args = parser.parse_args()
try:
    owner, repo = args.repo.split("/")[-2:]
except Exception as e:
    print(e)
    print("Invalid owner + repo: ", args.repo)

file_selector = args.file_selector
redownload = args.redownload
reinstall = args.reinstall

url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

resp = requests.get(url)
js = resp.json()
version = js['tag_name'][1:]
try:
    release = next(x for x in js['assets'] if file_selector in x['name'])
except StopIteration:
    names = "\n".join([x['name'] for x in js['assets']])
    print(f"{file_selector=} not found. Available options:\n{names}")
    sys.exit(1)
url = release['browser_download_url']
fname = release['name']
path = Path(tempfile.gettempdir()) / fname

# Check if file exists to avoid redownload
if path.exists():
    if redownload:
        download = True
    else:
        download = False
else:
    download = True

if download == True:
    print(f"Downloading {url} to {path}")
    resp = requests.get(url)
    with open(path, "wb") as fil:
        fil.write(resp.content)


# Find the name of the package after install
package_name = subprocess.run('rpm -qp --queryformat "%{NAME}" ' + str(path), shell=True, capture_output=True, text=True).stdout

# Check if package is already installed, and find the version number of it
cmd_result = subprocess.run("rpm --queryformat '%{VERSION}\n' -q "+ package_name, shell=True, capture_output=True, text=True)
installed_versions = cmd_result.stdout.splitlines()

install = True
if len(installed_versions) == 1:
    installed_version = installed_versions[0]
    rpm_version = subprocess.run('rpm -qp --queryformat "%{VERSION}" ' + str(path), shell=True, capture_output=True, text=True).stdout
    if Version(installed_version) < Version(rpm_version):
        install = True
    elif Version(installed_version) == Version(rpm_version):
        if reinstall:
            install = True
        else:
            print(f"Version {installed_version} already installed; not installing.")
            install = False
    else:
        print(f"Installed version {installed_version} newer than downloaded version {rpm_version}; not installing.")

if install:
    cmd = ['sudo', '-S', 'dnf', 'install', '--assumeyes', str(path)]
    cmd_s = shlex.join(cmd)
    print("Installing ...")
    print(cmd_s)
    subprocess.call(cmd)
