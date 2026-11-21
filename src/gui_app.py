ACTIVE_GAME_PROC = None
"""
🌙 Moon Launcher Studio - Complete Desktop GUI
Full-featured desktop interface for Moon Launcher covering all CLI studios:
- Play Dashboard & Instance Manager
- Full Mod Manager Studio (enable/disable/delete/search mods)
- Modpack Catalog (Modrinth API search & 1-click install)
- Servers & Multiplayer Studio (servers.dat, live TCP ping, direct connect, host tunnel)
- Crash Diagnostic Studio & Game Log Analyzer
- Skin & Cape Customization Studio
- System Diagnostics & Auto-Updater Studio
"""

import os
import sys
import re
import json
import shutil
import subprocess
import threading
import urllib.request
import urllib.parse
import platform
import socket
import socket
import struct

_orig_getaddrinfo = socket.getaddrinfo
_dns_cache = {}

def resolve_a_record_tcp(domain, dns_servers=("8.8.8.8", "8.8.4.4")):
    if domain in _dns_cache:
        return _dns_cache[domain]
    parts = domain.split('.')
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return [domain]
    header = bytes([0x12, 0x34, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    qname = b""
    for part in domain.split('.'):
        if not part: continue
        qname += bytes([len(part)]) + part.encode('latin1')
    qname += b"\x00"
    payload = header + qname + bytes([0x00, 0x01, 0x00, 0x01])
    length_prefix = struct.pack("!H", len(payload))
    for s in dns_servers:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.5)
        try:
            sock.connect((s, 53))
            sock.sendall(length_prefix + payload)
            len_data = sock.recv(2)
            if len(len_data) < 2:
                continue
            resp_len = struct.unpack("!H", len_data)[0]
            resp = b""
            while len(resp) < resp_len:
                chunk = sock.recv(resp_len - len(resp))
                if not chunk: break
                resp += chunk
            ancount = struct.unpack("!H", resp[6:8])[0]
            if ancount == 0: continue
            idx = 12
            while resp[idx] != 0:
                if resp[idx] & 0xc0 == 0xc0:
                    idx += 2
                    break
                idx += resp[idx] + 1
            else:
                idx += 1
            idx += 4
            ips = []
            for _ in range(ancount):
                if idx >= len(resp): break
                if resp[idx] & 0xc0 == 0xc0: idx += 2
                else:
                    while resp[idx] != 0: idx += resp[idx] + 1
                    idx += 1
                rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", resp[idx:idx+10])
                idx += 10
                rdata = resp[idx:idx+rdlength]
                idx += rdlength
                if rtype == 1 and rdlength == 4:
                    ips.append(socket.inet_ntoa(rdata))
            if ips:
                _dns_cache[domain] = ips
                return ips
        except Exception:
            continue
        finally:
            sock.close()
    return []

def safe_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except Exception:
        pass
    ips = resolve_a_record_tcp(str(host))
    if ips:
        results = []
        for ip in ips:
            try:
                res = _orig_getaddrinfo(ip, port, socket.AF_INET, type, proto, flags)
                results.extend(res)
            except Exception:
                pass
        if results:
            return results
    return _orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = safe_getaddrinfo

import webview

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from paths import (
    BASE_DIR,
    CONFIG_PATH,
    FRIENDS_PATH,
    RESOURCE_DIR,
    SRC_DIR,
    VERSIONS_DIR,
    ensure_user_workspace,
    resolve_resource,
)

ensure_user_workspace()

try:
    import auth_ms
except Exception:
    auth_ms = None

try:
    import launcher
except Exception as e:
    launcher = None
    print(f"Warning: Could not import launcher: {e}")

try:
    import network_hub
except Exception as e:
    network_hub = None

try:
    import updater
except Exception as e:
    updater = None

def read_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning reading {CONFIG_PATH}: {e}")
    # Backup fallback to global state file if config missing/corrupt
    active_from_state = "1.20.1"
    state_file = os.path.expandvars(r"%APPDATA%\.minecraft\moon_launcher_state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8-sig") as sf:
                s_data = json.load(sf)
                if s_data.get("active_version"):
                    active_from_state = s_data["active_version"]
        except Exception:
            pass
    return {
        "username": "Player",
        "version_name": active_from_state,
        "ram_max_gb": 8,
        "ram_min_gb": 2,
        "width": 1280,
        "height": 720,
        "fullscreen": False,
        "discord_rpc": True,
        "jvm_g1gc_preset": True
    }

def write_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8-sig") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def parse_version_sort_key(item):
    """
    Returns a sort key tuple so that installed versions are sorted descending
    from highest/newest (e.g. 26.2, 1.21.11, 1.21.1, 1.20.1, 1.12.2) down to oldest.
    """
    name = item.get("name", "")
    mc = item.get("mc_version", "")

    m_nf = re.search(r'neoforge-(\d+)\.(\d+)(?:\.(\d+))?', name, re.IGNORECASE)
    if m_nf:
        maj = int(m_nf.group(1))
        min_ = int(m_nf.group(2))
        patch = int(m_nf.group(3)) if m_nf.group(3) else 0
        if maj != 1:
            return (maj, min_, patch)

    target_str = mc or ""
    if not target_str:
        target_str = name

    parts = [int(p) for p in re.findall(r'\d+', target_str)]
    if len(parts) >= 2 and parts[0] == 1:
        sub = parts[1:]
        while len(sub) < 3:
            sub.append(0)
        return tuple(sub)
    elif parts:
        sub = list(parts)
        while len(sub) < 3:
            sub.append(0)
        return tuple(sub)
    return (0, 0, 0)

def get_skin_head_data_url(skin_val=None, username="Player"):
    """
    Extracts a 128x128 pixel-art head avatar (front face + hat/hair outer layer)
    from skin file, bytes, or data URL. Completely decoupled from username so
    changing username NEVER changes or resets the active player skin.
    """
    try:
        from PIL import Image
        import io, base64

        img = None
        if skin_val:
            if isinstance(skin_val, bytes):
                img = Image.open(io.BytesIO(skin_val)).convert('RGBA')
            elif isinstance(skin_val, str):
                if skin_val.startswith("data:image"):
                    b64_part = skin_val.split(",", 1)[1] if "," in skin_val else skin_val
                    raw = base64.b64decode(b64_part)
                    img = Image.open(io.BytesIO(raw)).convert('RGBA')
                elif os.path.exists(skin_val):
                    img = Image.open(skin_val).convert('RGBA')

        # 1. Master active_skin.png (universal skin independent of username)
        if img is None:
            active_p = os.path.join(BASE_DIR, "skins", "active_skin.png")
            if os.path.exists(active_p):
                try: img = Image.open(active_p).convert('RGBA')
                except Exception: pass

        # 2. Check skins/<username>.png if exists
        if img is None and username:
            default_p = os.path.join(BASE_DIR, "skins", f"{username}.png")
            if os.path.exists(default_p):
                try: img = Image.open(default_p).convert('RGBA')
                except Exception: pass

        # 3. Check any existing .png skin in skins/ folder
        if img is None:
            skins_d = os.path.join(BASE_DIR, "skins")
            if os.path.exists(skins_d):
                for f_name in sorted(os.listdir(skins_d)):
                    if f_name.lower().endswith(".png") and not f_name.startswith("."):
                        cand_p = os.path.join(skins_d, f_name)
                        try:
                            img = Image.open(cand_p).convert('RGBA')
                            break
                        except Exception: pass

        if img is not None:
            w, h = img.size
            scale = max(1, w // 64)
            head_base = img.crop((8 * scale, 8 * scale, 16 * scale, 16 * scale))
            hat_box = (40 * scale, 8 * scale, 48 * scale, 16 * scale)
            head_hat = img.crop(hat_box)

            combined = Image.new('RGBA', head_base.size)
            combined.paste(head_base, (0, 0))
            combined.paste(head_hat, (0, 0), head_hat)

            head_128 = combined.resize((128, 128), Image.Resampling.NEAREST)
            buf = io.BytesIO()
            head_128.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"Error extracting avatar head: {e}")

    # Neutral default avatar (independent of username, never morphs based on nickname)
    return "https://minotar.net/bust/Steve/128.png"

def get_system_specs():
    try:
        import psutil
        total_ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        avail_ram_gb = round(psutil.virtual_memory().available / (1024**3), 1)
    except Exception:
        total_ram_gb = 16.0
        avail_ram_gb = 8.0

    # 1. Retrieve Friendly Processor Name from Windows Registry
    cpu_name = platform.processor() or "x86_64 Processor"
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        if val and str(val).strip():
            cpu_name = str(val).strip()
    except Exception:
        pass

    # 2. Accurate Windows Version Detection (Detect Windows 11 Build >= 22000)
    os_name = f"{platform.system()} {platform.release()}"
    try:
        win_ver = platform.win32_ver()
        build = int(win_ver[1].split('.')[-1]) if win_ver[1] else 0
        if build >= 22000:
            os_name = f"Windows 11 (Build {build})"
        elif build > 0:
            os_name = f"Windows 10 (Build {build})"
    except Exception:
        pass

    # 3. Detect Dedicated/Integrated GPU from Windows Registry
    gpu_names = []
    try:
        import winreg
        reg_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
        for i in range(winreg.QueryInfoKey(key)[0]):
            sub_name = winreg.EnumKey(key, i)
            if sub_name.isdigit():
                sub = winreg.OpenKey(key, sub_name)
                try:
                    desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                    d_lower = desc.lower()
                    if desc and desc not in gpu_names and not any(x in d_lower for x in ("mirage", "virtual", "remote", "citrix")):
                        gpu_names.append(desc)
                except Exception:
                    pass
                winreg.CloseKey(sub)
        winreg.CloseKey(key)
    except Exception:
        pass
    gpu_str = " / ".join(gpu_names) if gpu_names else "Standard Graphics Adapter"

    detected_javas = []
    if launcher and hasattr(launcher, 'discover_all_local_javas'):
        try:
            j_list = launcher.discover_all_local_javas()
            for j in j_list:
                detected_javas.append({"path": j[0], "major": j[1], "vendor": j[2]})
        except Exception:
            pass

    return {
        "os": os_name,
        "cpu": cpu_name,
        "gpu": gpu_str,
        "ram_total_gb": total_ram_gb,
        "ram_avail_gb": avail_ram_gb,
        "detected_javas": detected_javas
    }

class InstallManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = {
            "active": False,
            "slug": "",
            "title": "",
            "type": "",
            "step": "Idle",
            "current_file": "",
            "current_index": 0,
            "total_files": 0,
            "percent": 0,
            "speed_str": "",
            "logs": [],
            "completed": False,
            "success": False,
            "error": None,
            "result": None
        }

    def reset(self, slug, p_type="modpack"):
        with self.lock:
            self.status = {
                "active": True,
                "slug": slug,
                "title": slug,
                "type": p_type,
                "step": "Connecting to Modrinth API...",
                "current_file": "",
                "current_index": 0,
                "total_files": 0,
                "percent": 5,
                "speed_str": "",
                "logs": [f"Initiating installation for {slug}..."],
                "completed": False,
                "success": False,
                "error": None,
                "result": None
            }

    def update(self, **kwargs):
        with self.lock:
            for k, v in kwargs.items():
                if k == "log" and v:
                    self.status["logs"].append(str(v))
                    if len(self.status["logs"]) > 30:
                        self.status["logs"].pop(0)
                else:
                    self.status[k] = v

    def finish(self, success, result=None, error=None):
        with self.lock:
            self.status["active"] = False
            self.status["completed"] = True
            self.status["success"] = success
            self.status["percent"] = 100 if success else self.status.get("percent", 0)
            self.status["step"] = "Installation Complete!" if success else f"Failed: {error}"
            self.status["result"] = result
            self.status["error"] = error
            if result and isinstance(result, dict):
                if result.get("title"):
                    self.status["title"] = result["title"]
                if result.get("type"):
                    self.status["type"] = result["type"]
                if result.get("version_name"):
                    self.status["version_name"] = result["version_name"]
            if success:
                self.status["logs"].append("All installation triggers finished successfully.")
            else:
                self.status["logs"].append(f"Error: {error}")

    def get_status(self):
        with self.lock:
            return dict(self.status)

INSTALL_MANAGER = InstallManager()

class MoonApi:
    """Complete Python API Bridge for all Moon Launcher features"""

    def get_launcher_state(self):
        cfg = read_config()
        installed_versions = []
        if launcher and hasattr(launcher, 'get_all_available_versions'):
            try:
                avail_map = launcher.get_all_available_versions()
                for v_name, v_path in avail_map.items():
                    loader, mc_ver = "Vanilla", "1.20.1"
                    if hasattr(launcher, 'detect_version_and_loader'):
                        try:
                            mc_ver, loader = launcher.detect_version_and_loader(v_path)
                        except Exception:
                            pass
                    
                    mods_dir = os.path.join(v_path, "mods")
                    mod_count = 0
                    if os.path.exists(mods_dir) and os.path.isdir(mods_dir):
                        try:
                            mod_count = len([f for f in os.listdir(mods_dir) if f.endswith(".jar")])
                        except Exception:
                            pass

                    # Calculate mods folder size (fast)
                    mods_bytes = 0
                    if os.path.exists(mods_dir) and os.path.isdir(mods_dir):
                        try:
                            for mf in os.scandir(mods_dir):
                                if mf.is_file():
                                    mods_bytes += mf.stat().st_size
                        except Exception:
                            pass
                    size_mb = round(mods_bytes / (1024 * 1024), 1)

                    installed_versions.append({
                        "name": v_name,
                        "path": v_path,
                        "loader": loader,
                        "mc_version": mc_ver,
                        "mod_count": mod_count,
                        "size_mb": size_mb
                    })
            except Exception as err:
                print(f"Error reading versions from launcher: {err}")

        # Sort installed versions descending from newest/highest (26 down to 1.XX)
        installed_versions.sort(key=lambda x: str(x.get("name", "")).lower())
        installed_versions.sort(key=parse_version_sort_key, reverse=True)

        installed_names = {v["name"] for v in installed_versions}
        cfg_ver = str(cfg.get("version_name") or "").strip()
        if cfg_ver and cfg_ver in installed_names:
            active_ver = cfg_ver
        elif installed_versions:
            active_ver = installed_versions[0]["name"]
        else:
            active_ver = ""

        # Ensure persistent Moon ID exists via unified network_hub generator
        if network_hub and hasattr(network_hub, "get_or_create_moon_id"):
            moon_id = network_hub.get_or_create_moon_id(cfg.get("username", "Player"))
            cfg["moon_id"] = moon_id
        else:
            moon_id = cfg.get("moon_id") or "MOON-4821"

        friends_list = []
        incoming_requests = []
        servers_list = []
        cloud_reachable = False
        if network_hub and hasattr(network_hub, "cloud_sync_friends"):
            try:
                sync_res = network_hub.cloud_sync_friends()
                friends_list = sync_res.get("friends", [])
                incoming_requests = sync_res.get("incoming_requests", [])
                cloud_reachable = bool(sync_res.get("cloud_reachable"))
            except Exception:
                pass

        if os.path.exists(FRIENDS_PATH):
            try:
                with open(FRIENDS_PATH, "r", encoding="utf-8-sig") as f:
                    f_data = json.load(f)
                    if isinstance(f_data, dict):
                        if not friends_list:
                            for x in f_data.get("friends", []):
                                if isinstance(x, dict):
                                    friends_list.append(x)
                                elif isinstance(x, str):
                                    friends_list.append({"username": x, "status": "offline"})
                        servers_list = f_data.get("servers", [])
            except Exception:
                pass

        cloud_api_url = ""
        sb_url, sb_key = ("", "")
        if network_hub:
            if hasattr(network_hub, "get_cloud_api_config"):
                cloud_api_url = network_hub.get_cloud_api_config()
            if hasattr(network_hub, "get_supabase_config"):
                sb_url, sb_key = network_hub.get_supabase_config()

        companion_url = ""
        if active_ver:
            for meta_p in (
                os.path.join(VERSIONS_DIR, active_ver, "moon-companion.json"),
                os.path.join(VERSIONS_DIR, active_ver, "config", "moon-companion.json"),
            ):
                if os.path.exists(meta_p):
                    try:
                        with open(meta_p, "r", encoding="utf-8-sig") as mf:
                            companion_url = json.load(mf).get("url", "")
                        if companion_url:
                            break
                    except Exception:
                        pass

        specs = get_system_specs()
        active_account = auth_ms.get_active_account() if auth_ms else None
        if active_account and active_account.get("username"):
            cfg["username"] = active_account["username"]
            cfg["auth_type"] = "microsoft"
        else:
            cfg["auth_type"] = "offline"
        accounts_list = auth_ms.list_accounts_public() if auth_ms else []

        avatar_url = get_skin_head_data_url(cfg.get("custom_skin"), cfg.get("username", "Player"))

        local_ver = "v2.5.1"
        v_json = resolve_resource("version.json")
        if os.path.exists(v_json):
            try:
                with open(v_json, "r", encoding="utf-8-sig") as vf:
                    local_ver = "v" + str(json.load(vf).get("version", "2.5.1")).lstrip("v")
            except Exception:
                pass

        return {
            "config": cfg,
            "moon_id": moon_id,
            "active_version": active_ver,
            "versions": installed_versions,
            "friends": friends_list,
            "incoming_requests": incoming_requests,
            "cloud_reachable": cloud_reachable,
            "cloud_api_url": cloud_api_url,
            "cloud_engine": "cloudflare" if cloud_api_url else ("supabase" if (sb_url and sb_key) else "local"),
            "supabase_url": sb_url,
            "supabase_configured": bool(cloud_api_url or (sb_url and sb_key)),
            "companion_url": companion_url,
            "servers": servers_list,
            "specs": specs,
            "avatar_url": avatar_url,
            "accounts": accounts_list,
            "active_account": {
                "id": active_account.get("id"),
                "type": active_account.get("type"),
                "username": active_account.get("username"),
                "uuid": active_account.get("uuid"),
            } if active_account else None,
            "launcher_version": local_ver,
            "rpc_status": {
                "enabled": bool(cfg.get("discord_rpc", True)),
                "connected": bool(launcher and getattr(launcher, "GLOBAL_RPC", None) and launcher.GLOBAL_RPC.connected),
            },
            "is_game_running": bool((ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)) and (ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)).poll() is None),
            "game_pid": (ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)).pid if ((ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)) and (ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)).poll() is None) else None
        }

    # ==========================================
    # FRIENDS & MULTIPLAYER API (MOON-ID SYSTEM)
    # ==========================================
    def get_friends(self):
        cfg = read_config()
        if network_hub and hasattr(network_hub, "cloud_sync_friends"):
            try:
                return network_hub.cloud_sync_friends()
            except Exception:
                pass
        moon_id = network_hub.get_or_create_moon_id(cfg.get("username", "Player")) if (network_hub and hasattr(network_hub, "get_or_create_moon_id")) else cfg.get("moon_id", "MOON-4821")
        return {"friends": [], "incoming_requests": [], "outgoing_requests": [], "cloud_reachable": False, "my_moon_id": moon_id}

    def add_friend(self, moon_id_or_input):
        clean = str(moon_id_or_input).strip()
        if not clean:
            return {"success": False, "error": "Please enter a valid Moon ID or username"}

        data = {"friends": [], "servers": []}
        if os.path.exists(FRIENDS_PATH):
            try:
                with open(FRIENDS_PATH, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                pass

        cloud_res = None
        if network_hub and hasattr(network_hub, "cloud_send_friend_request"):
            cloud_res = network_hub.cloud_send_friend_request(clean, read_config().get("username"))
            if cloud_res and not cloud_res.get("success", True):
                return cloud_res

        resolved = network_hub.resolve_player_by_moon_id(clean) if (network_hub and hasattr(network_hub, "resolve_player_by_moon_id")) else None
        f_id = (cloud_res or {}).get("player_id") or (resolved or {}).get("player_id")
        if not f_id:
            clean_id = clean.upper()
            f_id = clean_id if clean_id.startswith("MOON-") else f"MOON-{clean_id}"
        f_user = (cloud_res or {}).get("username") or (resolved or {}).get("username") or f_id
        f_status = (resolved or {}).get("status", "offline")
        f_srv = (resolved or {}).get("server_addr", "")

        friends = data.setdefault("friends", [])
        for item in friends:
            if isinstance(item, dict) and (item.get("player_id", "").upper() == f_id.upper() or item.get("username", "").lower() == f_user.lower()):
                item["player_id"] = f_id
                item["username"] = f_user
                item["status"] = f_status
                if f_srv:
                    item["server_addr"] = f_srv
                try:
                    with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    pass
                return {"success": True, "friend": item, "cloud_synced": bool(cloud_res and cloud_res.get("cloud_synced"))}

        new_entry = {
            "player_id": f_id,
            "username": f_user,
            "status": f_status,
            "server_addr": f_srv,
            "version_name": (resolved or {}).get("version_name", ""),
        }
        friends.append(new_entry)
        try:
            with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True, "friend": new_entry, "cloud_synced": bool(cloud_res and cloud_res.get("cloud_synced"))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def accept_friend(self, player_id):
        if network_hub and hasattr(network_hub, "cloud_accept_friend_request"):
            return network_hub.cloud_accept_friend_request(player_id)
        return {"success": False, "error": "Network hub unavailable"}

    def decline_friend(self, player_id):
        if network_hub and hasattr(network_hub, "cloud_remove_friendship"):
            network_hub.cloud_remove_friendship(player_id)
        return self.delete_friend(player_id)

    def delete_friend(self, player_id_or_name):
        if network_hub and hasattr(network_hub, "cloud_remove_friendship"):
            try:
                network_hub.cloud_remove_friendship(player_id_or_name)
            except Exception:
                pass
        if not os.path.exists(FRIENDS_PATH):
            return {"success": True}
        try:
            with open(FRIENDS_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            target = str(player_id_or_name).strip().lower()
            data["friends"] = [
                f for f in data.get("friends", [])
                if (isinstance(f, dict) and f.get("player_id", "").lower() != target and f.get("username", "").lower() != target)
                or (isinstance(f, str) and f.lower() != target)
            ]
            with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_social_extras(self, peer_id=None, party_id=None):
        """Fetches active Party/Squad state, invites, and cross-server chat feed."""
        if not network_hub:
            return {"party": None, "pending_invites": [], "messages": []}
        try:
            st = network_hub.cloud_get_party_state()
            eff_party = party_id or ((st.get("party") or {}).get("party_id") if isinstance(st.get("party"), dict) else None)
            msgs = network_hub.cloud_poll_chat(peer_id=peer_id, party_id=eff_party if (party_id or not peer_id) else None)
            return {
                "party": st.get("party"),
                "pending_invites": st.get("pending_invites", []),
                "messages": msgs,
                "my_moon_id": st.get("my_moon_id", ""),
            }
        except Exception as e:
            return {"party": None, "pending_invites": [], "messages": [], "error": str(e)}

    def send_chat_message(self, recipient_id=None, party_id=None, body=""):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_send_chat(recipient_id=recipient_id, party_id=party_id, body=body)

    def create_party(self):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_create_party()

    def mass_invite_party(self, targets=None):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_invite_party(targets=targets)

    def join_party(self, party_id):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_join_party(party_id)

    def leave_party(self, party_id=None):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_leave_party(party_id=party_id)

    def set_party_target(self, target_server, target_world=""):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        return network_hub.cloud_set_party_target(target_server, target_world)

    def sync_friends_whitelist(self):
        if not network_hub or not launcher:
            return {"success": False, "error": "Engine unavailable"}
        try:
            v_dir = launcher.get_active_version_dir()
        except Exception:
            v_dir = None
        return network_hub.sync_friends_whitelist(version_dir=v_dir, enabled=True)

    def open_mod_companion(self):
        cfg = read_config()
        active_ver = cfg.get("version_name", "")
        if active_ver:
            for meta_p in (
                os.path.join(VERSIONS_DIR, active_ver, "moon-companion.json"),
                os.path.join(VERSIONS_DIR, active_ver, "config", "moon-companion.json"),
            ):
                if os.path.exists(meta_p):
                    try:
                        with open(meta_p, "r", encoding="utf-8-sig") as f:
                            url = json.load(f).get("url", "")
                        if url:
                            webbrowser.open(url)
                            return {"success": True, "url": url}
                    except Exception:
                        pass
        return {"success": False, "error": "Launch Minecraft first to open the In-Game Mod Companion Hub"}

    def _refresh_rpc(self, cfg=None, version_dir=None):
        """Synchronize Discord Rich Presence with the latest profile/settings."""
        if not (launcher and hasattr(launcher, 'ensure_global_rpc')):
            return
        try:
            current_cfg = cfg if cfg is not None else read_config()
            v_dir = version_dir
            if not v_dir:
                v_name = current_cfg.get("version_name", "")
                if v_name and hasattr(launcher, 'find_version_dir_by_name'):
                    v_dir = launcher.find_version_dir_by_name(v_name)
                elif hasattr(launcher, 'get_active_version_dir'):
                    v_dir = launcher.get_active_version_dir()
                else:
                    v_dir = os.path.join(VERSIONS_DIR, v_name)
            launcher.ensure_global_rpc(v_dir, current_cfg)
        except Exception:
            pass

    def switch_version(self, version_name):
        return self.set_active_version(version_name)

    def set_active_version(self, version_name):
        cfg = read_config()
        clean_name = str(version_name).strip()
        cfg["version_name"] = clean_name
        write_config(cfg)
        if launcher and hasattr(launcher, 'set_active_version'):
            try:
                launcher.set_active_version(clean_name)
            except Exception as e:
                print(f"Error updating launcher active version: {e}")
        if network_hub and hasattr(network_hub, 'update_active_version'):
            v_dir = os.path.join(VERSIONS_DIR, clean_name)
            network_hub.update_active_version(v_dir, clean_name)
        v_dir = launcher.find_version_dir_by_name(clean_name) if (launcher and hasattr(launcher, 'find_version_dir_by_name')) else os.path.join(VERSIONS_DIR, clean_name)
        self._refresh_rpc(cfg, v_dir)
        return {"success": True, "active_version": clean_name}

    def set_ram(self, ram_gb):
        cfg = read_config()
        cfg["ram_max_gb"] = int(ram_gb)
        write_config(cfg)
        return {"success": True, "ram_max_gb": int(ram_gb)}

    def set_player_name(self, username):
        import shutil
        if auth_ms and auth_ms.get_active_account():
            return {
                "success": False,
                "error": "Signed in with Microsoft. Switch to Offline account to set a custom username.",
            }
        if auth_ms:
            ok, err, clean = auth_ms.validate_minecraft_username(username)
            if not ok:
                return {"success": False, "error": err}
        else:
            clean = str(username).strip().replace(" ", "_") or "Player"
        cfg = read_config()
        cfg["username"] = clean
        cfg["auth_type"] = "offline"

        # Ensure active skin is preserved and linked to new username
        main_skins_dir = os.path.join(BASE_DIR, "skins")
        os.makedirs(main_skins_dir, exist_ok=True)
        active_skin_path = os.path.join(main_skins_dir, "active_skin.png")
        target_skin_path = os.path.join(main_skins_dir, f"{clean}.png")

        # If active_skin.png does not exist yet, find any existing skin
        if not os.path.exists(active_skin_path):
            existing_skin = cfg.get("custom_skin")
            if existing_skin and os.path.exists(existing_skin):
                try: shutil.copy2(existing_skin, active_skin_path)
                except Exception: pass
            else:
                for cand in os.listdir(main_skins_dir):
                    if cand.lower().endswith(".png") and not cand.startswith("."):
                        try:
                            shutil.copy2(os.path.join(main_skins_dir, cand), active_skin_path)
                            break
                        except Exception: pass

        # Replicate active skin to target {clean}.png and active_skin.png for CustomSkinLoader
        if os.path.exists(active_skin_path):
            try:
                shutil.copy2(active_skin_path, target_skin_path)
            except Exception: pass
            cfg["custom_skin"] = active_skin_path

        write_config(cfg)
        v_dir = None
        if launcher and hasattr(launcher, 'set_global_username'):
            v_dir = os.path.join(VERSIONS_DIR, cfg.get("version_name", ""))
            launcher.set_global_username(clean, v_dir)
        self._refresh_rpc(cfg, v_dir)

        # Avatar strictly displays the active skin! Name change does NOT affect skin!
        new_avatar = get_skin_head_data_url(active_skin_path if os.path.exists(active_skin_path) else cfg.get("custom_skin"), clean)
        return {"success": True, "username": clean, "avatar_url": new_avatar}

    def choose_java_file(self):
        """Opens native file picker to select custom javaw.exe executable"""
        selected_path = None
        try:
            if webview.windows and len(webview.windows) > 0:
                result = webview.windows[0].create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=('Java Executable (javaw.exe; java.exe)', 'All files (*.*)')
                )
                if result and len(result) > 0:
                    selected_path = result[0]
        except Exception as e:
            print(f"Webview java file dialog error: {e}")

        if not selected_path:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected_path = filedialog.askopenfilename(
                    title="Select Java Executable (javaw.exe)",
                    filetypes=[("Java Executable", "javaw.exe;java.exe"), ("All Files", "*.*")]
                )
                root.destroy()
            except Exception as e:
                print(f"Tkinter java file dialog error: {e}")

        if selected_path and os.path.exists(selected_path):
            cfg = read_config()
            cfg["java_path"] = selected_path
            write_config(cfg)

            # Sync to active version
            v_name = cfg.get("version_name")
            if v_name:
                v_dir = os.path.join(VERSIONS_DIR, v_name)
                if launcher and hasattr(launcher, 'save_config'):
                    launcher.save_config(v_dir, cfg)

            return {"success": True, "java_path": selected_path}

        return {"success": False, "cancelled": True}

    def open_external_url(self, url):
        """Opens a link in the user's default web browser"""
        try:
            import webbrowser
            if url and str(url).startswith(("http://", "https://")):
                webbrowser.open(str(url))
                return {"success": True}
            return {"success": False, "error": "Invalid URL"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def choose_skin_file(self):
        """Opens native file picker dialog to pick a .png skin file"""
        import base64
        selected_path = None
        try:
            if webview.windows and len(webview.windows) > 0:
                result = webview.windows[0].create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=('Minecraft Skin (*.png)', 'All files (*.*)')
                )
                if result and len(result) > 0:
                    selected_path = result[0]
        except Exception as e:
            print(f"Webview file dialog exception: {e}")

        if not selected_path:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected_path = filedialog.askopenfilename(
                    title="Select Minecraft Skin (.png)",
                    filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
                )
                root.destroy()
            except Exception as e:
                print(f"Tkinter file dialog exception: {e}")

        if selected_path and os.path.exists(selected_path):
            try:
                with open(selected_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                cfg = read_config()
                head_url = get_skin_head_data_url(selected_path, cfg.get("username", "Player"))
                return {
                    "success": True,
                    "path": selected_path,
                    "filename": os.path.basename(selected_path),
                    "preview_url": head_url
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "cancelled": True}

    def apply_skin_data(self, filename, base64_data, skin_model=None):
        """Saves uploaded base64 skin image directly to skins/<username>.png and applies it"""
        import base64
        cfg = read_config()
        username = cfg.get("username", "Player")
        v_name = cfg.get("version_name", "1.20.1")
        v_dir = os.path.join(VERSIONS_DIR, v_name)

        main_skins_dir = os.path.join(BASE_DIR, "skins")
        os.makedirs(main_skins_dir, exist_ok=True)
        active_path = os.path.join(main_skins_dir, "active_skin.png")
        saved_path = os.path.join(main_skins_dir, f"{username}.png")

        try:
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
            raw_bytes = base64.b64decode(base64_data)
            if not raw_bytes.startswith(b"\x89PNG"):
                return {"success": False, "error": "Invalid skin file. Must be a PNG image."}
            with open(active_path, "wb") as f_act:
                f_act.write(raw_bytes)
            with open(saved_path, "wb") as f:
                f.write(raw_bytes)

            cfg["custom_skin"] = active_path
            cfg["custom_skin_url"] = ""
            if skin_model in ("auto", "classic", "slim"):
                cfg["skin_model"] = skin_model
            write_config(cfg)

            if launcher and hasattr(launcher, 'apply_skin_setting'):
                launcher.apply_skin_setting(v_dir, cfg, active_path)
                launcher.save_config(v_dir, cfg)

            if network_hub and hasattr(network_hub, 'trigger_lan_skin_broadcast'):
                try: network_hub.trigger_lan_skin_broadcast()
                except Exception: pass

            self._refresh_rpc(cfg, v_dir)
            new_avatar = get_skin_head_data_url(saved_path, username)
            return {"success": True, "saved_path": saved_path, "avatar_url": new_avatar}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_skin(self, skin_val, skin_model=None):
        cfg = read_config()
        clean_val = str(skin_val).strip()
        username = cfg.get("username", "Player")
        v_dir = os.path.join(VERSIONS_DIR, cfg.get("version_name", ""))
        if skin_model in ("auto", "classic", "slim"):
            cfg["skin_model"] = skin_model

        if clean_val.lower() in ('auto', 'reset', 'default', 'steve', 'none'):
            if launcher and hasattr(launcher, 'apply_skin_setting'):
                launcher.apply_skin_setting(v_dir, cfg, 'reset')
                launcher.save_config(v_dir, cfg)
            else:
                cfg["custom_skin"] = ""
                cfg["custom_skin_url"] = ""
                write_config(cfg)
            self._refresh_rpc(None, v_dir)
            active_path = os.path.join(BASE_DIR, "skins", "active_skin.png")
            new_avatar = get_skin_head_data_url(active_path if os.path.exists(active_path) else None, username)
            return {"success": True, "skin": "default", "avatar_url": new_avatar}

        if launcher and hasattr(launcher, 'apply_skin_setting'):
            res = launcher.apply_skin_setting(v_dir, cfg, clean_val)
            if isinstance(res, dict) and not res.get("success", True):
                return res
            launcher.save_config(v_dir, cfg)
        else:
            if clean_val.startswith(("http://", "https://")):
                cfg["custom_skin_url"] = clean_val
            else:
                cfg["custom_skin"] = clean_val
            write_config(cfg)

        if network_hub and hasattr(network_hub, 'trigger_lan_skin_broadcast'):
            try: network_hub.trigger_lan_skin_broadcast()
            except Exception: pass

        latest_cfg = read_config()
        self._refresh_rpc(latest_cfg, v_dir)
        new_avatar = get_skin_head_data_url(latest_cfg.get("custom_skin"), username)
        return {"success": True, "skin": clean_val, "avatar_url": new_avatar}

    def preview_skin_input(self, val):
        """Downloads skin texture from URL or Minecraft username and returns cropped 128x128 head preview."""
        s = str(val or "").strip()
        if not s:
            return {"success": False, "error": "Enter a skin URL or player name"}
        url = s if s.startswith(("http://", "https://")) else f"https://minotar.net/skin/{urllib.parse.quote(s)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read()
            if not raw.startswith(b"\x89PNG"):
                return {"success": False, "error": "URL did not return a valid PNG skin"}
            return {"success": True, "preview_url": get_skin_head_data_url(raw)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_skin_model(self, model):
        m = str(model or "auto").lower()
        if m not in ("auto", "classic", "slim"):
            return {"success": False, "error": "Invalid skin model"}
        cfg = read_config()
        cfg["skin_model"] = m
        write_config(cfg)
        v_dir = os.path.join(VERSIONS_DIR, cfg.get("version_name", ""))
        if launcher and hasattr(launcher, "ensure_custom_skin_loader"):
            launcher.ensure_custom_skin_loader(v_dir, cfg)
            launcher.save_config(v_dir, cfg)
        return {"success": True, "skin_model": m}

    def apply_cape(self, cape_val):
        cfg = read_config()
        v_dir = os.path.join(VERSIONS_DIR, cfg.get("version_name", ""))
        if launcher and hasattr(launcher, "apply_cape_setting"):
            res = launcher.apply_cape_setting(v_dir, cfg, cape_val)
            if res.get("success"):
                launcher.save_config(v_dir, cfg)
            return res
        return {"success": False, "error": "Cape engine unavailable"}

    def choose_cape_file(self):
        selected_path = None
        try:
            if webview.windows and len(webview.windows) > 0:
                result = webview.windows[0].create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=('Minecraft Cape (*.png)', 'All files (*.*)')
                )
                if result and len(result) > 0:
                    selected_path = result[0]
        except Exception:
            pass
        if selected_path and os.path.exists(selected_path):
            return self.apply_cape(selected_path)
        return {"success": False, "cancelled": True}

    # ==========================================
    # MICROSOFT ACCOUNT & MULTI-ACCOUNT AUTH API
    # ==========================================
    def get_accounts(self):
        if not auth_ms:
            return {"accounts": [], "active": None}
        acc = auth_ms.get_active_account()
        return {
            "accounts": auth_ms.list_accounts_public(),
            "active": {
                "id": acc.get("id"),
                "type": acc.get("type"),
                "username": acc.get("username"),
                "uuid": acc.get("uuid"),
            } if acc else None,
        }

    def login_microsoft(self):
        if not auth_ms:
            return {"success": False, "error": "Microsoft auth module unavailable"}
        import time
        auth_url = auth_ms.get_authorize_url()
        captured = {"url": None, "closed": False}
        try:
            auth_win = webview.create_window(
                "Sign in with Microsoft — Moon Launcher",
                url=auth_url,
                width=520,
                height=700,
                resizable=True,
            )
            def _on_closed():
                captured["closed"] = True
            auth_win.events.closed += _on_closed

            deadline = time.time() + 180
            while time.time() < deadline and not captured["closed"]:
                try:
                    cur_u = auth_win.get_current_url() or ""
                    if cur_u.startswith("https://login.live.com/oauth20_desktop.srf") and ("code=" in cur_u or "error=" in cur_u):
                        captured["url"] = cur_u
                        try:
                            auth_win.destroy()
                        except Exception:
                            pass
                        break
                except Exception:
                    break
                time.sleep(0.35)
        except Exception as e:
            return {"success": False, "error": f"Could not open Microsoft login window: {e}"}

        if not captured["url"]:
            return {"success": False, "cancelled": True, "error": "Microsoft sign-in cancelled or timed out."}
        if "error=" in captured["url"] and "code=" not in captured["url"]:
            return {"success": False, "error": "Microsoft sign-in was denied or returned an error."}

        try:
            acc = auth_ms.login_with_auth_code(captured["url"])
            if launcher and hasattr(launcher, "set_global_username"):
                v_dir = os.path.join(VERSIONS_DIR, read_config().get("version_name", ""))
                launcher.set_global_username(acc["username"], v_dir)
            if network_hub and hasattr(network_hub, "update_lan_skin_identity"):
                network_hub.update_lan_skin_identity(acc["username"])
            self._refresh_rpc()
            avatar_url = get_skin_head_data_url(os.path.join(BASE_DIR, "skins", "active_skin.png"), acc["username"])
            return {
                "success": True,
                "account": {
                    "id": acc["id"],
                    "type": "microsoft",
                    "username": acc["username"],
                    "uuid": acc["uuid"],
                },
                "avatar_url": avatar_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def login_microsoft_code(self, code_or_url):
        if not auth_ms:
            return {"success": False, "error": "Microsoft auth module unavailable"}
        try:
            acc = auth_ms.login_with_auth_code(code_or_url)
            if launcher and hasattr(launcher, "set_global_username"):
                v_dir = os.path.join(VERSIONS_DIR, read_config().get("version_name", ""))
                launcher.set_global_username(acc["username"], v_dir)
            if network_hub and hasattr(network_hub, "update_lan_skin_identity"):
                network_hub.update_lan_skin_identity(acc["username"])
            self._refresh_rpc()
            avatar_url = get_skin_head_data_url(os.path.join(BASE_DIR, "skins", "active_skin.png"), acc["username"])
            return {"success": True, "username": acc["username"], "avatar_url": avatar_url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def switch_account(self, account_id):
        if not auth_ms:
            return {"success": False, "error": "Account manager unavailable"}
        try:
            res = auth_ms.switch_account(account_id)
            if launcher and hasattr(launcher, "set_global_username"):
                v_dir = os.path.join(VERSIONS_DIR, read_config().get("version_name", ""))
                launcher.set_global_username(res.get("username", "Player"), v_dir)
            if network_hub and hasattr(network_hub, "update_lan_skin_identity"):
                network_hub.update_lan_skin_identity(res.get("username", "Player"))
            self._refresh_rpc()
            return {"success": True, "account": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def logout_account(self, account_id):
        if not auth_ms:
            return {"success": False, "error": "Account manager unavailable"}
        auth_ms.remove_account(account_id)
        self._refresh_rpc()
        return {"success": True}

    def save_settings(self, settings):
        cfg = read_config()
        if isinstance(settings, dict):
            for k, v in settings.items():
                if k in ("cloud_api_url", "supabase_url"):
                    cfg[k] = str(v or "").strip().rstrip("/")
                elif k == "supabase_key":
                    cfg[k] = str(v or "").strip()
                else:
                    cfg[k] = v
            write_config(cfg)
            self._refresh_rpc(cfg)
            if network_hub and hasattr(network_hub, "start_cloud_presence_service"):
                try:
                    network_hub.start_cloud_presence_service(cfg.get("username"))
                    network_hub.cloud_update_presence(cfg.get("username"))
                except Exception:
                    pass
        return {"success": True}

    def get_rpc_status(self):
        cfg = read_config()
        rpc = getattr(launcher, "GLOBAL_RPC", None) if launcher else None
        return {
            "enabled": bool(cfg.get("discord_rpc", True)),
            "connected": bool(rpc and rpc.connected),
            "last_error": getattr(rpc, "last_error", "") if rpc else "",
        }

    def _get_cli_cmd(self, cmd_args):
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):
            cli_exe = os.path.join(os.path.dirname(exe_path), "Moon-Launcher-CLI.exe")
            target_exe = cli_exe if os.path.exists(cli_exe) else exe_path
            return f'"{target_exe}" {cmd_args}'
        if exe_path.lower().endswith("pythonw.exe"):
            console_py = exe_path[:-5] + ".exe"
            if os.path.exists(console_py):
                exe_path = console_py
        cli_py = os.path.join(SRC_DIR, "cli.py")
        if not os.path.exists(cli_py):
            cli_py = os.path.join(SRC_DIR, "launcher.py")
        return f'"{exe_path}" "{cli_py}" {cmd_args}'

    def launch_game(self, direct_server=None, version_name=None):
        if version_name and launcher and hasattr(launcher, 'set_active_version'):
            try:
                launcher.set_active_version(str(version_name).strip())
            except Exception:
                pass
        """
        Directly launches Minecraft in the background without spawning flickering
        CMD console windows. Tracks active process and updates Discord RPC.
        Supports direct server connect (--server host --port port).
        """
        global ACTIVE_GAME_PROC
        try:
            proc = ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)
            if proc and proc.poll() is None:
                return {
                    "success": False,
                    "already_running": True,
                    "pid": proc.pid,
                    "error": f"Minecraft is already running (PID: {proc.pid})!"
                }

            if not launcher:
                return {"success": False, "error": "Launcher engine not available"}

            version_dir = launcher.get_active_version_dir()
            cfg = launcher.load_config(version_dir)
            mc_ver, loader = "1.20.1", "Forge"
            if hasattr(launcher, 'detect_version_and_loader'):
                try: mc_ver, loader = launcher.detect_version_and_loader(version_dir)
                except Exception: pass

            j_path = launcher.get_best_java_for_version(mc_ver, cfg.get('java_path')) if hasattr(launcher, 'get_best_java_for_version') else cfg.get('java_path')

            # Verify Java compatibility before launching
            if hasattr(launcher, 'inspect_java_binary') and hasattr(launcher, 'get_required_java_version'):
                j_valid, j_major, j_detail = launcher.inspect_java_binary(j_path)
                req_java = launcher.get_required_java_version(mc_ver)
                if not j_valid or (j_major and j_major != req_java):
                    rec = launcher.get_java_recommendation(mc_ver) if hasattr(launcher, 'get_java_recommendation') else {}
                    return {
                        "success": False,
                        "java_missing": True,
                        "mc_version": mc_ver,
                        "required_java": req_java,
                        "current_java": j_major,
                        "java_name": rec.get("name", f"Java {req_java} LTS"),
                        "web_url": rec.get("web_url", f"https://adoptium.net/temurin/releases/?version={req_java}"),
                        "direct_msi": rec.get("direct_msi", rec.get("web_url")),
                        "reason": rec.get("reason", f"Minecraft {mc_ver} memerlukan Java {req_java} LTS."),
                        "error": f"Minecraft {mc_ver} memerlukan {rec.get('name', 'Java ' + str(req_java))} (terdeteksi: Java {j_major if j_major else 'Tidak Ditemukan'})."
                    }

            if direct_server:
                srv_str = str(direct_server).strip()
                if ':' in srv_str:
                    host, port = srv_str.split(':', 1)
                    cfg['server'] = host.strip()
                    cfg['port'] = port.strip()
                else:
                    cfg['server'] = srv_str
                    cfg['port'] = '25565'

            proc = launcher.launch_game(version_dir, cfg)
            if proc:
                ACTIVE_GAME_PROC = proc if hasattr(proc, 'pid') else getattr(launcher, 'ACTIVE_GAME_PROC', None)
                v_name = cfg.get('version_name', os.path.basename(version_dir))
                return {
                    "success": True,
                    "message": f"Minecraft ({v_name}) started!",
                    "pid": ACTIVE_GAME_PROC.pid if ACTIVE_GAME_PROC else None,
                    "version_name": v_name
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to launch Minecraft. Please check Java or launch_args.txt."
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_game_status(self):
        """Returns whether Minecraft process is currently running."""
        global ACTIVE_GAME_PROC
        proc = ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)
        is_running = bool(proc and proc.poll() is None)
        return {
            "is_running": is_running,
            "pid": proc.pid if is_running else None
        }

    def get_qol_state(self):
        """Returns Phase 2 QoL telemetry: HUD overlay, playtime, gamma, and world backups."""
        try:
            import client_qol
            cfg = read_config()
            active_ver = cfg.get("version_name", "")
            v_dir = os.path.join(VERSIONS_DIR, active_ver) if active_ver else ""
            return {
                "overlay": client_qol.GLOBAL_HUD_OVERLAY.status(),
                "playtime": client_qol.get_playtime_summary(active_ver),
                "gamma": client_qol.get_gamma_state(v_dir),
                "backups": client_qol.list_instance_backups(v_dir)[:5],
            }
        except Exception as e:
            return {"error": str(e), "overlay": {"running": False}, "playtime": {"instance_formatted": "0s", "total_all_formatted": "0s"}}

    def toggle_hud_overlay(self):
        import client_qol
        cfg = read_config()
        proc = ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)
        pid = proc.pid if (proc and proc.poll() is None) else None
        st = client_qol.GLOBAL_HUD_OVERLAY.toggle(version_name=cfg.get("version_name") or "Minecraft", pid=pid)
        return {"success": True, "overlay": st}

    def set_audio_preset(self, preset="normal"):
        import client_qol
        res = client_qol.apply_audio_preset(preset)
        if res.get("success"):
            client_qol.GLOBAL_HUD_OVERLAY.set_audio_preset_label(preset)
        return res

    def toggle_borderless(self):
        import client_qol
        proc = ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)
        pid = proc.pid if (proc and proc.poll() is None) else None
        return client_qol.toggle_borderless_window(pid)

    def toggle_gamma(self):
        import client_qol
        cfg = read_config()
        active_ver = cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, active_ver) if active_ver else ""
        return client_qol.set_gamma_boost(v_dir, None)

    def backup_worlds_now(self):
        import client_qol
        cfg = read_config()
        active_ver = cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, active_ver) if active_ver else ""
        return client_qol.backup_instance_saves(v_dir, max_keep=4, force=True)

    def kill_game_process(self):
        """Stops running Minecraft instance."""
        global ACTIVE_GAME_PROC
        proc = ACTIVE_GAME_PROC or getattr(launcher, 'ACTIVE_GAME_PROC', None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                return {"success": True, "message": "Game process terminated"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "No running game process found"}

    def run_preflight_test(self, version_name=None):
        target = f'"{version_name}"' if version_name else ''
        cmd_str = self._get_cli_cmd(f'/test {target}'.strip())
        cmd = f'start "Moon Launcher - Preflight Auto-Fix" {cmd_str}'
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return {"success": True}

    def run_auto_fix(self, version_name=None):
        target = f'"{version_name}"' if version_name else ''
        cmd_str = self._get_cli_cmd(f'/fix {target}'.strip())
        cmd = f'start "Moon Launcher - Automated Repair" {cmd_str}'
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return {"success": True}

    # ==========================================
    # MOD MANAGER STUDIO API
    # ==========================================
    def get_mods_list(self, version_name=None):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "1.20.1")
        mods_dir = os.path.join(VERSIONS_DIR, v_name, "mods")
        if not os.path.exists(mods_dir):
            return {"mods": [], "mods_dir": mods_dir, "version_name": v_name}

        mods = []
        try:
            for f in sorted(os.listdir(mods_dir)):
                f_path = os.path.join(mods_dir, f)
                if not os.path.isfile(f_path):
                    continue
                is_enabled = f.endswith(".jar")
                is_disabled = f.endswith((".jar.disabled", ".disabled"))
                if not (is_enabled or is_disabled):
                    continue

                clean_name = f.replace(".jar.disabled", "").replace(".disabled", "").replace(".jar", "")
                size_kb = round(os.path.getsize(f_path) / 1024, 1)

                mods.append({
                    "filename": f,
                    "name": clean_name,
                    "enabled": is_enabled,
                    "size_kb": size_kb
                })
        except Exception as e:
            print(f"Error reading mods: {e}")

        return {"mods": mods, "mods_dir": mods_dir, "version_name": v_name}

    def toggle_mod(self, filename, version_name=None):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "1.20.1")
        mods_dir = os.path.join(VERSIONS_DIR, v_name, "mods")
        old_path = os.path.join(mods_dir, filename)
        if not os.path.exists(old_path):
            return {"success": False, "error": "File not found"}

        if filename.endswith(".jar"):
            new_filename = filename + ".disabled"
        elif filename.endswith(".disabled"):
            new_filename = filename[:-9] if filename.endswith(".disabled") else filename + ".jar"
            if not new_filename.endswith(".jar"):
                new_filename += ".jar"
        else:
            return {"success": False, "error": "Unknown mod extension"}

        new_path = os.path.join(mods_dir, new_filename)
        try:
            os.rename(old_path, new_path)
            return {"success": True, "old_name": filename, "new_name": new_filename}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_mod(self, filename, version_name=None):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "1.20.1")
        mods_dir = os.path.join(VERSIONS_DIR, v_name, "mods")
        f_path = os.path.join(mods_dir, filename)
        if not os.path.exists(f_path):
            return {"success": False, "error": "File not found"}

        backup_dir = os.path.join(BASE_DIR, "_backup_unused_mods")
        os.makedirs(backup_dir, exist_ok=True)
        try:
            dest = os.path.join(backup_dir, filename)
            shutil.move(f_path, dest)
            return {"success": True, "filename": filename}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # CRASH DIAGNOSTICS & LOGS STUDIO API
    # ==========================================
    def get_crash_diagnostics(self, version_name=None):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "1.20.1")
        v_dir = os.path.join(VERSIONS_DIR, v_name)
        if not os.path.exists(v_dir):
            return {"has_crash": False, "message": "Version directory not found"}

        report = None
        if launcher and hasattr(launcher, 'analyze_latest_crash'):
            try:
                report = launcher.analyze_latest_crash(v_dir)
            except Exception as e:
                print(f"Error in analyze_latest_crash: {e}")

        if not report or not report.get("failure_message"):
            return {
                "has_crash": False,
                "message": "No recorded crash reports found for this instance.",
                "version_name": v_name
            }

        return {
            "has_crash": True,
            "error_type": report.get("error_type", "General Exception"),
            "description": report.get("description", "Minecraft encountered a runtime crash"),
            "failure_message": report.get("failure_message", ""),
            "remediation": report.get("remediation", ["Run preflight check or adjust RAM allocation"]),
            "filename": report.get("filename", "crash-report.txt"),
            "time": report.get("time", "Recently"),
            "stacktrace": report.get("stacktrace", "")[:1500] if report.get("stacktrace") else "",
            "version_name": v_name
        }

    def get_latest_log(self, version_name=None, max_lines=200):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "1.20.1")
        log_file = os.path.join(VERSIONS_DIR, v_name, "logs", "latest.log")
        if not os.path.exists(log_file):
            return {"lines": ["Log file not found at " + log_file]}

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                return {"lines": [line.rstrip() for line in all_lines[-max_lines:]]}
        except Exception as e:
            return {"lines": [f"Error reading log: {e}"]}

    # ==========================================
    # SERVERS & MULTIPLAYER STUDIO API
    # ==========================================
    def get_servers(self):
        data = {}
        if os.path.exists(FRIENDS_PATH):
            try:
                with open(FRIENDS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        servers = data.get("servers", [])
        results = []
        for s in servers:
            name = s.get("name", "Minecraft Server")
            addr = s.get("address", "")
            cat = s.get("category", "Custom")
            ping_info = {"online": False, "latency": 0, "motd": "Offline", "players_online": 0, "players_max": 0}
            if network_hub and hasattr(network_hub, 'ping_minecraft_server') and addr:
                try:
                    p = network_hub.ping_minecraft_server(addr, timeout=1.2)
                    if p and p.get("online"):
                        ping_info = p
                except Exception:
                    pass

            results.append({
                "name": name,
                "address": addr,
                "category": cat,
                "ping": ping_info
            })
        return {"servers": results}

    def add_server(self, name, address, category="Custom"):
        data = {"friends": [], "servers": []}
        if os.path.exists(FRIENDS_PATH):
            try:
                with open(FRIENDS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        servers = data.get("servers", [])
        servers.append({"name": str(name).strip(), "address": str(address).strip(), "category": category})
        data["servers"] = servers
        try:
            with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_server(self, address_or_name):
        if not os.path.exists(FRIENDS_PATH):
            return {"success": False}
        try:
            with open(FRIENDS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            clean = str(address_or_name).lower().strip()
            data["servers"] = [s for s in data.get("servers", []) if s.get("name", "").lower() != clean and s.get("address", "").lower() != clean]
            with open(FRIENDS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_host_tunnel(self):
        cmd_str = self._get_cli_cmd('/host')
        cmd = f'start "Moon Launcher - Host Tunnel" {cmd_str}'
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return {"success": True, "message": "Host tunnel window opened"}

    def start_p2p_host(self, port=None, friends_only=True):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        try:
            import p2p_tunnel
            cfg = read_config()
            uname = cfg.get("username", "Player")
            moon_id = network_hub.get_or_create_moon_id(uname)
            v_dir = launcher.get_active_version_dir() if launcher else None
            detected_port = int(network_hub.detect_active_minecraft_port(v_dir) or 0)
            if not port and detected_port <= 0:
                ingame_host = network_hub.trigger_ingame_action(v_dir, "/ingame/host", {"friends_only": bool(friends_only)})
                if int(ingame_host.get("port") or 0) > 0:
                    detected_port = int(ingame_host["port"])
            use_port = int(port or detected_port or 25565)
            t_info = network_hub.get_tunnel_status() if hasattr(network_hub, "get_tunnel_status") else {}
            fb = str((t_info or {}).get("public_address") or "")
            res = p2p_tunnel.GLOBAL_P2P_HOST.start(moon_id, uname, local_port=use_port, friends_only=bool(friends_only), fallback_addr=fb)
            if res.get("success"):
                try:
                    network_hub.cloud_set_party_target(res.get("room_code") or moon_id, cfg.get("version_name", ""))
                except Exception:
                    pass
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def connect_p2p_peer(self, target_room_or_host):
        if not network_hub:
            return {"success": False, "error": "Network hub unavailable"}
        try:
            import p2p_tunnel
            cfg = read_config()
            uname = cfg.get("username", "Player")
            moon_id = network_hub.get_or_create_moon_id(uname)
            v_dir = launcher.get_active_version_dir() if launcher else None
            res = p2p_tunnel.GLOBAL_P2P_PEER.connect(moon_id, uname, str(target_room_or_host).strip(), version_dir=v_dir)
            if res.get("success") and res.get("local_address"):
                network_hub.copy_to_clipboard(res["local_address"])
                ingame_res = network_hub.trigger_ingame_action(
                    v_dir,
                    "/ingame/join",
                    {"address": res["local_address"], "name": f"Moon P2P ({str(target_room_or_host).strip()})"},
                )
                res["ingame_triggered"] = bool(ingame_res.get("success"))
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_p2p(self):
        import p2p_tunnel
        p2p_tunnel.GLOBAL_P2P_HOST.stop()
        p2p_tunnel.GLOBAL_P2P_PEER.stop()
        return {"success": True}

    def get_p2p_status(self):
        import p2p_tunnel
        return {
            "host": p2p_tunnel.GLOBAL_P2P_HOST.status(),
            "peer": p2p_tunnel.GLOBAL_P2P_PEER.status(),
        }

    def push_cloud_profile(self, version_name=None):
        import cloud_sync_mods
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else ""
        moon_id = network_hub.get_or_create_moon_id(cfg.get("username", "Player")) if network_hub else cfg.get("moon_id", "")
        return cloud_sync_mods.push_cloud_profile(moon_id, v_dir)

    def pull_cloud_profile(self, version_name=None):
        import cloud_sync_mods
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else ""
        moon_id = network_hub.get_or_create_moon_id(cfg.get("username", "Player")) if network_hub else cfg.get("moon_id", "")
        return cloud_sync_mods.pull_cloud_profile(moon_id, v_dir)

    def audit_instance_mods(self, version_name=None):
        import cloud_sync_mods
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else ""
        return cloud_sync_mods.check_modrinth_updates(v_dir)

    def update_instance_mod(self, old_file_name, download_url, new_filename, sha512="", version_name=None):
        import cloud_sync_mods
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else ""
        return cloud_sync_mods.apply_modrinth_update(v_dir, old_file_name, download_url, new_filename, expected_sha512=sha512)

    # ==========================================
    # INSTANCE DELETION & MANAGEMENT
    # ==========================================
    def delete_version(self, version_name):
        target_dir = os.path.join(VERSIONS_DIR, version_name)
        if not os.path.exists(target_dir):
            return {"success": False, "error": "Instance directory not found"}

        # Delete directory
        def _force_rm(func, path, exc_info):
            import stat
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        try:
            shutil.rmtree(target_dir, onerror=_force_rm)
            cfg = read_config()
            if cfg.get("version_name") == version_name:
                # pick next available version
                rem = [d for d in os.listdir(VERSIONS_DIR) if os.path.isdir(os.path.join(VERSIONS_DIR, d)) and not d.startswith((".", "_"))]
                new_v = rem[0] if rem else ""
                cfg["version_name"] = new_v
                write_config(cfg)
            return {"success": True, "deleted": version_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # UPDATE CHECKER API
    # ==========================================
    def check_updates(self):
        if updater and hasattr(updater, 'check_for_updates'):
            try:
                res = updater.check_for_updates(timeout=3.0)
                if res:
                    return res
            except Exception as e:
                print(f"Error checking updates: {e}")
        return {"update_available": False, "local_version": "v2.5.1"}

    def run_launcher_update(self):
        cmd_str = self._get_cli_cmd('/update')
        cmd = f'start "Moon Launcher - Studio Updater" {cmd_str}'
        subprocess.Popen(cmd, shell=True, cwd=BASE_DIR)
        return {"success": True}

    def start_package_install(self, slug_or_id, project_type=None):
        """
        Starts background package installation with live progress reporting.
        """
        cfg = read_config()
        v_name = cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else None

        INSTALL_MANAGER.reset(slug_or_id, project_type or "mod")

        def _bg_worker():
            def _progress_cb(**kw):
                INSTALL_MANAGER.update(**kw)

            try:
                if launcher and hasattr(launcher, "install_modrinth_package"):
                    res = launcher.install_modrinth_package(
                        slug_or_id,
                        project_type=project_type,
                        version_dir=v_dir,
                        non_interactive=True,
                        progress_cb=_progress_cb
                    )
                    if res and res.get("success"):
                        INSTALL_MANAGER.finish(True, result=res)
                    else:
                        INSTALL_MANAGER.finish(False, error=res.get("error") if res else "Unknown install error")
                else:
                    INSTALL_MANAGER.finish(False, error="Launcher package engine unavailable")
            except Exception as e:
                INSTALL_MANAGER.finish(False, error=str(e))

        t = threading.Thread(target=_bg_worker, daemon=True)
        t.start()
        return {"success": True, "message": "Installation worker started"}

    def get_install_status(self):
        return INSTALL_MANAGER.get_status()

    def install_package(self, slug_or_id, project_type=None):
        """
        Installs package in-process (modpack, mod, resourcepack, or shader)
        without opening a separate flashing CMD window.
        """
        try:
            cfg = read_config()
            v_name = cfg.get("version_name", "")
            v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else None
            if launcher and hasattr(launcher, "install_modrinth_package"):
                return launcher.install_modrinth_package(slug_or_id, project_type=project_type, version_dir=v_dir, non_interactive=True)
            else:
                return {"success": False, "error": "Launcher package engine unavailable"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def install_modpack(self, slug_or_id):
        return self.start_package_install(slug_or_id, "modpack")

    def create_instance(self, loader_type="fabric", mc_version="1.21.1"):
        """Installs Vanilla or Mod Loader (Fabric/Forge/NeoForge/Quilt) from GUI with live progress HUD."""
        ldr = str(loader_type or "vanilla").strip().lower()
        ver = str(mc_version or "1.21.1").strip()
        label = f"{ldr.capitalize()} {ver}"
        INSTALL_MANAGER.reset(label, "instance")
        INSTALL_MANAGER.update(title=f"Installing {label}", step=f"Preparing {label} runtime...", percent=10)

        def _bg():
            try:
                if not launcher:
                    INSTALL_MANAGER.finish(False, error="Launcher engine unavailable")
                    return
                if ldr == "vanilla":
                    INSTALL_MANAGER.update(step=f"Downloading Minecraft Vanilla {ver}...", percent=35)
                    res_dir = launcher.install_vanilla_version(ver)
                else:
                    INSTALL_MANAGER.update(step=f"Installing {ldr.capitalize()} loader for {ver}...", percent=35)
                    res_dir = launcher.install_mod_loader(ldr, ver)

                if res_dir and os.path.exists(res_dir):
                    INSTALL_MANAGER.update(step="Finalizing profile & Moon Sync...", percent=95)
                    INSTALL_MANAGER.finish(True, result={"version_name": os.path.basename(res_dir), "path": res_dir})
                else:
                    INSTALL_MANAGER.finish(False, error=f"Failed to install {label}. Check internet connection or version number.")
            except Exception as e:
                INSTALL_MANAGER.finish(False, error=str(e))

        threading.Thread(target=_bg, daemon=True).start()
        return {"success": True, "message": "Instance creation started"}

    def import_local_modpack(self):
        """Opens file picker for .mrpack or .zip modpack and installs it with live progress HUD."""
        selected = None
        try:
            if webview.windows and len(webview.windows) > 0:
                res = webview.windows[0].create_file_dialog(
                    webview.OPEN_DIALOG,
                    file_types=('Modpack Archive (*.mrpack;*.zip)', 'All files (*.*)')
                )
                if res and len(res) > 0:
                    selected = res[0]
        except Exception:
            pass
        if not selected or not os.path.exists(selected):
            return {"success": False, "cancelled": True}

        fname = os.path.basename(selected)
        INSTALL_MANAGER.reset(fname, "modpack")
        INSTALL_MANAGER.update(title=f"Importing {fname}", step="Unpacking modpack archive...", percent=15)

        def _bg():
            try:
                if selected.lower().endswith(".mrpack"):
                    res_dir = launcher.install_from_mrpack(selected, progress_cb=lambda **kw: INSTALL_MANAGER.update(**kw))
                else:
                    res_dir = launcher.install_from_zip(selected)
                if res_dir and os.path.exists(res_dir):
                    INSTALL_MANAGER.finish(True, result={"version_name": os.path.basename(res_dir), "path": res_dir})
                else:
                    INSTALL_MANAGER.finish(False, error="Failed to import modpack archive.")
            except Exception as e:
                INSTALL_MANAGER.finish(False, error=str(e))

        threading.Thread(target=_bg, daemon=True).start()
        return {"success": True, "filename": fname}

    def install_java_runtime(self, major_version=21):
        """Downloads and installs Eclipse Temurin Java JRE in 1 click into runtime/."""
        try:
            major = int(major_version)
        except Exception:
            major = 21
        INSTALL_MANAGER.reset(f"Java {major} LTS", "runtime")
        INSTALL_MANAGER.update(title=f"Installing Eclipse Temurin Java {major}", step="Connecting to Adoptium API...", percent=5)

        def _bg():
            try:
                res = launcher.download_adoptium_java(major, progress_cb=lambda **kw: INSTALL_MANAGER.update(**kw))
                if res and res.get("success"):
                    cfg = read_config()
                    cfg["java_path"] = res["java_path"]
                    write_config(cfg)
                    INSTALL_MANAGER.finish(True, result=res)
                else:
                    INSTALL_MANAGER.finish(False, error=res.get("error") if res else "Java install failed")
            except Exception as e:
                INSTALL_MANAGER.finish(False, error=str(e))

        threading.Thread(target=_bg, daemon=True).start()
        return {"success": True}

    def get_packs_list(self, pack_type="resourcepacks", version_name=None):
        """Lists resourcepacks or shaderpacks for the active instance."""
        folder_key = "shaderpacks" if pack_type in ("shader", "shaders", "shaderpacks") else "resourcepacks"
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        target_dir = os.path.join(VERSIONS_DIR, v_name, folder_key)
        if not os.path.exists(target_dir):
            return {"packs": [], "dir": target_dir, "type": folder_key, "version_name": v_name}

        packs = []
        for f in sorted(os.listdir(target_dir)):
            fp = os.path.join(target_dir, f)
            is_dir = os.path.isdir(fp)
            if not is_dir and not f.lower().endswith((".zip", ".zip.disabled", ".disabled")):
                continue
            enabled = not f.lower().endswith(".disabled")
            clean = f.replace(".zip.disabled", "").replace(".disabled", "").replace(".zip", "")
            size_mb = round((os.path.getsize(fp) if os.path.isfile(fp) else 0) / (1024 * 1024), 2)
            packs.append({
                "filename": f,
                "name": clean,
                "enabled": enabled,
                "is_dir": is_dir,
                "size_mb": size_mb,
            })
        return {"packs": packs, "dir": target_dir, "type": folder_key, "version_name": v_name}

    def toggle_pack(self, pack_type, filename, version_name=None):
        folder_key = "shaderpacks" if pack_type in ("shader", "shaders", "shaderpacks") else "resourcepacks"
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        target_dir = os.path.join(VERSIONS_DIR, v_name, folder_key)
        old_p = os.path.join(target_dir, filename)
        if not os.path.exists(old_p):
            return {"success": False, "error": "Pack not found"}
        new_name = filename[:-9] if filename.endswith(".disabled") else filename + ".disabled"
        try:
            os.rename(old_p, os.path.join(target_dir, new_name))
            return {"success": True, "new_name": new_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_pack(self, pack_type, filename, version_name=None):
        folder_key = "shaderpacks" if pack_type in ("shader", "shaders", "shaderpacks") else "resourcepacks"
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        fp = os.path.join(VERSIONS_DIR, v_name, folder_key, filename)
        if not os.path.exists(fp):
            return {"success": False, "error": "Pack not found"}
        try:
            if os.path.isdir(fp):
                shutil.rmtree(fp)
            else:
                os.remove(fp)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_folder(self, folder_type="root", version_name=None):
        cfg = read_config()
        v_name = version_name or cfg.get("version_name", "")
        v_dir = os.path.join(VERSIONS_DIR, v_name) if v_name else BASE_DIR

        if folder_type == "mods":
            target = os.path.join(v_dir, "mods") if os.path.exists(v_dir) else os.path.join(BASE_DIR, "mods")
        elif folder_type == "resourcepacks":
            target = os.path.join(v_dir, "resourcepacks") if os.path.exists(v_dir) else os.path.join(BASE_DIR, "resourcepacks")
        elif folder_type == "shaderpacks":
            target = os.path.join(v_dir, "shaderpacks") if os.path.exists(v_dir) else os.path.join(BASE_DIR, "shaderpacks")
        elif folder_type == "crash":
            target = os.path.join(v_dir, "crash-reports") if os.path.exists(v_dir) else BASE_DIR
        elif folder_type == "logs":
            target = os.path.join(v_dir, "logs") if os.path.exists(v_dir) else BASE_DIR
        elif folder_type == "saves":
            target = os.path.join(v_dir, "saves") if os.path.exists(v_dir) else BASE_DIR
        elif folder_type == "screenshots":
            target = os.path.join(v_dir, "screenshots") if os.path.exists(v_dir) else BASE_DIR
        elif folder_type == "version":
            target = v_dir if os.path.exists(v_dir) else BASE_DIR
        else:
            target = BASE_DIR

        os.makedirs(target, exist_ok=True)
        try:
            os.startfile(target)
            return {"success": True, "path": target}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_external_url(self, url):
        import webbrowser
        try:
            webbrowser.open(str(url).strip())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==============================================================================
    # P2P / PUBLIC ANYCAST MODPACK SHARING
    # ==============================================================================

    def start_pack_share(self, version_name=None):
        try:
            import pack_share
            v_name = version_name
            if not v_name:
                cfg = read_config()
                v_name = cfg.get("version_name", "")
            return pack_share.start_pack_share(v_name)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_pack_share(self):
        try:
            import pack_share
            return pack_share.stop_pack_share()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pack_share_status(self):
        try:
            import pack_share
            return pack_share.get_pack_share_status()
        except Exception as e:
            return {"running": False, "error": str(e)}

    def resolve_pack_code(self, code):
        try:
            import pack_share
            return pack_share.resolve_pack_code(code)
        except Exception as e:
            return {"found": False, "error": str(e)}

    def import_pack_by_code(self, code):
        try:
            import pack_share
            clean_code = pack_share.normalize_pack_code(code)
            INSTALL_MANAGER.reset(clean_code, "modpack")
            INSTALL_MANAGER.update(title=f"Importing {clean_code}", step="Mencari kode modpack di Cloud...")

            def _bg_import():
                def _cb(**kw):
                    INSTALL_MANAGER.update(**kw)

                try:
                    res = pack_share.download_and_install_shared_pack(clean_code, progress_cb=_cb)
                    if res and res.get("success"):
                        INSTALL_MANAGER.finish(True, result=res)
                    else:
                        INSTALL_MANAGER.finish(False, error=res.get("error") if res else "Gagal mengunduh modpack")
                except Exception as ex:
                    INSTALL_MANAGER.finish(False, error=str(ex))

            t = threading.Thread(target=_bg_import, daemon=True)
            t.start()
            return {"success": True, "message": "Import worker started"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_modrinth(self, query="", project_type="all", index="relevance", offset=0, limit=24):
        base_url = "https://api.modrinth.com/v2/search"
        params = {
            "limit": str(limit),
            "offset": str(offset),
            "index": index
        }
        if query:
            params["query"] = query
        facets = []
        if project_type and project_type != "all":
            facets.append([f"project_type:{project_type}"])
        if facets:
            params["facets"] = json.dumps(facets)

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "MoonLauncherStudioGUI/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {"hits": [], "total_hits": 0, "error": str(e)}

def main():
    html_file = resolve_resource("gui", "index.html")

    if not os.path.exists(html_file):
        print(f"Error: Could not find GUI html at {html_file}")
        sys.exit(1)

    api = MoonApi()
    if network_hub:
        try:
            if hasattr(network_hub, "start_mod_bridge_server"):
                network_hub.start_mod_bridge_server()
            if hasattr(network_hub, "start_cloud_presence_service"):
                network_hub.start_cloud_presence_service(read_config().get("username"))
        except Exception:
            pass
    if launcher and hasattr(launcher, "ensure_global_rpc"):
        try:
            launcher.ensure_global_rpc()
        except Exception:
            pass

    window = webview.create_window(
        title="Moon Launcher Studio",
        url=html_file,
        js_api=api,
        width=1240,
        height=780,
        min_size=(1020, 680),
        background_color="#FFF3E3"
    )

    def _on_gui_closed():
        if launcher and getattr(launcher, "GLOBAL_RPC", None):
            try:
                launcher.GLOBAL_RPC.close()
            except Exception:
                pass
        if network_hub and hasattr(network_hub, "stop_mod_bridge_server"):
            try:
                network_hub.stop_mod_bridge_server()
            except Exception:
                pass

    window.events.closed += _on_gui_closed
    webview.start(debug=False)

if __name__ == "__main__":
    cli_args = [a for a in sys.argv[1:] if not a.lower().endswith("launcher.py") and not a.lower().endswith("gui_app.py")]
    if cli_args:
        if launcher and hasattr(launcher, "main"):
            sys.argv = [sys.argv[0]] + cli_args
            try:
                launcher.main()
            except SystemExit:
                pass
            except Exception as e:
                print(f"Error running launcher command: {e}")
                try:
                    input("Press ENTER to exit...")
                except Exception:
                    pass
            sys.exit(0)
    main()
