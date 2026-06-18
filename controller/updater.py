# ===== controller/updater.py =====

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.logger import get_logger

logger = get_logger("updater")


def get_current_version() -> str:
    version_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "build",
        "version.json",
    )
    try:
        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


def check_for_update() -> bool:
    try:
        import requests

        current = get_current_version()
        logger.info(f"Current version: {current}")

        version_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "build",
            "version.json",
        )
        repo_owner = "yourrepo"
        repo_name = "render-agent"
        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                data = json.load(f)
            url_path = data.get("controller_url", "")
            if "github.com" in url_path:
                parts = url_path.split("github.com/")[1].split("/")
                if len(parts) >= 2:
                    repo_owner = parts[0]
                    repo_name = parts[1]

        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        resp = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code != 200:
            logger.debug(f"GitHub API returned {resp.status_code}")
            return False

        release = resp.json()
        remote_version = release.get("tag_name", "").lstrip("v")

        if not remote_version:
            return False

        def parse_version(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except Exception:
                return (0, 0, 0)

        if parse_version(remote_version) > parse_version(current):
            logger.info(f"Update available: {current} -> {remote_version}")
            return True

        return False
    except Exception:
        import traceback

        logger.debug(f"Update check failed: {traceback.format_exc()}")
        return False


def start_background_check(interval_seconds: int = 3600) -> None:
    import threading

    def _loop():
        time.sleep(10)
        while True:
            try:
                check_for_update()
            except Exception:
                import traceback

                logger.debug(f"Background update check error: {traceback.format_exc()}")
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info(f"Auto-updater background check started (every {interval_seconds}s)")