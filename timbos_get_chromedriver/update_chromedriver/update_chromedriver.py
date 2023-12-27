import logging
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import requests

logger = logging.getLogger(__name__)


platform_to = {
    "chrome_browser_executable": {
        "linux": "google-chrome-stable",
        "windows": "chrome.exe",
    },
    "chrome_version_invocation": {
        "linux": ["google-chrome-stable", "--version"],
        "windows": ["where", "chrome.exe"],
    },
    "chromedriver_executable": {
        "linux": "chromedriver",
        "windows": "chromedriver.exe",
    },
    "chromedriver_subdir_name": {
        "linux": "chromedriver-linux64",
        "windows": "chromedriver-win64",
    },
    "google_platform_designation": {
        "linux": "linux64",
        "windows": "win64",
    },
    "which_where_success_response": {
        "linux": "google-chrome-stable",
        "windows": "chrome.exe",
    },
    "which_where_invocation": {
        "linux": ["which", "google-chrome-stable"],
        "windows": ["powershell", "-c", "Get-Command", "chrome.exe"],
    },
    "zip_filename": {
        "linux": "chromedriver-linux64.zip",
        "windows": "chromedriver-win64.zip",
    },
}


def chrome_browser_available_on_path(platform=None) -> bool:
    if platform not in platform_to["which_where_success_response"].keys():
        raise Exception(f"Unsupported platform: {platform}.")
    try:
        _ = get_subprocess_output(platform_to["which_where_invocation"][platform])
        return True
    except subprocess.CalledProcessError as exc:
        return False


def download_binary_file(url: str, path: str) -> None:
    response = requests.get(url)
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def get_chrome_browser_version(platform=None) -> str:
    if platform not in ["linux", "windows"]:
        raise Exception(f"Unsupported platform: {platform}.")

    ver = None
    if platform == "windows":
        cmd = [
            "reg",
            "query",
            "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Google Chrome",
        ]
        result = get_subprocess_output(cmd)
        lines = str.splitlines(result)
        for l in lines:
            if "DisplayVersion" in l:
                ver = l.split("REG_SZ")[1].strip()
                break
    elif platform == "linux":
        cmd = [
            "google-chrome-stable",
            "--version",
        ]
        result = get_subprocess_output(cmd)
        ver = result.split("Chrome")[1].strip()

    if ver and is_a_version_number(ver):
        return ver
    else:
        return None


def get_platform() -> str:
    platform = sys.platform
    if platform.startswith("win32"):
        return "windows"
    elif platform.startswith("linux"):
        return "linux"
    elif platform == "darwin":
        return "mac"
    else:
        raise Exception(f"Unsupported platform: {sys.platform=}, {os.name=}.")


def get_subprocess_output(args: list[str]) -> str:
    return subprocess.check_output(args).decode("utf-8").strip()


def is_a_version_number(s: str) -> bool:
    return bool(re.match(r"^[\d.]+$", s))


def match_chromedriver_to_chrome_browser(chromedrivers_base_path=None) -> None:
    if not chromedrivers_base_path:
        temp_dir = tempfile.mkdtemp()
        chromedrivers_base_path = os.path.join(temp_dir, "bin", "chromedrivers")

    config_path_to_chromedriver = None

    platform = get_platform()

    # determine whether chrome browser is available on path, and what version
    system_chrome_browser = {}
    if chrome_browser_available_on_path(platform=platform):
        if ver := get_chrome_browser_version(platform=platform):
            system_chrome_browser["version"] = ver
            system_chrome_browser["major_version"] = int(ver.split(".")[0])

        else:
            raise Exception(
                f"Cannot determine version of the {platform_to['chrome_browser_executable'][platform]} on path."
            )
    else:
        raise Exception(
            f"Cannot find {platform_to['chrome_browser_executable'][platform]} on path."
        )

    logger.info(
        f"Found {platform_to['chrome_browser_executable'][platform]} {system_chrome_browser['version']} on path"
    )

    # determine what versions of chromedriver are available locally
    try:
        os.makedirs(chromedrivers_base_path)
    except FileExistsError:
        pass
    except PermissionError as exc:
        raise Exception(f"Error: {repr(exc)}")

    local_chromedrivers_major_version_to_version = None
    all_files_and_dirs = os.listdir(chromedrivers_base_path)
    subdirs = [
        d
        for d in all_files_and_dirs
        if os.path.isdir(os.path.join(chromedrivers_base_path, d))
    ]
    # subdir names need to be version numbers, so remove any that aren't
    subdirs = list(filter(lambda x: is_a_version_number(x), subdirs))

    # subdirs need to contain the correct subsubdir by platform
    subdirs = list(
        filter(
            lambda x: os.path.isdir(
                os.path.join(
                    chromedrivers_base_path,
                    x,
                    platform_to["chromedriver_subdir_name"][platform],
                )
            ),
            subdirs,
        )
    )

    if not subdirs:
        logger.info(
            f"No {platform_to['google_platform_designation'][platform]} chromedrivers found under {chromedrivers_base_path}."
        )

    local_chromedriver_versions = subdirs

    # next, determine if we have a local chromedriver of a suitable version
    local_chromedriver_chosen_version = {}

    # case: check if browser full version matches a local chromedriver full version
    if system_chrome_browser["version"] in local_chromedriver_versions:
        local_chromedriver_chosen_version["version"] = system_chrome_browser["version"]
        local_chromedriver_chosen_version["path"] = os.path.join(
            chromedrivers_base_path,
            local_chromedriver_chosen_version["version"],
            platform_to["chromedriver_subdir_name"][platform],
            platform_to["chromedriver_executable"][platform],
        )
        config_path_to_chromedriver = local_chromedriver_chosen_version["path"]

        logger.info(
            f"Using existing {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} at {local_chromedriver_chosen_version['path']}"
        )
        return config_path_to_chromedriver

    # case: check if browser major version matches a local chromedriver major version
    local_chromedrivers_major_version_to_version = {
        K: V
        for K, V in zip(
            [int(x.split(".")[0]) for x in local_chromedriver_versions],
            local_chromedriver_versions,
        )
    }
    if (
        system_chrome_browser["major_version"]
        in local_chromedrivers_major_version_to_version.keys()
    ):
        local_chromedriver_chosen_version[
            "version"
        ] = local_chromedrivers_major_version_to_version[
            system_chrome_browser["major_version"]
        ]
        local_chromedriver_chosen_version["path"] = os.path.join(
            chromedrivers_base_path,
            local_chromedriver_chosen_version["version"],
            platform_to["chromedriver_subdir_name"][platform],
            platform_to["chromedriver_executable"][platform],
        )
        config_path_to_chromedriver = local_chromedriver_chosen_version["path"]

        logger.info(
            f"Using existing {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} at {local_chromedriver_chosen_version['path']}"
        )
        return config_path_to_chromedriver

    # invariant now: system chrome browser doesn't match any local chromedriver
    logger.info(
        f"Did not find any local chromedrivers with appropriate version for system Chrome browser. Will check online..."
    )

    # case: check if there's a downloadable chromedriver of same major version as chrome browser major version
    # if so, download that version of chromedriver

    google_json_endpoint = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    try:
        response = requests.get(google_json_endpoint)
    except Exception as exc:
        raise Exception(
            f"Cannot resolve url {google_json_endpoint} to find a compatible version of {platform_to['chromedriver_executable'][platform]}: {exc}. Exiting."
        )

    if response.status_code != 200:
        raise Exception(
            f"Cannot resolve url {google_json_endpoint} to find a compatible version of {platform_to['chromedriver_executable'][platform]}: {exc}. Exiting."
        )

    json = response.json()

    # first, try to find an exact match of versions
    for each_version in json["versions"]:
        if (
            "version" in each_version
            and each_version["version"] == system_chrome_browser["version"]
            and "downloads" in each_version
            and "chromedriver" in each_version["downloads"]
        ):
            for each_chromedriver in each_version["downloads"]["chromedriver"]:
                if (
                    each_chromedriver["platform"]
                    == platform_to["google_platform_designation"][platform]
                ):
                    download_url = each_chromedriver["url"]

                    # download this version of chromedriver
                    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                        download_binary_file(
                            download_url, os.path.join(tmp, "chromedriver.zip")
                        )
                        with zipfile.ZipFile(
                            os.path.join(tmp, "chromedriver.zip"), "r"
                        ) as z:
                            z.extractall(
                                os.path.join(
                                    chromedrivers_base_path,
                                    each_version["version"],
                                )
                            )

                    local_chromedriver_chosen_version["version"] = each_version[
                        "version"
                    ]

                    local_chromedriver_chosen_version["path"] = os.path.join(
                        chromedrivers_base_path,
                        local_chromedriver_chosen_version["version"],
                        platform_to["chromedriver_subdir_name"][platform],
                        platform_to["chromedriver_executable"][platform],
                    )
                    # on linux, ensure that the new chromedriver is executable
                    if platform == "linux":
                        os.chmod(
                            local_chromedriver_chosen_version["path"],
                            os.stat(local_chromedriver_chosen_version["path"]).st_mode
                            | 0o111,
                        )
                        config_path_to_chromedriver = local_chromedriver_chosen_version[
                            "path"
                        ]

                    logger.info(
                        f"Downloaded {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} to {local_chromedriver_chosen_version['path']}"
                    )

                    logger.info(
                        f"Found {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} at {local_chromedriver_chosen_version['path']}"
                    )
                    return config_path_to_chromedriver

    # invariant now: we didn't find an exact match of versions online

    # so, try to find the highest version of chromedriver that's less than or equal to the system chrome browser version
    json_versions = list(json["versions"])
    for i, each_version in enumerate(json_versions):
        if each_version["version"] > system_chrome_browser["version"]:
            desired_version = json_versions[i - 1]
            local_chromedriver_chosen_version["version"] = desired_version["version"]
            for each_chromedriver in desired_version["downloads"]["chromedriver"]:
                if (
                    each_chromedriver["platform"]
                    == platform_to["google_platform_designation"][platform]
                ):
                    download_url = each_chromedriver["url"]

                    # download this version of chromedriver
                    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                        download_binary_file(
                            download_url,
                            os.path.join(tmp, "chromedriver.zip"),
                        )
                        with zipfile.ZipFile(
                            os.path.join(tmp, "chromedriver.zip"), "r"
                        ) as z:
                            z.extractall(
                                os.path.join(
                                    chromedrivers_base_path,
                                    local_chromedriver_chosen_version["version"],
                                )
                            )
                        logger.info(
                            f"Downloaded {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} from {each_chromedriver['url']}"
                        )

                    local_chromedriver_chosen_version["path"] = os.path.join(
                        chromedrivers_base_path,
                        local_chromedriver_chosen_version["version"],
                        platform_to["chromedriver_subdir_name"][platform],
                        platform_to["chromedriver_executable"][platform],
                    )
                    # on linux, ensure that the new chromedriver is executable
                    if platform == "linux":
                        os.chmod(
                            local_chromedriver_chosen_version["path"],
                            os.stat(local_chromedriver_chosen_version["path"]).st_mode
                            | 0o111,
                        )

                    config_path_to_chromedriver = local_chromedriver_chosen_version[
                        "path"
                    ]
                    logger.info(
                        f"Using downloaded {platform_to['chromedriver_executable'][platform]} {local_chromedriver_chosen_version['version']} at {local_chromedriver_chosen_version['path']}"
                    )
                    return config_path_to_chromedriver

    # invariant now: we couldn't find any downloadable chromedriver matching the system chrome browser version

    raise Exception(
        f"Cannot find a {platform_to['chromedriver_executable'][platform]} version for chrome browser version {system_chrome_browser['major_version']} locally or in {google_json_endpoint}."
    )
