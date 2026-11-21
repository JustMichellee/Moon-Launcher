"""
Centralized path and resource resolution for Moon Launcher (GUI & CLI).
Works identically in:
  1. Modular development mode (running from src/ inside the repo root)
  2. Portable frozen .exe mode (PyInstaller CLI / GUI executables)
  3. System-installed mode (e.g. Program Files -> user data in %LOCALAPPDATA%)
"""

import json
import os
import shutil
import sys

APP_DIR_NAME = "MoonLauncher"


def get_src_dir():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """Directory containing bundled read-only assets (gui/, assets/, templates/)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(get_src_dir())


def _is_dir_writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".moon_write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def get_base_dir():
    """Writable directory for user configs, versions, skins, runtime, and logs."""
    env_home = os.environ.get("MOON_LAUNCHER_HOME", "").strip()
    if env_home:
        os.makedirs(env_home, exist_ok=True)
        return os.path.abspath(env_home)

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if _is_dir_writable(exe_dir):
            return exe_dir
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        fallback_dir = os.path.join(local_app, APP_DIR_NAME)
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    return os.path.dirname(get_src_dir())


SRC_DIR = get_src_dir()
RESOURCE_DIR = get_resource_dir()
BASE_DIR = get_base_dir()

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")
GUI_DIR = os.path.join(RESOURCE_DIR, "gui")
TEMPLATES_DIR = os.path.join(RESOURCE_DIR, "templates")

VERSIONS_DIR = os.path.join(BASE_DIR, "versions")
SKINS_DIR = os.path.join(BASE_DIR, "skins")
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
CACHE_DIR = os.path.join(BASE_DIR, ".moon_cache")
CONFIG_PATH = os.path.join(BASE_DIR, "launcher_config.json")
ACCOUNTS_PATH = os.path.join(BASE_DIR, "accounts.json")
FRIENDS_PATH = os.path.join(BASE_DIR, "friends.json")
VERSION_FILE = os.path.join(BASE_DIR, "version.json")

DEFAULT_CONFIG = {
    "username": "Player",
    "version_name": "",
    "ram_max_gb": 4,
    "ram_min_gb": 1,
    "width": 1280,
    "height": 720,
    "fullscreen": False,
    "discord_rpc": True,
    "jvm_g1gc_preset": True,
}

DEFAULT_FRIENDS = {
    "friends": [],
    "servers": [],
}


def resolve_resource(*parts):
    """Find a resource inside BASE_DIR first (user override), then RESOURCE_DIR."""
    candidate_base = os.path.join(BASE_DIR, *parts)
    if os.path.exists(candidate_base):
        return candidate_base
    candidate_res = os.path.join(RESOURCE_DIR, *parts)
    if os.path.exists(candidate_res):
        return candidate_res
    return candidate_base


def ensure_user_workspace():
    """Initialize required runtime directories and default config files for new users."""
    for d in (VERSIONS_DIR, SKINS_DIR, RUNTIME_DIR, LOGS_DIR, CACHE_DIR):
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass

    if not os.path.exists(FRIENDS_PATH):
        try:
            with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_FRIENDS, f, indent=2)
        except Exception:
            pass

    # Seed default Player skin if user has no active skin yet
    active_skin = os.path.join(SKINS_DIR, "active_skin.png")
    if not os.path.exists(active_skin):
        default_skin = resolve_resource("skins", "Player.png")
        if os.path.exists(default_skin):
            try:
                shutil.copy2(default_skin, active_skin)
            except Exception:
                pass

