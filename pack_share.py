"""
Moon Launcher - P2P & Live Cloud Modpack Sharing Engine
Enables instant 1-click modpack sharing via codes like MOON-PACK-9821.
Zero external websites, zero manual file transfers. Direct peer-to-peer / public anycast tunnel.
"""

import os
import sys
import time
import json
import random
import re
import socket
import threading
import subprocess
import zipfile
import urllib.request
import urllib.parse
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, ".moon_cache")
SHARES_CACHE_DIR = os.path.join(CACHE_DIR, "shares")
DOWNLOADS_DIR = os.path.join(CACHE_DIR, "downloads")
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")
VERSIONS_DIR = os.path.join(BASE_DIR, "versions")

os.makedirs(SHARES_CACHE_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(RUNTIME_DIR, exist_ok=True)

# Supabase Cloud Configuration
DEFAULT_SUPABASE_URL = "https://fcozsefkufbvztgniuwk.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_4NvjQ6A6TS9fBAFQpjWyaA_WjgP8BuZ"

# Active Host Sharing State
SHARE_LOCK = threading.Lock()
ACTIVE_SHARE = {
    "running": False,
    "code": None,
    "version_name": None,
    "public_url": None,
    "local_port": None,
    "size_bytes": 0,
    "mod_count": 0,
    "mc_version": None,
    "loader": None,
    "bytes_sent": 0,
    "active_downloads": 0,
    "start_time": None,
    "server_thread": None,
    "tunnel_proc": None,
    "heartbeat_thread": None,
    "zip_path": None
}

def get_supabase_creds():
    url = os.environ.get("MOON_SUPABASE_URL", "")
    key = os.environ.get("MOON_SUPABASE_KEY", "")
    if not url or not key:
        cfg_p = os.path.join(BASE_DIR, "launcher_config.json")
        if os.path.exists(cfg_p):
            try:
                with open(cfg_p, "r", encoding="utf-8-sig") as f:
                    d = json.load(f)
                    url = url or d.get("supabase_url", "")
                    key = key or d.get("supabase_key", "")
            except Exception:
                pass
    return (url or DEFAULT_SUPABASE_URL).rstrip('/'), (key or DEFAULT_SUPABASE_KEY)

def supabase_req(endpoint, method="GET", payload=None, extra_headers=None):
    sb_url, sb_key = get_supabase_creds()
    target = f"{sb_url}/rest/v1/{endpoint}"
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "User-Agent": "Moon-Launcher-PackShare/1.0"
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(target, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            raw = resp.read().decode('utf-8')
            return json.loads(raw) if raw.strip() else {}
    except Exception as e:
        return None

def normalize_pack_code(raw_code):
    """
    Normalizes code into standard MOON-PACK-XXXX format.
    Accepts: '9821', 'moon-pack-9821', 'MOON-PACK-9821', 'pack 9821', etc.
    """
    if not raw_code:
        return ""
    s = str(raw_code).strip().upper()
    s = re.sub(r'[\s_]+', '-', s)
    if re.match(r'^\d{4,6}$', s):
        return f"MOON-PACK-{s}"
    if s.startswith("PACK-"):
        return f"MOON-{s}"
    if not s.startswith("MOON-PACK-"):
        m = re.search(r'(MOON-PACK-\w+)', s)
        if m:
            return m.group(1)
        m2 = re.search(r'(\d{4,6})', s)
        if m2:
            return f"MOON-PACK-{m2.group(1)}"
    return s

def get_local_ip_addresses():
    """Returns list of local IP addresses (LAN, Radmin VPN 26.x.x.x, etc.)."""
    ips = []
    try:
        host = socket.gethostname()
        for ip in socket.gethostbyname_ex(host)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return list(dict.fromkeys(ips))

def scan_version_metadata(version_dir):
    """Quickly inspects a version directory to extract mc_version, loader, and mod count."""
    v_name = os.path.basename(version_dir)
    mc_ver = "1.20.1"
    loader = "Vanilla"
    mod_cnt = 0
    
    mods_d = os.path.join(version_dir, "mods")
    if os.path.exists(mods_d) and os.path.isdir(mods_d):
        try:
            mod_cnt = len([f for f in os.listdir(mods_d) if f.lower().endswith(".jar") and not f.lower().endswith(".disabled")])
        except Exception:
            pass

    # Check launcher_config.json inside version dir
    cfg_p = os.path.join(version_dir, "launcher_config.json")
    if os.path.exists(cfg_p):
        try:
            with open(cfg_p, "r", encoding="utf-8-sig") as f:
                c = json.load(f)
                mc_ver = c.get("minecraft_version") or c.get("mc_version") or mc_ver
                loader = c.get("loader") or loader
        except Exception:
            pass

    # Check version json files
    for f in os.listdir(version_dir):
        if f.lower().endswith(".json") and f.lower() not in ("launcher_config.json", "manifest.json", "usercache.json"):
            try:
                with open(os.path.join(version_dir, f), "r", encoding="utf-8-sig", errors="ignore") as jf:
                    jd = json.load(jf)
                    if "id" in jd:
                        raw_id = str(jd.get("id", ""))
                        if "forge" in raw_id.lower():
                            loader = "Forge"
                        elif "fabric" in raw_id.lower():
                            loader = "Fabric"
                        elif "neoforge" in raw_id.lower():
                            loader = "NeoForge"
                        elif "quilt" in raw_id.lower():
                            loader = "Quilt"
                    if "inheritsFrom" in jd:
                        mc_ver = jd.get("inheritsFrom") or mc_ver
                    elif "clientVersion" in jd:
                        mc_ver = jd.get("clientVersion") or mc_ver
            except Exception:
                pass
            break

    if mod_cnt > 0 and loader == "Vanilla":
        loader = "Forge"

    return {
        "version_name": v_name,
        "mc_version": mc_ver,
        "loader": loader,
        "mod_count": mod_cnt
    }

def package_instance_zip(version_dir, progress_cb=None):
    """
    Creates a clean, standalone .zip archive of a Minecraft instance.
    Includes: mods, config, defaultconfigs, scripts, kubejs, shaderpacks, resourcepacks,
              options.txt, servers.dat, icon.png, and client jar/json.
    Excludes: saves, logs, crash-reports, natives, caches.
    """
    if not os.path.exists(version_dir):
        raise FileNotFoundError(f"Instance folder does not exist: {version_dir}")

    meta = scan_version_metadata(version_dir)
    clean_name = re.sub(r'[\\/*?:"<>|]', '', meta["version_name"]).strip()
    out_zip = os.path.join(SHARES_CACHE_DIR, f"{clean_name}.zip")

    # Fast caching check: if zip exists and is newer than mods dir, reuse it!
    mods_d = os.path.join(version_dir, "mods")
    if os.path.exists(out_zip) and os.path.exists(mods_d):
        zip_mtime = os.path.getmtime(out_zip)
        mods_mtime = os.path.getmtime(mods_d)
        if zip_mtime > mods_mtime:
            if progress_cb:
                progress_cb(step="Using cached package...", percent=100)
            return out_zip, os.path.getsize(out_zip), meta

    EXCLUDE_DIRS = {
        'saves', 'logs', 'crash-reports', 'natives', '.fabric',
        '.mixin.out', '.cache', 'server-resource-packs', '__pycache__'
    }
    EXCLUDE_FILES = {
        'usercache.json', 'usernamecache.json', 'launch_args.txt', 'playit.log'
    }

    if progress_cb:
        progress_cb(step=f"Scanning files in {meta['version_name']}...", percent=5)

    files_to_pack = []
    total_raw_bytes = 0

    for root, dirs, files in os.walk(version_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in files:
            if f in EXCLUDE_FILES or f.endswith('.log') or f.endswith('.tmp') or f.endswith('.part'):
                continue
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, version_dir)
            sz = os.path.getsize(full_p)
            files_to_pack.append((full_p, rel_p, sz))
            total_raw_bytes += sz

    total_files = len(files_to_pack)
    if progress_cb:
        progress_cb(step=f"Compressing {total_files} files ({total_raw_bytes // (1024*1024)} MB)...", percent=10)

    # Hybrid fast compression: ZIP_STORED for jars/media, ZIP_DEFLATED for configs
    temp_zip = out_zip + ".tmp"
    if os.path.exists(temp_zip):
        try: os.remove(temp_zip)
        except Exception: pass

    with zipfile.ZipFile(temp_zip, 'w') as z:
        # Write manifest.json
        manifest_data = {
            "format_version": 1,
            "pack_name": meta["version_name"],
            "mc_version": meta["mc_version"],
            "loader": meta["loader"],
            "mod_count": meta["mod_count"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        z.writestr("moon_pack_manifest.json", json.dumps(manifest_data, indent=2))

        packed_bytes = 0
        for idx, (full_p, rel_p, sz) in enumerate(files_to_pack, 1):
            ext = os.path.splitext(full_p)[1].lower()
            method = zipfile.ZIP_STORED if ext in ('.jar', '.zip', '.png', '.webp', '.ogg', '.mp3') else zipfile.ZIP_DEFLATED
            z.write(full_p, rel_p, compress_type=method)
            packed_bytes += sz

            if progress_cb and (idx % 20 == 0 or idx == total_files):
                pct = int(10 + (idx / total_files) * 85)
                progress_cb(step=f"Packaging: {os.path.basename(rel_p)[:30]}", percent=pct)

    if os.path.exists(out_zip):
        try: os.remove(out_zip)
        except Exception: pass
    os.rename(temp_zip, out_zip)

    final_size = os.path.getsize(out_zip)
    if progress_cb:
        progress_cb(step="Packaging complete!", percent=100)

    return out_zip, final_size, meta


# ==============================================================================
# HTTP STREAMING SERVER FOR MODPACK TRANSFER
# ==============================================================================

import http.server
import socketserver

class MoonPackHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ('/manifest.json', '/manifest'):
            with SHARE_LOCK:
                st = dict(ACTIVE_SHARE)
            info = {
                "code": st.get("code"),
                "pack_name": st.get("version_name"),
                "mc_version": st.get("mc_version"),
                "loader": st.get("loader"),
                "mod_count": st.get("mod_count"),
                "size_bytes": st.get("size_bytes"),
                "uptime_seconds": int(time.time() - st["start_time"]) if st.get("start_time") else 0
            }
            body = json.dumps(info).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

        elif path in ('/pack.zip', '/download', '/pack'):
            with SHARE_LOCK:
                zip_p = ACTIVE_SHARE.get("zip_path")
                p_name = ACTIVE_SHARE.get("version_name") or "modpack"
            if not zip_p or not os.path.exists(zip_p):
                self.send_error(404, "Modpack package file not found")
                return

            total_size = os.path.getsize(zip_p)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(total_size))
            self.send_header('Content-Disposition', f'attachment; filename="{p_name}.zip"')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with SHARE_LOCK:
                ACTIVE_SHARE["active_downloads"] += 1

            try:
                with open(zip_p, 'rb') as f:
                    while True:
                        chunk = f.read(256 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        with SHARE_LOCK:
                            ACTIVE_SHARE["bytes_sent"] += len(chunk)
            except Exception:
                pass
            finally:
                with SHARE_LOCK:
                    ACTIVE_SHARE["active_downloads"] = max(0, ACTIVE_SHARE["active_downloads"] - 1)

        elif path in ('/ping', '/status'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok","moon_launcher":true}')

        else:
            self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        # Silent suppress default stderr console logging
        pass


def _find_free_port(start_port=25585):
    for p in range(start_port, start_port + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    return 25585


def _start_public_tunnel(local_port):
    """
    Attempts to start a high-speed Anycast public tunnel:
    1. Cloudflare Quick Tunnel (cloudflared) -> trycloudflare.com
    2. OpenSSH Pinggy tunnel (ssh.exe) -> pinggy-free.link
    """
    # 1. Check for cloudflared
    cf_bins = [
        shutil.which('cloudflared'),
        r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        r'C:\Program Files\cloudflared\cloudflared.exe',
        os.path.join(RUNTIME_DIR, 'cloudflared.exe')
    ]
    cf_path = next((b for b in cf_bins if b and os.path.exists(b)), None)

    if cf_path:
        try:
            cmd = [cf_path, 'tunnel', '--url', f'http://127.0.0.1:{local_port}']
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            # Scan stdout for trycloudflare.com
            for _ in range(35):
                line = p.stdout.readline()
                if not line and p.poll() is not None:
                    break
                m = re.search(r'(https://[a-zA-Z0-9\.\-]+\.trycloudflare\.com)', line)
                if m:
                    return p, m.group(1)
            p.kill()
        except Exception:
            pass

    # 2. Fallback to OpenSSH Pinggy tunnel
    ssh_bin = shutil.which('ssh')
    if ssh_bin:
        try:
            cmd = [
                ssh_bin, '-p', '443',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=8',
                f'-R0:localhost:{local_port}',
                'a.pinggy.io'
            ]
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            for _ in range(20):
                line = p.stdout.readline()
                if not line and p.poll() is not None:
                    break
                m = re.search(r'(https://[a-zA-Z0-9\.\-]+\.(?:free\.pinggy\.net|pinggy-free\.link))', line)
                if m:
                    return p, m.group(1)
            p.kill()
        except Exception:
            pass

    # Fallback: LAN / local IP only
    ips = get_local_ip_addresses()
    first_ip = ips[0] if ips else "127.0.0.1"
    return None, f"http://{first_ip}:{local_port}"


def _heartbeat_worker(pack_code, host_user, meta, public_url):
    """Refreshes presence entry in Supabase every 20 seconds while share is active."""
    while True:
        with SHARE_LOCK:
            if not ACTIVE_SHARE["running"] or ACTIVE_SHARE["code"] != pack_code:
                break
        try:
            payload = {
                "player_id": pack_code,
                "username": host_user,
                "status": "sharing_pack",
                "version_name": meta["version_name"],
                "mc_version": meta["mc_version"],
                "loader": meta["loader"],
                "mod_count": meta["mod_count"],
                "server_addr": public_url,
                "tunnel_active": True,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            supabase_req("presence", method="POST", payload=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})
        except Exception:
            pass
        time.sleep(20.0)


def start_pack_share(version_name, custom_code=None, port=None, progress_cb=None):
    """
    Starts sharing a modpack publicly with code MOON-PACK-XXXX.
    """
    global ACTIVE_SHARE

    # Stop any previous share session first
    stop_pack_share()

    v_dir = os.path.join(VERSIONS_DIR, version_name) if not os.path.isabs(version_name) else version_name
    if not os.path.exists(v_dir):
        return {"success": False, "error": f"Version '{version_name}' not found on disk."}

    # 1. Package the instance into zip
    zip_path, size_bytes, meta = package_instance_zip(v_dir, progress_cb=progress_cb)

    # 2. Pick port and bind HTTP server
    local_p = port or _find_free_port(25585)
    class ReuseServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    httpd = ReuseServer(('0.0.0.0', local_p), MoonPackHTTPHandler)
    server_t = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_t.start()

    # 3. Start tunnel
    if progress_cb:
        progress_cb(step="Membuka tunnel Anycast Cloudflare...", percent=92)
    tunnel_proc, public_url = _start_public_tunnel(local_p)
    if "trycloudflare.com" in public_url or "pinggy" in public_url:
        if progress_cb:
            progress_cb(step="Menstabilkan Anycast Global Edge...", percent=96)
        time.sleep(2.0)

    # 4. Generate code
    code = normalize_pack_code(custom_code) if custom_code else f"MOON-PACK-{random.randint(1000, 9999)}"

    # Master username
    cfg_p = os.path.join(BASE_DIR, "launcher_config.json")
    user_name = "Player"
    if os.path.exists(cfg_p):
        try:
            with open(cfg_p, "r", encoding="utf-8-sig") as f:
                user_name = json.load(f).get("username", "Player")
        except Exception:
            pass

    # 5. Register in Supabase presence
    payload = {
        "player_id": code,
        "username": user_name,
        "status": "sharing_pack",
        "version_name": meta["version_name"],
        "mc_version": meta["mc_version"],
        "loader": meta["loader"],
        "mod_count": meta["mod_count"],
        "server_addr": public_url,
        "tunnel_active": True,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    supabase_req("presence", method="POST", payload=payload, extra_headers={"Prefer": "resolution=merge-duplicates"})

    # 6. Start Heartbeat thread
    hb_t = threading.Thread(target=_heartbeat_worker, args=(code, user_name, meta, public_url), daemon=True)
    hb_t.start()

    with SHARE_LOCK:
        ACTIVE_SHARE = {
            "running": True,
            "code": code,
            "version_name": meta["version_name"],
            "public_url": public_url,
            "local_port": local_p,
            "size_bytes": size_bytes,
            "mod_count": meta["mod_count"],
            "mc_version": meta["mc_version"],
            "loader": meta["loader"],
            "bytes_sent": 0,
            "active_downloads": 0,
            "start_time": time.time(),
            "server_obj": httpd,
            "server_thread": server_t,
            "tunnel_proc": tunnel_proc,
            "heartbeat_thread": hb_t,
            "zip_path": zip_path,
            "host_user": user_name
        }

    if progress_cb:
        progress_cb(step="Ready to share!", percent=100)

    return {
        "success": True,
        "code": code,
        "pack_name": meta["version_name"],
        "public_url": public_url,
        "size_bytes": size_bytes,
        "mod_count": meta["mod_count"],
        "mc_version": meta["mc_version"],
        "loader": meta["loader"]
    }


def stop_pack_share():
    """Stops the active share server and cleans up Supabase record."""
    global ACTIVE_SHARE
    with SHARE_LOCK:
        if not ACTIVE_SHARE["running"]:
            return {"success": True, "message": "No active share running"}

        code = ACTIVE_SHARE.get("code")
        httpd = ACTIVE_SHARE.get("server_obj")
        tunnel = ACTIVE_SHARE.get("tunnel_proc")

        if tunnel:
            try:
                tunnel.terminate()
                tunnel.wait(timeout=2)
            except Exception:
                try: tunnel.kill()
                except Exception: pass

        if httpd:
            try:
                threading.Thread(target=httpd.shutdown, daemon=True).start()
            except Exception:
                pass

        ACTIVE_SHARE["running"] = False

    # Delete presence entry
    if code:
        try:
            supabase_req(f"presence?player_id=eq.{urllib.parse.quote(code)}", method="DELETE")
        except Exception:
            pass

    return {"success": True, "message": "Pack share stopped"}


def get_pack_share_status():
    """Returns real-time status of the current modpack share session."""
    with SHARE_LOCK:
        if not ACTIVE_SHARE["running"]:
            return {"running": False}

        now = time.time()
        uptime = int(now - ACTIVE_SHARE["start_time"]) if ACTIVE_SHARE["start_time"] else 0
        return {
            "running": True,
            "code": ACTIVE_SHARE["code"],
            "pack_name": ACTIVE_SHARE["version_name"],
            "public_url": ACTIVE_SHARE["public_url"],
            "local_port": ACTIVE_SHARE["local_port"],
            "size_bytes": ACTIVE_SHARE["size_bytes"],
            "mod_count": ACTIVE_SHARE["mod_count"],
            "mc_version": ACTIVE_SHARE["mc_version"],
            "loader": ACTIVE_SHARE["loader"],
            "bytes_sent": ACTIVE_SHARE["bytes_sent"],
            "active_downloads": ACTIVE_SHARE["active_downloads"],
            "uptime_seconds": uptime,
            "host_user": ACTIVE_SHARE.get("host_user", "Player")
        }


# ==============================================================================
# RECEIVER ENGINE (IMPORT BY MOON-PACK CODE)
# ==============================================================================

def resolve_pack_code(code_input):
    """
    Queries Supabase to find the download URL and metadata for a given MOON-PACK-XXXX code.
    """
    clean_code = normalize_pack_code(code_input)
    if not clean_code:
        return {"found": False, "error": "Kode kosong"}

    endpoint = f"presence?player_id=eq.{urllib.parse.quote(clean_code)}"
    res = supabase_req(endpoint, method="GET")

    if isinstance(res, list) and res:
        item = res[0]
        s_addr = item.get("server_addr", "").strip()
        if not s_addr:
            return {"found": False, "error": f"Host untuk {clean_code} sedang tidak aktif"}

        return {
            "found": True,
            "code": clean_code,
            "pack_name": item.get("version_name", "Shared Modpack"),
            "mc_version": item.get("mc_version", "1.20.1"),
            "loader": item.get("loader", "Forge"),
            "mod_count": item.get("mod_count", 0),
            "host_user": item.get("username", "Friend"),
            "download_url": f"{s_addr.rstrip('/')}/pack.zip",
            "manifest_url": f"{s_addr.rstrip('/')}/manifest.json",
            "updated_at": item.get("updated_at")
        }

    return {
        "found": False,
        "error": f"Kode '{clean_code}' tidak ditemukan. Pastikan temanmu masih membuka Moon Launcher dan menekan 'Share Modpack'!"
    }


def download_and_install_shared_pack(code_or_url, progress_cb=None):
    """
    Downloads and installs a shared modpack completely within Moon Launcher.
    Uses solid green progress bar (#90EE90) styling in GUI.
    """
    target_url = None
    pack_name = "Imported Modpack"
    meta = {}

    if str(code_or_url).startswith("http://") or str(code_or_url).startswith("https://"):
        target_url = str(code_or_url).strip()
    else:
        # Resolve code
        if progress_cb:
            progress_cb(step="Mencari kode modpack di Cloud...", percent=5)

        info = resolve_pack_code(code_or_url)
        if not info["found"]:
            return {"success": False, "error": info["error"]}

        target_url = info["download_url"]
        pack_name = info["pack_name"]
        meta = info

    clean_name = re.sub(r'[\\/*?:"<>|]', '', pack_name).strip()
    dest_zip = os.path.join(DOWNLOADS_DIR, f"{clean_name}.zip")

    if progress_cb:
        progress_cb(step=f"Menghubungkan ke host {meta.get('host_user', '')}...", percent=10)

    # 1. Download stream with speed and progress calculation
    req = urllib.request.Request(target_url, headers={
        "User-Agent": "Moon-Launcher/1.0",
        "Accept": "*/*"
    })

    try:
        resp = None
        for attempt in range(4):
            try:
                resp = urllib.request.urlopen(req, timeout=15)
                break
            except urllib.error.HTTPError as he:
                if he.code == 530 and attempt < 3:
                    if progress_cb:
                        progress_cb(step=f"Menunggu Anycast Edge siap (detik ke-{(attempt+1)*2})...", percent=12)
                    time.sleep(2.0)
                    continue
                raise
        if not resp:
            return {"success": False, "error": "Tidak dapat terhubung ke host modpack."}

        with resp:
            total_sz = resp.headers.get('Content-Length')
            total_sz = int(total_sz) if total_sz and total_sz.isdigit() else 0

            downloaded = 0
            t_start = time.time()
            last_ui_update = 0

            with open(dest_zip, 'wb') as out_f:
                while True:
                    chunk = resp.read(128 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_ui_update > 0.15:
                        last_ui_update = now
                        elapsed = max(0.01, now - t_start)
                        speed = downloaded / elapsed # bytes/sec
                        speed_mb = speed / (1024 * 1024)
                        
                        if total_sz > 0:
                            pct = int(10 + (downloaded / total_sz) * 75)
                            rem_bytes = max(0, total_sz - downloaded)
                            eta_s = int(rem_bytes / speed) if speed > 0 else 0
                            step_text = f"Downloading: {downloaded // (1024*1024)} MB / {total_sz // (1024*1024)} MB ({speed_mb:.1f} MB/s) - ETA: {eta_s}s"
                        else:
                            pct = 45
                            step_text = f"Downloading: {downloaded // (1024*1024)} MB ({speed_mb:.1f} MB/s)"

                        if progress_cb:
                            progress_cb(
                                percent=pct,
                                step=step_text,
                                downloaded_bytes=downloaded,
                                total_bytes=total_sz,
                                speed_str=f"{speed_mb:.1f} MB/s"
                            )

    except Exception as e:
        if os.path.exists(dest_zip):
            try: os.remove(dest_zip)
            except Exception: pass
        return {"success": False, "error": f"Download gagal: {str(e)}"}

    # 2. Extract and configure modpack
    if progress_cb:
        progress_cb(step=f"Mengekstrak dan mengonfigurasi '{clean_name}'...", percent=88)

    try:
        # Import install_from_zip from launcher.py
        import launcher
        new_dir = launcher.install_from_zip(dest_zip, custom_name=clean_name)
        if not new_dir or not os.path.exists(new_dir):
            return {"success": False, "error": "Gagal mengekstrak arsip modpack"}

        # Set newly installed version as active in launcher_config.json
        cfg_p = os.path.join(BASE_DIR, "launcher_config.json")
        if os.path.exists(cfg_p):
            try:
                with open(cfg_p, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
                cfg["version_name"] = clean_name
                with open(cfg_p, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass

        if progress_cb:
            progress_cb(step="Instalasi modpack selesai! Siap dimainkan.", percent=100)

        # Remove temp zip after successful install
        try: os.remove(dest_zip)
        except Exception: pass

        return {
            "success": True,
            "version_name": clean_name,
            "loader": meta.get("loader", "Forge"),
            "mc_version": meta.get("mc_version", "1.20.1"),
            "mod_count": meta.get("mod_count", 0)
        }

    except Exception as e:
        return {"success": False, "error": f"Gagal mengonfigurasi modpack: {str(e)}"}
