#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moon Launcher Auto-Updater Engine
Provides seamless 1-click updates from GitHub repository without manual reinstall or system conflicts.
Preserves 100% of player settings, saves, skins, custom configs, and modpacks.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import hashlib
import py_compile
import subprocess
import re
import threading

# ANSI Colors
C_BORDER  = '\033[38;2;60;70;90m'
C_AMBER   = '\033[38;2;245;158;11m'
C_GREEN   = '\033[38;2;74;222;128m'
C_CYAN    = '\033[38;2;56;189;248m'
C_PURPLE  = '\033[38;2;168;85;247m'
C_BLUE    = '\033[38;2;96;165;250m'
C_RED     = '\033[38;2;248;113;113m'
C_WHITE   = '\033[38;2;241;245;249m'
C_MUTED   = '\033[38;2;148;163;184m'
CLR_RESET = '\033[0m'

REPO_OWNER = "JustMichellee"
REPO_NAME = "Moon-Launcher"
BRANCH = "main"

API_COMMITS_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
API_TREE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{BRANCH}?recursive=1"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.json")

# Protected files & directories that must NEVER be overwritten or touched
PROTECTED_EXACT = {
    "launcher_config.json",
    "launcher_config.json.user_backup",
    "launcher_profiles.json",
    "config.json",
    "friends.json",
    "options.txt",
    "servers.dat"
}

PROTECTED_PREFIXES = (
    "versions/", "versions\\",
    "skins/", "skins\\",
    "mods/", "mods\\",
    "libraries/", "libraries\\",
    "assets/indexes/", "assets/indexes\\",
    "assets/objects/", "assets/objects\\",
    "saves/", "saves\\",
    "logs/", "logs\\",
    "backups/", "backups\\",
    "resourcepacks/", "resourcepacks\\",
    "shaderpacks/", "shaderpacks\\",
    ".git/", ".git\\"
)

UPDATABLE_CORE_FILES = [
    "launcher.py",
    "network_hub.py",
    "updater.py",
    "Moon Launcher.bat",
    "version.json",
    "README.md"
]

# Global cache for background checker
CACHED_UPDATE_INFO = None
CACHED_UPDATE_LOCK = threading.Lock()

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(text))

def get_visible_width(text):
    return len(strip_ansi(text))

def render_box(lines, width=68, title=None):
    content_lines = []
    for l in lines:
        s = strip_ansi(str(l)).strip()
        is_div = len(s) > 0 and all(c in '─-=' for c in s)
        if not is_div:
            content_lines.append(l)

    t_len = get_visible_width(f" {title} ") if title else 0
    max_c_w = max([get_visible_width(l) for l in content_lines] + [t_len + 2, width - 4])
    width = max(width, max_c_w + 4)

    top = f"{C_BORDER}╭{'─' * (width - 2)}╮{CLR_RESET}"
    bottom = f"{C_BORDER}╰{'─' * (width - 2)}╯{CLR_RESET}"
    out = [top]
    if title:
        v_title = f" {title} "
        out[0] = f"{C_BORDER}╭─{C_WHITE}\033[1m{v_title}{CLR_RESET}{C_BORDER}{'─' * max(0, width - 4 - t_len)}╮{CLR_RESET}"

    for l in lines:
        s = strip_ansi(str(l)).strip()
        if len(s) > 0 and all(c in '─-=' for c in s):
            out.append(f"{C_BORDER}├{'─' * (width - 2)}┤{CLR_RESET}")
        else:
            v_w = get_visible_width(l)
            pad = max(0, width - 4 - v_w)
            out.append(f"{C_BORDER}│{CLR_RESET}  {l}{' ' * pad}{C_BORDER}│{CLR_RESET}")
    out.append(bottom)
    return "\n".join(out)

def calc_git_blob_sha(filepath):
    """Calculates git blob SHA with normalized LF line endings for accurate comparison."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "rb") as f:
            data = f.read().replace(b"\r\n", b"\n")
        return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    except Exception:
        return None

def is_protected(rel_path):
    """Checks if a file path belongs to the user and is strictly protected."""
    rel_clean = rel_path.replace("\\", "/").strip("/")
    base_name = os.path.basename(rel_clean)
    if rel_clean in PROTECTED_EXACT or base_name in PROTECTED_EXACT:
        return True
    if any(rel_clean.startswith(p.replace("\\", "/")) for p in PROTECTED_PREFIXES):
        return True
    if rel_clean.startswith(".git"):
        return True
    return False

def get_local_version_info():
    """Reads current local version and commit SHA."""
    data = {
        "version": "2.4.2",
        "commit_sha": "",
        "updated_at": "",
        "release_notes": ""
    }
    # 1. Check version.json
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8-sig") as f:
                saved = json.load(f)
                data.update(saved)
        except Exception:
            pass

    # 2. If commit_sha empty, try git rev-parse HEAD
    if not data.get("commit_sha"):
        git_dir = os.path.join(BASE_DIR, ".git")
        if os.path.exists(git_dir):
            try:
                res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and res.stdout.strip():
                    data["commit_sha"] = res.stdout.strip()
            except Exception:
                pass
    return data

def save_local_version_info(info):
    """Saves updated version info to version.json."""
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
        return True
    except Exception:
        return False

def fetch_remote_version_info(timeout=4.0):
    """
    Fetches the latest remote version info from GitHub.
    Uses GitHub API commits, with automatic fallback to Raw CDN version.json.
    """
    result = {
        "commit_sha": "",
        "version": "2.4.2",
        "message": "Latest Moon Launcher updates",
        "date": "",
        "author": "JustMichellee",
        "raw_tree": []
    }

    # 1. Try GitHub Commits API
    api_success = False
    try:
        req = urllib.request.Request(f"{API_COMMITS_URL}?_t={int(time.time())}", headers={"User-Agent": "Moon-Launcher-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            c_data = json.loads(resp.read().decode("utf-8"))
            result["commit_sha"] = c_data.get("sha", "")
            result["message"] = c_data.get("commit", {}).get("message", "").split("\n")[0]
            result["date"] = c_data.get("commit", {}).get("committer", {}).get("date", "")
            result["author"] = c_data.get("commit", {}).get("author", {}).get("name", "JustMichellee")
            api_success = True
    except Exception:
        pass

    # 2. Try Raw CDN version.json for version tag & notes
    try:
        raw_v_url = f"{RAW_BASE_URL}version.json?_t={int(time.time())}"
        req2 = urllib.request.Request(raw_v_url, headers={"User-Agent": "Moon-Launcher-Updater/1.0"})
        with urllib.request.urlopen(req2, timeout=timeout) as resp:
            v_data = json.loads(resp.read().decode("utf-8"))
            if v_data.get("version"):
                result["version"] = v_data.get("version")
            if v_data.get("release_notes"):
                result["message"] = v_data.get("release_notes")
            if not result["commit_sha"] and v_data.get("commit_sha"):
                result["commit_sha"] = v_data.get("commit_sha")
    except Exception:
        pass

    if not result["commit_sha"]:
        return None

    return result

def check_for_updates(timeout=3.5):
    """
    Checks if a newer commit or update is available on GitHub.
    Returns: dict with update details or None
    """
    local = get_local_version_info()
    remote = fetch_remote_version_info(timeout=timeout)
    if not remote:
        return None

    local_sha = local.get("commit_sha", "")
    remote_sha = remote.get("commit_sha", "")

    # If local SHA is known and matches remote SHA, check if core files match
    has_update = False
    if not local_sha:
        has_update = True
    else:
        s_len = min(len(local_sha), len(remote_sha), 7)
        if s_len >= 4 and local_sha[:s_len].lower() != remote_sha[:s_len].lower():
            has_update = True

    return {
        "update_available": has_update,
        "local_version": local.get("version", "2.4.2"),
        "local_sha": local_sha[:7] if local_sha else "unknown",
        "remote_version": remote.get("version", "2.4.2"),
        "remote_sha": remote_sha[:7] if remote_sha else "latest",
        "full_remote_sha": remote_sha,
        "message": remote.get("message", "New updates available"),
        "date": remote.get("date", "")
    }

def start_background_update_checker():
    """Starts a non-blocking background daemon thread to check for updates on startup."""
    def _worker():
        global CACHED_UPDATE_INFO
        try:
            info = check_for_updates(timeout=3.0)
            with CACHED_UPDATE_LOCK:
                CACHED_UPDATE_INFO = info
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def get_update_notice():
    """Returns a visual notification string if a background update was discovered."""
    with CACHED_UPDATE_LOCK:
        if CACHED_UPDATE_INFO and CACHED_UPDATE_INFO.get("update_available"):
            r_ver = CACHED_UPDATE_INFO.get("remote_version", "")
            r_sha = CACHED_UPDATE_INFO.get("remote_sha", "")
            return f"{C_AMBER}* [Update Available]{CLR_RESET} {C_WHITE}v{r_ver} ({r_sha}){CLR_RESET} {C_MUTED}from GitHub! Type {C_CYAN}/update{C_MUTED} to install.{CLR_RESET}"
    return ""

def download_file_with_progress(url, dest_path, desc=""):
    """Downloads a file and prints a clean progress percentage."""
    req = urllib.request.Request(f"{url}?_t={int(time.time())}", headers={"User-Agent": "Moon-Launcher-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=12.0) as resp:
        total_size = resp.getheader('Content-Length')
        total_size = int(total_size) if total_size else None

        downloaded = 0
        chunks = []
        while True:
            chunk = resp.read(16384)
            if not chunk:
                break
            chunks.append(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = int((downloaded / total_size) * 100)
                sys.stdout.write(f"\r  {C_CYAN}Downloading {desc}...{CLR_RESET} {C_WHITE}{pct}%{CLR_RESET} ({downloaded // 1024} KB)")
                sys.stdout.flush()

        if total_size:
            sys.stdout.write("\n")

    data = b"".join(chunks)
    with open(dest_path, "wb") as f:
        f.write(data)
    return len(data)

def apply_update_from_github(force=False):
    """
    Interactive full update procedure:
    1. Checks GitHub for differences.
    2. Displays update summary box.
    3. Prompts user confirmation.
    4. Downloads only updatable files (core scripts and templates), strictly skipping user data.
    5. Validates syntax via py_compile.
    6. Swaps files atomically with .bak backups.
    7. Seamlessly restarts launcher.
    """
    box_w = 68
    print(f"\n{C_CYAN}[Moon Updater] Connecting to GitHub repository (JustMichellee/Moon-Launcher)...{CLR_RESET}")

    check = check_for_updates(timeout=6.0)
    if not check:
        print(f"\n{C_RED}[Moon Updater] Could not connect to GitHub. Please check your internet connection.{CLR_RESET}\n")
        return False

    local_sha = check["local_sha"]
    remote_sha = check["remote_sha"]
    full_remote_sha = check["full_remote_sha"]
    remote_ver = check["remote_version"]
    msg = check["message"]
    has_update = check["update_available"]

    if not has_update and not force:
        lines = [
            f"{C_GREEN}\033[1mMoon Launcher is Already Up to Date!\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Active Version :{CLR_RESET} {C_CYAN}v{remote_ver} ({local_sha}){CLR_RESET}",
            f"  {C_WHITE}* Branch / Repo  :{CLR_RESET} {C_WHITE}main @ JustMichellee/Moon-Launcher{CLR_RESET}",
            f"  {C_WHITE}* Latest Commit  :{CLR_RESET} {C_MUTED}{msg}{CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"{C_MUTED}Tip: Use /update force to re-verify and refresh all core files.{CLR_RESET}"
        ]
        print("\n" + render_box(lines, box_w, title="Launcher Updater") + "\n")
        return True

    # Display update available box
    lines = [
        f"{C_AMBER}\033[1mNew Moon Launcher Update Available!\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"  {C_WHITE}* Current Version :{CLR_RESET} {C_RED}{local_sha}{CLR_RESET}",
        f"  {C_WHITE}* Latest on GitHub:{CLR_RESET} {C_GREEN}\033[1m{remote_sha} (v{remote_ver})\033[0m",
        f"  {C_WHITE}* Release Summary :{CLR_RESET} {C_WHITE}{msg}{CLR_RESET}",
        f"  {C_WHITE}* Target Branch   :{CLR_RESET} {C_CYAN}main{CLR_RESET}",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"{C_MUTED}Safe Update: 100% of your Minecraft saves, mods, skins & configs are preserved.{CLR_RESET}"
    ]
    print("\n" + render_box(lines, box_w, title="Launcher Updater") + "\n")

    ans = input(f"{C_WHITE}Do you want to download and apply this update now? [Y/n]: {CLR_RESET}").strip().lower()
    if ans not in ('', 'y', 'yes'):
        print(f"{C_MUTED}Update postponed.{CLR_RESET}\n")
        return False

    print(f"\n{C_CYAN}[Moon Updater] Fetching repository manifest from GitHub...{CLR_RESET}")

    # Determine files to update
    files_to_update = []
    try:
        req = urllib.request.Request(f"{API_TREE_URL}?_t={int(time.time())}", headers={"User-Agent": "Moon-Launcher-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            tree_data = json.loads(resp.read().decode("utf-8")).get("tree", [])

        for item in tree_data:
            if item.get("type") != "blob":
                continue
            rel_p = item["path"]
            if is_protected(rel_p):
                continue

            r_sha = item["sha"]
            loc_p = os.path.join(BASE_DIR, rel_p)
            loc_sha = calc_git_blob_sha(loc_p)

            if force or loc_sha != r_sha:
                files_to_update.append(rel_p)
    except Exception as e:
        # Fallback to standard core files if tree API fails
        for core_f in UPDATABLE_CORE_FILES:
            if not is_protected(core_f):
                files_to_update.append(core_f)

    if not files_to_update:
        print(f"{C_GREEN}[Moon Updater] All core files are already 100% synchronized!{CLR_RESET}\n")
        save_local_version_info({
            "version": remote_ver,
            "commit_sha": full_remote_sha,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "release_notes": msg
        })
        return True

    print(f"{C_GREEN}[Moon Updater] {len(files_to_update)} core file(s) queued for update.{CLR_RESET}\n")

    staged_downloads = []
    try:
        for rel_f in files_to_update:
            clean_rel = rel_f.replace('\\', '/')
            raw_url = f"{RAW_BASE_URL}{clean_rel}"
            target_path = os.path.join(BASE_DIR, rel_f)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            tmp_path = target_path + ".tmp_update"

            download_file_with_progress(raw_url, tmp_path, desc=os.path.basename(rel_f))
            staged_downloads.append((rel_f, target_path, tmp_path))

            # Syntax verification for Python scripts
            if rel_f.endswith(".py"):
                try:
                    py_compile.compile(tmp_path, doraise=True)
                except Exception as py_err:
                    print(f"\n{C_RED}[Moon Updater] Verification failed on {rel_f}: {py_err}{CLR_RESET}")
                    raise RuntimeError(f"Corrupted download for {rel_f}")

        print(f"\n{C_GREEN}[Moon Updater] All files downloaded and verified successfully!{CLR_RESET}")

        # Atomic replacement with backup
        for rel_f, target_path, tmp_path in staged_downloads:
            if os.path.exists(target_path):
                bak_path = target_path + ".bak"
                try:
                    if os.path.exists(bak_path):
                        os.remove(bak_path)
                    os.replace(target_path, bak_path)
                except Exception:
                    pass
            os.replace(tmp_path, target_path)

        # Update version.json
        save_local_version_info({
            "version": remote_ver,
            "commit_sha": full_remote_sha,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "release_notes": msg
        })

        # If repo is git tracked, update HEAD reference if possible
        if os.path.exists(os.path.join(BASE_DIR, ".git")):
            try:
                subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, capture_output=True, timeout=5)
                subprocess.run(["git", "reset", "--soft", "origin/main"], cwd=BASE_DIR, capture_output=True, timeout=3)
            except Exception:
                pass

        print(f"\n{C_GREEN}[OK] Moon Launcher updated to version {remote_ver} ({remote_sha})!{CLR_RESET}")
        print(f"{C_CYAN}Restarting Moon Launcher to apply updates...{CLR_RESET}\n")
        time.sleep(1.2)

        # Relaunch process seamlessly
        if sys.platform == 'win32':
            subprocess.Popen([sys.executable] + sys.argv, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)

    except Exception as e:
        print(f"\n{C_RED}[Moon Updater] Update failed: {e}{CLR_RESET}")
        print(f"{C_MUTED}Cleaning up temporary files. Your active launcher remains intact.{CLR_RESET}\n")
        for _, _, tmp_path in staged_downloads:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
        return False

def handle_update_command(args, version_dir=None, cfg=None):
    """Handles /update commands from user prompt or CLI."""
    sub = args[0].lower() if args else ""
    if sub in ("check", "status", "info"):
        check = check_for_updates(timeout=6.0)
        if not check:
            print(f"\n{C_RED}[Moon Updater] Could not connect to GitHub.{CLR_RESET}\n")
            return
        box_w = 68
        status_tag = f"{C_GREEN}[UP TO DATE]{CLR_RESET}" if not check["update_available"] else f"{C_AMBER}[UPDATE READY]{CLR_RESET}"
        lines = [
            f"{status_tag} {C_WHITE}\033[1mMoon Launcher GitHub Status\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Installed Commit :{CLR_RESET} {C_CYAN}{check['local_sha']}{CLR_RESET}",
            f"  {C_WHITE}* Latest on GitHub :{CLR_RESET} {C_GREEN}{check['remote_sha']}{CLR_RESET}",
            f"  {C_WHITE}* Latest Message   :{CLR_RESET} {C_MUTED}{check['message']}{CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        if check["update_available"]:
            lines.append(f"{C_CYAN}Type /update to download and apply this update.{CLR_RESET}")
        else:
            lines.append(f"{C_MUTED}No updates required. Launcher is running latest code.{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Launcher Updater") + "\n")
    elif sub in ("force", "reinstall", "repair"):
        apply_update_from_github(force=True)
    else:
        apply_update_from_github(force=False)
