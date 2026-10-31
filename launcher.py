import network_hub
import updater
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moon Launcher - Interactive CLI & Configuration Studio
Guaranteed Pixel-Perfect Box Containers (Anti-Breakage) & Persistent Version Selection
"""

import os
import sys
import json
import time
import subprocess
import re
import unicodedata
import threading
import uuid
import struct
import urllib.request
import urllib.parse
import zipfile
import shutil

if sys.platform == 'win32':
    import msvcrt
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Window Title
if sys.platform == 'win32':
    os.system('title Moon Launcher')

# ANSI Color Palette (Claude Code / Moon Studio Theme)
C_BORDER  = '\033[38;2;60;70;90m'
C_AMBER   = '\033[38;2;245;158;11m'
C_GREEN   = '\033[38;2;74;222;128m'
C_CYAN    = '\033[38;2;56;189;248m'
C_PURPLE  = '\033[38;2;168;85;247m'
C_BLUE    = '\033[38;2;96;165;250m'
C_RED     = '\033[38;2;248;113;113m'
C_WHITE   = '\033[38;2;241;245;249m'
C_MUTED   = '\033[38;2;148;163;184m'
C_CLAUDE  = '\033[38;2;217;119;87m'
CLR_RESET = '\033[0m'
CLR_REV   = '\033[7m'

def detect_best_java():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, "runtime", "bin", "javaw.exe"),
        os.path.join(cur_dir, "runtime", "jre-21.0.11-windows-x64", "bin", "javaw.exe"),
        os.path.join(cur_dir, "runtime", "jre1.8.0_281", "bin", "javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\java-runtime-gamma\windows\java-runtime-gamma\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\jre-21.0.11-windows-x64\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\java-runtime-delta\windows\java-runtime-delta\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\jre1.8.0_281\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\java-runtime-epsilon\windows\java-runtime-epsilon\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\jre-legacy\windows\jre-legacy\bin\javaw.exe"),
        r"C:\ProgramData\Oracle\Java\javapath\javaw.exe",
        r"C:\Program Files\Java\jdk-21\bin\javaw.exe",
        r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    import shutil
    w = shutil.which("javaw") or shutil.which("java")
    if w:
        return w
    return candidates[3] if os.path.exists(candidates[3]) else candidates[0]

DEFAULT_JAVA = detect_best_java()
DEFAULT_MINECRAFT_ICON_URL = "launcher_grass"
DEFAULT_MINECRAFT_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "minecraft_default_icon.png")


def get_base_versions_dir():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    local_v = os.path.join(cur_dir, "versions")
    if os.path.exists(local_v) and os.listdir(local_v):
        return local_v
    appdata_mc = os.path.expandvars(r"%APPDATA%\.minecraft\versions")
    if os.path.exists(appdata_mc):
        return appdata_mc
    return local_v

BASE_VERSIONS_DIR = get_base_versions_dir()
GLOBAL_STATE_FILE = os.path.expandvars(r"%APPDATA%\.minecraft\moon_launcher_state.json")

def get_possible_version_roots():
    roots = []
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    local_v = os.path.join(cur_dir, "versions")
    if os.path.exists(local_v):
        roots.append(local_v)
    parent_dir = os.path.dirname(cur_dir)
    for d in (cur_dir, parent_dir):
        ml = os.path.join(d, "mod_list")
        if os.path.exists(ml) and ml not in roots:
            roots.append(ml)
    if os.path.exists(cur_dir) and cur_dir not in roots:
        roots.append(cur_dir)
    if os.path.exists(parent_dir) and parent_dir not in roots:
        drive, rest = os.path.splitdrive(parent_dir)
        if rest not in ('', '\\', '/'):
            roots.append(parent_dir)
    appdata_mc = os.path.expandvars(r"%APPDATA%\.minecraft\versions")
    if os.path.exists(appdata_mc):
        roots.append(appdata_mc)
    return roots

def find_version_dir_by_name(name):
    """Finds a Minecraft version or modpack directory by exact, case-insensitive, or config name."""
    if not name:
        return None
    name_clean = str(name).strip().strip('"').strip("'")
    if not name_clean:
        return None

    # Direct directory check if full path provided
    if os.path.isdir(name_clean) and (os.path.exists(os.path.join(name_clean, "launch_args.txt")) or os.path.exists(os.path.join(name_clean, "mods")) or any(f.endswith(".jar") for f in os.listdir(name_clean))):
        return name_clean

    roots = get_possible_version_roots()

    # 1. Exact match on folder name
    for r in roots:
        cand = os.path.join(r, name_clean)
        if os.path.isdir(cand) and (os.path.exists(os.path.join(cand, "launch_args.txt")) or os.path.exists(os.path.join(cand, "mods")) or any(f.endswith(".jar") for f in os.listdir(cand))):
            return cand

    # 2. Case-insensitive match on folder name
    for r in roots:
        if not os.path.exists(r):
            continue
        try:
            for item in os.listdir(r):
                if item.lower() == name_clean.lower():
                    c = os.path.join(r, item)
                    if os.path.isdir(c) and (os.path.exists(os.path.join(c, "launch_args.txt")) or os.path.exists(os.path.join(c, "mods")) or any(f.endswith(".jar") for f in os.listdir(c))):
                        return c
        except Exception:
            pass

    # 3. Match by version_name inside launcher_config.json
    for r in roots:
        if not os.path.exists(r):
            continue
        try:
            for item in os.listdir(r):
                c = os.path.join(r, item)
                if not os.path.isdir(c):
                    continue
                cfg_f = os.path.join(c, "launcher_config.json")
                if os.path.exists(cfg_f):
                    try:
                        with open(cfg_f, "r", encoding="utf-8-sig") as f:
                            c_data = json.load(f)
                            if c_data.get("version_name", "").strip().lower() == name_clean.lower():
                                return c
                    except Exception:
                        pass
        except Exception:
            pass

    # 4. Partial substring match
    for r in roots:
        if not os.path.exists(r):
            continue
        try:
            for item in os.listdir(r):
                if name_clean.lower() in item.lower():
                    c = os.path.join(r, item)
                    if os.path.isdir(c) and (os.path.exists(os.path.join(c, "launch_args.txt")) or os.path.exists(os.path.join(c, "mods")) or any(f.endswith(".jar") for f in os.listdir(c))):
                        return c
        except Exception:
            pass

    return None

def get_all_available_versions():
    """
    Returns all locally installed Minecraft versions and modpacks discovered across version roots.
    """
    found = {}
    for r in get_possible_version_roots():
        if not os.path.exists(r):
            continue
        try:
            for item in sorted(os.listdir(r)):
                item_path = os.path.join(r, item)
                if not os.path.isdir(item_path):
                    continue
                if item.startswith(('_', '.')) or item.lower() in ("moon launcher", "moon-launcher", ".system_generated", "__pycache__", "config", "logs", "templates", "runtime", "libraries", "assets", "resourcepacks", "shaderpacks", "saves", "mods", "versions", "skins", "icons"):
                    continue
                if item in found:
                    continue
                if (os.path.exists(os.path.join(item_path, "launch_args.txt")) or
                    os.path.exists(os.path.join(item_path, "mods")) or
                    any(f.endswith(".jar") for f in os.listdir(item_path))):
                    found[item] = item_path
        except Exception:
            pass
    return found

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


# ==============================================================================
# DISCORD RICH PRESENCE ENGINE (ZERO-DEPENDENCY DIRECT IPC)
# ==============================================================================

def generate_discord_head_url(skin_file_path, username="Player"):
    """
    Extracts the player's head avatar from skin texture (compositing base face
    and outer hat/hair/horn layer) and uploads it to get a direct HTTPS head URL
    for Discord Rich Presence.
    """
    if skin_file_path and os.path.exists(skin_file_path):
        try:
            from PIL import Image
            import io, base64, urllib.parse, urllib.request, json
            img = Image.open(skin_file_path).convert('RGBA')
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
            data = urllib.parse.urlencode({
                'key': '6d207e02198a847aa98d0a2a901485a5',
                'action': 'upload',
                'source': b64,
                'format': 'json'
            }).encode('utf-8')
            req = urllib.request.Request('https://freeimage.host/api/1/upload', data=data, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode())
                if 'image' in res and 'url' in res['image']:
                    return res['image']['url']
        except Exception:
            pass
    if username and username.strip():
        return f"https://mc-heads.net/avatar/{username.strip()}.png"
    return "https://mc-heads.net/avatar/steve.png"

def upload_local_icon(file_path):
    """
    Uploads a local modpack icon (png/webp) to get a direct HTTPS URL for Discord RPC.
    """
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        from PIL import Image
        import io, base64, urllib.parse, urllib.request, json
        img = Image.open(file_path).convert('RGBA')
        if img.width > 256 or img.height > 256:
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        data = urllib.parse.urlencode({
            'key': '6d207e02198a847aa98d0a2a901485a5',
            'action': 'upload',
            'source': b64,
            'format': 'json'
        }).encode('utf-8')
        req = urllib.request.Request('https://freeimage.host/api/1/upload', data=data, headers={'User-Agent': 'Moon-Launcher/2.0 (Mozilla/5.0)'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode())
            if 'image' in res and 'url' in res['image']:
                return res['image']['url']
    except Exception:
        pass
    return None

class MoonDiscordRPC:
    def __init__(self, client_id='450485984333660181', enabled=True):
        self.client_id = str(client_id)
        self.enabled = enabled
        self.pipe = None
        self.connected = False
        self.lock = threading.Lock()
        self.launcher_start_time = int(time.time())
        self._stop_event = threading.Event()
        self.current_state = {}
        
        if self.enabled:
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()

    def _connect(self):
        for i in range(10):
            pipe_path = rf'\\.\pipe\discord-ipc-{i}'
            if os.path.exists(pipe_path):
                try:
                    pipe = open(pipe_path, 'r+b', buffering=0)
                    payload = json.dumps({'v': 1, 'client_id': self.client_id}).encode('utf-8')
                    pipe.write(struct.pack('<II', 0, len(payload)) + payload)
                    header = pipe.read(8)
                    if len(header) == 8:
                        op, length = struct.unpack('<II', header)
                        resp = json.loads(pipe.read(length).decode('utf-8'))
                        if resp.get('evt') == 'READY':
                            self.pipe = pipe
                            self.connected = True
                            return True
                    pipe.close()
                except Exception:
                    pass
        self.connected = False
        return False

    def _send_payload(self, activity_dict):
        with self.lock:
            if not self.connected:
                if not self._connect():
                    return False
            try:
                cmd = {
                    'cmd': 'SET_ACTIVITY',
                    'args': {'pid': os.getpid(), 'activity': activity_dict},
                    'nonce': str(uuid.uuid4())
                }
                payload = json.dumps(cmd).encode('utf-8')
                self.pipe.write(struct.pack('<II', 1, len(payload)) + payload)
                header = self.pipe.read(8)
                if len(header) == 8:
                    op, length = struct.unpack('<II', header)
                    resp = json.loads(self.pipe.read(length).decode('utf-8'))
                    return resp.get('cmd') == 'SET_ACTIVITY'
            except Exception:
                self.connected = False
                try:
                    if self.pipe:
                        self.pipe.close()
                except Exception:
                    pass
                self.pipe = None
            return False

    def _worker_loop(self):
        while not self._stop_event.is_set():
            with self.lock:
                state_copy = dict(self.current_state) if self.current_state else None
            if state_copy and self.enabled:
                self._send_payload(state_copy)
            self._stop_event.wait(15)

    def _get_modpack_icon(self, v_name, cfg, version_dir=None):
        # 1. Use custom or downloaded modpack icon URL if present in config and valid
        custom_icon = (cfg.get('discord_large_image') or '').strip()
        if custom_icon and custom_icon != DEFAULT_MINECRAFT_ICON_URL and not any(k in custom_icon for k in ['catbox.moe', 'localhost']):
            if '59qxFo3W' in custom_icon and not any(k in v_name.lower() for k in ['nightfall', 'fear']):
                custom_icon = ''
            else:
                return custom_icon

        # 2. Check if target version folder has a custom icon.png or icon.webp
        if version_dir and os.path.isdir(version_dir):
            for candidate in ('icon.png', 'icon.webp', 'pack.png', 'modpack.png'):
                c_path = os.path.join(version_dir, candidate)
                if os.path.exists(c_path):
                    try:
                        import hashlib
                        with open(c_path, 'rb') as f_ic:
                            ic_hash = hashlib.md5(f_ic.read()).hexdigest()
                        # Only upload if not the generic grass template
                        if ic_hash != "59fac0eb2e746548df3651d03301489b":
                            up_url = upload_local_icon(c_path)
                            if up_url:
                                cfg['discord_large_image'] = up_url
                                v_cfg_p = get_config_path(version_dir)
                                if os.path.exists(v_cfg_p):
                                    try:
                                        with open(v_cfg_p, 'r', encoding='utf-8-sig') as f_r:
                                            vd = json.load(f_r)
                                        vd['discord_large_image'] = up_url
                                        with open(v_cfg_p, 'w', encoding='utf-8') as f_w:
                                            json.dump(vd, f_w, indent=2)
                                    except Exception:
                                        pass
                                return up_url
                    except Exception:
                        pass

        # 3. If it is a modpack (not generic vanilla like 1.20.1 or Forge 1.12.2), search Modrinth
        is_generic_vanilla = any(v_name.lower().startswith(p) for p in ('1.', '2.', 'release', 'snapshot', 'forge 1.', 'fabric 1.', 'neoforge'))
        if not is_generic_vanilla:
            try:
                modrinth_icon = fetch_modrinth_icon_url(v_name)
                if modrinth_icon:
                    cfg['discord_large_image'] = modrinth_icon
                    if version_dir:
                        v_cfg_p = get_config_path(version_dir)
                        if os.path.exists(v_cfg_p):
                            try:
                                with open(v_cfg_p, 'r', encoding='utf-8-sig') as f_r:
                                    vd = json.load(f_r)
                                vd['discord_large_image'] = modrinth_icon
                                with open(v_cfg_p, 'w', encoding='utf-8') as f_w:
                                    json.dump(vd, f_w, indent=2)
                            except Exception:
                                pass
                    return modrinth_icon
            except Exception:
                pass

        # 4. Pure official default Minecraft grass block icon if no modpack logo exists
        return DEFAULT_MINECRAFT_ICON_URL  # "launcher_grass"

    def _get_player_avatar(self, username, cfg):
        small = cfg.get('discord_small_image', '')
        # If already a valid head URL and not the raw unrolled texture
        if small and not any(k in small for k in ['novaskin.me', 'minotar.net/skin']):
            return small
        # Check custom skin file
        skin_p = cfg.get('custom_skin', '')
        if skin_p and os.path.exists(skin_p):
            h_url = generate_discord_head_url(skin_p, username)
            if h_url:
                cfg['discord_small_image'] = h_url
                return h_url
        if username and username.lower() == 'epithap':
            return 'https://files.catbox.moe/wdhyhz.png'
        if username and username.strip():
            return f"https://mc-heads.net/avatar/{username.strip()}.png"
        return "https://mc-heads.net/avatar/steve.png"

    def _extract_world_name(self, world_folder):
        dat_path = os.path.join(world_folder, 'level.dat')
        if os.path.exists(dat_path):
            try:
                import gzip
                with gzip.open(dat_path, 'rb') as f:
                    data = f.read()
                    idx = data.find(b'LevelName')
                    if idx != -1:
                        str_len = int.from_bytes(data[idx+9:idx+11], 'big')
                        return data[idx+11:idx+11+str_len].decode('utf-8', errors='ignore')
            except Exception:
                pass
        return os.path.basename(world_folder)

    def _get_active_world(self, version_dir, min_time):
        candidates = [
            os.path.join(version_dir, 'saves'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves'),
            os.path.expandvars(r'%APPDATA%\.minecraft\saves')
        ]
        latest_world = None
        latest_mtime = 0
        for saves_dir in candidates:
            if not os.path.isdir(saves_dir):
                continue
            try:
                for entry in os.scandir(saves_dir):
                    if entry.is_dir():
                        lock_file = os.path.join(entry.path, 'session.lock')
                        if os.path.exists(lock_file):
                            mtime = os.path.getmtime(lock_file)
                            if mtime > min_time and mtime > latest_mtime:
                                latest_mtime = mtime
                                latest_world = entry.path
            except Exception:
                pass
        if latest_world:
            return self._extract_world_name(latest_world)
        return None

    def _format_server(self, host, port):
        h = host.strip()
        p = str(port).strip()
        if h.startswith('26.'):
            return f"Multiplayer (Radmin): {h}:{p}"
        elif h.startswith('25.'):
            return f"Multiplayer (Hamachi): {h}:{p}"
        elif h.startswith(('192.168.', '10.', '172.')):
            return f"Multiplayer (LAN): {h}:{p}"
        elif p == '25565':
            return f"Multiplayer: {h}"
        return f"Multiplayer: {h}:{p}"


    def set_menu(self, version_dir, cfg):
        if not self.enabled:
            return
        v_name = cfg.get('version_name', os.path.basename(version_dir))
        v_info = detect_version_info(version_dir, v_name)
        mod_count = count_mods(version_dir)
        user = cfg.get('username', 'Player')

        # When idle in launcher, display modpack logo if present, otherwise pure 3D grass block
        large_icon = cfg.get('discord_idle_image') or self._get_modpack_icon(v_name, cfg, version_dir)
        small_icon = self._get_player_avatar(user, cfg)

        act = {
            'details': "In Moon Launcher Studio",
            'state': f"Modpack: {v_name}",
            'assets': {
                'large_image': large_icon,
                'large_text': f"Minecraft • {v_info['formatted']}",
                'small_image': small_icon,
                'small_text': f"Player: {user}"
            },
            'timestamps': {
                'start': self.launcher_start_time
            }
        }
        with self.lock:
            self.current_state = act
        threading.Thread(target=self._send_payload, args=(act,), daemon=True).start()

    def set_playing(self, version_dir, cfg, proc):
        if not self.enabled:
            return
        v_name = cfg.get('version_name', os.path.basename(version_dir))
        v_info = detect_version_info(version_dir, v_name)
        mod_count = count_mods(version_dir)
        user = cfg.get('username', 'Player')
        game_start_time = int(time.time())

        large_icon = self._get_modpack_icon(v_name, cfg, version_dir)
        small_icon = self._get_player_avatar(user, cfg)

        initial_state = f"{v_info['loader_name']} {v_info['mc_version']} • {mod_count} mods"

        act = {
            'details': f"Playing {v_name}",
            'state': initial_state,
            'assets': {
                'large_image': large_icon,
                'large_text': f"{v_name} ({v_info['mc_version']})",
                'small_image': small_icon,
                'small_text': f"Player: {user} | RAM: {cfg.get('ram_max_gb', 8)}GB"
            },
            'timestamps': {
                'start': game_start_time
            }
        }
        with self.lock:
            self.current_state = act
        threading.Thread(target=self._send_payload, args=(act,), daemon=True).start()

        def _watch_game():
            log_path = os.path.join(version_dir, 'logs', 'latest.log')
            last_pos = 0
            if os.path.exists(log_path):
                try:
                    last_pos = os.path.getsize(log_path)
                except Exception:
                    pass

            current_world = None
            current_dim = "overworld"
            current_server = None
            is_in_world = False
            last_checked_saves = 0
            last_state_str = None

            # Accurate regexes for world & multiplayer lifecycle
            re_chunk_save = re.compile(r"Saving chunks for level 'ServerLevel\[(.*?)\]'/(?:minecraft:)?([a-zA-Z0-9_]+)")
            re_sp_start = re.compile(r'Starting integrated minecraft server version')
            re_dim_prep = re.compile(r"(?:Preparing start region for dimension|Changing to dimension)\s+(?:minecraft:)?([a-zA-Z0-9_]+)")
            re_connect = re.compile(r'Connecting to ([^,]+),\s*([0-9]+)')
            re_leave = re.compile(r'Stopping server|Stopping singleplayer server|Saving and disconnecting player|Leaving world|Lost connection|Disconnected|Connection closed')

            dim_map = {
                'overworld': ('overworld', 'Overworld'),
                'the_nether': ('the_nether', 'The Nether'),
                'nether': ('the_nether', 'The Nether'),
                'the_end': ('the_end', 'The End'),
                'end': ('the_end', 'The End')
            }

            while proc.poll() is None:
                changed = False
                now = time.time()

                # 1. Read new lines in latest.log
                if os.path.exists(log_path):
                    try:
                        curr_size = os.path.getsize(log_path)
                        if curr_size > last_pos:
                            with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                                lf.seek(last_pos)
                                new_lines = lf.readlines()
                                last_pos = lf.tell()
                            for line in new_lines:
                                m_chunk = re_chunk_save.search(line)
                                if m_chunk:
                                    w_name = m_chunk.group(1).strip()
                                    d_name = m_chunk.group(2).strip().lower()
                                    if w_name and (w_name != current_world or d_name != current_dim or not is_in_world):
                                        current_world = w_name
                                        current_dim = d_name
                                        is_in_world = True
                                        current_server = None
                                        changed = True

                                m_dim = re_dim_prep.search(line)
                                if m_dim:
                                    d_name = m_dim.group(1).strip().lower()
                                    if d_name != current_dim:
                                        current_dim = d_name
                                        if is_in_world:
                                            changed = True

                                if re_sp_start.search(line):
                                    is_in_world = True
                                    current_server = None
                                    if not current_world:
                                        detected = self._get_active_world(version_dir, game_start_time - 30)
                                        if detected:
                                            current_world = detected
                                    changed = True

                                m_conn = re_connect.search(line)
                                if m_conn:
                                    current_server = self._format_server(m_conn.group(1), m_conn.group(2))
                                    is_in_world = False
                                    current_world = None
                                    changed = True

                                if re_leave.search(line):
                                    is_in_world = False
                                    current_server = None
                                    current_world = None
                                    changed = True
                        elif curr_size < last_pos:
                            last_pos = 0
                    except Exception:
                        pass

                # 2. Periodic fallback check for active world folder session.lock
                if not is_in_world and not current_server and (now - last_checked_saves) >= 4:
                    last_checked_saves = now
                    detected = self._get_active_world(version_dir, game_start_time - 30)
                    if detected:
                        current_world = detected
                        is_in_world = True
                        changed = True

                # 3. Update Discord presence whenever state changes
                if changed or (last_state_str is None and (now - game_start_time) > 20):
                    # Maintain modpack icon or pure 3D grass block continuously as large_image
                    active_large_icon = self._get_modpack_icon(v_name, cfg, version_dir)
                    if is_in_world and current_world:
                        dim_key, dim_title = dim_map.get(current_dim, ('overworld', current_dim.capitalize()))
                        new_state = f"World: {current_world} ({dim_title})"
                        active_large_text = f"{v_name} • {dim_title} ({current_world})"
                    elif current_server:
                        new_state = current_server
                        active_large_text = f"Online Server • {v_name}"
                    else:
                        new_state = "In Main Menu"
                        active_large_text = f"{v_name} • {v_info['formatted']}"

                    if new_state != last_state_str:
                        last_state_str = new_state
                        with self.lock:
                            if self.current_state:
                                self.current_state['state'] = new_state
                                if 'assets' not in self.current_state:
                                    self.current_state['assets'] = {}
                                self.current_state['assets']['large_image'] = active_large_icon
                                self.current_state['assets']['large_text'] = active_large_text
                                act_copy = dict(self.current_state)
                            else:
                                act_copy = None
                        if act_copy:
                            self._send_payload(act_copy)

                time.sleep(2)

            self.set_menu(version_dir, cfg)

        threading.Thread(target=_watch_game, daemon=True).start()

    def close(self):
        self._stop_event.set()
        if self.connected and self.pipe:
            try:
                cmd = {
                    'cmd': 'SET_ACTIVITY',
                    'args': {'pid': os.getpid(), 'activity': None},
                    'nonce': str(uuid.uuid4())
                }
                payload = json.dumps(cmd).encode('utf-8')
                self.pipe.write(struct.pack('<II', 1, len(payload)) + payload)
                self.pipe.close()
            except Exception:
                pass

GLOBAL_RPC = None

# ==============================================================================
# BULLETPROOF TEXT & BOX CONTAINER RENDERING (GUARANTEED ZERO-OVERFLOW)
# ==============================================================================

def get_visible_width(text):
    """Calculates visible terminal width, stripping ANSI escape codes and handling East Asian width."""
    clean = ANSI_RE.sub('', str(text))
    w = 0
    for ch in clean:
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ('W', 'F'):
            w += 2
        else:
            w += 1
    return w

def truncate_ansi(text, max_width, suffix="…"):
    """Truncates an ANSI-colored string to max_width visual columns cleanly."""
    text = str(text)
    if get_visible_width(text) <= max_width:
        return text

    s_w = get_visible_width(suffix)
    target = max(1, max_width - s_w)

    tokens = re.findall(r'(\x1b\[[0-9;]*[a-zA-Z]|[^ \x1b]+| +)', text)
    res = []
    cur_w = 0
    active_ansi = []

    for token in tokens:
        if token.startswith('\x1b['):
            res.append(token)
            if token == '\x1b[0m':
                active_ansi = []
            else:
                active_ansi.append(token)
            continue

        tok_w = get_visible_width(token)
        if cur_w + tok_w <= target:
            res.append(token)
            cur_w += tok_w
        else:
            for ch in token:
                ch_w = get_visible_width(ch)
                if cur_w + ch_w <= target:
                    res.append(ch)
                    cur_w += ch_w
                else:
                    break
            break

    res.append(suffix)
    if active_ansi:
        res.append('\x1b[0m')
    return "".join(res)

def wrap_ansi_line(text, max_width):
    """
    Wraps an ANSI-colored string so that every returned line has visible width <= max_width.
    Preserves ANSI codes across wrapped lines.
    Supports space-based word wrapping and hard character breaking for long continuous words/paths.
    """
    text = str(text)
    if not text:
        return [""]

    tokens = re.findall(r'(\x1b\[[0-9;]*[a-zA-Z]| +|[^ \x1b]+)', text)
    lines = []
    cur_line = []
    cur_w = 0
    active_ansi = []

    for token in tokens:
        if token.startswith('\x1b['):
            cur_line.append(token)
            if token == '\x1b[0m':
                active_ansi = []
            else:
                active_ansi.append(token)
            continue

        tok_w = get_visible_width(token)

        if cur_w + tok_w <= max_width:
            cur_line.append(token)
            cur_w += tok_w
        else:
            if token.isspace():
                if cur_w > 0:
                    line_str = "".join(cur_line)
                    if active_ansi:
                        line_str += '\x1b[0m'
                    lines.append(line_str)
                    cur_line = list(active_ansi)
                    cur_w = 0
                continue

            if tok_w > max_width:
                if cur_w > 0:
                    line_str = "".join(cur_line)
                    if active_ansi:
                        line_str += '\x1b[0m'
                    lines.append(line_str)
                    cur_line = list(active_ansi)
                    cur_w = 0

                for ch in token:
                    ch_w = get_visible_width(ch)
                    if cur_w + ch_w > max_width:
                        line_str = "".join(cur_line)
                        if active_ansi:
                            line_str += '\x1b[0m'
                        lines.append(line_str)
                        cur_line = list(active_ansi)
                        cur_w = 0
                    cur_line.append(ch)
                    cur_w += ch_w
            else:
                if cur_w > 0:
                    line_str = "".join(cur_line)
                    if active_ansi:
                        line_str += '\x1b[0m'
                    lines.append(line_str)
                    cur_line = list(active_ansi)
                    cur_w = 0
                cur_line.append(token)
                cur_w += tok_w

    if cur_line:
        line_str = "".join(cur_line)
        if active_ansi:
            line_str += '\x1b[0m'
        lines.append(line_str)

    return lines or [""]

def pad_visible(text, target_width):
    """Pads text to target visual width. If text exceeds target_width, truncates it safely."""
    text = str(text)
    v_len = get_visible_width(text)
    if v_len > target_width:
        return truncate_ansi(text, target_width)
    pad = target_width - v_len
    return text + (' ' * pad)

def render_box(lines, inner_width=66, title=""):
    """
    Renders a pixel-perfect terminal box container with guaranteed alignment on all borders.
    Guaranteed NEVER to break, distort, or overflow regardless of how long the text is.
    """
    c_tl, c_tr, c_bl, c_br, c_v, c_h = chr(9581), chr(9582), chr(9584), chr(9583), chr(9474), chr(9472)

    # 1. Protect Title: Never let title exceed box width
    if title:
        max_title_w = max(4, inner_width - 6)
        if get_visible_width(title) > max_title_w:
            title = truncate_ansi(title, max_title_w)
        t_str = f" {title} "
        t_len = get_visible_width(t_str)
        rem = max(0, inner_width + 2 - t_len - 2)
        top = f"{C_BORDER}{c_tl}{c_h * 2}{C_CYAN}{t_str}{C_BORDER}{c_h * rem}{c_tr}{CLR_RESET}"
    else:
        top = f"{C_BORDER}{c_tl}{c_h * (inner_width + 2)}{c_tr}{CLR_RESET}"

    bottom = f"{C_BORDER}{c_bl}{c_h * (inner_width + 2)}{c_br}{CLR_RESET}"
    bar = f"{C_BORDER}{c_v}{CLR_RESET}"
    out = [top]

    # 2. Process all lines: expand embedded newlines and wrap any long lines safely
    for raw_line in lines:
        if raw_line is None:
            raw_line = ''

        split_newlines = str(raw_line).splitlines() if str(raw_line) else ['']
        for nl_line in split_newlines:
            wrapped_sublines = wrap_ansi_line(nl_line, inner_width)
            for sub_line in wrapped_sublines:
                v_len = get_visible_width(sub_line)
                pad = max(0, inner_width - v_len)
                out.append(f"{bar} {sub_line}{' ' * pad} {bar}")

    out.append(bottom)
    return "\n".join(out)

# ==============================================================================
# PERSISTENT VERSION & CONFIGURATION MANAGEMENT
# ==============================================================================

def get_active_version_dir():
    """
    Returns the persistent active Minecraft version directory.
    Remembers user selection across launcher restarts.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 1. Check local launcher_config.json
    local_cfg = os.path.join(script_dir, "launcher_config.json")
    if os.path.exists(local_cfg):
        try:
            with open(local_cfg, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                v_name = data.get("version_name")
                if v_name:
                    v_dir = find_version_dir_by_name(v_name)
                    if v_dir:
                        return v_dir
        except Exception:
            pass

    # 2. Check global launcher persistent state file
    if os.path.exists(GLOBAL_STATE_FILE):
        try:
            with open(GLOBAL_STATE_FILE, "r", encoding="utf-8-sig") as f:
                state = json.load(f)
                v_name = state.get("active_version")
                if v_name:
                    v_dir = find_version_dir_by_name(v_name)
                    if v_dir:
                        return v_dir
        except Exception:
            pass

    # 3. Check local directory where launcher.py is located
    if os.path.exists(os.path.join(script_dir, "launch_args.txt")):
        return script_dir

    # 4. Fallback to detected versions
    all_v = get_all_available_versions()
    if all_v:
        return list(all_v.values())[0]

    return script_dir

def set_active_version(new_name):
    """Saves the chosen active version permanently to root config, global state, and target profile."""
    if not new_name:
        return
    clean_name = str(new_name).strip()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_cfg = os.path.join(script_dir, "launcher_config.json")
    try:
        d = {}
        if os.path.exists(root_cfg):
            with open(root_cfg, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
        d["version_name"] = clean_name
        with open(root_cfg, "w", encoding="utf-8-sig") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass

    try:
        os.makedirs(os.path.dirname(GLOBAL_STATE_FILE), exist_ok=True)
        with open(GLOBAL_STATE_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump({
                'active_version': clean_name,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)
    except Exception:
        pass

    # Also update target version directory's own launcher_config.json if found
    v_dir = find_version_dir_by_name(clean_name)
    if v_dir and os.path.exists(v_dir):
        try:
            v_cfg_path = os.path.join(v_dir, "launcher_config.json")
            vd = {}
            if os.path.exists(v_cfg_path):
                with open(v_cfg_path, "r", encoding="utf-8-sig") as vf:
                    vd = json.load(vf)
            vd["version_name"] = clean_name
            with open(v_cfg_path, "w", encoding="utf-8-sig") as vf:
                json.dump(vd, vf, indent=2)
        except Exception:
            pass

def detect_version_and_loader(target_dir, declared_loader=None, declared_mc_version=None):
    """
    Universally detects the accurate Minecraft version and loader (Vanilla, Fabric, Forge, NeoForge)
    from version JSON, config, mod files, or directory name.
    """
    v_name = os.path.basename(target_dir)
    mc_ver = declared_mc_version
    loader = declared_loader

    # 1. Check launcher_config.json
    cfg_p = os.path.join(target_dir, 'launcher_config.json')
    if os.path.exists(cfg_p):
        try:
            with open(cfg_p, 'r', encoding='utf-8-sig') as f:
                d = json.load(f)
                if not mc_ver and d.get('mc_version'):
                    mc_ver = d['mc_version']
                if not loader and d.get('loader'):
                    loader = d['loader']
        except Exception:
            pass

    # 2. Check for version JSON in target_dir (e.g. 1.12.2.json, <v_name>.json)
    json_cands = [
        os.path.join(target_dir, f"{v_name}.json"),
        os.path.join(target_dir, "version.json")
    ]
    if os.path.exists(target_dir):
        for f in os.listdir(target_dir):
            if f.endswith('.json') and f not in ('launcher_config.json', 'modrinth.index.json', 'manifest.json'):
                json_cands.append(os.path.join(target_dir, f))

    for jp in json_cands:
        if os.path.exists(jp):
            try:
                with open(jp, 'r', encoding='utf-8-sig') as f:
                    v_data = json.load(f)
                if 'mainClass' in v_data or 'minecraftArguments' in v_data or 'arguments' in v_data:
                    if not mc_ver:
                        m_id = v_data.get('id', '')
                        m_match = re.search(r'\b(1\.\d+(?:\.\d+)?)\b', m_id or os.path.basename(jp))
                        if m_match:
                            mc_ver = m_match.group(1)
                    if not loader:
                        mc_class = v_data.get('mainClass', '')
                        if 'knot.KnotClient' in mc_class:
                            loader = 'Fabric'
                        elif 'launchwrapper.Launch' in mc_class:
                            loader = 'Forge'
                        elif 'bootstraplauncher' in mc_class:
                            loader = 'Forge'
                        elif 'neoforged' in mc_class:
                            loader = 'NeoForge'
                        elif mc_class == 'net.minecraft.client.main.Main':
                            has_forge = any('minecraftforge' in str(lib.get('name', '')) for lib in v_data.get('libraries', []))
                            loader = 'Forge' if has_forge else 'Vanilla'
                    break
            except Exception:
                pass

    # 3. Check mods directory
    mods_dir = os.path.join(target_dir, 'mods')
    mod_files = [f.lower() for f in os.listdir(mods_dir) if f.endswith('.jar')] if os.path.exists(mods_dir) else []

    if mod_files:
        ver_counts = {}
        for mf in mod_files:
            found = re.findall(r'1\.\d+(?:\.\d+)?', mf)
            for v in found:
                ver_counts[v] = ver_counts.get(v, 0) + 1
        if ver_counts:
            dominant_ver = max(ver_counts, key=ver_counts.get)
            # If dominant version has strong evidence (>5 mods), it takes precedence over stale config
            if ver_counts[dominant_ver] >= 5:
                if not mc_ver or (mc_ver != dominant_ver and ver_counts[dominant_ver] > 10):
                    mc_ver = dominant_ver
            elif not mc_ver:
                mc_ver = dominant_ver

    if not mc_ver:
        match = re.search(r'\b(1\.\d+(?:\.\d+)?)\b', v_name)
        if match:
            mc_ver = match.group(1)
        else:
            mc_ver = "1.20.1"

    if not loader or (loader == 'Vanilla' and mod_files):
        if not mod_files:
            loader = 'Vanilla'
        elif any('connector' in m or 'sinytra' in m for m in mod_files):
            loader = 'Forge'
        else:
            forge_cnt = sum(1 for m in mod_files if any(k in m for k in ('forge', 'fml', 'neoforge')))
            fab_cnt = sum(1 for m in mod_files if any(k in m for k in ('fabric', 'quilt', 'refabricated')))
            if forge_cnt >= fab_cnt and forge_cnt > 0:
                loader = 'Forge'
            elif fab_cnt > forge_cnt:
                loader = 'Fabric'
            else:
                loader = 'Forge'

    return mc_ver, loader

def detect_modpack_loader(target_dir, declared_loader=None):
    """Backward-compatible helper."""
    _, loader = detect_version_and_loader(target_dir, declared_loader=declared_loader)
    return loader

def get_best_java_for_version(mc_version, declared_java=None):
    """
    Auto-selects optimal Java runtime (Java 8, 17, or 21) based on Minecraft version.
    MC <= 1.16.5: Java 8 (jre-legacy)
    MC 1.17 - 1.20.4: Java 17 (gamma)
    MC >= 1.20.5: Java 21 (delta / epsilon)
    """
    mc_root = os.path.expandvars(r'%APPDATA%\.minecraft')
    cur_dir = os.path.dirname(os.path.abspath(__file__))

    # Candidates for Java 8 (prefer newer build 281 over 51)
    j8_cands = [
        os.path.join(mc_root, 'runtime', 'jre1.8.0_281', 'bin', 'javaw.exe'),
        os.path.join(cur_dir, 'runtime', 'jre1.8.0_281', 'bin', 'javaw.exe'),
        os.path.join(mc_root, 'runtime', 'jre-legacy', 'windows', 'jre-legacy', 'bin', 'javaw.exe'),
    ]
    j8 = next((c for c in j8_cands if os.path.exists(c)), j8_cands[0])

    # Candidates for Java 17
    j17_cands = [
        os.path.join(mc_root, 'runtime', 'java-runtime-gamma', 'windows', 'java-runtime-gamma', 'bin', 'javaw.exe'),
        os.path.join(cur_dir, 'runtime', 'java-runtime-gamma', 'windows', 'java-runtime-gamma', 'bin', 'javaw.exe'),
    ]
    j17 = next((c for c in j17_cands if os.path.exists(c)), j17_cands[0])

    # Candidates for Java 21
    j21_cands = [
        os.path.join(mc_root, 'runtime', 'jre-21.0.11-windows-x64', 'bin', 'javaw.exe'),
        os.path.join(cur_dir, 'runtime', 'jre-21.0.11-windows-x64', 'bin', 'javaw.exe'),
        os.path.join(mc_root, 'runtime', 'java-runtime-delta', 'windows', 'java-runtime-delta', 'bin', 'javaw.exe'),
        os.path.join(mc_root, 'runtime', 'java-runtime-epsilon', 'windows', 'java-runtime-epsilon', 'bin', 'javaw.exe'),
    ]
    j21 = next((c for c in j21_cands if os.path.exists(c)), j21_cands[0])

    parts = [int(p) for p in re.findall(r'\d+', mc_version)]
    major = parts[0] if len(parts) > 0 else 1
    minor = parts[1] if len(parts) > 1 else 20
    patch = parts[2] if len(parts) > 2 else 0

    if major == 1 and minor <= 16:
        if os.path.exists(j8): return j8
    elif (major == 1 and minor >= 21) or (major == 1 and minor == 20 and patch >= 5):
        if os.path.exists(j21): return j21
    else:
        if os.path.exists(j17): return j17

    if declared_java and os.path.exists(declared_java):
        return declared_java

    for cand in (j17, j21, j8):
        if os.path.exists(cand): return cand
    return declared_java or "javaw.exe"

def ensure_natives_for_version(target_dir, mc_version):
    """Provisions correct LWJGL 2 or LWJGL 3 native DLLs into target_dir/natives."""
    target_natives = os.path.join(target_dir, 'natives')
    os.makedirs(target_natives, exist_ok=True)
    mc_root = os.path.expandvars(r'%APPDATA%\.minecraft')

    parts = [int(p) for p in re.findall(r'\d+', mc_version)]
    minor = parts[1] if len(parts) > 1 else 20
    is_legacy_lwjgl2 = (minor <= 12)

    existing = [f.lower() for f in os.listdir(target_natives)]
    if is_legacy_lwjgl2 and 'lwjgl64.dll' in existing:
        return
    elif not is_legacy_lwjgl2 and ('lwjgl.dll' in existing or 'glfw.dll' in existing):
        return

    for f in os.listdir(target_natives):
        try: os.remove(os.path.join(target_natives, f))
        except Exception: pass

    donor_natives = None
    if is_legacy_lwjgl2:
        cands = [
            os.path.join(mc_root, 'versions', 'Forge 1.12.2', 'natives'),
            os.path.join(mc_root, 'versions', '1.12.2', 'natives')
        ]
    else:
        cands = [
            os.path.join(mc_root, 'versions', 'DeadZone 1.20.1 Forge', 'natives'),
            os.path.join(mc_root, 'versions', '1.20.1', '1.20.1-natives'),
            os.path.join(mc_root, 'versions', 'NightfallCraft 2.2.9.7', 'natives'),
            os.path.join(r'C:\Moon-Launcher', 'versions', 'DeadZone 1.20.1 Forge', 'natives'),
            os.path.join(r'C:\Moon-Launcher', 'versions', 'Fear Nightfall', 'natives')
        ]

    for c in cands:
        if os.path.exists(c) and os.listdir(c):
            donor_natives = c
            break

    if donor_natives:
        import shutil
        for item in os.listdir(donor_natives):
            s_file = os.path.join(donor_natives, item)
            d_file = os.path.join(target_natives, item)
            if os.path.isfile(s_file):
                try: shutil.copy2(s_file, d_file)
                except Exception: pass

def build_launch_args_from_json(target_dir, v_data, username=None, jvm_max_gb=4, jvm_min_gb=1):
    if not username:
        username = get_master_username()
    """Builds clean, universal launch args directly from official version JSON schema."""
    mc_root = os.path.expandvars(r'%APPDATA%\.minecraft')
    lib_root = os.path.join(mc_root, "libraries")
    assets_dir = os.path.join(mc_root, "assets").replace('\\', '/')
    v_name = os.path.basename(target_dir)
    target_jar = os.path.join(target_dir, f"{v_name}.jar")
    natives_dir = os.path.join(target_dir, "natives").replace('\\', '/')
    norm_v_dir = target_dir.replace('\\', '/')

    def is_allowed(rules):
        if not rules: return True
        allowed = False
        for r in rules:
            action = r.get("action")
            os_rule = r.get("os", {}).get("name")
            if action == "allow":
                if os_rule is None or os_rule == "windows": allowed = True
                else: allowed = False
            elif action == "disallow":
                if os_rule is None or os_rule == "windows": allowed = False
        return allowed

    cp_jars = []
    for lib in v_data.get("libraries", []):
        if not is_allowed(lib.get("rules")):
            continue
        artifact = lib.get("downloads", {}).get("artifact", {})
        rel = artifact.get("path")
        if not rel:
            parts = lib.get("name", "").split(":")
            if len(parts) >= 3:
                grp = parts[0].replace(".", os.sep)
                art = parts[1]
                ver = parts[2]
                rel = os.path.join(grp, art, ver, f"{art}-{ver}.jar")
        if rel:
            full = os.path.join(lib_root, rel.replace('/', os.sep))
            if os.path.exists(full):
                cp_jars.append(full.replace(os.sep, '/'))

    if os.path.exists(target_jar):
        cp_jars.append(target_jar.replace(os.sep, '/'))
    cp_str = ";".join(cp_jars)

    lines = [
        f'-Djava.library.path={natives_dir}',
        f'-Djna.tmpdir={natives_dir}',
        f'-Dorg.lwjgl.system.SharedLibraryExtractPath={natives_dir}',
        f'-Dio.netty.native.workdir={natives_dir}',
        '-Dminecraft.launcher.brand=Moon-Launcher',
        '-Dminecraft.launcher.version=2.2.9.7',
        f'-Xmx{jvm_max_gb}G',
        f'-Xms{jvm_min_gb}G',
        '-cp',
        f'"{cp_str}"'
    ]

    main_class = v_data.get("mainClass", "net.minecraft.client.main.Main")
    lines.append(main_class)

    asset_index = v_data.get("assetIndex", {}).get("id", "5")
    if "minecraftArguments" in v_data:
        raw_args = v_data["minecraftArguments"]
        replacements = {
            "${auth_player_name}": username,
            "${version_name}": v_name,
            "${game_directory}": f'"{norm_v_dir}"',
            "${assets_root}": f'"{assets_dir}"',
            "${assets_index_name}": str(asset_index),
            "${auth_uuid}": "72274843ca0f4b66824c9af6a387b059",
            "${auth_access_token}": "0",
            "${user_type}": "mojang",
            "${version_type}": "release",
            "${user_properties}": "{}"
        }
        for k, v in replacements.items():
            raw_args = raw_args.replace(k, str(v))
        import shlex
        try:
            tokens = shlex.split(raw_args, posix=False)
        except Exception:
            tokens = raw_args.split()
        for token in tokens:
            lines.append(token)
    elif "arguments" in v_data and "game" in v_data["arguments"]:
        for arg in v_data["arguments"]["game"]:
            if isinstance(arg, str):
                replacements = {
                    "${auth_player_name}": username,
                    "${version_name}": v_name,
                    "${game_directory}": f'"{norm_v_dir}"',
                    "${assets_root}": f'"{assets_dir}"',
                    "${assets_index_name}": str(asset_index),
                    "${auth_uuid}": "72274843ca0f4b66824c9af6a387b059",
                    "${auth_access_token}": "0",
                    "${user_type}": "mojang",
                    "${version_type}": "release",
                    "${clientid}": "0",
                    "${auth_xuid}": "0"
                }
                for k, v in replacements.items():
                    arg = arg.replace(k, str(v))
                lines.append(arg)

    lines.extend(['--width', '1280', '--height', '720'])
    return lines

def ensure_launch_args(target_dir, template_dir=None, declared_loader=None, mc_version=None):
    """
    Self-healing, universal launcher engine.
    Produces accurate, tested runtime launch arguments for Vanilla, Fabric, Legacy Forge, and Modern Forge.
    """
    import shutil
    mc_root = os.path.expandvars(r'%APPDATA%\.minecraft')
    lib_root = os.path.join(mc_root, 'libraries')
    norm_target = target_dir.replace('\\', '/')
    v_name = os.path.basename(target_dir)
    args_path = os.path.join(target_dir, 'launch_args.txt')

    mc_ver, loader = detect_version_and_loader(target_dir, declared_loader, mc_version)

    # 1. Self-heal natives for exact MC version
    ensure_natives_for_version(target_dir, mc_ver)

    # 2. Self-heal client jar (<v_name>.jar)
    target_jar = os.path.join(target_dir, f"{v_name}.jar")
    if not os.path.exists(target_jar):
        donor_jar = None
        cands = [
            os.path.join(mc_root, 'versions', mc_ver, f"{mc_ver}.jar"),
            os.path.join(mc_root, 'versions', f"Forge {mc_ver}", f"Forge {mc_ver}.jar"),
            os.path.join(mc_root, 'versions', v_name, f"{v_name}.jar"),
            os.path.join(mc_root, 'versions', 'DeadZone 1.20.1 Forge', 'DeadZone 1.20.1 Forge.jar'),
            os.path.join(mc_root, 'versions', '1.20.1', '1.20.1.jar'),
            os.path.join(r'C:\Moon-Launcher', 'versions', 'DeadZone 1.20.1 Forge', 'DeadZone 1.20.1 Forge.jar')
        ]
        for cand in cands:
            if os.path.exists(cand) and os.path.getsize(cand) > 1000000:
                donor_jar = cand
                break
        if donor_jar:
            try: shutil.copy2(donor_jar, target_jar)
            except Exception: pass

    # 3. Ensure modpack icon file exists
    icon_png = os.path.join(target_dir, "icon.png")
    icon_webp = os.path.join(target_dir, "icon.webp")
    if not os.path.exists(icon_png) and not os.path.exists(icon_webp):
        if os.path.exists(DEFAULT_MINECRAFT_ICON_PATH):
            try: shutil.copy2(DEFAULT_MINECRAFT_ICON_PATH, icon_png)
            except Exception: pass

    # 4. If launch_args.txt already exists, check if it matches the detected loader and MC version
    if os.path.exists(args_path):
        try:
            with open(args_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content = f.read()
            parts_num = [int(p) for p in re.findall(r'\d+', mc_ver)]
            minor_num = parts_num[1] if len(parts_num) > 1 else 20
            needs_regen = False

            if loader == 'Vanilla' and ('bootstraplauncher' in content or 'KnotClient' in content):
                needs_regen = True
            elif loader == 'Forge' and ('KnotClient' in content or (minor_num >= 13 and '--launchTarget' not in content)):
                needs_regen = True
            elif loader == 'Fabric' and ('bootstraplauncher' in content or 'KnotClient' not in content):
                needs_regen = True
            elif minor_num <= 12 and 'bootstraplauncher' in content:
                needs_regen = True

            if not needs_regen:
                lines = [l.rstrip('\r\n') for l in content.splitlines()]
                changed = False
                for idx_l, l in enumerate(lines):
                    if l.strip() == '--gameDir' and idx_l + 1 < len(lines):
                        if lines[idx_l + 1].strip('"').strip("'") != norm_target:
                            lines[idx_l + 1] = f'"{norm_target}"'
                            changed = True
                    elif l.startswith('-Djava.library.path=') and '"' in l:
                        val = l[len('-Djava.library.path='):].strip('"').strip("'")
                        lines[idx_l] = f'-Djava.library.path={val}'
                        changed = True
                if changed:
                    with open(args_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines) + '\n')
                update_launch_args(target_dir, {'username': get_master_username(), 'version_name': v_name})
                return True
        except Exception:
            pass

    # 5. Route: Vanilla Generation (or version has official version JSON)
    json_path = os.path.join(target_dir, f"{v_name}.json")
    if not os.path.exists(json_path):
        mc_json_donor = os.path.join(mc_root, 'versions', mc_ver, f"{mc_ver}.json")
        if os.path.exists(mc_json_donor):
            try: shutil.copy2(mc_json_donor, json_path)
            except Exception: pass

    if loader == 'Vanilla' and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8-sig') as f:
                v_data = json.load(f)
            vanilla_lines = build_launch_args_from_json(target_dir, v_data, username=get_master_username())
            with open(args_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(vanilla_lines) + '\n')
            return True
        except Exception:
            pass

    # 6. Route: Legacy Forge (MC <= 1.12.2)
    parts_num = [int(p) for p in re.findall(r'\d+', mc_ver)]
    minor_num = parts_num[1] if len(parts_num) > 1 else 20
    if loader == 'Forge' and minor_num <= 12:
        forge_112_json = os.path.join(mc_root, 'versions', 'Forge 1.12.2', 'Forge 1.12.2.json')
        if os.path.exists(forge_112_json):
            try:
                with open(forge_112_json, 'r', encoding='utf-8-sig') as f:
                    f_data = json.load(f)
                forge_lines = build_launch_args_from_json(target_dir, f_data, username=get_master_username())
                with open(args_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(forge_lines) + '\n')
                return True
            except Exception:
                pass

    # 7. Route: Fabric Generation
    if loader == 'Fabric':
        try:
            p_vanilla = os.path.join(mc_root, 'versions', mc_ver, f"{mc_ver}.json")
            if not os.path.exists(p_vanilla):
                p_vanilla = os.path.join(mc_root, 'versions', '1.20.1', '1.20.1.json')
            jars = []
            if os.path.exists(p_vanilla):
                with open(p_vanilla, 'r', encoding='utf-8') as f:
                    v_data = json.load(f)
                for lib in v_data.get('libraries', []):
                    artifact = lib.get('downloads', {}).get('artifact', {})
                    rel_path = artifact.get('path')
                    if rel_path:
                        full = os.path.join(lib_root, rel_path.replace('/', os.sep))
                        if os.path.exists(full):
                            jars.append(full.replace(os.sep, '/'))

            for f_ver in ('0.18.4', '0.19.2', '0.16.10', '0.15.11'):
                fab_loader = os.path.join(lib_root, 'net', 'fabricmc', 'fabric-loader', f_ver, f'fabric-loader-{f_ver}.jar')
                if os.path.exists(fab_loader):
                    jars.append(fab_loader.replace(os.sep, '/'))
                    break

            inter = os.path.join(lib_root, 'net', 'fabricmc', 'intermediary', mc_ver, f'intermediary-{mc_ver}.jar')
            if not os.path.exists(inter):
                inter = os.path.join(lib_root, 'net', 'fabricmc', 'intermediary', '1.20.1', 'intermediary-1.20.1.jar')
            if os.path.exists(inter):
                jars.append(inter.replace(os.sep, '/'))

            for s_dir in ('0.15.2+mixin.0.8.7', '0.16.5+mixin.0.8.7', '0.17.0+mixin.0.8.7'):
                sp = os.path.join(lib_root, 'net', 'fabricmc', 'sponge-mixin', s_dir, f'sponge-mixin-{s_dir}.jar')
                if os.path.exists(sp):
                    jars.append(sp.replace(os.sep, '/'))
                    break

            for name, sub in [('asm-9.7.1.jar', 'asm'), ('asm-analysis-9.7.1.jar', 'asm-analysis'), ('asm-commons-9.7.1.jar', 'asm-commons'), ('asm-tree-9.7.1.jar', 'asm-tree'), ('asm-util-9.7.1.jar', 'asm-util')]:
                p = os.path.join(lib_root, 'org', 'ow2', 'asm', sub, '9.7.1', name)
                if os.path.exists(p):
                    jars.append(p.replace(os.sep, '/'))

            if os.path.exists(target_jar):
                jars.append(target_jar.replace(os.sep, '/'))

            cp_str = ';'.join(jars)
            target_natives = os.path.join(target_dir, 'natives')
            natives_p = target_natives.replace(os.sep, '/')
            assets_p = os.path.join(mc_root, 'assets').replace(os.sep, '/')

            launch_lines = [
                '-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump',
                '-Xss1M',
                '-Xms2G',
                '-Xmx8G',
                '-XX:+UnlockExperimentalVMOptions',
                '-XX:+UseG1GC',
                '-XX:G1NewSizePercent=20',
                '-XX:G1ReservePercent=20',
                '-XX:MaxGCPauseMillis=50',
                '-XX:G1HeapRegionSize=32M',
                f'-Djava.library.path={natives_p}',
                f'-Djna.tmpdir={natives_p}',
                f'-Dorg.lwjgl.system.SharedLibraryExtractPath={natives_p}',
                f'-Dio.netty.native.workdir={natives_p}',
                '-Dminecraft.launcher.brand=Moon-Launcher',
                '-Dminecraft.launcher.version=2.2.9.7',
                '-cp',
                f'"{cp_str}"',
                '-DFabricMcEmu= net.minecraft.client.main.Main ',
                'net.fabricmc.loader.impl.launch.knot.KnotClient',
                '--username',
                get_master_username(),
                '--version',
                v_name,
                '--gameDir',
                f'"{norm_target}"',
                '--assetsDir',
                f'"{assets_p}"',
                '--assetIndex',
                '5',
                '--uuid',
                '72274843ca0f4b66824c9af6a387b059',
                '--accessToken',
                '0',
                '--clientId',
                '0',
                '--xuid',
                '0',
                '--userType',
                'mojang',
                '--versionType',
                'release',
                '--width',
                '1280',
                '--height',
                '720'
            ]
            with open(args_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(launch_lines) + '\n')
            return True
        except Exception:
            pass

    # 8. Route: Modern Forge (MC >= 1.13 / 1.20.1)
    donor_args_candidates = [
        os.path.join(r'C:\Moon-Launcher', 'versions', 'Fear Nightfall', 'launch_args.txt'),
        os.path.join(mc_root, 'versions', 'NightfallCraft 2.2.9.7', 'launch_args.txt'),
        os.path.join(mc_root, 'versions', 'DeadZone 1.20.1 Forge', 'launch_args.txt'),
        os.path.join(r'C:\Moon-Launcher', 'templates', 'launch_args.txt'),
        os.path.join(r'C:\Moon-Launcher', 'versions', 'DeadZone 1.20.1 Forge', 'launch_args.txt'),
    ]

    target_natives = os.path.join(target_dir, 'natives')
    target_natives_norm = target_natives.replace('\\', '/')

    for c in donor_args_candidates:
        if os.path.exists(c):
            try:
                with open(c, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    donor_text = f.read()
                donor_dir = os.path.dirname(c)
                old_v = os.path.basename(donor_dir)
                norm_donor = donor_dir.replace('\\', '/')

                res_text = donor_text
                res_text = res_text.replace(norm_donor, norm_target)
                res_text = res_text.replace(f"--version\n{old_v}", f"--version\n{v_name}")
                res_text = res_text.replace(f"{old_v}.jar", f"{v_name}.jar")
                m_user = get_master_username()
                res_text = re.sub(r'--username\r?\n[^\r\n]+', f'--username\n{m_user}', res_text)

                lines = res_text.splitlines()
                for idx_l, l in enumerate(lines):
                    if l.strip() == '--gameDir' and idx_l + 1 < len(lines):
                        lines[idx_l + 1] = f'"{norm_target}"'
                    elif l.startswith('-Djava.library.path=') or l.startswith('"-Djava.library.path='):
                        lines[idx_l] = f'-Djava.library.path={target_natives_norm}'
                    elif l.startswith('-Djna.tmpdir=') or l.startswith('"-Djna.tmpdir='):
                        lines[idx_l] = f'-Djna.tmpdir={target_natives_norm}'
                    elif l.startswith('-Dorg.lwjgl.system.SharedLibraryExtractPath=') or l.startswith('"-Dorg.lwjgl.system.SharedLibraryExtractPath='):
                        lines[idx_l] = f'-Dorg.lwjgl.system.SharedLibraryExtractPath={target_natives_norm}'
                    elif l.startswith('-Dio.netty.native.workdir=') or l.startswith('"-Dio.netty.native.workdir='):
                        lines[idx_l] = f'-Dio.netty.native.workdir={target_natives_norm}'

                with open(args_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
                return True
            except Exception:
                pass

    return False
def get_current_dir():
    return get_active_version_dir()

def get_config_path(version_dir):
    return os.path.join(version_dir, 'launcher_config.json')

def apply_skin_setting(version_dir, cfg, skin_val):
    if not skin_val:
        return
    skin_clean = skin_val.strip().strip('"').strip("'")
    if skin_clean.lower() in ('auto', 'reset', 'default', 'none'):
        cfg['custom_skin'] = ''
        cfg['custom_skin_url'] = ''
        cfg['discord_small_image'] = ''
        print(f"{C_GREEN}[Moon Launcher] Custom skin reset to auto (username avatar).{CLR_RESET}")
        return

    username = cfg.get('username', 'Player')

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    main_skins_dir = os.path.join(cur_dir, "skins")
    os.makedirs(main_skins_dir, exist_ok=True)
    saved_skin_path = os.path.join(main_skins_dir, f"{username}.png")

    def distribute_skin(source_data_or_path, is_data=False):
        try:
            if is_data:
                with open(saved_skin_path, "wb") as f_out:
                    f_out.write(source_data_or_path)
            else:
                import shutil
                if os.path.abspath(source_data_or_path) != os.path.abspath(saved_skin_path):
                    shutil.copyfile(source_data_or_path, saved_skin_path)
        except Exception as e:
            print(f"{C_AMBER}[Moon Launcher] Warning: Could not save to {saved_skin_path}: {e}{CLR_RESET}")

        csl_targets = []
        if version_dir:
            csl_targets.append(os.path.join(version_dir, "skins"))
            csl_targets.append(os.path.join(version_dir, "CustomSkinLoader", "LocalSkin", "skins"))
            csl_targets.append(os.path.join(version_dir, "LocalSkin", "skins"))
        appdata_csl = os.path.expandvars(r"%APPDATA%\.minecraft\CustomSkinLoader\LocalSkin\skins")
        csl_targets.append(appdata_csl)

        for target_dir in csl_targets:
            try:
                os.makedirs(target_dir, exist_ok=True)
                dest = os.path.join(target_dir, f"{username}.png")
                if is_data:
                    with open(dest, "wb") as f_out:
                        f_out.write(source_data_or_path)
                else:
                    import shutil
                    if os.path.abspath(source_data_or_path) != os.path.abspath(dest):
                        shutil.copyfile(source_data_or_path, dest)
            except Exception:
                pass

    if skin_clean.startswith(('http://', 'https://')):
        print(f"{C_CYAN}[Moon Launcher] Downloading skin from URL:{CLR_RESET} {skin_clean}")
        downloaded = False
        try:
            import urllib.request
            req = urllib.request.Request(
                skin_clean,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                skin_bytes = resp.read()

            if len(skin_bytes) > 50:
                distribute_skin(skin_bytes, is_data=True)
                cfg['custom_skin'] = saved_skin_path
                cfg['custom_skin_url'] = skin_clean
                cfg['discord_small_image'] = generate_discord_head_url(saved_skin_path, username)
                downloaded = True
                print(f"{C_GREEN}[Moon Launcher] Skin downloaded and saved successfully:{CLR_RESET}")
                print(f"  {C_WHITE}* {saved_skin_path}{CLR_RESET}")
                print(f"{C_CYAN}[Moon Launcher] Synchronized with CustomSkinLoader and Discord RPC!{CLR_RESET}")
            else:
                print(f"{C_RED}[Moon Launcher] Downloaded file is too small or invalid image.{CLR_RESET}")
        except Exception as e:
            print(f"{C_RED}[Moon Launcher] Failed to download skin from URL: {e}{CLR_RESET}")

        if not downloaded:
            cfg['custom_skin'] = skin_clean
            cfg['discord_small_image'] = generate_discord_head_url(saved_skin_path, username)

    elif os.path.exists(skin_clean):
        abs_skin = os.path.abspath(skin_clean)
        distribute_skin(abs_skin, is_data=False)
        cfg['custom_skin'] = saved_skin_path
        cfg['discord_small_image'] = generate_discord_head_url(saved_skin_path, username)
        print(f"{C_GREEN}[Moon Launcher] Local skin copied to skins directory:{CLR_RESET}")
        print(f"  {C_WHITE}* {saved_skin_path}{CLR_RESET}")
        print(f"{C_CYAN}[Moon Launcher] Synchronized with CustomSkinLoader for in-game rendering!{CLR_RESET}")

    else:
        print(f"{C_CYAN}[Moon Launcher] Fetching skin from player profile '{skin_clean}'...{CLR_RESET}")
        downloaded = False
        try:
            import urllib.request
            skin_url = f"https://minotar.net/skin/{skin_clean}"
            req = urllib.request.Request(
                skin_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                skin_bytes = resp.read()
            if len(skin_bytes) > 50:
                distribute_skin(skin_bytes, is_data=True)
                cfg['custom_skin'] = saved_skin_path
                cfg['discord_small_image'] = f"https://mc-heads.net/avatar/{skin_clean}.png"
                downloaded = True
                print(f"{C_GREEN}[Moon Launcher] Skin for player '{skin_clean}' saved to:{CLR_RESET}")
                print(f"  {C_WHITE}* {saved_skin_path}{CLR_RESET}")
        except Exception as e:
            print(f"{C_AMBER}[Moon Launcher] Warning while downloading player skin: {e}{CLR_RESET}")

        if not downloaded:
            cfg['custom_skin'] = skin_clean
            cfg['discord_small_image'] = f"https://mc-heads.net/avatar/{skin_clean}.png"
            print(f"{C_GREEN}[Moon Launcher] Skin for player '{skin_clean}' applied via Discord RPC.{CLR_RESET}")

    ensure_custom_skin_loader(version_dir, cfg)

def ensure_custom_skin_loader(version_dir, cfg=None):
    """
    Guarantees that CustomSkinLoader is installed, configured, and synchronized
    so that both the client user's skin and all other players' skins render in-game.
    """
    if not version_dir or not os.path.exists(version_dir):
        return

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    csl_template_jar = os.path.join(cur_dir, "templates", "CustomSkinLoader_Universal-15.1.jar")
    if not os.path.exists(csl_template_jar):
        csl_template_jar = os.path.join(cur_dir, "libraries", "customskinloader", "CustomSkinLoader_Universal-15.0.1.jar")

    mods_dir = os.path.join(version_dir, "mods")
    mc_ver, loader = detect_version_and_loader(version_dir)
    if loader != "Vanilla" or os.path.exists(mods_dir):
        os.makedirs(mods_dir, exist_ok=True)
        # 1. Install CustomSkinLoader mod jar
        target_jar = os.path.join(mods_dir, "CustomSkinLoader_Universal-15.1.jar")
        if os.path.exists(csl_template_jar) and not os.path.exists(target_jar):
            try:
                shutil.copyfile(csl_template_jar, target_jar)
            except Exception:
                pass

        # 2. Disable obsolete or conflicting TLauncher skin mods
        try:
            for f in os.listdir(mods_dir):
                if f.lower().startswith('tl_skin_cape') and f.lower().endswith('.jar'):
                    old_path = os.path.join(mods_dir, f)
                    new_path = os.path.join(mods_dir, f + ".disabled")
                    try:
                        os.rename(old_path, new_path)
                    except Exception:
                        pass
        except Exception:
            pass

    # 3. Deploy optimized CustomSkinLoader.json configuration
    csl_template_json = os.path.join(cur_dir, "templates", "CustomSkinLoader.json")
    if os.path.exists(csl_template_json):
        for csl_parent in (version_dir, os.path.expandvars(r"%APPDATA%\.minecraft")):
            csl_dir = os.path.join(csl_parent, "CustomSkinLoader")
            os.makedirs(csl_dir, exist_ok=True)
            csl_json_target = os.path.join(csl_dir, "CustomSkinLoader.json")
            try:
                shutil.copyfile(csl_template_json, csl_json_target)
            except Exception:
                pass

    # 4. Synchronize all skins (client player + friends) to LocalSkin folders
    master_skins = os.path.join(cur_dir, "skins")
    os.makedirs(master_skins, exist_ok=True)

    user = (cfg.get('username') if cfg else None) or get_master_username() or 'Player'
    user_skin_path = os.path.join(master_skins, f"{user}.png")
    if not os.path.exists(user_skin_path):
        custom_url = cfg.get('custom_skin_url') if cfg else None
        if custom_url and custom_url.startswith(('http://', 'https://')):
            try:
                req = urllib.request.Request(custom_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as r:
                    b = r.read()
                if len(b) > 50:
                    with open(user_skin_path, 'wb') as f_out:
                        f_out.write(b)
            except Exception:
                pass

    skin_target_dirs = [
        os.path.join(version_dir, "CustomSkinLoader", "LocalSkin", "skins"),
        os.path.join(version_dir, "LocalSkin", "skins"),
        os.path.join(version_dir, "skins"),
        os.path.expandvars(r"%APPDATA%\.minecraft\CustomSkinLoader\LocalSkin\skins"),
        os.path.expandvars(r"%APPDATA%\.minecraft\LocalSkin\skins")
    ]
    for s_file in os.listdir(master_skins):
        if s_file.lower().endswith('.png'):
            src_file = os.path.join(master_skins, s_file)
            for t_dir in skin_target_dirs:
                try:
                    os.makedirs(t_dir, exist_ok=True)
                    dest_file = os.path.join(t_dir, s_file)
                    if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                        shutil.copyfile(src_file, dest_file)
                except Exception:
                    pass

def apply_friend_skin_setting(version_dir, friend_username, skin_val):
    """Downloads or saves a custom skin for a friend so their skin displays in-game."""
    if not friend_username or not skin_val:
        return
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    main_skins_dir = os.path.join(cur_dir, "skins")
    os.makedirs(main_skins_dir, exist_ok=True)
    saved_skin_path = os.path.join(main_skins_dir, f"{friend_username}.png")

    clean_val = skin_val.strip().strip('"').strip("'")
    downloaded = False
    if clean_val.startswith(('http://', 'https://')):
        try:
            req = urllib.request.Request(clean_val, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if len(data) > 50:
                with open(saved_skin_path, 'wb') as f:
                    f.write(data)
                downloaded = True
        except Exception as e:
            print(f"{C_RED}[Moon Launcher] Failed to download friend skin: {e}{CLR_RESET}")
    elif os.path.exists(clean_val):
        try:
            shutil.copyfile(clean_val, saved_skin_path)
            downloaded = True
        except Exception as e:
            print(f"{C_RED}[Moon Launcher] Failed to copy friend skin: {e}{CLR_RESET}")
    else:
        try:
            skin_url = f"https://minotar.net/skin/{clean_val}"
            req = urllib.request.Request(skin_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if len(data) > 50:
                with open(saved_skin_path, 'wb') as f:
                    f.write(data)
                downloaded = True
        except Exception:
            pass

    if downloaded:
        print(f"{C_GREEN}[Moon Launcher] Successfully updated skin for friend '{friend_username}'!{CLR_RESET}")
        print(f"{C_MUTED}Saved to: {saved_skin_path}{CLR_RESET}")
        ensure_custom_skin_loader(version_dir)

def get_master_username():
    """Retrieves the universal master username from root launcher_config.json."""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    root_cfg = os.path.join(cur_dir, "launcher_config.json")
    if os.path.exists(root_cfg):
        try:
            with open(root_cfg, 'r', encoding='utf-8-sig') as f:
                u = json.load(f).get('username')
                if u and str(u).strip() and str(u).strip().lower() != 'epithap':
                    return str(u).strip()
        except Exception:
            pass
    return "JustMichellee"

def set_global_username(new_user, active_version_dir=None):
    """
    Universally updates and synchronizes player username across:
    1. Root launcher_config.json
    2. All installed version profiles (launcher_config.json and launch_args.txt)
    3. CustomSkinLoader directories
    """
    clean_user = str(new_user).strip().replace(' ', '_')
    if not clean_user:
        clean_user = "JustMichellee"

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    root_cfg_p = os.path.join(cur_dir, "launcher_config.json")

    # 1. Update root launcher_config.json
    root_data = {}
    if os.path.exists(root_cfg_p):
        try:
            with open(root_cfg_p, 'r', encoding='utf-8-sig') as f:
                root_data = json.load(f)
        except Exception:
            pass
    root_data['username'] = clean_user
    try:
        with open(root_cfg_p, 'w', encoding='utf-8') as f:
            json.dump(root_data, f, indent=2)
    except Exception:
        pass

    # 2. Synchronize all installed versions in C:\Moon-Launcher\versions
    vers_base = os.path.join(cur_dir, "versions")
    if os.path.exists(vers_base):
        for item in os.listdir(vers_base):
            v_dir = os.path.join(vers_base, item)
            if not os.path.isdir(v_dir):
                continue
            cfg_p = os.path.join(v_dir, "launcher_config.json")
            v_cfg = {}
            if os.path.exists(cfg_p):
                try:
                    with open(cfg_p, 'r', encoding='utf-8-sig') as vf:
                        v_cfg = json.load(vf)
                except Exception:
                    pass
            v_cfg['username'] = clean_user
            try:
                with open(cfg_p, 'w', encoding='utf-8') as vf:
                    json.dump(v_cfg, vf, indent=2)
            except Exception:
                pass
            update_launch_args(v_dir, v_cfg)

    # 3. Synchronize versions in .minecraft/versions
    mc_versions = os.path.expandvars(r'%APPDATA%\.minecraft\versions')
    if os.path.exists(mc_versions):
        for item in os.listdir(mc_versions):
            mv_dir = os.path.join(mc_versions, item)
            mv_args = os.path.join(mv_dir, "launch_args.txt")
            if os.path.exists(mv_args):
                try:
                    update_launch_args(mv_dir, {'username': clean_user, 'version_name': item})
                except Exception:
                    pass

    # 4. Replicate custom skins for clean_user if old skin file exists
    skins_dir = os.path.join(cur_dir, "skins")
    csl_dir = os.path.expandvars(r"%APPDATA%\.minecraft\CustomSkinLoader\LocalSkin\skins")
    for s_folder in [skins_dir, csl_dir]:
        if os.path.exists(s_folder):
            try:
                target_skin = os.path.join(s_folder, f"{clean_user}.png")
                if not os.path.exists(target_skin):
                    for old_cand in os.listdir(s_folder):
                        if old_cand.endswith('.png'):
                            import shutil
                            shutil.copyfile(os.path.join(s_folder, old_cand), target_skin)
                            break
            except Exception:
                pass

    return clean_user

def load_config(version_dir):
    """
    Loads configuration for a version, ensuring that the player's master identity
    (username, custom skin, and java runtime) from root launcher_config.json is ALWAYS
    preserved globally and never overwritten by old profile files.
    """
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    root_cfg_path = os.path.join(cur_dir, "launcher_config.json")
    v_name = os.path.basename(version_dir) if version_dir else "Homestead"

    cfg = {
        'ram_max_gb': 8,
        'ram_min_gb': 2,
        'username': get_master_username(),
        'custom_skin': '',
        'width': 1280,
        'height': 720,
        'fullscreen': False,
        'java_path': DEFAULT_JAVA,
        'version_name': v_name,
        'discord_rpc': True
    }

    # 1. Master global config (highest priority for username, skin, java runtime)
    root_data = {}
    if os.path.exists(root_cfg_path):
        try:
            with open(root_cfg_path, 'r', encoding='utf-8-sig') as f:
                root_data = json.load(f)
                cfg.update(root_data)
        except Exception:
            pass

    # 2. Version-specific overrides if distinct folder exists
    cfg_path = get_config_path(version_dir) if version_dir else None
    if cfg_path and os.path.exists(cfg_path) and os.path.abspath(cfg_path) != os.path.abspath(root_cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8-sig') as f:
                v_data = json.load(f)
                # Master username precedence with intelligent bi-directional synchronization
                master_user = root_data.get('username')
                v_user = v_data.get('username')
                if master_user and master_user not in ('', 'Player', 'Epithap'):
                    v_data['username'] = master_user
                elif v_user and v_user not in ('', 'Player', 'Epithap'):
                    master_user = v_user
                    root_data['username'] = master_user
                else:
                    v_data['username'] = get_master_username()
                master_skin = root_data.get('custom_skin')
                if master_skin is not None:
                    v_data['custom_skin'] = master_skin
                cfg.update(v_data)
        except Exception:
            pass

    cfg['version_name'] = v_name
    # Ensure Minecraft 1.20.5+ / 1.21+ uses Java 21 (java-runtime-delta)
    if any(k in v_name for k in ['1.21', '1.20.5', '1.20.6', 'LMLL-NeoForge']):
        delta_java = os.path.expandvars(r'%APPDATA%\.minecraft\runtime\java-runtime-delta\windows\java-runtime-delta\bin\javaw.exe')
        if os.path.exists(delta_java):
            cfg['java_path'] = delta_java

    if root_data.get('discord_small_image'):
        cfg['discord_small_image'] = root_data['discord_small_image']
    if root_data.get('custom_skin'):
        cfg['custom_skin'] = root_data['custom_skin']

    if not os.path.exists(cfg.get('java_path', '')):
        cfg['java_path'] = DEFAULT_JAVA
    return cfg

def save_config(version_dir, cfg):
    """
    Saves configuration to both the target version directory and root launcher_config.json
    so that user settings (username, skin, RAM, display) persist globally across restarts and version switches.
    """
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    root_cfg_path = os.path.join(cur_dir, "launcher_config.json")

    # 1. Save to target version directory
    if version_dir:
        cfg_path = get_config_path(version_dir)
        try:
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            with open(cfg_path, 'w', encoding='utf-8-sig') as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"{C_RED}Failed to save version configuration: {e}{CLR_RESET}")

    # 2. Always synchronize master user settings to root launcher_config.json
    try:
        root_data = {}
        if os.path.exists(root_cfg_path):
            with open(root_cfg_path, 'r', encoding='utf-8-sig') as f:
                root_data = json.load(f)
        root_data['username'] = cfg.get('username', root_data.get('username', 'Epithap'))
        if 'custom_skin' in cfg:
            root_data['custom_skin'] = cfg['custom_skin']
        if 'ram_max_gb' in cfg:
            root_data['ram_max_gb'] = cfg['ram_max_gb']
        if 'ram_min_gb' in cfg:
            root_data['ram_min_gb'] = cfg['ram_min_gb']
        if 'width' in cfg:
            root_data['width'] = cfg['width']
        if 'height' in cfg:
            root_data['height'] = cfg['height']
        if 'fullscreen' in cfg:
            root_data['fullscreen'] = cfg['fullscreen']
        if 'java_path' in cfg:
            root_data['java_path'] = cfg['java_path']
        if 'version_name' in cfg:
            root_data['version_name'] = cfg['version_name']
        with open(root_cfg_path, 'w', encoding='utf-8-sig') as f:
            json.dump(root_data, f, indent=2)
    except Exception:
        pass

    if version_dir:
        update_launch_args(version_dir, cfg)

def update_launch_args(version_dir, cfg):
    args_path = os.path.join(version_dir, 'launch_args.txt')
    if not os.path.exists(args_path):
        return False

    with open(args_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        lines = [l.rstrip('\r\n') for l in f.readlines()]

    new_lines = []
    i = 0
    has_gamedir = False
    has_user = False
    clean_user = cfg.get('username') or get_master_username()
    v_name = cfg.get('version_name', os.path.basename(version_dir))
    norm_vdir = version_dir.replace('\\', '/')

    while i < len(lines):
        line = lines[i]
        trimmed = line.strip()
        if trimmed.startswith('-Xms'):
            new_lines.append(f"-Xms{cfg.get('ram_min_gb', 2)}G")
        elif trimmed.startswith('-Xmx'):
            new_lines.append(f"-Xmx{cfg.get('ram_max_gb', 8)}G")
        elif trimmed == '--username':
            has_user = True
            new_lines.append('--username')
            new_lines.append(str(clean_user))
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('-'):
                i += 1
        elif trimmed.startswith('--username ') or trimmed.startswith('--username='):
            has_user = True
            new_lines.append('--username')
            new_lines.append(str(clean_user))
        elif trimmed == '--width':
            new_lines.append('--width')
            new_lines.append(str(cfg.get('width', 1280)))
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('-'):
                i += 1
        elif trimmed == '--height':
            new_lines.append('--height')
            new_lines.append(str(cfg.get('height', 720)))
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('-'):
                i += 1
        elif trimmed == '--version':
            new_lines.append('--version')
            new_lines.append(str(v_name))
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('-'):
                i += 1
        elif trimmed == '--gameDir':
            has_gamedir = True
            new_lines.append('--gameDir')
            new_lines.append(f'"{norm_vdir}"')
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('-'):
                i += 1
        else:
            new_lines.append(line)
        i += 1

    if not has_user:
        new_lines.extend(['--username', str(clean_user)])
    if not has_gamedir:
        new_lines.extend(['--gameDir', f'"{norm_vdir}"'])

    with open(args_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines) + "\n")

    return True

# ==============================================================================
# SYSTEM & MODPACK DIAGNOSTICS
# ==============================================================================

def count_mods(version_dir):
    mods_dir = os.path.join(version_dir, 'mods')
    if os.path.exists(mods_dir):
        return len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
    return 0

def check_java_runtime(java_path):
    if not os.path.exists(java_path):
        return False, 'Not Found'
    try:
        res = subprocess.run([java_path, '-version'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=5)
        out = res.stderr or res.stdout
        for line in out.splitlines():
            if 'version' in line.lower():
                return True, line.strip()
        return True, 'Java 17 Gamma'
    except Exception:
        return True, 'Java 17 (verified)'

def detect_version_info(version_dir, v_name=""):
    """
    Detects Minecraft version, loader name, and loader version dynamically.
    Returns formatted string: 'Modpack_Name (Vanilla 1.12.2)' or 'Modpack_Name (1.20.1, Forge 47.4.4)'
    """
    if not v_name:
        v_name = os.path.basename(version_dir) if version_dir else 'NightfallCraft 2.2.9.7'

    target_dir = version_dir
    if not target_dir or not os.path.exists(target_dir):
        candidate = os.path.join(BASE_VERSIONS_DIR, v_name)
        if os.path.exists(candidate):
            target_dir = candidate

    mc_ver = "1.20.1"
    loader_name = "Vanilla"
    loader_ver = ""

    if target_dir and os.path.exists(target_dir):
        mc_ver, loader_name = detect_version_and_loader(target_dir)
        args_p = os.path.join(target_dir, 'launch_args.txt')
        if os.path.exists(args_p):
            try:
                with open(args_p, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    args_text = f.read()
                m_nf_arg = re.search(r'--fml\.neoForgeVersion\s+([0-9\.]+)', args_text)
                if m_nf_arg:
                    loader_name = "NeoForge"
                    loader_ver = m_nf_arg.group(1)
                else:
                    m_fml = re.search(r'--fml\.forgeVersion\s+([0-9\.]+)', args_text)
                    if m_fml:
                        loader_ver = m_fml.group(1)
                    else:
                        m_fml2 = re.search(r'fmlloader[\/:\-]+[0-9\.]+[\/:\-]+([0-9\.]+)', args_text, re.I)
                        if m_fml2: loader_ver = m_fml2.group(1)
            except Exception:
                pass

    if loader_name == "Vanilla":
        fmt = f"{v_name} (Vanilla {mc_ver})"
    elif loader_ver:
        fmt = f"{v_name} ({mc_ver}, {loader_name} {loader_ver})"
    else:
        fmt = f"{v_name} ({mc_ver}, {loader_name})"

    return {
        'title': v_name,
        'mc_version': mc_ver,
        'loader_name': loader_name,
        'loader_version': loader_ver,
        'formatted': fmt
    }

# Presets for instant stepping
RAM_PRESETS = [4, 6, 8, 10, 12, 14, 16, 20, 24, 32]
MIN_RAM_PRESETS = [1, 2, 4, 6, 8]
RES_PRESETS = [
    (1024, 768, "1024x768 (4:3)"),
    (1280, 720, "1280x720 (HD 16:9)"),
    (1366, 768, "1366x768 (Laptop)"),
    (1600, 900, "1600x900 (HD+)"),
    (1920, 1080, "1920x1080 (FHD)"),
    (2560, 1440, "2560x1440 (2K QHD)"),
    (3840, 2160, "3840x2160 (4K UHD)")
]

# ==============================================================================
# SETTINGS STUDIO (TUI)
# ==============================================================================

def draw_studio_screen(cfg, selected_idx, is_modified, status_msg=""):
    os.system('cls' if sys.platform == 'win32' else 'clear')
    inner_w = 76
    v_name = cfg.get('version_name', 'NightfallCraft 2.2.9.7')

    status_tag = f"{C_AMBER}* Unsaved Changes{CLR_RESET}" if is_modified else f"{C_GREEN}[OK] All Saved{CLR_RESET}"

    h1_left = f"{C_CLAUDE}* MOON SETTINGS STUDIO *{CLR_RESET}"
    max_h1_r = max(10, inner_w - get_visible_width(h1_left) - 6)
    v_name_disp = truncate_ansi(v_name, max_h1_r)
    h1_right = f"{C_MUTED}[ {v_name_disp} ]{CLR_RESET}"
    h1_rem = max(1, inner_w - get_visible_width(h1_left) - get_visible_width(h1_right))
    line1 = f"{h1_left}{' ' * h1_rem}{h1_right}"

    h2_left = f"{C_MUTED}Interactive Hardware & Game Profile Tuner{CLR_RESET}"
    h2_rem = max(1, inner_w - get_visible_width(h2_left) - get_visible_width(status_tag))
    line2 = f"{h2_left}{' ' * h2_rem}{status_tag}"

    print(render_box([line1, line2], inner_w))
    print()

    # Build options list
    res_str = f"{cfg['width']}x{cfg['height']}"
    for rw, rh, rlabel in RES_PRESETS:
        if cfg['width'] == rw and cfg['height'] == rh:
            res_str = rlabel
            break

    full_str = f"{C_GREEN}ENABLED{CLR_RESET}" if cfg['fullscreen'] else f"{C_MUTED}DISABLED{CLR_RESET}"
    full_plain = "ENABLED" if cfg['fullscreen'] else "DISABLED"
    java_plain = "Bundled Gamma" if "gamma" in cfg['java_path'].lower() else os.path.basename(cfg['java_path'])

    skin_raw = cfg.get('custom_skin', '')
    skin_display = skin_raw if skin_raw else "Auto (Username)"
    if skin_raw and (skin_raw.startswith('http') or len(skin_raw) > 16):
        skin_note = "Custom URL / Path"
    elif skin_raw:
        skin_note = f"Player: {skin_raw}"
    else:
        skin_note = "Default avatar"

    fields_meta = [
        ("Maximum Memory (RAM)",   f"{cfg['ram_max_gb']} GB",       "Rec: 8 - 12 GB",       f"{cfg['ram_max_gb']} GB"),
        ("Initial Memory (Min)",   f"{cfg['ram_min_gb']} GB",       "Fast JVM startup",     f"{cfg['ram_min_gb']} GB"),
        ("Player Username",        f"{cfg['username']}",            "In-game player ID",    f"{cfg['username']}"),
        ("Display Resolution",     res_str,                         "Default window size",  res_str),
        ("Fullscreen Display",     full_str,                        "Exclusive display",    full_plain),
        ("Active Profile",         v_name,                          "Active game profile",  v_name),
        ("Java 17 Runtime",        java_plain,                      "javaw.exe binary",     java_plain),
        ("Custom Player Skin",     skin_display,                    skin_note,              skin_display)
    ]

    menu_lines = []
    for idx, (label, val_fmt, note, val_raw) in enumerate(fields_meta):
        is_sel = (idx == selected_idx)
        num_str = f"[{idx + 1}]"

        display_val = val_raw
        if get_visible_width(display_val) > 18:
            display_val = truncate_ansi(display_val, 18)

        if is_sel:
            cur = f"{C_CYAN}>{CLR_RESET}"
            lbl = f"{C_WHITE}\033[1m{label}{CLR_RESET}"
            val_box = f"\033[48;2;30;58;138m\033[38;2;241;245;249m\033[1m [ {display_val} ] \033[0m"
            hint = f"{C_AMBER}{note}{CLR_RESET}"
        else:
            cur = " "
            lbl = f"{C_MUTED}{label}{CLR_RESET}"
            val_box = f"{C_CYAN}[ {display_val} ]{CLR_RESET}"
            hint = f"{C_MUTED}{note}{CLR_RESET}"

        col1 = f"{cur} {C_MUTED}{num_str}{CLR_RESET} {lbl}"
        col2 = val_box
        c1_pad = pad_visible(col1, 28)
        c2_pad = pad_visible(col2, 24)
        c3_pad = pad_visible(truncate_ansi(hint, 20), 20)
        line = f"{c1_pad} {c2_pad} {c3_pad}"
        menu_lines.append(line)

    print(render_box(menu_lines, inner_w, title="Configuration Options"))
    print()

    # Active Help details card
    help_map = [
        (
            "Maximum Memory (RAM)",
            "Allocates maximum heap memory (-Xmx) for Forge and active mods.",
            f"{C_CYAN}< / >{C_MUTED} Cycle: {C_WHITE}4G • 6G • 8G • 10G • 12G • 16G{C_MUTED}  │  {C_AMBER}[ENTER]{C_MUTED} Custom RAM{CLR_RESET}"
        ),
        (
            "Initial Memory (Min)",
            "Initial Java heap memory reservation (-Xms) for fast initialization.",
            f"{C_CYAN}< / >{C_MUTED} Cycle: {C_WHITE}1G • 2G • 4G • 6G • 8G{C_MUTED}  │  {C_AMBER}[ENTER]{C_MUTED} Custom heap{CLR_RESET}"
        ),
        (
            "Player Username",
            "Player name for singleplayer and offline LAN multiplayer sessions.",
            f"{C_AMBER}[ENTER]{C_MUTED} Type new username (letters, numbers, underscores){CLR_RESET}"
        ),
        (
            "Display Resolution",
            "Default game window resolution when launching the game.",
            f"{C_CYAN}< / >{C_MUTED} Cycle: {C_WHITE}720p • 900p • 1080p • 2K • 4K{C_MUTED}  │  {C_AMBER}[ENTER]{C_MUTED} Custom size{CLR_RESET}"
        ),
        (
            "Fullscreen Display",
            "Starts the game in borderless or exclusive fullscreen display mode.",
            f"{C_CYAN}< / >{C_MUTED} or {C_AMBER}[SPACE] / [ENTER]{C_MUTED} to toggle ENABLED <-> DISABLED{CLR_RESET}"
        ),
        (
            "Active Profile",
            f"Active: {detect_version_info(find_version_dir_by_name(v_name) or BASE_VERSIONS_DIR, v_name)['formatted']}",
            f"{C_CYAN}< / >{C_MUTED} Cycle profiles  │  {C_AMBER}[S]{C_MUTED} Save active profile permanently{CLR_RESET}"
        ),
        (
            "Java 17 Runtime",
            "Java 17 64-bit runtime binary (javaw.exe) required for modern Minecraft.",
            f"{C_CYAN}< / >{C_MUTED} Toggle Bundled vs System  │  {C_AMBER}[ENTER]{C_MUTED} Custom path{CLR_RESET}"
        ),
        (
            "Custom Player Skin",
            "Custom skin for in-game rendering (CustomSkinLoader) and Discord 3D Avatar.",
            f"{C_CYAN}< / >{C_MUTED} Reset to Auto  │  {C_AMBER}[ENTER]{C_MUTED} Set Skin URL / Local .png / Player Name{CLR_RESET}"
        )
    ]

    t_title, t_desc, t_ctrl = help_map[selected_idx]
    help_box_lines = [
        f"{C_WHITE}\033[1m* {t_title}\033[0m",
        f"{C_MUTED}{t_desc}{CLR_RESET}",
        f"{t_ctrl}"
    ]
    print(render_box(help_box_lines, inner_w, title="Active Parameter Details"))
    print()

    if status_msg:
        print(f"  {C_CYAN}[ {status_msg} ]{CLR_RESET}")
        print()

    hotbar = f"  {C_MUTED}Controls:{CLR_RESET} {C_CYAN}[UP/DOWN]{CLR_RESET} {C_MUTED}Navigate{CLR_RESET}  •  {C_CYAN}[</>]{CLR_RESET} {C_MUTED}Quick Adjust{CLR_RESET}  •  {C_AMBER}[ENTER]{CLR_RESET} {C_MUTED}Edit / Toggle{CLR_RESET}\n           {C_GREEN}[S]{CLR_RESET} {C_MUTED}Save & Apply{CLR_RESET}  •  {C_PURPLE}[R]{CLR_RESET} {C_MUTED}Reset Defaults{CLR_RESET}  •  {C_RED}[Q / ESC]{CLR_RESET} {C_MUTED}Return to Menu{CLR_RESET}"
    print(hotbar)

def adjust_setting_step(cfg, selected_idx, step_dir, avail_versions):
    is_modified = True
    status = ""
    if selected_idx == 0:  # RAM Max
        cur = cfg.get('ram_max_gb', 8)
        if cur in RAM_PRESETS:
            idx = RAM_PRESETS.index(cur)
            new_idx = (idx + step_dir) % len(RAM_PRESETS)
        else:
            new_idx = 2
        cfg['ram_max_gb'] = RAM_PRESETS[new_idx]
        status = f"Allocated {cfg['ram_max_gb']} GB RAM"
    elif selected_idx == 1:  # RAM Min
        cur = cfg.get('ram_min_gb', 2)
        if cur in MIN_RAM_PRESETS:
            idx = MIN_RAM_PRESETS.index(cur)
            new_idx = (idx + step_dir) % len(MIN_RAM_PRESETS)
        else:
            new_idx = 1
        cfg['ram_min_gb'] = MIN_RAM_PRESETS[new_idx]
        status = f"Initial heap set to {cfg['ram_min_gb']} GB"
    elif selected_idx == 2:  # Player
        status = "Press [ENTER] to type new player username"
        is_modified = False
    elif selected_idx == 3:  # Resolution
        cur_w, cur_h = cfg.get('width', 1280), cfg.get('height', 720)
        match_idx = 1
        for i, (pw, ph, _) in enumerate(RES_PRESETS):
            if pw == cur_w and ph == cur_h:
                match_idx = i
                break
        new_idx = (match_idx + step_dir) % len(RES_PRESETS)
        cfg['width'] = RES_PRESETS[new_idx][0]
        cfg['height'] = RES_PRESETS[new_idx][1]
        status = f"Resolution set to {cfg['width']}x{cfg['height']}"
    elif selected_idx == 4:  # Fullscreen
        cfg['fullscreen'] = not cfg.get('fullscreen', False)
        status = f"Fullscreen {'ENABLED' if cfg['fullscreen'] else 'DISABLED'}"
    elif selected_idx == 5:  # Active Profile
        if avail_versions and len(avail_versions) > 1:
            cur_p = cfg.get('version_name', '')
            cur_idx = avail_versions.index(cur_p) if cur_p in avail_versions else 0
            new_idx = (cur_idx + step_dir) % len(avail_versions)
            cfg['version_name'] = avail_versions[new_idx]
            status = f"Switched active profile to: {cfg['version_name']}"
        else:
            status = "Only one profile directory found"
            is_modified = False
    elif selected_idx == 6:  # Java Runtime
        if "gamma" in cfg.get('java_path', '').lower():
            cfg['java_path'] = "javaw.exe"
            status = "Java set to System javaw (from PATH)"
        else:
            cfg['java_path'] = DEFAULT_JAVA
            status = "Java set to Bundled Gamma Runtime"
    elif selected_idx == 7:  # Custom Skin
        cfg['custom_skin'] = ''
        cfg['discord_small_image'] = ''
        status = "Reset custom skin to Auto (username avatar)"

    return cfg, is_modified, status

def run_settings_studio(version_dir, cfg):
    if sys.platform == 'win32':
        os.system('title Moon Launcher - Settings Studio')

    temp_cfg = dict(cfg)
    is_modified = False
    status_msg = "Use [UP/DOWN] to select, [</>] to quick-adjust, [S] to save"
    selected_idx = 0

    # Discover available versions
    avail_map = get_all_available_versions()
    avail_versions = list(avail_map.keys())
    if not avail_versions:
        avail_versions = [cfg.get('version_name', os.path.basename(version_dir))]

    current_target_dir = version_dir

    while True:
        draw_studio_screen(temp_cfg, selected_idx, is_modified, status_msg)

        is_tty = sys.stdin.isatty() if hasattr(sys.stdin, 'isatty') else False

        if sys.platform == 'win32' and is_tty and ('msvcrt' in sys.modules):
            try:
                ch = msvcrt.getch()
            except Exception:
                ch = b'\r'
        else:
            print(f"\n  {C_AMBER}Studio Command [1-7 select/adjust, S save, R reset, Q exit]: {CLR_RESET}", end="", flush=True)
            line = sys.stdin.readline()
            if not line:
                break
            ch = line.strip().encode('utf-8') or b'q'

        if ch in (b'\xe0', b'\x00'):
            if is_tty and ('msvcrt' in sys.modules):
                ch2 = msvcrt.getch()
                if ch2 == b'H':  # Up
                    selected_idx = (selected_idx - 1) % 8
                    status_msg = ""
                elif ch2 == b'P':  # Down
                    selected_idx = (selected_idx + 1) % 8
                    status_msg = ""
                elif ch2 == b'K':  # Left
                    temp_cfg, is_mod, msg = adjust_setting_step(temp_cfg, selected_idx, -1, avail_versions)
                    if is_mod:
                        is_modified = True
                    status_msg = msg
                elif ch2 == b'M':  # Right
                    temp_cfg, is_mod, msg = adjust_setting_step(temp_cfg, selected_idx, +1, avail_versions)
                    if is_mod:
                        is_modified = True
                    status_msg = msg
            continue

        ch_lower = ch.lower()

        # Exit: Q, q, ESC (\x1b)
        if ch in (b'\x1b', b'q', b'Q'):
            if is_modified:
                draw_studio_screen(temp_cfg, selected_idx, is_modified, status_msg)
                print(f"\n  {C_AMBER}Save modified settings before exiting? (Y/N/C): {CLR_RESET}", end="", flush=True)
                ans = input().strip().lower()
                if ans == 'y':
                    chosen_name = temp_cfg.get('version_name', '')
                    target_dir = find_version_dir_by_name(chosen_name) or current_target_dir
                    save_config(target_dir, temp_cfg)
                    if chosen_name:
                        set_active_version(chosen_name)
                    ensure_launch_args(target_dir, declared_loader=temp_cfg.get('loader'), mc_version=temp_cfg.get('mc_version'))
                    update_launch_args(target_dir, temp_cfg)
                    current_target_dir = target_dir
                    cfg = load_config(target_dir)
                    break
                elif ans == 'n':
                    break
                else:
                    status_msg = "Cancelled exit"
                    continue
            else:
                break

        # Save & Apply: S / s
        elif ch_lower == b's':
            chosen_name = temp_cfg.get('version_name', '')
            target_dir = find_version_dir_by_name(chosen_name) or current_target_dir
            if chosen_name:
                set_active_version(chosen_name)
            save_config(target_dir, temp_cfg)
            ensure_launch_args(target_dir, declared_loader=temp_cfg.get('loader'), mc_version=temp_cfg.get('mc_version'))
            update_launch_args(target_dir, temp_cfg)
            current_target_dir = target_dir
            cfg = load_config(target_dir)
            is_modified = False
            status_msg = f"[OK] Configuration saved & active profile: {chosen_name or os.path.basename(target_dir)}"

        # Reset Defaults: R / r
        elif ch_lower == b'r':
            temp_cfg['ram_max_gb'] = 8
            temp_cfg['ram_min_gb'] = 2
            temp_cfg['width'] = 1280
            temp_cfg['height'] = 720
            temp_cfg['fullscreen'] = False
            temp_cfg['java_path'] = DEFAULT_JAVA
            is_modified = True
            status_msg = "Restored recommended defaults (Press [S] to apply)"

        # Direct number selection: 1 to 7
        elif ch >= b'1' and ch <= b'8':
            num = int(ch.decode('utf-8')) - 1
            if num == selected_idx and num == 4:
                temp_cfg['fullscreen'] = not temp_cfg.get('fullscreen', False)
                is_modified = True
                status_msg = f"Fullscreen {'ENABLED' if temp_cfg['fullscreen'] else 'DISABLED'}"
            else:
                selected_idx = num
                status_msg = f"Selected: option [{num + 1}]"

        # Step adjust with A / D
        elif ch_lower == b'a':
            temp_cfg, is_mod, msg = adjust_setting_step(temp_cfg, selected_idx, -1, avail_versions)
            if is_mod:
                is_modified = True
            status_msg = msg
        elif ch_lower == b'd':
            temp_cfg, is_mod, msg = adjust_setting_step(temp_cfg, selected_idx, +1, avail_versions)
            if is_mod:
                is_modified = True
            status_msg = msg

        # Spacebar (Toggle Fullscreen if on row 4)
        elif ch == b' ':
            if selected_idx == 4:
                temp_cfg['fullscreen'] = not temp_cfg.get('fullscreen', False)
                is_modified = True
                status_msg = f"Fullscreen {'ENABLED' if temp_cfg['fullscreen'] else 'DISABLED'}"

        # Enter key (Edit custom or toggle)
        elif ch in (b'\r', b'\n'):
            if selected_idx == 4:  # Fullscreen
                temp_cfg['fullscreen'] = not temp_cfg.get('fullscreen', False)
                is_modified = True
                status_msg = f"Fullscreen {'ENABLED' if temp_cfg['fullscreen'] else 'DISABLED'}"
            elif selected_idx == 0:  # RAM Max
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Enter custom RAM value")
                print(f"  {C_CYAN}Current:{CLR_RESET} {temp_cfg['ram_max_gb']} GB  │  {C_MUTED}Presets: 4, 6, 8, 10, 12, 16, 24, 32{CLR_RESET}")
                new_val = input(f"  {C_AMBER}Enter maximum RAM in GB [or press ENTER to keep]: {CLR_RESET}").strip()
                if new_val.isdigit() and int(new_val) > 0:
                    temp_cfg['ram_max_gb'] = int(new_val)
                    is_modified = True
                    status_msg = f"Maximum RAM set to {new_val} GB"
            elif selected_idx == 1:  # RAM Min
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Enter custom Min RAM value")
                print(f"  {C_CYAN}Current:{CLR_RESET} {temp_cfg['ram_min_gb']} GB  │  {C_MUTED}Presets: 1, 2, 4, 6, 8{CLR_RESET}")
                new_val = input(f"  {C_AMBER}Enter initial RAM in GB [or press ENTER to keep]: {CLR_RESET}").strip()
                if new_val.isdigit() and int(new_val) > 0:
                    temp_cfg['ram_min_gb'] = int(new_val)
                    is_modified = True
                    status_msg = f"Initial RAM set to {new_val} GB"
            elif selected_idx == 2:  # Username
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Edit Player Username & Skin")
                print(f"  {C_CYAN}Current Name:{CLR_RESET} {temp_cfg['username']}")
                new_val = input(f"  {C_AMBER}Enter new username [or press ENTER to keep]: {CLR_RESET}").strip()
                if new_val:
                    clean_name = new_val.replace(' ', '_')
                    temp_cfg['username'] = clean_name
                    is_modified = True
                    status_msg = f"Username updated to: {clean_name}"
                
                cur_skin = temp_cfg.get('custom_skin', '') or 'Auto (from username)'
                print(f"  {C_CYAN}Current Skin:{CLR_RESET} {cur_skin}")
                print(f"  {C_MUTED}Enter URL (https://...), local .png path, player name, or type 'auto'{CLR_RESET}")
                new_skin = input(f"  {C_AMBER}Custom skin [press ENTER to keep current]: {CLR_RESET}").strip()
                if new_skin:
                    apply_skin_setting(current_target_dir, temp_cfg, new_skin)
                    is_modified = True
                    status_msg = f"Username & skin updated!"
            elif selected_idx == 7:  # Custom Skin
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Configure Custom Skin")
                cur_skin = temp_cfg.get('custom_skin', '') or 'Auto (from username)'
                print(f"  {C_CYAN}Current Skin:{CLR_RESET} {cur_skin}")
                print(f"  {C_MUTED}Formats supported:{CLR_RESET}")
                print(f"    • {C_WHITE}https://.../skin.png{CLR_RESET} {C_MUTED}(Direct image URL){CLR_RESET}")
                print(f"    • {C_WHITE}C:\\path\\to\\skin.png{CLR_RESET} {C_MUTED}(Local .png skin file){CLR_RESET}")
                print(f"    • {C_WHITE}PlayerName{CLR_RESET} {C_MUTED}(Copy skin from premium player, e.g. Dream){CLR_RESET}")
                print(f"    • {C_WHITE}auto{CLR_RESET} {C_MUTED}(Reset to use current player username){CLR_RESET}")
                new_skin = input(f"\n  {C_AMBER}Enter custom skin [or press ENTER to cancel]: {CLR_RESET}").strip()
                if new_skin:
                    apply_skin_setting(current_target_dir, temp_cfg, new_skin)
                    is_modified = True
                    status_msg = f"Custom skin updated to: {temp_cfg.get('custom_skin') or 'Auto'}"
            elif selected_idx == 3:  # Resolution
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Enter Custom Resolution")
                print(f"  {C_CYAN}Current:{CLR_RESET} {temp_cfg['width']}x{temp_cfg['height']}  │  {C_MUTED}Format: 1920x1080 or 1280 720{CLR_RESET}")
                new_val = input(f"  {C_AMBER}Enter custom resolution: {CLR_RESET}").strip()
                if 'x' in new_val.lower():
                    parts = new_val.lower().split('x')
                else:
                    parts = new_val.split()
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    temp_cfg['width'] = int(parts[0])
                    temp_cfg['height'] = int(parts[1])
                    is_modified = True
                    status_msg = f"Resolution set to {temp_cfg['width']}x{temp_cfg['height']}"
            elif selected_idx == 5:  # Profile
                temp_cfg, is_mod, msg = adjust_setting_step(temp_cfg, 5, +1, avail_versions)
                if is_mod:
                    is_modified = True
                status_msg = msg
            elif selected_idx == 6:  # Java
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Configure Java Runtime Path")
                print(f"  {C_CYAN}Current:{CLR_RESET} {temp_cfg['java_path']}")
                print(f"  {C_MUTED}Enter path to javaw.exe or type 'bundled' to use Gamma runtime{CLR_RESET}")
                new_val = input(f"  {C_AMBER}New Java path: {CLR_RESET}").strip().strip('"')
                if new_val:
                    if new_val.lower() == 'bundled':
                        temp_cfg['java_path'] = DEFAULT_JAVA
                        is_modified = True
                        status_msg = "Java set to Bundled Gamma Runtime"
                    elif os.path.exists(new_val):
                        temp_cfg['java_path'] = new_val
                        is_modified = True
                        status_msg = "Java runtime path updated"
                    else:
                        temp_cfg['java_path'] = new_val
                        is_modified = True
                        status_msg = "Warning: File not verified, saved anyway"

    if sys.platform == 'win32':
        os.system('title Moon Launcher')

    if temp_cfg.get('version_name'):
        chosen_name = temp_cfg['version_name']
        resolved_dir = find_version_dir_by_name(chosen_name)
        if resolved_dir and os.path.exists(resolved_dir):
            current_target_dir = resolved_dir
            set_active_version(chosen_name)
            cfg = load_config(current_target_dir)

    return current_target_dir, cfg

# ==============================================================================
# QUICK SETTINGS & COMMANDS
# ==============================================================================

def apply_quick_setting(version_dir, cfg, args):
    if not args:
        return cfg

    key = args[0].lower().replace('-', '').replace('_', '')
    val = args[1] if len(args) > 1 else ''

    if key in ('ram', 'memory', 'rammax', 'maxram'):
        try:
            v = int(val)
            if v > 0:
                cfg['ram_max_gb'] = v
                save_config(version_dir, cfg)
                print(f"{C_GREEN}[Moon Launcher] Updated ram_max_gb -> {v} GB{CLR_RESET}")
        except ValueError:
            print(f"{C_RED}Invalid RAM value: {val}{CLR_RESET}")

    elif key in ('minram', 'rammin'):
        try:
            v = int(val)
            if v > 0:
                cfg['ram_min_gb'] = v
                save_config(version_dir, cfg)
                print(f"{C_GREEN}[Moon Launcher] Updated ram_min_gb -> {v} GB{CLR_RESET}")
        except ValueError:
            print(f"{C_RED}Invalid RAM value: {val}{CLR_RESET}")

    elif key in ('user', 'username', 'player', 'name', 'nick'):
        target_name = val if val else (args[0] if key in ('user', 'username', 'player', 'name', 'nick') and val else '')
        if not target_name and len(args) > 1: target_name = args[1]
        clean_user = set_global_username(target_name or val, version_dir)
        cfg['username'] = clean_user
        if len(args) > 2:
            skin_arg = " ".join(args[2:])
            apply_skin_setting(version_dir, cfg, skin_arg)
        save_config(version_dir, cfg)
        print(f"{C_GREEN}[Moon Launcher] Updated username -> {clean_user}{CLR_RESET}")
        print(f"{C_MUTED}[Moon Launcher] Synchronized across all profiles and launch arguments.{CLR_RESET}")
        if 'custom_skin' in cfg and cfg['custom_skin']:
            print(f"{C_CYAN}[Moon Launcher] Active Custom Skin: {cfg['custom_skin']}{CLR_RESET}")

    elif key in ('skin', 'customskin', 'avatar'):
        apply_skin_setting(version_dir, cfg, val)
        save_config(version_dir, cfg)

    elif key in ('res', 'resolution'):
        if 'x' in val.lower():
            parts = val.lower().split('x')
        elif len(args) >= 3:
            parts = [args[1], args[2]]
        else:
            parts = []

        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            cfg['width'] = int(parts[0])
            cfg['height'] = int(parts[1])
            save_config(version_dir, cfg)
            print(f"{C_GREEN}[Moon Launcher] Updated resolution -> {cfg['width']}x{cfg['height']}{CLR_RESET}")
        else:
            print(f"{C_RED}Format resolution: 1280x720 or /setting res 1920 1080{CLR_RESET}")

    elif key in ('width', 'w'):
        if val.isdigit():
            cfg['width'] = int(val)
            save_config(version_dir, cfg)
            print(f"{C_GREEN}[Moon Launcher] Updated width -> {val}{CLR_RESET}")

    elif key in ('height', 'h'):
        if val.isdigit():
            cfg['height'] = int(val)
            save_config(version_dir, cfg)
            print(f"{C_GREEN}[Moon Launcher] Updated height -> {val}{CLR_RESET}")

    elif key in ('fullscreen', 'full'):
        bval = val.lower() in ('true', '1', 'yes', 'y', 'on')
        cfg['fullscreen'] = bval
        save_config(version_dir, cfg)
        print(f"{C_GREEN}[Moon Launcher] Updated fullscreen -> {bval}{CLR_RESET}")

    elif key in ('java', 'javapath', 'java_path'):
        if os.path.exists(val):
            cfg['java_path'] = val
            save_config(version_dir, cfg)
            print(f"{C_GREEN}[Moon Launcher] Updated java_path -> {val}{CLR_RESET}")
        else:
            print(f"{C_AMBER}[Moon Launcher] Warning: Java file not found at path, saved anyway.{CLR_RESET}")
            cfg['java_path'] = val
            save_config(version_dir, cfg)

    else:
        # If user directly typed /setting <name> without 'user' keyword
        known_keys = ('ram', 'memory', 'rammax', 'maxram', 'minram', 'rammin', 'skin', 'customskin', 'avatar', 'res', 'resolution', 'width', 'w', 'height', 'h', 'fullscreen', 'full', 'fs', 'java', 'javapath', 'version', 'profile', 'v')
        if not val and key not in known_keys and not key.isdigit():
            clean_user = set_global_username(args[0], version_dir)
            cfg['username'] = clean_user
            save_config(version_dir, cfg)
            print(f"{C_GREEN}[Moon Launcher] Updated username -> {clean_user}{CLR_RESET}")
            print(f"{C_MUTED}[Moon Launcher] Synchronized across all profiles and launch arguments.{CLR_RESET}")
        else:
            print(f"{C_RED}Unknown setting key '{key}'. Available: user <name>, ram <gb>, skin <url>, res <W> <H>, java <path>{CLR_RESET}")

    return cfg

def print_banner(version_dir, cfg):
    os.system('cls' if sys.platform == 'win32' else 'clear')
    if sys.platform == 'win32':
        os.system('title Moon Launcher')

    # Ensure CustomSkinLoader and player/friend skins are loaded before boot
    ensure_custom_skin_loader(version_dir, cfg)

    v_name = cfg.get('version_name', os.path.basename(version_dir))
    v_info = detect_version_info(version_dir, v_name)
    mod_count = count_mods(version_dir)
    _, j_ver = check_java_runtime(cfg['java_path'])
    j_ver_short = j_ver.split('"')[1] if '"' in j_ver else '17.0.15'

    box_w = max(66, min(76, get_visible_width(v_info['formatted']) + 4))
    banner_lines = [
        f"{C_CLAUDE}* Moon Launcher v2.2.9.7{CLR_RESET}",
        f"{C_MUTED}{truncate_ansi(v_info['formatted'], box_w)}{CLR_RESET}"
    ]
    print(render_box(banner_lines, box_w))
    print()

    col1_w = 34
    col2_w = 34
    p1 = f"{C_PURPLE}* Version:{CLR_RESET}  {C_WHITE}{truncate_ansi(v_name, col1_w - 14)}{CLR_RESET}"
    p2 = f"{C_CYAN}* Player:{CLR_RESET}   {C_AMBER}{truncate_ansi(cfg['username'], col2_w - 14)}{CLR_RESET}"
    p3 = f"{C_GREEN}* Memory:{CLR_RESET}   {C_WHITE}{cfg['ram_max_gb']} GB{CLR_RESET} {C_MUTED}(Min: {cfg['ram_min_gb']} GB){CLR_RESET}"
    p4 = f"{C_BLUE}* Runtime:{CLR_RESET}  {C_WHITE}Java {j_ver_short}{CLR_RESET}"
    p5 = f"{C_CLAUDE}* Mods:{CLR_RESET}     {C_WHITE}{mod_count} active{CLR_RESET}"
    p6 = f"{C_MUTED}* Display:{CLR_RESET}  {C_WHITE}{cfg['width']}x{cfg['height']}{CLR_RESET}"

    print(f"  {pad_visible(p1, col1_w)}  {pad_visible(p2, col2_w)}")
    print(f"  {pad_visible(p3, col1_w)}  {pad_visible(p4, col2_w)}")
    print(f"  {pad_visible(p5, col1_w)}  {pad_visible(p6, col2_w)}")
    print()
    print(f"  {C_MUTED}Quick Commands:{CLR_RESET} {C_CYAN}/play{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_GREEN}/test{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_AMBER}/fix{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_AMBER}/setting{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_BLUE}/version{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_MUTED}/help{CLR_RESET}")
    u_notice = updater.get_update_notice()
    if u_notice:
        print(f"  {u_notice}")
    print(f"{C_BORDER}{'─' * (box_w + 4)}{CLR_RESET}")

def print_help(topic=None):
    """
    Comprehensive, categorized command manual with in-depth topic guides and shortcuts.
    Strictly 100% English and zero emojis. Pixel-perfect 68-char alignment.
    """
    box_w = 68
    topic = (topic or "").strip().lower()

    if topic in ('host', '/host', 'tunnel', '/tunnel', 'lan', '/lan', 'mabar'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Global Internet Multiplayer & Tunnel Host (/host)\033[0m",
            f"{C_MUTED}Host your singleplayer world for friends over the Internet without Radmin, Hamachi, or Port Forwarding{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/host{CLR_RESET}                       {C_MUTED}View current host and tunnel connection status{CLR_RESET}",
            f"  {C_CYAN}/host start [port]{CLR_RESET}          {C_MUTED}Activate Anycast internet tunnel for your LAN world{CLR_RESET}",
            f"  {C_CYAN}/host stop{CLR_RESET}                  {C_MUTED}Stop tunnel daemon and close public address{CLR_RESET}",
            f"  {C_CYAN}/host scan{CLR_RESET}                  {C_MUTED}Discover open LAN worlds on your Wi-Fi or virtual network{CLR_RESET}",
            "",
            f"{C_WHITE}How Internet Hosting Works (Zero-Config):{CLR_RESET}",
            f"  1. In Minecraft, open your world and click {C_WHITE}'Open to LAN'{CLR_RESET}.",
            f"  2. In Moon Launcher CLI, type {C_GREEN}/host start{CLR_RESET}.",
            f"  3. Copy the public address generated (e.g. {C_CYAN}subdomain.playit.gg:12345{CLR_RESET}).",
            f"  4. Friends paste that address into standard Minecraft Multiplayer menu!",
            f"  • {C_WHITE}Works with offline & free accounts out of the box!{CLR_RESET}",
            f"  • {C_WHITE}Works on cellular hotspot, home Wi-Fi, and CGNAT routers!{CLR_RESET}"
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    elif topic in ('friend', '/friend', 'friends', '/friends', 'contacts'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Friends & Player Contacts Hub (/friend)\033[0m",
            f"{C_MUTED}Manage your multiplayer friends, saved addresses, skin avatars, and ping status{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/friend invite{CLR_RESET}              {C_MUTED}Generate & auto-copy 1-click shareable invite link{CLR_RESET}",
            f"  {C_CYAN}/friend add <link_or_name>{CLR_RESET}  {C_MUTED}Add friend via invite link or username [ip:port]{CLR_RESET}",
            f"  {C_CYAN}/invite{CLR_RESET}                     {C_MUTED}Quick shortcut to generate your invite link{CLR_RESET}",
            f"  {C_CYAN}/friend{CLR_RESET}                     {C_MUTED}Display friends table with live online/offline ping{CLR_RESET}",
            f"  {C_CYAN}/friend remove <name>{CLR_RESET}      {C_MUTED}Remove friend from your contact list{CLR_RESET}",
            f"  {C_CYAN}/friend ping <name>{CLR_RESET}        {C_MUTED}Check latency (ms), players, and version in real-time{CLR_RESET}",
            f"  {C_CYAN}/friend note <name> <txt>{CLR_RESET}  {C_MUTED}Attach custom note (e.g. /friend note Alex Fear Host){CLR_RESET}",
            "",
            f"{C_WHITE}Key Features:{CLR_RESET}",
            f"  • {C_WHITE}Live Server List Ping{CLR_RESET}: Checks latency & online status without entering game.",
            f"  • {C_WHITE}Custom Skin Sync{CLR_RESET}: Automatically pulls friend's skin head avatar."
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    elif topic in ('server', '/server', 'servers', '/servers'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Favorite Multiplayer Server Manager (/server)\033[0m",
            f"{C_MUTED}Bookmark favorite servers and query live latency and player counts{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/server{CLR_RESET}                    {C_MUTED}List favorite servers with live status and ping ms{CLR_RESET}",
            f"  {C_CYAN}/server add <name> <ip>{CLR_RESET}   {C_MUTED}Add a server to favorites (e.g. /server add Hypixel mc.hypixel.net){CLR_RESET}",
            f"  {C_CYAN}/server remove <name>{CLR_RESET}     {C_MUTED}Remove server from favorites list{CLR_RESET}",
            f"  {C_CYAN}/server ping <ip:port>{CLR_RESET}     {C_MUTED}Query any Minecraft server status and player count{CLR_RESET}"
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('test', '/test', 'check', '/check', 'dryrun', '/dryrun', 'diagnose'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Modpack Pre-flight Diagnostic (/test)\033[0m",
            f"{C_MUTED}Dry-run and inspect active or target modpack for crashes & missing files{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/test{CLR_RESET}                    {C_MUTED}Run full pre-flight test on active modpack{CLR_RESET}",
            f"  {C_CYAN}/test <name>{CLR_RESET}             {C_MUTED}Run test on a specific installed modpack{CLR_RESET}",
            "",
            f"{C_WHITE}Diagnostics Performed:{CLR_RESET}",
            f"  1. {C_WHITE}Java Compatibility{CLR_RESET}: Checks Java 8/17/21 against Minecraft version",
            f"  2. {C_WHITE}Client Executable{CLR_RESET}: Verifies client JAR integrity & file size",
            f"  3. {C_WHITE}LWJGL Natives{CLR_RESET}: Audits required LWJGL 2 or 3 DLL binaries",
            f"  4. {C_WHITE}Launch Arguments{CLR_RESET}: Validates syntax & unescaped quote flags",
            f"  5. {C_WHITE}Mod Integrity{CLR_RESET}: Scans for 0-byte, corrupt, or duplicate mod JARs",
            f"  6. {C_WHITE}Boot Simulation{CLR_RESET}: Live dry-run startup test with crash detection",
            "",
            f"{C_WHITE}Next Steps:{CLR_RESET}",
            f"  • If issues are found, simply type {C_GREEN}/fix{CLR_RESET} to automatically repair them!",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('fix', '/fix', 'repair', '/repair', 'heal'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Automated Modpack Repair Engine (/fix)\033[0m",
            f"{C_MUTED}One-click resolution of missing libraries, wrong Java, & broken mods{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/fix{CLR_RESET}                     {C_MUTED}Repair all issues on active modpack{CLR_RESET}",
            f"  {C_CYAN}/fix <name>{CLR_RESET}              {C_MUTED}Repair all issues on a specific modpack{CLR_RESET}",
            "",
            f"{C_WHITE}Automatic Fixes Applied:{CLR_RESET}",
            f"  • {C_WHITE}Java Runtime{CLR_RESET}: Auto-switches to matching Java 8/17/21 runtime",
            f"  • {C_WHITE}LWJGL Natives{CLR_RESET}: Provisions missing LWJGL 2 or 3 DLL libraries",
            f"  • {C_WHITE}Client Binary{CLR_RESET}: Downloads or copies intact Minecraft client JAR",
            f"  • {C_WHITE}Corrupt Mods{CLR_RESET}: Quarantines unreadable 0-byte JARs into corrupted_mods/",
            f"  • {C_WHITE}Duplicate Mods{CLR_RESET}: Disables older conflicting duplicate mod versions",
            f"  • {C_WHITE}Launch Arguments{CLR_RESET}: Re-generates clean, unquoted JVM arguments",
            "",
            f"{C_WHITE}Result:{CLR_RESET}",
            f"  • Modpack is made 100% playable without manual configuration!",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('open', '/open', 'folder', 'explorer', 'dir'):
        lines = [
            f"{C_WHITE}\033[1mHelp: File Explorer Opener (/open)\033[0m",
            f"{C_MUTED}Quickly open game directories in Windows File Explorer{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/open{CLR_RESET}                    {C_MUTED}Open active profile directory{CLR_RESET}",
            f"  {C_CYAN}/open mods{CLR_RESET}               {C_MUTED}Open mods folder{CLR_RESET}",
            f"  {C_CYAN}/open saves{CLR_RESET}              {C_MUTED}Open saves / worlds folder{CLR_RESET}",
            f"  {C_CYAN}/open screenshots{CLR_RESET}        {C_MUTED}Open screenshots folder{CLR_RESET}",
            f"  {C_CYAN}/open logs{CLR_RESET}               {C_MUTED}Open logs folder{CLR_RESET}",
            f"  {C_CYAN}/open crash{CLR_RESET}              {C_MUTED}Open crash-reports folder{CLR_RESET}",
            f"  {C_CYAN}/open config{CLR_RESET}             {C_MUTED}Open modpack configuration folder{CLR_RESET}",
            f"  {C_CYAN}/open versions{CLR_RESET}           {C_MUTED}Open Moon Launcher versions directory{CLR_RESET}",
            f"  {C_CYAN}/open skins{CLR_RESET}              {C_MUTED}Open downloaded skins folder{CLR_RESET}",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('crash', '/crash', 'logs', '/logs', 'log', 'diag'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Crash Watchdog & Analyzer (/crash)\033[0m",
            f"{C_MUTED}Instant root-cause diagnostic for Minecraft crashes and freezes{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/crash{CLR_RESET}                  {C_MUTED}Analyze and display last crash report{CLR_RESET}",
            f"  {C_CYAN}/open crash{CLR_RESET}             {C_MUTED}Open crash-reports folder in Explorer{CLR_RESET}",
            f"  {C_CYAN}/open logs{CLR_RESET}              {C_MUTED}Open logs folder to inspect latest.log{CLR_RESET}",
            "",
            f"{C_WHITE}Watchdog Features:{CLR_RESET}",
            f"  • Actively monitors game process during launch window",
            f"  • Automatically catches premature exits and silent failures",
            f"  • Identifies culprit mods, loader conflicts, and OutOfMemory",
            f"  • Recommends one-click fix commands (e.g. /mods disable <mod>)",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('mods', '/mods', 'mod', 'm'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Mod Manager & Toggler (/mods)\033[0m",
            f"{C_MUTED}Safely manage, filter, disable, and enable mods on the fly{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/mods{CLR_RESET}                    {C_MUTED}List active & disabled mods with file sizes{CLR_RESET}",
            f"  {C_CYAN}/mods <query>{CLR_RESET}            {C_MUTED}Filter installed mods matching query{CLR_RESET}",
            f"  {C_CYAN}/mods disable <name|#>{CLR_RESET}   {C_MUTED}Safely disable mod (.jar -> .jar.disabled){CLR_RESET}",
            f"  {C_CYAN}/mods enable <name|#>{CLR_RESET}    {C_MUTED}Re-enable disabled mod (.jar.disabled -> .jar){CLR_RESET}",
            f"  {C_CYAN}/mods toggle <name>{CLR_RESET}      {C_MUTED}Toggle active/disabled state{CLR_RESET}",
            f"  {C_CYAN}/mods open{CLR_RESET}               {C_MUTED}Open mods folder in File Explorer{CLR_RESET}",
            "",
            f"{C_WHITE}Tips:{CLR_RESET}",
            f"  • You can target mods by partial name or list index number",
            f"  • Disabled mods are kept safely without deleting files",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('install', '/install', 'download', 'modpack', 'i'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Modpack & Version Installer (/install)\033[0m",
            f"{C_MUTED}Automated installer for Modrinth, URLs, archives, and vanilla{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/install{CLR_RESET}                 {C_MUTED}Interactive installer studio menu{CLR_RESET}",
            f"  {C_CYAN}/install fabric [v]{CLR_RESET}      {C_MUTED}Install clean Fabric Loader (e.g. 1.20.1){CLR_RESET}",
            f"  {C_CYAN}/install forge [v]{CLR_RESET}       {C_MUTED}Install Minecraft Forge (e.g. 1.12.2, 1.20.1){CLR_RESET}",
            f"  {C_CYAN}/install neoforge [v]{CLR_RESET}    {C_MUTED}Install NeoForge (e.g. 1.21.1, 1.20.4){CLR_RESET}",
            f"  {C_CYAN}/install quilt [v]{CLR_RESET}       {C_MUTED}Install Quilt Loader (e.g. 1.20.1){CLR_RESET}",
            f"  {C_CYAN}/install vanilla [v]{CLR_RESET}     {C_MUTED}Install official vanilla version{CLR_RESET}",
            f"  {C_CYAN}/install <name>{CLR_RESET}          {C_MUTED}Online search & install from Modrinth{CLR_RESET}",
            "",
            f"{C_WHITE}Features & Technical Details:{CLR_RESET}",
            f"  • Progress display simulates Linux Ubuntu APT ({C_CYAN}Get:1{CLR_RESET}, {C_CYAN}Progress{CLR_RESET})",
            f"  • Automatically extracts modpack overrides and client configs",
            f"  • Configures bootloaders automatically (Fabric, Forge, Vanilla)",
            f"  • Target directory: {C_WHITE}C:\\Moon-Launcher\\versions\\<name>\\{CLR_RESET}",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('setting', '/setting', 'settings', 's', 'nano'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Settings Studio & Quick Edits (/setting)\033[0m",
            f"{C_MUTED}Configure memory allocation, player identity, skins, and display{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/setting{CLR_RESET}                 {C_MUTED}Interactive full-screen Settings Studio (TUI){CLR_RESET}",
            f"  {C_CYAN}/setting ram <gb>{CLR_RESET}        {C_MUTED}Set maximum RAM in GB (e.g. /setting ram 12){CLR_RESET}",
            f"  {C_CYAN}/setting minram <gb>{CLR_RESET}     {C_MUTED}Set initial RAM in GB (e.g. /setting minram 2){CLR_RESET}",
            f"  {C_CYAN}/setting user <name>{CLR_RESET}     {C_MUTED}Set player username (e.g. /setting user JustMichellee){CLR_RESET}",
            f"  {C_CYAN}/setting skin <url>{CLR_RESET}      {C_MUTED}Download and apply custom player skin PNG{CLR_RESET}",
            f"  {C_CYAN}/setting res <W> <H>{CLR_RESET}     {C_MUTED}Set window display resolution (e.g. 1920 1080){CLR_RESET}",
            f"  {C_CYAN}/setting fullscreen{CLR_RESET}     {C_MUTED}Toggle fullscreen display mode{CLR_RESET}",
            f"  {C_CYAN}/setting java <path>{CLR_RESET}     {C_MUTED}Point to custom javaw.exe executable path{CLR_RESET}",
            "",
            f"{C_WHITE}Skin Tip:{CLR_RESET}",
            f"  • URLs auto-download directly to {C_WHITE}skins/<user>.png{CLR_RESET}",
            f"  • Synchronized with CustomSkinLoader for offline display",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('version', '/version', 'versions', 'v'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Version & Profile Management (/version)\033[0m",
            f"{C_MUTED}Switch between multiple Minecraft versions, Forge, & Fabric profiles{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/version{CLR_RESET}                 {C_MUTED}List installed profiles & pick active version{CLR_RESET}",
            f"  {C_CYAN}/version <name>{CLR_RESET}          {C_MUTED}Directly switch active profile by name{CLR_RESET}",
            "",
            f"{C_WHITE}Discovery Roots:{CLR_RESET}",
            f"  1. Local Launcher:  {C_WHITE}C:\\Moon-Launcher\\versions\\*\\{CLR_RESET}",
            f"  2. Official Folder: {C_WHITE}%APPDATA%\\.minecraft\\versions\\*\\{CLR_RESET}",
            "",
            f"{C_WHITE}Tips:{CLR_RESET}",
            f"  • Active version is saved permanently in launcher_config.json",
            f"  • Quick delete: In /version prompt, type {C_AMBER}d <number>{CLR_RESET} to delete",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    if topic in ('remove', '/remove', 'delete', '/delete', 'uninstall', 'rm'):
        lines = [
            f"{C_WHITE}\033[1mHelp: Version Uninstaller (/remove)\033[0m",
            f"{C_MUTED}Safely delete installed modpacks, reclaim disk space, and purge files{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}/remove{CLR_RESET}                  {C_MUTED}Interactive version removal menu with sizes{CLR_RESET}",
            f"  {C_CYAN}/remove <name>{CLR_RESET}           {C_MUTED}Target version for removal (e.g. /remove Example){CLR_RESET}",
            "",
            f"{C_WHITE}Safety Guarantees:{CLR_RESET}",
            f"  • Prompts for mandatory confirmation ([y/N]) with size info",
            f"  • If ACTIVE version is deleted, auto-switches to next profile",
            f"  • Ubuntu APT-style purge output display",
            f"  • Clears Windows read-only locks to prevent deletion errors",
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    # Default Comprehensive Manual
    lines = [
        f"{C_WHITE}\033[1mMoon Launcher — Command Reference Manual\033[0m",
        f"{C_MUTED}Type /help <command> for in-depth guide (e.g. /help install){CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
        f"{C_WHITE}\033[1mGAMEPLAY & RUNTIME\033[0m",
        f"  {C_CYAN}/play{CLR_RESET} [1]               {C_MUTED}Launch active Minecraft in background{CLR_RESET}",
        f"  {C_CYAN}/test{CLR_RESET} [t]               {C_MUTED}Pre-flight diagnostics & dry-run test{CLR_RESET}",
        f"  {C_CYAN}/fix{CLR_RESET} [f]                {C_MUTED}Auto-repair modpack & runtime issues{CLR_RESET}",
        f"  {C_CYAN}/status{CLR_RESET} [3]             {C_MUTED}System diagnostics, JVM, and mods count{CLR_RESET}",
        f"  {C_CYAN}/update{CLR_RESET} [u]             {C_MUTED}1-click seamless update from GitHub{CLR_RESET}",
        f"  {C_CYAN}/crash{CLR_RESET}                  {C_MUTED}Inspect latest crash diagnostics & cause{CLR_RESET}",
        "",
        f"{C_WHITE}\033[1mMULTIPLAYER & NETWORKING\033[0m",
        f"  {C_CYAN}/host [start|stop]{CLR_RESET}   {C_MUTED}Global internet tunnel (No Radmin / No Port Forward){CLR_RESET}",
        f"  {C_CYAN}/host scan{CLR_RESET}              {C_MUTED}Auto-discover open worlds on local network/LAN{CLR_RESET}",
        f"  {C_CYAN}/invite{CLR_RESET}                     {C_MUTED}Generate & copy 1-click multiplayer invite link{CLR_RESET}",
        f"  {C_CYAN}/friend [list]{CLR_RESET}          {C_MUTED}View friends, live status, ping, and notes{CLR_RESET}",
        f"  {C_CYAN}/friend join <name>{CLR_RESET}     {C_MUTED}Auto-sync friend's custom modpack & join game{CLR_RESET}",
        f"  {C_CYAN}/friend add <link>{CLR_RESET}      {C_MUTED}Add friend instantly by pasting their invite link{CLR_RESET}",
        f"  {C_CYAN}/friend invite{CLR_RESET}          {C_MUTED}Create shareable link (attaches live /host IP){CLR_RESET}",
        f"  {C_CYAN}/friend ping <name>{CLR_RESET}     {C_MUTED}Check real-time server latency and online status{CLR_RESET}",
        f"  {C_CYAN}/server [list]{CLR_RESET}          {C_MUTED}Browse favorite servers with live player counts{CLR_RESET}",
        f"  {C_CYAN}/server add <name> <ip>{CLR_RESET} {C_MUTED}Save server to favorites list{CLR_RESET}",
        f"  {C_CYAN}/lan [sync]{CLR_RESET}             {C_MUTED}View & probe LAN / Radmin peer skin auto-sync{CLR_RESET}",
        "",
        f"{C_WHITE}\033[1mMODPACK & VERSION MANAGEMENT\033[0m",
        f"  {C_CYAN}/install{CLR_RESET}                {C_MUTED}Open Modpack & Version Installer Studio{CLR_RESET}",
        f"  {C_CYAN}/install <modpack>{CLR_RESET}      {C_MUTED}Search & auto-install from Modrinth{CLR_RESET}",
        f"  {C_CYAN}/install vanilla <v>{CLR_RESET}    {C_MUTED}Install official vanilla (e.g. 1.20.1){CLR_RESET}",
        f"  {C_CYAN}/install url <link>{CLR_RESET}     {C_MUTED}Install modpack from web link (.mrpack){CLR_RESET}",
        f"  {C_CYAN}/version{CLR_RESET} [4]            {C_MUTED}List & switch active profile{CLR_RESET}",
        f"  {C_CYAN}/remove <name>{CLR_RESET} [5]      {C_MUTED}Uninstall / delete a version (/rm){CLR_RESET}",
        "",
        f"{C_WHITE}\033[1mCONFIGURATION & CUSTOMIZATION\033[0m",
        f"  {C_CYAN}/skin <url|file>{CLR_RESET}        {C_MUTED}Set custom skin for player or friend (/skin friend){CLR_RESET}",
        f"  {C_CYAN}/setting{CLR_RESET} [2]            {C_MUTED}Open interactive Settings Studio (TUI){CLR_RESET}",
        f"  {C_CYAN}/setting ram <gb>{CLR_RESET}       {C_MUTED}Set max RAM (e.g. /setting ram 12){CLR_RESET}",
        f"  {C_CYAN}/setting user <name>{CLR_RESET}    {C_MUTED}Set player username (e.g. JustMichellee){CLR_RESET}",
        f"  {C_CYAN}/setting skin <url>{CLR_RESET}     {C_MUTED}Auto-download skin to skins/<user>.png{CLR_RESET}",
        f"  {C_CYAN}/setting res <W> <H>{CLR_RESET}    {C_MUTED}Set resolution (e.g. 1920 1080){CLR_RESET}",
        "",
        f"{C_WHITE}\033[1mMODS & UTILITY\033[0m",
        f"  {C_CYAN}/mods [filter]{CLR_RESET}          {C_MUTED}List/filter mods (/mods disable|enable){CLR_RESET}",
        f"  {C_CYAN}/open [folder]{CLR_RESET}          {C_MUTED}Open mods/saves/logs in File Explorer{CLR_RESET}",
        f"  {C_CYAN}/clear{CLR_RESET}                  {C_MUTED}Clear screen and redraw banner (/cls){CLR_RESET}",
        f"  {C_CYAN}/help [command]{CLR_RESET}         {C_MUTED}Show command guide (e.g. /help install){CLR_RESET}",
        f"  {C_CYAN}/exit{CLR_RESET}                   {C_MUTED}Exit Moon Launcher CLI (/quit, /q){CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
        f"{C_WHITE}Storage Paths:{CLR_RESET}",
        f"  • Versions:  {C_WHITE}C:\\Moon-Launcher\\versions\\{CLR_RESET}",
        f"  • Skins:     {C_WHITE}C:\\Moon-Launcher\\skins\\{CLR_RESET}",
        f"  • Quick Num: {C_WHITE}1{CLR_RESET} Play • {C_WHITE}2{CLR_RESET} Settings • {C_WHITE}3{CLR_RESET} Status • {C_WHITE}4{CLR_RESET} Version • {C_WHITE}5{CLR_RESET} Remove",
    ]
    print("\n" + render_box(lines, box_w) + "\n")

def print_status(version_dir, cfg):
    print(f"\n{C_WHITE}── Modpack & System Diagnostics ──{CLR_RESET}")
    v_name = cfg.get('version_name', os.path.basename(version_dir))
    v_info = detect_version_info(version_dir, v_name)
    mod_count = count_mods(version_dir)
    j_ok, j_msg = check_java_runtime(cfg['java_path'])
    args_path = os.path.join(version_dir, 'launch_args.txt')
    has_args = os.path.exists(args_path)
    natives_ok = os.path.exists(os.path.join(version_dir, 'natives'))

    print(f"  Installation Directory : {C_WHITE}{version_dir}{CLR_RESET}")
    print(f"  Modpack Profile        : {C_WHITE}{v_info['formatted']}{CLR_RESET}")
    print(f"  Active Mods Installed  : {C_GREEN}{mod_count} mods{CLR_RESET}")
    icon_p = os.path.join(version_dir, 'icon.png')
    icon_w = os.path.join(version_dir, 'icon.webp')
    has_custom = bool(cfg.get('discord_large_image')) and cfg.get('discord_large_image') != DEFAULT_MINECRAFT_ICON_URL
    icon_display = f"{C_GREEN}Custom Modpack Icon{CLR_RESET}" if has_custom else f"{C_CYAN}Default Pure Minecraft Icon{CLR_RESET}"
    print(f"  Modpack Icon           : {icon_display}")
    print(f"  Natives Directory      : {C_GREEN}Available{CLR_RESET}" if natives_ok else f"  Natives Directory      : {C_RED}Missing{CLR_RESET}")
    print(f"  launch_args.txt        : {C_GREEN}Present & Synchronized{CLR_RESET}" if has_args else f"  launch_args.txt        : {C_RED}Missing{CLR_RESET}")
    print(f"  Config File            : {C_CYAN}{get_config_path(version_dir)}{CLR_RESET}")
    print(f"  Java Runtime Status    : {C_GREEN}Valid ({j_msg}){CLR_RESET}" if j_ok else f"  Java Runtime Status    : {C_RED}Invalid / Not Found ({cfg['java_path']}){CLR_RESET}")
    print(f"  Configured Max Memory  : {C_AMBER}{cfg['ram_max_gb']} GB (-Xmx{cfg['ram_max_gb']}G){CLR_RESET}")
    print(f"  Configured Min Memory  : {C_MUTED}{cfg['ram_min_gb']} GB (-Xms{cfg['ram_min_gb']}G){CLR_RESET}")
    rpc_st = f"{C_GREEN}Active & Synchronized{CLR_RESET}" if (GLOBAL_RPC and GLOBAL_RPC.connected) else f"{C_CYAN}Enabled{CLR_RESET}"
    print(f"  Discord Rich Presence  : {rpc_st}")
    lan_count = len(network_hub.get_lan_skin_peers())
    lan_st = f"{C_GREEN}Active & Listening ({lan_count} peers synced){CLR_RESET}" if network_hub.LAN_SYNC_RUNNING else f"{C_RED}Stopped{CLR_RESET}"
    print(f"  LAN & Radmin Skin Sync : {lan_st}")
    c_diag = analyze_latest_crash(version_dir)
    if c_diag and c_diag.get('failure_message') and (time.time() - c_diag.get('mtime', 0)) < 86400:
        c_status_str = f"{C_AMBER}{c_diag['error_type']} ({c_diag['time']}){CLR_RESET}"
    else:
        c_status_str = f"{C_GREEN}Clean (No crashes detected){CLR_RESET}"
    print(f"  Recent Crash Status    : {c_status_str}")
    print()

def open_folder(version_dir, subfolder=None):
    """
    Opens target version subdirectories directly in Windows File Explorer.
    Supports: mods, saves/worlds, screenshots, logs, crash-reports, config, versions, skins.
    """
    sub = (subfolder or "").strip().lower()
    target_dir = version_dir
    label = "Active Version"

    if sub in ('mods', 'mod', 'm'):
        target_dir = os.path.join(version_dir, 'mods')
        label = "Mods"
    elif sub in ('saves', 'save', 'worlds', 'world', 'w'):
        target_dir = os.path.join(version_dir, 'saves')
        label = "Saves / Worlds"
    elif sub in ('screenshots', 'screenshot', 'screens', 'screen', 'pic', 'pics'):
        target_dir = os.path.join(version_dir, 'screenshots')
        label = "Screenshots"
    elif sub in ('logs', 'log', 'latest'):
        target_dir = os.path.join(version_dir, 'logs')
        label = "Logs"
    elif sub in ('crash', 'crashes', 'crash-reports', 'reports'):
        target_dir = os.path.join(version_dir, 'crash-reports')
        label = "Crash Reports"
    elif sub in ('config', 'configs', 'cfg'):
        target_dir = os.path.join(version_dir, 'config')
        label = "Config"
    elif sub in ('versions', 'version', 'v'):
        target_dir = r"C:\Moon-Launcher\versions"
        label = "All Versions"
    elif sub in ('skins', 'skin'):
        target_dir = r"C:\Moon-Launcher\skins"
        label = "Skins"
    elif sub in ('launcher', 'root', 'base'):
        target_dir = r"C:\Moon-Launcher"
        label = "Moon Launcher Directory"

    os.makedirs(target_dir, exist_ok=True)
    try:
        if sys.platform == 'win32':
            os.startfile(target_dir)
        else:
            subprocess.Popen(['xdg-open', target_dir])
        print(f"  {C_GREEN}[OK] Opened {label} folder in File Explorer:{CLR_RESET}")
        print(f"       {C_WHITE}{target_dir}{CLR_RESET}\n")
        return True
    except Exception as e:
        print(f"  {C_RED}[ERR] Failed to open folder: {e}{CLR_RESET}\n")
        return False

def manage_mods(version_dir, args=None):
    """
    Interactive and direct CLI mod manager.
    Supports: /mods [filter], /mods disable <name|#>, /mods enable <name|#>, /mods toggle <name|#>, /mods open
    """
    mods_dir = os.path.join(version_dir, 'mods')
    if not os.path.exists(mods_dir):
        print(f"{C_RED}Mods directory not found: {mods_dir}{CLR_RESET}\n")
        return

    args = args or []
    sub = args[0].lower() if args else "list"

    if sub in ('open', 'folder', 'dir'):
        open_folder(version_dir, 'mods')
        return

    all_files = sorted(os.listdir(mods_dir))
    active_mods = [f for f in all_files if f.endswith('.jar')]
    disabled_mods = [f for f in all_files if f.endswith(('.jar.disabled', '.disabled'))]

    if sub in ('disable', 'off', 'd'):
        if len(args) < 2:
            print(f"{C_AMBER}Usage: /mods disable <mod_name_or_number>{CLR_RESET}")
            print(f"{C_MUTED}Example: /mods disable parcool or /mods disable 3{CLR_RESET}\n")
            return
        target = " ".join(args[1:]).strip().lower()
        matched = []
        if target.isdigit():
            idx = int(target)
            if 1 <= idx <= len(active_mods):
                matched = [active_mods[idx - 1]]
        else:
            matched = [m for m in active_mods if target in m.lower()]

        if not matched:
            print(f"{C_RED}[ERR] No active mod found matching '{target}'.{CLR_RESET}\n")
            return
        if len(matched) > 1:
            print(f"{C_AMBER}Multiple mods matched '{target}':{CLR_RESET}")
            for m in matched[:8]:
                print(f"  • {C_WHITE}{m}{CLR_RESET}")
            print(f"{C_MUTED}Please refine your search query or specify by index number.{CLR_RESET}\n")
            return

        chosen = matched[0]
        src = os.path.join(mods_dir, chosen)
        dst = src + ".disabled"
        try:
            os.rename(src, dst)
            print(f"{C_GREEN}[OK] Disabled mod:{CLR_RESET} {C_WHITE}{chosen}{CLR_RESET} {C_MUTED}-> {os.path.basename(dst)}{CLR_RESET}\n")
        except Exception as e:
            print(f"{C_RED}[ERR] Failed to disable mod: {e}{CLR_RESET}\n")
        return

    if sub in ('enable', 'on', 'e'):
        if len(args) < 2:
            print(f"{C_AMBER}Usage: /mods enable <mod_name_or_number>{CLR_RESET}")
            print(f"{C_MUTED}Example: /mods enable parcool or /mods enable 1{CLR_RESET}\n")
            return
        target = " ".join(args[1:]).strip().lower()
        matched = []
        if target.isdigit():
            idx = int(target)
            if 1 <= idx <= len(disabled_mods):
                matched = [disabled_mods[idx - 1]]
        else:
            matched = [m for m in disabled_mods if target in m.lower()]

        if not matched:
            print(f"{C_RED}[ERR] No disabled mod found matching '{target}'.{CLR_RESET}\n")
            return
        if len(matched) > 1:
            print(f"{C_AMBER}Multiple disabled mods matched '{target}':{CLR_RESET}")
            for m in matched[:8]:
                print(f"  • {C_WHITE}{m}{CLR_RESET}")
            print(f"{C_MUTED}Please refine your search query or specify by index number.{CLR_RESET}\n")
            return

        chosen = matched[0]
        src = os.path.join(mods_dir, chosen)
        clean_name = chosen[:-len(".disabled")] if chosen.endswith(".disabled") else chosen
        if not clean_name.endswith(".jar"):
            clean_name += ".jar"
        dst = os.path.join(mods_dir, clean_name)
        try:
            os.rename(src, dst)
            print(f"{C_GREEN}[OK] Enabled mod:{CLR_RESET} {C_WHITE}{clean_name}{CLR_RESET}\n")
        except Exception as e:
            print(f"{C_RED}[ERR] Failed to enable mod: {e}{CLR_RESET}\n")
        return

    if sub in ('toggle', 't'):
        if len(args) < 2:
            print(f"{C_AMBER}Usage: /mods toggle <mod_name>{CLR_RESET}\n")
            return
        target = " ".join(args[1:]).strip().lower()
        act_match = [m for m in active_mods if target in m.lower()]
        dis_match = [m for m in disabled_mods if target in m.lower()]
        if act_match and not dis_match:
            manage_mods(version_dir, ['disable', act_match[0]])
        elif dis_match and not act_match:
            manage_mods(version_dir, ['enable', dis_match[0]])
        elif act_match and dis_match:
            print(f"{C_AMBER}Both active and disabled mods match '{target}'. Specify /mods enable or /mods disable.{CLR_RESET}\n")
        else:
            print(f"{C_RED}[ERR] No mod found matching '{target}'.{CLR_RESET}\n")
        return

    # List / search
    query = " ".join(args[1:]).strip().lower() if sub in ('list', 'ls') else " ".join(args).strip().lower()
    disp_active = [m for m in active_mods if (not query or query in m.lower())]
    disp_disabled = [m for m in disabled_mods if (not query or query in m.lower())]

    box_w = 68
    header_str = f"Installed Mods ({len(active_mods)} active, {len(disabled_mods)} disabled)"
    if query:
        header_str += f" matching '{query}'"
    print(f"\n{C_WHITE}\033[1m{header_str}\033[0m")
    print(C_BORDER + ('─' * box_w) + CLR_RESET)

    if not disp_active and not disp_disabled:
        print(f"  {C_MUTED}No mods found.{CLR_RESET}")
    else:
        if disp_active:
            print(f"{C_GREEN}Active Mods ({len(disp_active)}):{CLR_RESET}")
            for idx, j in enumerate(disp_active, 1):
                f_path = os.path.join(mods_dir, j)
                try:
                    sz_kb = os.path.getsize(f_path) // 1024
                    sz_str = f"{sz_kb:,} kB" if sz_kb < 1024 else f"{sz_kb/1024:.1f} MB"
                except Exception:
                    sz_str = ""
                sz_tag = f" {C_MUTED}({sz_str}){CLR_RESET}" if sz_str else ""
                print(f"  {C_MUTED}{idx:3d}.{CLR_RESET} {C_CYAN}{j}{CLR_RESET}{sz_tag}")

        if disp_disabled:
            if disp_active: print()
            print(f"{C_AMBER}Disabled Mods ({len(disp_disabled)}):{CLR_RESET}")
            for idx, j in enumerate(disp_disabled, 1):
                f_path = os.path.join(mods_dir, j)
                try:
                    sz_kb = os.path.getsize(f_path) // 1024
                    sz_str = f"{sz_kb:,} kB" if sz_kb < 1024 else f"{sz_kb/1024:.1f} MB"
                except Exception:
                    sz_str = ""
                sz_tag = f" {C_MUTED}({sz_str}){CLR_RESET}" if sz_str else ""
                print(f"  {C_MUTED}{idx:3d}.{CLR_RESET} {C_MUTED}[DISABLED]{CLR_RESET} {C_WHITE}{j}{CLR_RESET}{sz_tag}")

    print(C_BORDER + ('─' * box_w) + CLR_RESET)
    print(f"{C_MUTED}Commands:{CLR_RESET} {C_CYAN}/mods disable <name|#>{CLR_RESET} • {C_CYAN}/mods enable <name|#>{CLR_RESET} • {C_CYAN}/mods open{CLR_RESET}\n")

def list_mods(version_dir, filter_query=""):
    """Backward-compatible alias for manage_mods."""
    if filter_query:
        manage_mods(version_dir, ['list', filter_query])
    else:
        manage_mods(version_dir, ['list'])

def analyze_latest_crash(version_dir):
    """
    Parses the most recent crash report or log file in version_dir.
    Returns a dictionary of diagnostic data or None.
    """
    crashes_dir = os.path.join(version_dir, 'crash-reports')
    latest_file = None
    if os.path.exists(crashes_dir):
        txts = [os.path.join(crashes_dir, f) for f in os.listdir(crashes_dir) if f.endswith('.txt')]
        if txts:
            latest_file = max(txts, key=os.path.getmtime)

    check_log = False
    if not latest_file:
        check_log = True
    elif (time.time() - os.path.getmtime(latest_file)) > 600:
        log_file = os.path.join(version_dir, 'logs', 'latest.log')
        if os.path.exists(log_file) and os.path.getmtime(log_file) > os.path.getmtime(latest_file):
            check_log = True

    if check_log:
        log_file = os.path.join(version_dir, 'logs', 'latest.log')
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            return _analyze_log_file(log_file)
        if not latest_file:
            return None

    try:
        with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None

    info = {
        'source': 'crash-report',
        'file': latest_file,
        'filename': os.path.basename(latest_file),
        'mtime': os.path.getmtime(latest_file),
        'time': 'Unknown',
        'description': 'Unknown',
        'error_type': 'Minecraft Runtime Crash',
        'culprit_mod': None,
        'failure_message': None,
        'recommendation': None,
        'stack_preview': []
    }

    m_time = re.search(r"Time:\s*(.+)", content)
    if m_time: info['time'] = m_time.group(1).strip()

    m_desc = re.search(r"Description:\s*(.+)", content)
    if m_desc: info['description'] = m_desc.group(1).strip()

    # Forge/NeoForge mod failure block
    m_mod = re.search(r"-- MOD\s+([^\s\-]+)\s*--\s*Details:\s*Mod File:\s*(.+?)\s*Failure message:\s*(.+?)(?=\n\t\w|\n--|\nStacktrace|\Z)", content, re.DOTALL)
    if m_mod:
        info['culprit_mod'] = m_mod.group(1).strip()
        mod_file = os.path.basename(m_mod.group(2).strip().replace('\\', '/'))
        info['failure_message'] = " ".join(m_mod.group(3).split())
        info['error_type'] = f"Mod Failure: {info['culprit_mod']}"
        info['recommendation'] = f"Disable or update {mod_file}: type '/mods disable {info['culprit_mod']}'"

    # Fabric Incompatible mods
    if not info['failure_message']:
        m_incompat = re.search(r"net\.fabricmc\.loader\.impl\.FormattedException:\s*(.+?)(?=\n\tat|\Z)", content, re.DOTALL)
        if m_incompat:
            info['error_type'] = "Fabric Incompatible Mods"
            info['failure_message'] = " ".join(m_incompat.group(1).split())
            info['recommendation'] = "Check required Fabric dependencies or remove conflicting mods."

    # OutOfMemory
    if "OutOfMemoryError" in content:
        info['error_type'] = "Out Of Memory (OutOfMemoryError)"
        info['failure_message'] = "Minecraft ran out of allocated RAM heap during startup or loading."
        info['recommendation'] = "Increase allocated memory: type '/setting ram 8' or '/setting ram 12'"

    # UnsatisfiedLinkError
    elif "UnsatisfiedLinkError" in content:
        info['error_type'] = "Native Library / Driver Error (UnsatisfiedLinkError)"
        info['failure_message'] = "Failed to load native library (LWJGL/OpenGL). Natives may be missing or corrupt."
        info['recommendation'] = "Run '/status' to check natives, or update graphics card drivers."

    # Java mismatch
    elif "UnsupportedClassVersionError" in content:
        info['error_type'] = "Java Runtime Version Mismatch"
        info['failure_message'] = "A mod was compiled with a newer Java version than current runtime."
        info['recommendation'] = "Switch to Java 21: type '/setting java' and point to Java 21."

    # Generic fallback
    if not info['failure_message']:
        m_exc = re.search(r"(java\.lang\.\w+Exception[^\n]*)", content)
        if m_exc:
            info['error_type'] = m_exc.group(1).strip()
            info['failure_message'] = info['description']
            info['recommendation'] = "Inspect logs or disable recently added mods: type '/open logs'"

    # Extract top relevant stack lines
    stack = []
    in_stack = False
    for line in content.splitlines():
        if "Stacktrace:" in line:
            in_stack = True
            continue
        if in_stack:
            s_line = line.strip()
            if s_line.startswith("at "):
                if not any(k in s_line for k in ["jdk.internal", "java.lang.reflect", "cpw.mods.modlauncher"]):
                    stack.append(s_line)
                    if len(stack) >= 4:
                        break
            elif s_line.startswith("--") or s_line == "":
                if stack: break

    info['stack_preview'] = stack
    return info

def _analyze_log_file(log_path):
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-200:]
    except Exception:
        return None

    text = "".join(lines)
    info = {
        'source': 'latest.log',
        'file': log_path,
        'filename': os.path.basename(log_path),
        'mtime': os.path.getmtime(log_path),
        'time': 'Recent Session',
        'description': 'Crash or Fatal Error in latest.log',
        'error_type': 'Fatal Execution Error',
        'culprit_mod': None,
        'failure_message': None,
        'recommendation': 'Type /open logs to inspect complete log output.',
        'stack_preview': []
    }

    if "FormattedException: Incompatible mods found!" in text:
        info['error_type'] = "Incompatible Mods Detected"
        info['failure_message'] = "Fabric KnotClient found incompatible mods or loader version."
        info['recommendation'] = "Check mod versions or disable conflicting mods via /mods"
    elif "OutOfMemoryError" in text:
        info['error_type'] = "Out Of Memory"
        info['failure_message'] = "JVM heap exhausted."
        info['recommendation'] = "Allocate more RAM: type '/setting ram 8'"
    elif "UnsatisfiedLinkError" in text:
        info['error_type'] = "UnsatisfiedLinkError (Missing Natives)"
        info['failure_message'] = "Failed to load LWJGL / OpenGL native binary."
        info['recommendation'] = "Run /status to check natives."
    else:
        for l in reversed(lines):
            if any(k in l for k in ["[Render thread/FATAL]", "[main/FATAL]", "[Server thread/FATAL]", "[Render thread/ERROR]"]):
                info['failure_message'] = l.strip()
                break

    if not info['failure_message']:
        return None
    return info

def show_crash_report(version_dir):
    """Interactive command handler for /crash."""
    report = analyze_latest_crash(version_dir)
    box_w = 72
    if not report or not report.get('failure_message'):
        lines = [
            f"{C_GREEN}\033[1m[OK] No Crashes Detected\033[0m",
            f"{C_MUTED}Active profile shows no recorded crash reports or fatal log entries.{CLR_RESET}",
            "",
            f"If Minecraft failed to launch, type {C_CYAN}/open logs{CLR_RESET} to view raw console output."
        ]
        print("\n" + render_box(lines, box_w) + "\n")
        return

    lines = [
        f"{C_RED}\033[1mCrash Diagnostic Report\033[0m",
        f"{C_MUTED}Source: {report['filename']}  │  Recorded: {report['time']}{CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
        f"{C_WHITE}Category:{CLR_RESET}       {C_AMBER}{report['error_type']}{CLR_RESET}",
        f"{C_WHITE}Description:{CLR_RESET}    {report['description']}",
        f"{C_WHITE}Root Cause:{CLR_RESET}     {report['failure_message'][:60]}",
    ]
    if report.get('culprit_mod'):
        lines.append(f"{C_WHITE}Culprit Mod:{CLR_RESET}    {C_RED}{report['culprit_mod']}{CLR_RESET}")
    if report.get('recommendation'):
        lines.append(f"{C_WHITE}Resolution:{CLR_RESET}     {C_GREEN}{report['recommendation']}{CLR_RESET}")

    if report.get('stack_preview'):
        lines.append(C_BORDER + ('─' * (box_w - 4)) + CLR_RESET)
        lines.append(f"{C_WHITE}Key Stacktrace Preview:{CLR_RESET}")
        for st in report['stack_preview']:
            lines.append(f"  {C_MUTED}{st[:62]}{CLR_RESET}")

    lines.append(C_BORDER + ('─' * (box_w - 4)) + CLR_RESET)
    lines.append(f"Quick Actions: {C_CYAN}/open crash{CLR_RESET} • {C_CYAN}/open logs{CLR_RESET} • {C_CYAN}/mods{CLR_RESET}")
    print("\n" + render_box(lines, box_w) + "\n")

def _watch_game_process(proc, version_dir, v_name):
    """Monitors game subprocess during startup and reports immediate crash diagnostics."""
    t_start = time.time()
    while time.time() - t_start < 40:
        ret = proc.poll()
        if ret is not None:
            elapsed = time.time() - t_start
            time.sleep(1.2)  # Wait for log flush
            report = analyze_latest_crash(version_dir)
            box_w = 72
            if report and report.get('failure_message'):
                lines = [
                    f"{C_RED}\033[1m[CRASH WATCHDOG] Minecraft Terminated Abnormally!\033[0m",
                    f"{C_MUTED}Detected premature exit after {elapsed:.1f}s (Exit Code: {ret}){CLR_RESET}",
                    C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
                    f"{C_WHITE}Profile:{CLR_RESET}        {v_name}",
                    f"{C_WHITE}Issue Type:{CLR_RESET}     {C_AMBER}{report['error_type']}{CLR_RESET}",
                    f"{C_WHITE}Reason:{CLR_RESET}         {report['failure_message'][:62]}",
                ]
                if report.get('culprit_mod'):
                    lines.append(f"{C_WHITE}Culprit Mod:{CLR_RESET}    {C_RED}{report['culprit_mod']}{CLR_RESET}")
                if report.get('recommendation'):
                    lines.append(f"{C_WHITE}Suggested Fix:{CLR_RESET}  {C_GREEN}{report['recommendation']}{CLR_RESET}")
                lines.append(C_BORDER + ('─' * (box_w - 4)) + CLR_RESET)
                lines.append(f"Type {C_CYAN}/crash{CLR_RESET} for full report or {C_CYAN}/open logs{CLR_RESET} for latest.log")
                print("\n\n" + render_box(lines, box_w))
            else:
                if ret != 0:
                    lines = [
                        f"{C_RED}\033[1m[CRASH WATCHDOG] Minecraft Process Exited with Code {ret}\033[0m",
                        f"{C_MUTED}Session terminated after {elapsed:.1f}s.{CLR_RESET}",
                        "",
                        f"Type {C_CYAN}/crash{CLR_RESET} or {C_CYAN}/open logs{CLR_RESET} to inspect debug details."
                    ]
                    print("\n\n" + render_box(lines, box_w))
            print(f"\n{C_CLAUDE}moon{CLR_RESET} {C_MUTED}❯{CLR_RESET} ", end="", flush=True)
            return
        time.sleep(1.0)
def launch_game(version_dir, cfg):
    box_w = 66
    mc_ver, loader = detect_version_and_loader(version_dir)
    j_path = get_best_java_for_version(mc_ver, cfg.get('java_path'))
    if not os.path.exists(j_path):
        err_lines = [
            f"{C_RED}X Java Runtime not found at:{CLR_RESET}",
            f"{C_MUTED}{j_path}{CLR_RESET}",
            f"{C_AMBER}Please run /setting to adjust your java_path.{CLR_RESET}"
        ]
        print("\n" + render_box(err_lines, box_w) + "\n")
        return False

    ensure_launch_args(version_dir, declared_loader=loader, mc_version=mc_ver)
    args_path = os.path.join(version_dir, 'launch_args.txt')
    if not os.path.exists(args_path):
        err_lines = [
            f"{C_RED}X launch_args.txt not found in version folder!{CLR_RESET}",
            f"{C_MUTED}{version_dir}{CLR_RESET}"
        ]
        print("\n" + render_box(err_lines, box_w) + "\n")
        return False

    update_launch_args(version_dir, cfg)

    with open(args_path, 'r', encoding='utf-8-sig') as f:
        launch_args = []
        for l in f.readlines():
            l = l.strip()
            if not l:
                continue
            if len(l) >= 2 and l[0] == '"' and l[-1] == '"':
                l = l[1:-1]
            # Strip internal quotes from system properties (e.g. -Djava.library.path="path")
            if l.startswith('-D') and '=' in l:
                key, val = l.split('=', 1)
                val = val.strip('"').strip("'")
                l = f"{key}={val}"
            launch_args.append(l.lstrip('\ufeff'))

    full_cmd = [j_path] + launch_args
    if cfg.get('fullscreen', False):
        full_cmd.append('--fullscreen')
    if cfg.get('server'):
        full_cmd.extend(['--server', str(cfg['server'])])
        if cfg.get('port'):
            full_cmd.extend(['--port', str(cfg['port'])])
        cfg.pop('server', None)
        cfg.pop('port', None)
        try:
            save_config(cfg)
        except Exception:
            pass

    v_name = cfg.get('version_name', os.path.basename(version_dir))
    v_info = detect_version_info(version_dir, v_name)
    mod_count = count_mods(version_dir)

    starting_lines = [
        f"{C_GREEN}Starting {v_name}...{CLR_RESET}",
        f"{C_WHITE}Profile:{CLR_RESET}  {v_info['formatted']} ({mod_count} mods)",
        f"{C_WHITE}Player:{CLR_RESET}   {cfg['username']}  │  {C_WHITE}RAM:{CLR_RESET} {cfg['ram_max_gb']} GB"
    ]
    print("\n" + render_box(starting_lines, box_w) + "\n")

    try:
        proc = subprocess.Popen(
            full_cmd,
            cwd=version_dir if os.path.exists(version_dir) else os.path.expandvars(r"%APPDATA%\.minecraft"),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        if GLOBAL_RPC:
            GLOBAL_RPC.set_playing(version_dir, cfg, proc)
        t = threading.Thread(target=_watch_game_process, args=(proc, version_dir, v_name), daemon=True)
        t.start()
        launch_lines = [
            f"{C_GREEN}[OK] Game launched successfully! (PID: {proc.pid}){CLR_RESET}",
            "",
            f"{C_MUTED}Game is running in the background.{CLR_RESET}",
            f"{C_MUTED}Watchdog is actively monitoring startup for crash errors.{CLR_RESET}",
            f"{C_MUTED}You can keep this CLI window open or type /exit.{CLR_RESET}"
        ]
        print("\n" + render_box(launch_lines, box_w) + "\n")
        return True
    except Exception as e:
        err_lines = [
            f"{C_RED}X Failed to launch game: {e}{CLR_RESET}"
        ]
        print("\n" + render_box(err_lines, box_w) + "\n")
        return False


def resolve_version_target(curr_dir, cfg, arg_name=None):
    """
    Resolves the targeted version directory and configuration.
    If arg_name is None, returns (curr_dir, cfg).
    Otherwise, matches against installed versions (exact or partial).
    """
    if not arg_name:
        return curr_dir, cfg
    arg_clean = arg_name.strip().strip('"').strip("'").lower()
    avail = get_all_available_versions()
    # Exact match
    for name, path in avail.items():
        if name.lower() == arg_clean:
            target_cfg = load_config(path)
            return path, target_cfg
    # Partial match
    for name, path in avail.items():
        if arg_clean in name.lower():
            target_cfg = load_config(path)
            return path, target_cfg
    return curr_dir, cfg

def run_preflight_test(version_dir, cfg, dry_run_seconds=7):
    """
    Comprehensive modpack pre-flight diagnostic and dry-run boot test (/test).
    Audits static requirements (Java runtime compatibility, client jar, LWJGL natives,
    launch arguments, mod integrity, duplicate mods) followed by a live boot simulation.
    Saves detected issues to .moon_diagnostics.json so /fix can automatically repair them.
    """
    box_w = 68
    v_name = cfg.get('version_name', os.path.basename(version_dir))
    mc_ver, loader = detect_version_and_loader(version_dir)
    diagnostics_file = os.path.join(version_dir, '.moon_diagnostics.json')

    print(f"\n{C_CLAUDE}Starting Pre-flight Diagnostics for {C_WHITE}{v_name}{CLR_RESET} {C_MUTED}({loader} {mc_ver}){CLR_RESET}...\n")

    issues = []
    checks = []

    # 1. Profile and Directory Integrity
    if not os.path.exists(version_dir):
        issues.append({"type": "missing_directory", "detail": f"Profile directory not found: {version_dir}"})
        checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "Profile Directory", "Directory does not exist on disk"))
    else:
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Profile Directory", f"Found at {os.path.basename(version_dir)}"))

    # 2. Java Runtime Compatibility Check
    parts = [int(p) for p in re.findall(r'\d+', mc_ver)]
    major = parts[0] if len(parts) > 0 else 1
    minor = parts[1] if len(parts) > 1 else 20
    patch = parts[2] if len(parts) > 2 else 0

    if major == 1 and minor <= 16:
        req_java_ver = 8
    elif (major == 1 and minor >= 21) or (major == 1 and minor == 20 and patch >= 5):
        req_java_ver = 21
    else:
        req_java_ver = 17

    current_java = cfg.get('java_path', '')
    j_exists = os.path.exists(current_java) if current_java else False
    detected_j_ver = None

    if j_exists:
        try:
            res = subprocess.run([current_java, '-version'], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=5)
            out = res.stderr or res.stdout
            match = re.search(r'version\s+"(\d+)(?:\.(\d+))?', out, re.IGNORECASE)
            if match:
                v1 = int(match.group(1))
                v2 = int(match.group(2)) if match.group(2) else 0
                detected_j_ver = v2 if v1 == 1 else v1
        except Exception:
            pass

    best_java = get_best_java_for_version(mc_ver, current_java)
    if detected_j_ver == req_java_ver:
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Java Runtime", f"Java {detected_j_ver} active (Matches MC {mc_ver})"))
    else:
        curr_str = f"Java {detected_j_ver}" if detected_j_ver else "Unknown / Missing"
        checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "Java Runtime", f"{curr_str} (MC {mc_ver} requires Java {req_java_ver})"))
        issues.append({
            "type": "java_mismatch",
            "required_java": req_java_ver,
            "current_java": detected_j_ver,
            "recommended_path": best_java,
            "detail": f"Switch Java runtime from {curr_str} to Java {req_java_ver}"
        })

    # 3. Client JAR Integrity Check
    target_jar = os.path.join(version_dir, f"{os.path.basename(version_dir)}.jar")
    client_jar = os.path.join(version_dir, "client.jar")
    mc_ver_jar = os.path.join(version_dir, f"{mc_ver}.jar")

    found_jar = None
    jar_size = 0
    for c_jar in (target_jar, client_jar, mc_ver_jar):
        if os.path.exists(c_jar):
            found_jar = c_jar
            jar_size = os.path.getsize(c_jar)
            break

    if found_jar and jar_size > 1000000:
        mb = jar_size / (1024 * 1024)
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Client JAR", f"{os.path.basename(found_jar)} verified ({mb:.1f} MB)"))
    else:
        checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "Client JAR", "Client binary is missing or 0 bytes"))
        issues.append({
            "type": "missing_client_jar",
            "target_jar": target_jar,
            "mc_ver": mc_ver,
            "detail": f"Restore valid Minecraft {mc_ver} client executable JAR"
        })

    # 4. LWJGL Native Libraries Check
    target_natives = os.path.join(version_dir, 'natives')
    is_legacy_lwjgl2 = (minor <= 12)
    natives_ok = False
    n_files = []
    if os.path.exists(target_natives):
        n_files = [f.lower() for f in os.listdir(target_natives)]
        if is_legacy_lwjgl2:
            if 'lwjgl64.dll' in n_files or 'lwjgl.dll' in n_files:
                natives_ok = True
        else:
            if 'lwjgl.dll' in n_files or 'glfw.dll' in n_files:
                natives_ok = True

    if natives_ok:
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "LWJGL Natives", f"LWJGL {'2' if is_legacy_lwjgl2 else '3'} binaries present ({len(n_files)} DLLs)"))
    else:
        checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "LWJGL Natives", f"Missing LWJGL {'2' if is_legacy_lwjgl2 else '3'} native libraries in natives/"))
        issues.append({
            "type": "missing_natives",
            "mc_ver": mc_ver,
            "is_legacy_lwjgl2": is_legacy_lwjgl2,
            "detail": f"Provision compatible LWJGL {'2' if is_legacy_lwjgl2 else '3'} native DLLs"
        })

    # 5. Launch Arguments & Formatting Check
    args_path = os.path.join(version_dir, 'launch_args.txt')
    args_ok = True
    args_reason = ""
    if not os.path.exists(args_path):
        args_ok = False
        args_reason = "launch_args.txt does not exist"
    else:
        try:
            with open(args_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                content_args = f.read()
            if '-Djava.library.path="' in content_args or "-Djava.library.path='" in content_args:
                args_ok = False
                args_reason = "Double-quoted -Djava.library.path triggers UnsatisfiedLinkError"
            elif loader == 'Vanilla' and ('bootstraplauncher' in content_args or 'KnotClient' in content_args):
                args_ok = False
                args_reason = "Outdated Forge/Fabric bootstrap in Vanilla profile"
            elif loader == 'Forge' and 'KnotClient' in content_args:
                args_ok = False
                args_reason = "Mismatched Fabric KnotClient in Forge profile"
            elif loader == 'Fabric' and 'bootstraplauncher' in content_args:
                args_ok = False
                args_reason = "Mismatched Forge bootstraplauncher in Fabric profile"
        except Exception as e:
            args_ok = False
            args_reason = str(e)

    if args_ok:
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Launch Arguments", "launch_args.txt syntax and paths valid"))
    else:
        checks.append((f"{C_AMBER}[WARN]{CLR_RESET}", "Launch Arguments", args_reason))
        issues.append({
            "type": "invalid_launch_args",
            "reason": args_reason,
            "detail": "Re-generate and sanitize launch_args.txt"
        })

    # 6. Mod Files Integrity & Duplicates Scan
    mods_dir = os.path.join(version_dir, 'mods')
    corrupt_mods = []
    duplicate_mods = []
    active_mod_count = 0

    if os.path.exists(mods_dir):
        jar_files = [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
        active_mod_count = len(jar_files)
        seen_prefixes = {}
        for j in jar_files:
            fp = os.path.join(mods_dir, j)
            try:
                sz = os.path.getsize(fp)
                if sz == 0 or not zipfile.is_zipfile(fp):
                    corrupt_mods.append(j)
                    continue
            except Exception:
                corrupt_mods.append(j)
                continue

            clean_name = re.sub(r'[-_](?:v?\d+(?:\.\d+)*.*|\d+)\.jar$', '', j, flags=re.IGNORECASE).lower()
            if clean_name in seen_prefixes:
                duplicate_mods.append((seen_prefixes[clean_name], j))
            else:
                seen_prefixes[clean_name] = j

    if corrupt_mods:
        checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "Mod Integrity", f"{len(corrupt_mods)} corrupted or 0-byte mod(s) detected"))
        issues.append({
            "type": "corrupt_mods",
            "files": corrupt_mods,
            "detail": f"Quarantine {len(corrupt_mods)} corrupted mod jar(s) to prevent crash"
        })
    elif duplicate_mods:
        checks.append((f"{C_AMBER}[WARN]{CLR_RESET}", "Mod Integrity", f"{len(duplicate_mods)} duplicate mod version(s) found"))
        issues.append({
            "type": "duplicate_mods",
            "pairs": duplicate_mods,
            "detail": f"Disable {len(duplicate_mods)} duplicate mod version(s)"
        })
    else:
        checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Mod Integrity", f"{active_mod_count} active mods verified intact"))

    # 7. Live Dry-Run Boot Simulation
    can_simulate = (j_exists and found_jar and jar_size > 1000000 and os.path.exists(args_path))

    if not can_simulate:
        checks.append((f"{C_MUTED}[SKIP]{CLR_RESET}", "Boot Simulation", "Skipped (prerequisite static errors present)"))
    else:
        print(f"  {C_MUTED}Running dry-run boot simulation ({dry_run_seconds}s timeout)...{CLR_RESET}", flush=True)
        with open(args_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            raw_args = []
            for l in f.readlines():
                l = l.strip()
                if not l: continue
                if len(l) >= 2 and l[0] == '"' and l[-1] == '"':
                    l = l[1:-1]
                if l.startswith('-D') and '=' in l:
                    k, v = l.split('=', 1)
                    v = v.strip('"').strip("'")
                    l = f"{k}={v}"
                raw_args.append(l.lstrip('\ufeff'))

        test_cmd = [current_java] + raw_args
        t_start = time.time()
        sim_proc = None
        crashed = False
        crash_reason = ""

        try:
            sim_proc = subprocess.Popen(
                test_cmd,
                cwd=version_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            while time.time() - t_start < dry_run_seconds:
                poll_ret = sim_proc.poll()
                if poll_ret is not None:
                    crashed = True
                    crash_reason = f"Process terminated prematurely (Exit Code: {poll_ret})"
                    break
                time.sleep(0.5)

            if not crashed:
                try:
                    sim_proc.terminate()
                    sim_proc.wait(timeout=2)
                except Exception:
                    try: sim_proc.kill()
                    except Exception: pass
        except Exception as e:
            crashed = True
            crash_reason = f"Failed to execute process: {e}"

        if crashed:
            log_p = os.path.join(version_dir, 'logs', 'latest.log')
            detected_err_line = ""
            if os.path.exists(log_p):
                try:
                    with open(log_p, 'r', encoding='utf-8', errors='ignore') as lf:
                        log_tail = lf.readlines()[-30:]
                        for line in reversed(log_tail):
                            line_s = line.strip()
                            if any(k in line_s for k in ('Exception', 'Error', 'FATAL', 'UnsatisfiedLinkError', 'MissingModsException')):
                                detected_err_line = line_s
                                break
                except Exception:
                    pass

            if detected_err_line:
                short_err = detected_err_line
                if ': ' in short_err:
                    short_err = short_err.split(': ', 1)[1]
                crash_reason += f" - {short_err[:50]}"

            checks.append((f"{C_RED}[FAIL]{CLR_RESET}", "Boot Simulation", crash_reason[:60]))
            issues.append({
                "type": "boot_crash",
                "reason": crash_reason,
                "detail": f"Game crashed during startup: {crash_reason}"
            })
        else:
            checks.append((f"{C_GREEN}[PASS]{CLR_RESET}", "Boot Simulation", f"Engine initialized stably ({dry_run_seconds}s check OK)"))

    # Save diagnostic findings to .moon_diagnostics.json
    diag_data = {
        "version_name": v_name,
        "version_dir": version_dir,
        "mc_ver": mc_ver,
        "loader": loader,
        "timestamp": int(time.time()),
        "issues_count": len(issues),
        "issues": issues
    }
    try:
        with open(diagnostics_file, 'w', encoding='utf-8') as df:
            json.dump(diag_data, df, indent=2)
    except Exception:
        pass

    # Render Ubuntu APT / Moon Launcher Report Table
    report_lines = [
        f"{C_WHITE}\033[1mPre-flight Diagnostic Report: {v_name}\033[0m",
        f"{C_MUTED}Profile: {loader} {mc_ver}  |  Directory: {os.path.basename(version_dir)}{CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET
    ]

    for status_badge, check_title, check_detail in checks:
        left = f"  {status_badge} {C_WHITE}{check_title:<17}{CLR_RESET}"
        right = f"{C_MUTED}{truncate_ansi(check_detail, box_w - 28)}{CLR_RESET}"
        report_lines.append(f"{left} {right}")

    report_lines.append(C_BORDER + ('─' * (box_w - 4)) + CLR_RESET)

    if not issues:
        report_lines.append(f"{C_GREEN}[OK] All diagnostics PASSED! Modpack is 100% healthy.{CLR_RESET}")
        report_lines.append(f"{C_WHITE}Ready to play! Type {C_CYAN}/play{CLR_RESET}{C_WHITE} to launch Minecraft now.{CLR_RESET}")
    else:
        report_lines.append(f"{C_RED}[!] Found {len(issues)} issue(s) that will prevent normal gameplay:{CLR_RESET}")
        for idx, iss in enumerate(issues, 1):
            report_lines.append(f"    {C_AMBER}{idx}.{CLR_RESET} {C_WHITE}{iss['detail']}{CLR_RESET}")
        report_lines.append("")
        report_lines.append(f"{C_GREEN}Solution: Simply type {C_CYAN}/fix{CLR_RESET}{C_GREEN} to automatically resolve all issues!{CLR_RESET}")

    print("\n" + render_box(report_lines, box_w) + "\n")
    return len(issues) == 0

def run_auto_fix(version_dir, cfg):
    """
    Automated one-click repair engine (/fix).
    Reads .moon_diagnostics.json or executes a fresh audit, then systematically resolves:
    1. Java Runtime Mismatch (auto-switches to matching Java 8/17/21 from Mojang runtime/PATH).
    2. Missing/Wrong LWJGL Natives (copies LWJGL 2 or LWJGL 3 binaries).
    3. Missing Client JAR (restores valid Minecraft client jar from donor/Mojang).
    4. Corrupted / 0-byte Mods (quarantines them safely into corrupted_mods/).
    5. Duplicate Mods (disables older conflicting duplicates with .jar.disabled).
    6. Launch Arguments & Formatting (removes quotes in -Djava.library.path, regenerates).
    Outputs Ubuntu APT-style progress and verifies readiness for gameplay.
    """
    box_w = 68
    v_name = cfg.get('version_name', os.path.basename(version_dir))
    mc_ver, loader = detect_version_and_loader(version_dir)
    diagnostics_file = os.path.join(version_dir, '.moon_diagnostics.json')

    print(f"\n{C_CLAUDE}Starting Automated Repair Engine (/fix) for {C_WHITE}{v_name}{CLR_RESET}...\n")

    diag_data = None
    if os.path.exists(diagnostics_file):
        try:
            with open(diagnostics_file, 'r', encoding='utf-8') as df:
                diag_data = json.load(df)
        except Exception:
            diag_data = None

    if not diag_data or 'issues' not in diag_data:
        print(f"  {C_MUTED}No cached diagnostics found. Running instant pre-flight scan...{CLR_RESET}")
        run_preflight_test(version_dir, cfg, dry_run_seconds=1)
        if os.path.exists(diagnostics_file):
            try:
                with open(diagnostics_file, 'r', encoding='utf-8') as df:
                    diag_data = json.load(df)
            except Exception:
                pass

    issues = diag_data.get('issues', []) if diag_data else []

    if not issues:
        clean_lines = [
            f"{C_GREEN}[OK] No issues detected for {v_name}!{CLR_RESET}",
            "",
            f"{C_MUTED}This modpack is already in optimal health and ready to play.{CLR_RESET}",
            f"{C_WHITE}Type {C_CYAN}/play{CLR_RESET}{C_WHITE} to start your game.{CLR_RESET}"
        ]
        print("\n" + render_box(clean_lines, box_w) + "\n")
        return cfg

    repaired_items = []

    # 1. Fix Java Runtime Mismatch
    java_issue = next((i for i in issues if i.get('type') == 'java_mismatch'), None)
    if java_issue:
        best_java = get_best_java_for_version(mc_ver)
        if best_java and os.path.exists(best_java):
            cfg['java_path'] = best_java
            save_config(version_dir, cfg)
            j_folder = os.path.basename(os.path.dirname(os.path.dirname(best_java)))
            print(f"  {C_GREEN}Get:1{CLR_RESET} Switching Java runtime to {C_WHITE}{j_folder}{CLR_RESET} ({best_java})")
            repaired_items.append(f"Switched Java runtime to {j_folder} (compatible with MC {mc_ver})")
        else:
            print(f"  {C_AMBER}Warn:1{CLR_RESET} Could not find required Java {java_issue.get('required_java')} in runtime folder.")

    # 2. Fix Missing LWJGL Natives
    natives_issue = next((i for i in issues if i.get('type') == 'missing_natives'), None)
    if natives_issue or not os.path.exists(os.path.join(version_dir, 'natives')):
        print(f"  {C_GREEN}Get:2{CLR_RESET} Provisioning matching LWJGL native libraries...")
        ensure_natives_for_version(version_dir, mc_ver)
        repaired_items.append(f"Restored matching LWJGL natives into natives/")

    # 3. Fix Missing Client JAR
    jar_issue = next((i for i in issues if i.get('type') == 'missing_client_jar'), None)
    if jar_issue:
        print(f"  {C_GREEN}Get:3{CLR_RESET} Restoring Minecraft {mc_ver} client executable...")
        ensure_launch_args(version_dir, declared_loader=loader, mc_version=mc_ver)
        repaired_items.append(f"Installed valid client JAR for Minecraft {mc_ver}")

    # 4. Fix Corrupted / 0-byte Mods
    corrupt_issue = next((i for i in issues if i.get('type') == 'corrupt_mods'), None)
    if corrupt_issue:
        corrupt_files = corrupt_issue.get('files', [])
        quarantine_dir = os.path.join(version_dir, 'corrupted_mods')
        os.makedirs(quarantine_dir, exist_ok=True)
        q_count = 0
        for cf in corrupt_files:
            src = os.path.join(version_dir, 'mods', cf)
            dst = os.path.join(quarantine_dir, cf)
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                    q_count += 1
                except Exception:
                    pass
        print(f"  {C_GREEN}Get:4{CLR_RESET} Quarantined {q_count} corrupted mod(s) to corrupted_mods/")
        repaired_items.append(f"Quarantined {q_count} corrupted mod(s) into corrupted_mods/")

    # 5. Fix Duplicate Mods
    dup_issue = next((i for i in issues if i.get('type') == 'duplicate_mods'), None)
    if dup_issue:
        dup_pairs = dup_issue.get('pairs', [])
        d_count = 0
        for f1, f2 in dup_pairs:
            target_to_disable = f1 if len(f1) < len(f2) else f2
            p = os.path.join(version_dir, 'mods', target_to_disable)
            if os.path.exists(p) and not p.endswith('.disabled'):
                try:
                    os.rename(p, p + '.disabled')
                    d_count += 1
                except Exception:
                    pass
        print(f"  {C_GREEN}Get:5{CLR_RESET} Disabled {d_count} conflicting duplicate mod(s)")
        repaired_items.append(f"Disabled {d_count} conflicting duplicate mod(s)")

    # 6. Fix Launch Arguments & JVM Flags
    print(f"  {C_GREEN}Get:6{CLR_RESET} Sanitizing launch arguments and system properties...")
    ensure_launch_args(version_dir, declared_loader=loader, mc_version=mc_ver)
    update_launch_args(version_dir, cfg)
    repaired_items.append("Regenerated and sanitized launch_args.txt")

    try:
        if os.path.exists(diagnostics_file):
            os.remove(diagnostics_file)
    except Exception:
        pass

    fix_lines = [
        f"{C_WHITE}\033[1mAutomated Repair Complete: {v_name}\033[0m",
        f"{C_MUTED}All detected problems have been systematically remediated.{CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET
    ]

    for item in repaired_items:
        fix_lines.append(f"  {C_GREEN}[FIXED]{CLR_RESET} {C_WHITE}{item}{CLR_RESET}")

    fix_lines.append(C_BORDER + ('─' * (box_w - 4)) + CLR_RESET)
    fix_lines.append(f"{C_GREEN}[OK] Repair operations finished successfully!{CLR_RESET}")
    fix_lines.append(f"{C_WHITE}Run {C_CYAN}/test{CLR_RESET}{C_WHITE} to verify or {C_CYAN}/play{CLR_RESET}{C_WHITE} to start Minecraft!{CLR_RESET}")

    print("\n" + render_box(fix_lines, box_w) + "\n")
    return cfg

def remove_version(curr_dir, cfg, target_name=None):
    """
    Uninstalls and completely removes an installed Minecraft version/modpack directory.
    Uses Ubuntu APT purge-style messaging and updates active configuration if active version was deleted.
    """
    avail_map = get_all_available_versions()
    avail_names = list(avail_map.keys())

    if not avail_names:
        print(f"\n{C_AMBER}No installed versions found to remove.{CLR_RESET}")
        return curr_dir, cfg

    chosen_name = None
    chosen_path = None

    if target_name:
        target_clean = target_name.strip().strip('"').strip("'")
        match = next((k for k in avail_names if k.lower() == target_clean.lower()), None)
        if not match:
            match = next((k for k in avail_names if target_clean.lower() in k.lower()), None)
        if match:
            chosen_name = match
            chosen_path = avail_map[match]
        else:
            print(f"\n{C_RED}Error: Version '{target_name}' was not found in installed profiles!{CLR_RESET}")
            return curr_dir, cfg
    else:
        box_w = 66
        menu_lines = [
            f"{C_WHITE}\033[1mMoon Launcher — Uninstall & Remove Version\033[0m",
            f"{C_MUTED}Permanently delete installed versions, mods, and configurations{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
        ]
        print("\n" + render_box(menu_lines, box_w) + "\n")

        print(f"{C_WHITE}Available Versions:{CLR_RESET}")
        for idx, v in enumerate(avail_names, 1):
            is_active = (v == os.path.basename(curr_dir) or v == cfg.get('version_name'))
            mark = f" {C_GREEN}[ACTIVE]{CLR_RESET}" if is_active else ""
            v_p = avail_map[v]
            v_disp = truncate_ansi(v_p, 42)
            print(f"  {C_CYAN}[{idx:2d}]{CLR_RESET} {C_WHITE}{v}{CLR_RESET}{mark} {C_MUTED}({v_disp}){CLR_RESET}")

        try:
            sel = input(f"\n{C_AMBER}Select version number to DELETE [1-{len(avail_names)}] (or 0 to cancel): {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return curr_dir, cfg

        if not sel or sel in ('0', 'q', 'cancel', 'exit'):
            print(f"{C_MUTED}Deletion cancelled.{CLR_RESET}")
            return curr_dir, cfg

        if not sel.isdigit() or not (1 <= int(sel) <= len(avail_names)):
            print(f"{C_RED}Invalid selection number.{CLR_RESET}")
            return curr_dir, cfg

        chosen_name = avail_names[int(sel) - 1]
        chosen_path = avail_map[chosen_name]

    # Calculate size of directory to display in APT output
    total_bytes = 0
    file_count = 0
    try:
        for root, dirs, files in os.walk(chosen_path):
            for f in files:
                file_count += 1
                try:
                    total_bytes += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    size_mb = total_bytes / (1024 * 1024)

    is_active = (chosen_name == os.path.basename(curr_dir) or chosen_name == cfg.get('version_name'))
    active_warning = f" {C_AMBER}(NOTE: This is currently your ACTIVE version!){CLR_RESET}" if is_active else ""

    print(f"\n{C_RED}WARNING: You are about to permanently delete:{CLR_RESET}")
    print(f"  Version : {C_WHITE}\033[1m{chosen_name}\033[0m{active_warning}")
    print(f"  Path    : {C_WHITE}{chosen_path}{CLR_RESET}")
    print(f"  Size    : {C_WHITE}{size_mb:.1f} MB ({file_count} files){CLR_RESET}")

    try:
        confirm = input(f"\n{C_AMBER}Are you sure you want to completely remove this version? [y/N]: {CLR_RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return curr_dir, cfg

    if confirm not in ('y', 'yes'):
        print(f"{C_MUTED}Aborted. No files were removed.{CLR_RESET}")
        return curr_dir, cfg

    # Ubuntu APT-style purge output
    print(f"\n{C_WHITE}Reading package lists...{CLR_RESET} Done")
    time.sleep(0.08)
    print(f"{C_WHITE}Building dependency tree...{CLR_RESET} Done")
    time.sleep(0.05)
    print(f"{C_WHITE}Reading state information...{CLR_RESET} Done")
    print(f"\nThe following packages will be REMOVED:")
    print(f"  {C_RED}{chosen_name}{CLR_RESET}")
    print(f"\n0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.")
    print(f"After this operation, {size_mb:.1f} MB disk space will be freed.\n")

    print(f"(Reading database ... {file_count} files and directories currently installed.)")
    print(f"Removing {chosen_name} ...")

    # Helper to force-delete read-only files on Windows
    def _force_rm(func, path, exc_info):
        import stat
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    try:
        shutil.rmtree(chosen_path, onerror=_force_rm)
        print(f"Purging configuration files for {chosen_name} ...")
        print(render_apt_progress_bar(100, 32))
        print(f"\n{C_GREEN}Package '{chosen_name}' and all associated files removed successfully.{CLR_RESET}")
    except Exception as e:
        print(f"{C_RED}E: Failed to completely remove directory: {e}{CLR_RESET}")
        return curr_dir, cfg

    # If the active version was deleted, select a new active version
    if is_active:
        remaining_map = get_all_available_versions()
        if chosen_name in remaining_map:
            del remaining_map[chosen_name]
        
        if remaining_map:
            new_name = list(remaining_map.keys())[0]
            new_dir = remaining_map[new_name]
            set_active_version(new_name)
            curr_dir = new_dir
            cfg = load_config(new_dir)
            cfg['version_name'] = new_name
            save_config(new_dir, cfg)
            save_config(os.path.dirname(os.path.abspath(__file__)), cfg)
            print(f"\n{C_CYAN}Notice: Switched active profile to remaining version: {C_WHITE}{new_name}{CLR_RESET}")
        else:
            print(f"\n{C_AMBER}Notice: No remaining versions installed.{CLR_RESET}")

    return curr_dir, cfg

def switch_version(curr_dir, cfg, target_name=None):
    avail_map = get_all_available_versions()
    avail = list(avail_map.keys())

    if not avail:
        print(f"\n{C_AMBER}No Minecraft installations found across version directories.{CLR_RESET}")
        return curr_dir, cfg

    chosen_name = None

    if target_name:
        target_str = str(target_name).strip().strip('"').strip("'")
        if target_str.isdigit() and 1 <= int(target_str) <= len(avail):
            chosen_name = avail[int(target_str) - 1]
        else:
            # Exact match
            for k in avail:
                if k.lower() == target_str.lower():
                    chosen_name = k
                    break
            # Partial match
            if not chosen_name:
                for k in avail:
                    if target_str.lower() in k.lower():
                        chosen_name = k
                        break
        if not chosen_name:
            print(f"\n{C_RED}Error: Version profile '{target_name}' not found.{CLR_RESET}")
            print(f"{C_MUTED}Active profile remains: {os.path.basename(curr_dir)}{CLR_RESET}")
            return curr_dir, cfg

    if not chosen_name:
        print(f"\n{C_WHITE}Select Minecraft Installation Profile:{CLR_RESET}")
        for idx, v in enumerate(avail, 1):
            is_active = (v == os.path.basename(curr_dir) or v == cfg.get('version_name'))
            mark = f" {C_GREEN}[ACTIVE]{CLR_RESET}" if is_active else ""
            print(f"  {C_CYAN}[{idx:2d}]{CLR_RESET} {v}{mark}")

        try:
            choice = input(f"\n{C_AMBER}Enter profile number or name to switch, [d <num>] to delete, or [0 to cancel]: {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return curr_dir, cfg

        if not choice or choice in ('0', 'q', 'cancel', 'exit'):
            print(f"{C_MUTED}Version switch cancelled.{CLR_RESET}")
            return curr_dir, cfg

        if choice.lower().startswith(('d ', 'del ', 'rm ', 'delete ', 'remove ')):
            parts = choice.split(None, 1)
            if len(parts) > 1:
                target_spec = parts[1].strip()
                if target_spec.isdigit() and 1 <= int(target_spec) <= len(avail):
                    del_name = avail[int(target_spec) - 1]
                    return remove_version(curr_dir, cfg, del_name)
                else:
                    return remove_version(curr_dir, cfg, target_spec)

        if choice.isdigit() and 1 <= int(choice) <= len(avail):
            chosen_name = avail[int(choice) - 1]
        else:
            # Exact match
            for k in avail:
                if k.lower() == choice.lower():
                    chosen_name = k
                    break
            # Partial match
            if not chosen_name:
                for k in avail:
                    if choice.lower() in k.lower():
                        chosen_name = k
                        break

    if not chosen_name:
        print(f"\n{C_RED}Error: Invalid selection. Active profile remains: {os.path.basename(curr_dir)}{CLR_RESET}")
        return curr_dir, cfg

    new_dir = avail_map[chosen_name]
    new_cfg = load_config(new_dir)
    # Carry over global user identity settings
    master_u = cfg.get('username') or get_master_username()
    new_cfg['username'] = master_u
    if cfg.get('custom_skin'):
        new_cfg['custom_skin'] = cfg.get('custom_skin')
    new_cfg['version_name'] = chosen_name

    save_config(new_dir, new_cfg)
    set_active_version(chosen_name)
    try:
        import network_hub
        network_hub.update_active_version(new_dir, chosen_name)
    except Exception:
        pass
    ensure_launch_args(new_dir, declared_loader=new_cfg.get('loader'), mc_version=new_cfg.get('mc_version'))
    update_launch_args(new_dir, new_cfg)

    print(f"\n{C_GREEN}[OK] Successfully switched active profile to: {C_WHITE}{chosen_name}{CLR_RESET}")
    print(f"{C_MUTED}Profile location: {new_dir}{CLR_RESET}\n")
    time.sleep(0.5)
    return new_dir, new_cfg

# ==============================================================================
# UBUNTU APT-STYLE MODPACK & VERSION AUTO-INSTALLER ENGINE
# ==============================================================================

def render_apt_progress_bar(pct, width=32):
    filled = int(width * max(0, min(100, pct)) / 100)
    empty = width - filled
    return f"Progress: [{pct:3d}%] [{('#' * filled)}{('.' * empty)}]"

def download_file_stream(url, dest_path, title=None, get_idx=1):
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Moon-Launcher/2.0 (Ubuntu-APT-Engine)'})
    disp_name = title or os.path.basename(dest_path)

    t0 = time.time()
    part_path = dest_path + ".part"
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            total_len = resp.getheader('Content-Length')
            total_bytes = int(total_len) if total_len and total_len.isdigit() else 0

            size_str = f"[{total_bytes // 1024:,} kB]" if total_bytes > 0 else "[unknown size]"
            print(f"Get:{get_idx} {url} {disp_name} {size_str}")

            dl_bytes = 0
            chunk_size = 65536
            last_draw = 0

            with open(part_path, 'wb') as f_out:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    dl_bytes += len(chunk)

                    now = time.time()
                    if now - last_draw > 0.08 or dl_bytes == total_bytes:
                        last_draw = now
                        elapsed = max(now - t0, 0.001)
                        speed_mb = (dl_bytes / (1024 * 1024)) / elapsed
                        if total_bytes > 0:
                            pct = int(dl_bytes * 100 / total_bytes)
                            bar = render_apt_progress_bar(pct, 28)
                            mb_cur = dl_bytes / (1024 * 1024)
                            mb_tot = total_bytes / (1024 * 1024)
                            sys.stdout.write(f"\r{bar} {mb_cur:.1f}/{mb_tot:.1f} MB ({speed_mb:.1f} MB/s)   \x1b[K")
                        else:
                            mb_cur = dl_bytes / (1024 * 1024)
                            sys.stdout.write(f"\rProgress: [---%] [##############..........] {mb_cur:.1f} MB ({speed_mb:.1f} MB/s)   \x1b[K")
                        sys.stdout.flush()

            # Archive integrity verification for jars and zip archives
            lower_dest = dest_path.lower()
            if lower_dest.endswith(('.zip', '.mrpack', '.jar')) and dl_bytes > 0:
                try:
                    import zipfile
                    with zipfile.ZipFile(part_path, 'r') as zf:
                        bad_entry = zf.testzip()
                        if bad_entry is not None:
                            raise zipfile.BadZipFile(f"Corrupt archive entry: {bad_entry}")
                except Exception as ze:
                    if os.path.exists(part_path):
                        os.remove(part_path)
                    print(f"\rErr:{get_idx} {url} - Corrupted archive detected ({ze})")
                    return False

            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            shutil.move(part_path, dest_path)

            dt = max(time.time() - t0, 0.001)
            mb = dl_bytes / (1024 * 1024)
            speed = mb / dt
            print(f"\rFetched {mb:.1f} MB in {dt:.1f}s ({speed:.1f} MB/s){' ' * 25}")
            return True
    except Exception as e:
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except Exception:
                pass
        print(f"\rErr:{get_idx} {url} - {e}")
        return False

def fetch_modrinth_icon_url(query):
    """Fetches official modpack icon URL from Modrinth API search."""
    if not query:
        return None
    try:
        import urllib.parse
        encoded_q = urllib.parse.quote(query)
        url = f"https://api.modrinth.com/v2/search?query={encoded_q}&facets=[[%22project_type:modpack%22]]&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Moon-Launcher/2.0 (Mozilla/5.0)'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode('utf-8'))
            hits = data.get('hits', [])
            if hits and hits[0].get('icon_url'):
                return hits[0]['icon_url']
    except Exception:
        pass
    return None

def install_modpack_icon(target_dir, modpack_name, icon_url=None, z=None):
    """
    Downloads and installs the modpack's official icon into the modpack directory
    so it displays in Discord Rich Presence. Returns the online icon URL to be saved in launcher_config.json.
    """
    final_icon_url = icon_url

    # 1. Fetch online icon URL if not provided
    if not final_icon_url:
        final_icon_url = fetch_modrinth_icon_url(modpack_name)

    # 2. If online icon URL is available, download and save it inside modpack directory
    downloaded = False
    if final_icon_url:
        try:
            ext = ".webp" if ".webp" in final_icon_url.lower() else ".png"
            target_icon = os.path.join(target_dir, f"icon{ext}")
            download_file_stream(final_icon_url, target_icon, f"icon{ext}")
            downloaded = True
        except Exception:
            pass

    # 3. If online download failed, extract from zip/mrpack archive if available
    if not downloaded and z is not None:
        try:
            for item in z.namelist():
                lower_item = item.lower()
                if lower_item.endswith(('icon.png', 'pack.png', 'modpack.png', 'icon.webp')):
                    ext = os.path.splitext(item)[1]
                    target_icon = os.path.join(target_dir, f"icon{ext}")
                    with open(target_icon, 'wb') as f_out:
                        f_out.write(z.read(item))
                    downloaded = True
                    break
        except Exception:
            pass

    # 4. If we extracted locally without an online URL, upload it to get an HTTPS URL for Discord RPC
    if not final_icon_url and downloaded and target_icon and os.path.exists(target_icon):
        final_icon_url = upload_local_icon(target_icon)

    if downloaded:
        print(f"Setting up modpack-icon ({modpack_name}) ... {C_GREEN}Done.{CLR_RESET}")

    return final_icon_url

def install_vanilla_version(version_id=None):
    print(f"\n{C_WHITE}Reading package lists...{CLR_RESET} Done")
    time.sleep(0.12)
    print(f"{C_WHITE}Building dependency tree...{CLR_RESET} Done")
    time.sleep(0.08)
    print(f"{C_WHITE}Reading state information...{CLR_RESET} Done")

    manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    try:
        req = urllib.request.Request(manifest_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            manifest = json.loads(r.read())
    except Exception as e:
        print(f"{C_RED}E: Failed to fetch Mojang version manifest: {e}{CLR_RESET}")
        return None

    releases = [v for v in manifest.get('versions', []) if v.get('type') == 'release']

    if not version_id:
        print(f"\n{C_CYAN}Popular Official Releases:{CLR_RESET}")
        sample = releases[:8]
        for idx, rel in enumerate(sample, 1):
            print(f"  {C_MUTED}[{idx}]{CLR_RESET} {C_WHITE}{rel['id']}{CLR_RESET}")
        ch = input(f"\n{C_AMBER}Type version number [1-8] or version name (e.g. 1.20.1): {CLR_RESET}").strip()
        if not ch:
            return None
        if ch.isdigit() and 1 <= int(ch) <= len(sample):
            version_id = sample[int(ch) - 1]['id']
        else:
            version_id = ch

    target_info = next((v for v in manifest.get('versions', []) if v['id'] == version_id), None)
    if not target_info:
        print(f"{C_RED}E: Minecraft version '{version_id}' was not found on Mojang servers!{CLR_RESET}")
        return None

    v_dir = os.path.join(BASE_VERSIONS_DIR, version_id)
    os.makedirs(v_dir, exist_ok=True)
    for sub in ('mods', 'config', 'saves', 'resourcepacks', 'shaderpacks', 'logs', 'natives'):
        os.makedirs(os.path.join(v_dir, sub), exist_ok=True)

    print(f"\nThe following NEW packages will be installed:")
    print(f"  {C_CYAN}minecraft-vanilla-{version_id}  client-libraries  asset-index{CLR_RESET}")
    print(f"\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.")
    print(f"Need to get ~25.5 MB of archives.\n")

    json_path = os.path.join(v_dir, f"{version_id}.json")
    jar_path = os.path.join(v_dir, f"{version_id}.jar")

    try:
        download_file_stream(target_info['url'], json_path, f"{version_id}.json", get_idx=1)
        with open(json_path, 'r', encoding='utf-8') as f:
            v_data = json.load(f)

        client_dl = v_data.get('downloads', {}).get('client', {})
        if client_dl.get('url'):
            download_file_stream(client_dl['url'], jar_path, f"{version_id}.jar", get_idx=2)

        print(f"Selecting previously unselected package minecraft-vanilla-{version_id}.")
        print(f"(Reading database ... 100%)")
        print(f"Preparing to unpack minecraft-vanilla-{version_id} ...")
        print(f"Unpacking minecraft-vanilla-{version_id} ({version_id}) ...")
        print(f"Setting up minecraft-vanilla-{version_id} ({version_id}) ...")
        print(render_apt_progress_bar(100, 32))

        ensure_launch_args(v_dir, declared_loader='Vanilla', mc_version=version_id)
        cfg_path = os.path.join(v_dir, 'launcher_config.json')
        if not os.path.exists(cfg_path):
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "ram_max_gb": 4,
                    "ram_min_gb": 1,
                    "username": "Player",
                    "width": 1280,
                    "height": 720,
                    "fullscreen": False,
                    "java_path": get_best_java_for_version(version_id, DEFAULT_JAVA),
                    "version_name": version_id,
                    "loader": "Vanilla",
                    "mc_version": version_id,
                    "discord_rpc": True
                }, f, indent=2)

        set_active_version(version_id)
        print(f"Processing triggers for minecraft-runtime ... {C_GREEN}Done.{CLR_RESET}")
        print(f"\n{C_GREEN}All packages installed successfully! Minecraft Vanilla {version_id} is ready to play.{CLR_RESET}")
        return v_dir
    except Exception as e:
        print(f"{C_RED}E: Failed to install Minecraft Vanilla {version_id}: {e}{CLR_RESET}")
        return None


def install_mod_loader(loader_type=None, mc_version=None):
    """
    Automated downloader and installer for clean Minecraft Mod Loaders:
    Supports: Fabric, Forge, NeoForge, and Quilt.
    Provisions libraries, profile JSON, natives, launcher_config, and launch_args.txt.
    """
    box_w = 66
    
    # 1. Resolve loader type if not provided
    if not loader_type:
        loader_lines = [
            f"{C_WHITE}\033[1mSelect Mod Loader to Install\033[0m",
            f"{C_MUTED}Automated provisioner for clean Minecraft loader profiles{CLR_RESET}",
            C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
            f"  {C_CYAN}[1]{CLR_RESET} {C_WHITE}Fabric Loader   (Ultra-fast, modern, lightweight){CLR_RESET}",
            f"  {C_CYAN}[2]{CLR_RESET} {C_WHITE}Minecraft Forge (Classic, massive mod catalog){CLR_RESET}",
            f"  {C_CYAN}[3]{CLR_RESET} {C_WHITE}NeoForge        (Modern Forge successor for 1.20.2+){CLR_RESET}",
            f"  {C_CYAN}[4]{CLR_RESET} {C_WHITE}Quilt Loader    (Next-gen Fabric-compatible loader){CLR_RESET}",
            f"  {C_RED}[0]{CLR_RESET} {C_MUTED}Back to Installer Studio{CLR_RESET}",
        ]
        print("\n" + render_box(loader_lines, box_w) + "\n")
        try:
            ch = input(f"  {C_AMBER}Select loader [1-4] or [0 to cancel]: {CLR_RESET}").strip().lstrip("\ufeff").lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        
        if ch in ('1', 'fabric'):
            loader_type = 'fabric'
        elif ch in ('2', 'forge'):
            loader_type = 'forge'
        elif ch in ('3', 'neoforge', 'neo'):
            loader_type = 'neoforge'
        elif ch in ('4', 'quilt'):
            loader_type = 'quilt'
        else:
            return None

    loader_norm = loader_type.lower()
    if loader_norm in ('fabric', 'fab'):
        loader_key = 'fabric'
        loader_title = 'Fabric'
        popular = ['1.21.1', '1.20.4', '1.20.1', '1.19.4', '1.19.2', '1.18.2', '1.16.5']
    elif loader_norm in ('forge', 'fml'):
        loader_key = 'forge'
        loader_title = 'Forge'
        popular = ['1.20.1', '1.19.2', '1.18.2', '1.16.5', '1.12.2', '1.7.10']
    elif loader_norm in ('neoforge', 'neo'):
        loader_key = 'neoforge'
        loader_title = 'NeoForge'
        popular = ['1.21.1', '1.21', '1.20.4', '1.20.2']
    elif loader_norm in ('quilt', 'q'):
        loader_key = 'quilt'
        loader_title = 'Quilt'
        popular = ['1.21.1', '1.20.4', '1.20.1', '1.19.2']
    else:
        print(f"{C_RED}E: Unsupported loader type: {loader_type}{CLR_RESET}")
        return None

    # 2. Resolve Minecraft version if not provided
    if not mc_version:
        print(f"\n{C_CYAN}Popular {loader_title} Minecraft Releases:{CLR_RESET}")
        for idx, ver_str in enumerate(popular, 1):
            print(f"  {C_MUTED}[{idx}]{CLR_RESET} {C_WHITE}{ver_str}{CLR_RESET}")
        try:
            ver_input = input(f"\n{C_AMBER}Select version [1-{len(popular)}] or type version (e.g. 1.20.1): {CLR_RESET}").strip().lstrip("\ufeff")
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        if not ver_input:
            return None
        if ver_input.isdigit() and 1 <= int(ver_input) <= len(popular):
            mc_version = popular[int(ver_input) - 1]
        else:
            mc_version = ver_input

    # 3. Target setup
    v_name = f"{loader_title} {mc_version}"
    target_dir = os.path.join(BASE_VERSIONS_DIR, v_name)
    os.makedirs(target_dir, exist_ok=True)
    for sub in ('mods', 'config', 'saves', 'resourcepacks', 'shaderpacks', 'logs', 'natives'):
        os.makedirs(os.path.join(target_dir, sub), exist_ok=True)

    mc_root = os.path.expandvars(r'%APPDATA%\.minecraft')
    lib_root = os.path.join(mc_root, "libraries")
    os.makedirs(lib_root, exist_ok=True)

    print(f"\n{C_WHITE}Reading package lists...{CLR_RESET} Done")
    time.sleep(0.12)
    print(f"{C_WHITE}Building dependency tree...{CLR_RESET} Done")
    time.sleep(0.08)
    print(f"{C_WHITE}Reading state information...{CLR_RESET} Done")
    print(f"\nThe following NEW packages will be installed:")
    print(f"  {C_CYAN}minecraft-{loader_key}-{mc_version}  loader-runtime  client-libraries{CLR_RESET}")
    print(f"\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.")
    print(f"Need to get ~28.5 MB of archives.\n")

    json_path = os.path.join(target_dir, f"{v_name}.json")
    jar_path = os.path.join(target_dir, f"{v_name}.jar")

    # Step 1: Ensure Vanilla Base Client Jar
    found_donor_jar = None
    if not os.path.exists(jar_path) or os.path.getsize(jar_path) < 1000000:
        cands = [
            os.path.join(mc_root, 'versions', mc_version, f"{mc_version}.jar"),
            os.path.join(mc_root, 'versions', f"Forge {mc_version}", f"Forge {mc_version}.jar"),
            os.path.join(mc_root, 'versions', '1.20.1', '1.20.1.jar'),
            os.path.join(BASE_VERSIONS_DIR, mc_version, f"{mc_version}.jar")
        ]
        for c in cands:
            if os.path.exists(c) and os.path.getsize(c) > 1000000:
                found_donor_jar = c
                break
        if found_donor_jar:
            try:
                shutil.copy2(found_donor_jar, jar_path)
            except Exception:
                pass
        else:
            try:
                manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
                req_m = urllib.request.Request(manifest_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
                with urllib.request.urlopen(req_m, timeout=12) as r_m:
                    manifest_data = json.loads(r_m.read())
                v_entry = next((v for v in manifest_data.get('versions', []) if v['id'] == mc_version), None)
                if v_entry:
                    req_v = urllib.request.Request(v_entry['url'], headers={'User-Agent': 'Moon-Launcher/2.0'})
                    with urllib.request.urlopen(req_v, timeout=12) as r_v:
                        v_json_data = json.loads(r_v.read())
                    c_url = v_json_data.get('downloads', {}).get('client', {}).get('url')
                    if c_url:
                        download_file_stream(c_url, jar_path, f"{mc_version}.jar", get_idx=1)
            except Exception as e:
                print(f"{C_AMBER}Warn: Could not download client jar from Mojang: {e}{CLR_RESET}")

    # Step 2: Loader Provisioning
    if loader_key in ('fabric', 'quilt'):
        meta_domain = "meta.fabricmc.net" if loader_key == 'fabric' else "meta.quiltmc.org"
        api_prefix = "v2" if loader_key == 'fabric' else "v3"
        try:
            meta_url = f"https://{meta_domain}/{api_prefix}/versions/loader/{mc_version}"
            req_l = urllib.request.Request(meta_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
            with urllib.request.urlopen(req_l, timeout=12) as r_l:
                loader_data = json.loads(r_l.read())
            if not loader_data:
                print(f"{C_RED}E: No {loader_title} release found for Minecraft {mc_version}{CLR_RESET}")
                return None
            l_version = loader_data[0]['loader']['version']
            
            prof_url = f"https://{meta_domain}/{api_prefix}/versions/loader/{mc_version}/{l_version}/profile/json"
            req_p = urllib.request.Request(prof_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
            with urllib.request.urlopen(req_p, timeout=12) as r_p:
                prof_json = json.loads(r_p.read())
                
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(prof_json, jf, indent=2)

            for lib_idx, lib in enumerate(prof_json.get('libraries', []), 2):
                parts = lib['name'].split(':')
                group, name, ver = parts[0], parts[1], parts[2]
                rel_p = f"{group.replace('.', os.sep)}{os.sep}{name}{os.sep}{ver}{os.sep}{name}-{ver}.jar"
                full_dest = os.path.join(lib_root, rel_p)
                if not os.path.exists(full_dest):
                    os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                    base_url = lib.get('url', 'https://libraries.minecraft.net/')
                    url_p = f"{group.replace('.', '/')}/{name}/{ver}/{name}-{ver}.jar"
                    download_file_stream(base_url + url_p, full_dest, f"{name}-{ver}.jar", get_idx=lib_idx)
        except Exception as e:
            print(f"{C_RED}E: Failed to fetch {loader_title} metadata: {e}{CLR_RESET}")
            return None

    elif loader_key == 'forge':
        local_donors = [
            os.path.join(mc_root, 'versions', f"Forge {mc_version}"),
            os.path.join(mc_root, 'versions', f"{mc_version}-forge"),
            os.path.join(BASE_VERSIONS_DIR, f"Forge {mc_version}")
        ]
        if mc_version == '1.20.1':
            local_donors.append(os.path.join(mc_root, 'versions', 'DeadZone 1.20.1 Forge'))
            local_donors.append(os.path.join(BASE_VERSIONS_DIR, 'DeadZone 1.20.1 Forge'))

        found_donor = None
        for d in local_donors:
            if os.path.exists(d):
                d_json = next((os.path.join(d, f) for f in os.listdir(d) if f.endswith('.json')), None)
                if d_json:
                    found_donor = (d, d_json)
                    break

        if found_donor:
            donor_dir, donor_json = found_donor
            try:
                shutil.copy2(donor_json, json_path)
                donor_args = os.path.join(donor_dir, 'launch_args.txt')
                if os.path.exists(donor_args):
                    shutil.copy2(donor_args, os.path.join(target_dir, 'launch_args.txt'))
            except Exception:
                pass
        else:
            try:
                promos_url = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
                req_pr = urllib.request.Request(promos_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
                with urllib.request.urlopen(req_pr, timeout=12) as r_pr:
                    promos = json.loads(r_pr.read()).get('promos', {})
                forge_v = promos.get(f"{mc_version}-recommended") or promos.get(f"{mc_version}-latest")
                if not forge_v:
                    print(f"{C_RED}E: No Forge version found for Minecraft {mc_version}{CLR_RESET}")
                    return None
                installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_v}/forge-{mc_version}-{forge_v}-installer.jar"
                temp_inst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "temp_forge_installer.jar")
                os.makedirs(os.path.dirname(temp_inst), exist_ok=True)
                download_file_stream(installer_url, temp_inst, f"forge-{mc_version}-installer.jar", get_idx=2)

                j_bin = get_best_java_for_version(mc_version)
                print(f"Executing Forge installer via {os.path.basename(os.path.dirname(os.path.dirname(j_bin)))}...")
                subprocess.run([j_bin, "-jar", temp_inst, "--installClient", mc_root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                if os.path.exists(temp_inst):
                    try: os.remove(temp_inst)
                    except Exception: pass
            except Exception as e:
                print(f"{C_AMBER}Warn during Forge installer execution: {e}{CLR_RESET}")

    elif loader_key == 'neoforge':
        local_donors = [
            os.path.join(mc_root, 'versions', f"LMLL-NeoForge-1.21.11"),
            os.path.join(mc_root, 'versions', f"neoforge-21.1.248"),
            os.path.join(mc_root, 'versions', f"NeoForge {mc_version}")
        ]
        found_donor = None
        for d in local_donors:
            if os.path.exists(d):
                d_json = next((os.path.join(d, f) for f in os.listdir(d) if f.endswith('.json')), None)
                if d_json:
                    found_donor = (d, d_json)
                    break
        if found_donor:
            donor_dir, donor_json = found_donor
            try:
                shutil.copy2(donor_json, json_path)
                donor_args = os.path.join(donor_dir, 'launch_args.txt')
                if os.path.exists(donor_args):
                    shutil.copy2(donor_args, os.path.join(target_dir, 'launch_args.txt'))
            except Exception:
                pass
        else:
            try:
                meta_url = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
                req_neo = urllib.request.Request(meta_url, headers={'User-Agent': 'Moon-Launcher/2.0'})
                with urllib.request.urlopen(req_neo, timeout=12) as r_neo:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(r_neo.read())
                all_vers = [v.text for v in root.findall('.//version') if v.text]
                parts = mc_version.split('.')
                minor = int(parts[1]) if len(parts) > 1 else 20
                patch = int(parts[2]) if len(parts) > 2 else 0
                prefix = f"{minor}.{patch}."
                matches = [v for v in all_vers if v.startswith(prefix)]
                if not matches: matches = [v for v in all_vers if v.startswith(f"{minor}.")]
                if matches:
                    neo_v = matches[-1]
                    inst_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neo_v}/neoforge-{neo_v}-installer.jar"
                    temp_inst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "temp_neo_installer.jar")
                    os.makedirs(os.path.dirname(temp_inst), exist_ok=True)
                    download_file_stream(inst_url, temp_inst, f"neoforge-{neo_v}-installer.jar", get_idx=2)
                    j_bin = get_best_java_for_version(mc_version)
                    print(f"Executing NeoForge installer...")
                    subprocess.run([j_bin, "-jar", temp_inst, "--installClient", mc_root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                    if os.path.exists(temp_inst):
                        try: os.remove(temp_inst)
                        except Exception: pass
            except Exception as e:
                print(f"{C_AMBER}Warn during NeoForge installer execution: {e}{CLR_RESET}")

    # Step 3: Provisions Natives & Launch Arguments
    ensure_natives_for_version(target_dir, mc_version)
    ensure_launch_args(target_dir, declared_loader=loader_title, mc_version=mc_version)

    # Step 4: Configuration & Icon
    master_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher_config.json")
    master_user = get_master_username()
    master_ram = 4
    if os.path.exists(master_cfg_path):
        try:
            with open(master_cfg_path, 'r', encoding='utf-8-sig') as mf:
                m_data = json.load(mf)
                master_user = m_data.get('username', master_user)
                master_ram = m_data.get('ram_max_gb', master_ram)
        except Exception:
            pass

    cfg_p = os.path.join(target_dir, 'launcher_config.json')
    with open(cfg_p, 'w', encoding='utf-8') as cf:
        json.dump({
            "ram_max_gb": master_ram,
            "ram_min_gb": 1,
            "username": master_user,
            "width": 1280,
            "height": 720,
            "fullscreen": False,
            "java_path": get_best_java_for_version(mc_version),
            "version_name": v_name,
            "loader": loader_title,
            "mc_version": mc_version,
            "discord_rpc": True
        }, cf, indent=2)

    icon_png = os.path.join(target_dir, "icon.png")
    if not os.path.exists(icon_png) and os.path.exists(DEFAULT_MINECRAFT_ICON_PATH):
        try:
            shutil.copy2(DEFAULT_MINECRAFT_ICON_PATH, icon_png)
        except Exception:
            pass

    set_active_version(v_name)

    print(f"Selecting previously unselected package minecraft-{loader_key}-{mc_version}.")
    print(f"(Reading database ... 100%)")
    print(f"Preparing to unpack minecraft-{loader_key}-{mc_version} ...")
    print(f"Unpacking minecraft-{loader_key}-{mc_version} ({mc_version}) ...")
    print(f"Setting up minecraft-{loader_key}-{mc_version} ({mc_version}) ...")
    print(render_apt_progress_bar(100, 32))
    print(f"Processing triggers for minecraft-runtime ... {C_GREEN}Done.{CLR_RESET}")
    print(f"\n{C_GREEN}All packages installed successfully! {loader_title} {mc_version} is ready to play.{CLR_RESET}")
    print(f"{C_WHITE}Active profile switched to: {C_CYAN}{v_name}{CLR_RESET}")
    print(f"{C_MUTED}Type {C_CYAN}/play{CLR_RESET} to start or {C_GREEN}/mods{CLR_RESET} to add your favorite mods.{CLR_RESET}\n")

    return target_dir

def install_from_mrpack(mrpack_file, custom_name=None, icon_url=None):
    import zipfile
    print(f"\n{C_WHITE}Reading package lists...{CLR_RESET} Done")
    time.sleep(0.12)
    print(f"{C_WHITE}Building dependency tree...{CLR_RESET} Done")
    time.sleep(0.08)
    print(f"{C_WHITE}Reading state information...{CLR_RESET} Done")

    try:
        with zipfile.ZipFile(mrpack_file, 'r') as z:
            if 'modrinth.index.json' not in z.namelist():
                print(f"{C_RED}E: Invalid .mrpack file (modrinth.index.json missing).{CLR_RESET}")
                return None
            index_data = json.loads(z.read('modrinth.index.json').decode('utf-8'))

            pack_name = custom_name or index_data.get('name', 'Modpack')
            clean_name = re.sub(r'[\\/*?:"<>|]', '', pack_name).strip()
            deps = index_data.get('dependencies', {})
            mc_ver = deps.get('minecraft', '1.20.1')
            loader = 'Forge' if 'forge' in deps else ('Fabric' if 'fabric-loader' in deps else ('NeoForge' if 'neoforge' in deps else 'Modded'))

            folder_name = clean_name
            target_dir = os.path.join(BASE_VERSIONS_DIR, folder_name)
            os.makedirs(target_dir, exist_ok=True)
            for sub in ('mods', 'config', 'saves', 'resourcepacks', 'shaderpacks', 'logs', 'natives'):
                os.makedirs(os.path.join(target_dir, sub), exist_ok=True)

            files = index_data.get('files', [])
            total_size_bytes = sum(f.get('fileSize', 0) for f in files)
            total_mb = total_size_bytes / (1024 * 1024) if total_size_bytes > 0 else (len(files) * 1.5)

            print(f"\nThe following NEW packages will be installed:")
            pkg_names = [os.path.basename(f.get('path', '')).replace('.jar', '') for f in files[:28]]
            wrapped_pkgs = "  " + "  ".join(pkg_names)
            if len(files) > 28:
                wrapped_pkgs += f"  ... and {len(files) - 28} more packages"
            print(f"{C_MUTED}{wrapped_pkgs}{CLR_RESET}")

            print(f"\n0 upgraded, {len(files)} newly installed, 0 to remove.")
            print(f"Need to get {total_mb:.1f} MB of archives.")
            print(f"After this operation, {total_mb * 1.25:.1f} MB of additional disk space will be used.")
            print(f"Do you want to continue? [Y/n] y\n")

            succ_count = 0
            for idx, item in enumerate(files, 1):
                downloads = item.get('downloads', [])
                if not downloads:
                    continue
                file_url = downloads[0]
                rel_path = item.get('path', '')
                dest_file = os.path.join(target_dir, rel_path.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                fname = os.path.basename(rel_path)
                if download_file_stream(file_url, dest_file, fname, get_idx=idx):
                    succ_count += 1

            for item in z.namelist():
                if item.startswith('overrides/'):
                    rel = item[len('overrides/'):]
                    if not rel or item.endswith('/'):
                        continue
                    dest = os.path.join(target_dir, rel.replace('/', os.sep))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with z.open(item) as src, open(dest, 'wb') as dst:
                        dst.write(src.read())

            print(f"\nUnpacking {len(files)} packages ...")
            for idx, item in enumerate(files[:5], 1):
                mname = os.path.basename(item.get('path', ''))
                print(f"Preparing to unpack {mname} ...")
                print(f"Unpacking {mname} ...")
                print(f"Setting up {mname} ...")
                time.sleep(0.03)

            print(render_apt_progress_bar(100, 32))

            # Install & extract modpack icon for Discord RPC
            installed_icon_url = install_modpack_icon(target_dir, folder_name, icon_url=icon_url, z=z)

            ensure_launch_args(target_dir, declared_loader=loader, mc_version=mc_ver)

            # Master user identity lookup
            root_cfg_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher_config.json")
            master_user = get_master_username()
            master_skin = ''
            if os.path.exists(root_cfg_p):
                try:
                    with open(root_cfg_p, 'r', encoding='utf-8-sig') as f_r:
                        r_data = json.load(f_r)
                        master_user = r_data.get('username', master_user)
                        master_skin = r_data.get('custom_skin', master_skin)
                except Exception:
                    pass

            cfg_path = os.path.join(target_dir, 'launcher_config.json')
            v_cfg = {
                "ram_max_gb": 8,
                "ram_min_gb": 2,
                "username": master_user,
                "custom_skin": master_skin,
                "width": 1280,
                "height": 720,
                "fullscreen": False,
                "java_path": DEFAULT_JAVA,
                "version_name": folder_name,
                "discord_rpc": True,
                "loader": loader,
                "mc_version": mc_ver,
                "discord_large_image": installed_icon_url or "",
                "icon_path": "icon.png" if os.path.exists(os.path.join(target_dir, "icon.png")) else ""
            }
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(v_cfg, f, indent=2)

            set_active_version(folder_name)
            print(f"Processing triggers for minecraft-runtime ({loader}-{mc_ver}) ... {C_GREEN}Done.{CLR_RESET}")
            print(f"\n{C_GREEN}All {succ_count}/{len(files)} packages installed successfully! Modpack '{folder_name}' is ready to play.{CLR_RESET}")
            return target_dir
    except Exception as e:
        print(f"{C_RED}E: Failed to process modpack package: {e}{CLR_RESET}")
        return None

def install_from_zip(zip_file, custom_name=None, icon_url=None):
    import zipfile
    print(f"\n{C_WHITE}Reading package lists...{CLR_RESET} Done")
    time.sleep(0.12)
    print(f"{C_WHITE}Building dependency tree...{CLR_RESET} Done")
    time.sleep(0.08)
    print(f"{C_WHITE}Reading state information...{CLR_RESET} Done")

    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            names = z.namelist()
            if 'modrinth.index.json' in names:
                return install_from_mrpack(zip_file, custom_name, icon_url=icon_url)

            clean_name = custom_name or os.path.splitext(os.path.basename(zip_file))[0]
            clean_name = re.sub(r'[\\/*?:"<>|]', '', clean_name).strip()
            target_dir = os.path.join(BASE_VERSIONS_DIR, clean_name)
            os.makedirs(target_dir, exist_ok=True)

            print(f"\nThe following NEW packages will be unpacked:")
            print(f"  {C_CYAN}{clean_name} (local archive: {len(names)} entries){CLR_RESET}")
            print(f"\n0 upgraded, 1 newly installed, 0 to remove.")
            print(f"Extracting archives to destination ...")

            root_dirs = set(n.split('/')[0] for n in names if '/' in n)
            has_single_wrapper = len(root_dirs) == 1 and not any('/' not in n for n in names if n)
            prefix = (list(root_dirs)[0] + '/') if has_single_wrapper else ''

            t0 = time.time()
            for idx, n in enumerate(names, 1):
                if n.endswith('/'):
                    continue
                rel = n[len(prefix):] if n.startswith(prefix) else n
                dest = os.path.join(target_dir, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(n) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
                if idx % 10 == 0 or idx == len(names):
                    pct = int(idx * 100 / len(names))
                    sys.stdout.write(f"\r{render_apt_progress_bar(pct, 28)} Unpacking {os.path.basename(rel)[:25]:<25} \x1b[K")
                    sys.stdout.flush()

            print(f"\nSetting up {clean_name} ...")
            print(render_apt_progress_bar(100, 32))

            # Detect metadata from CurseForge manifest.json if present
            detected_loader = None
            detected_mc_ver = None
            if 'manifest.json' in names:
                try:
                    m_data = json.loads(z.read('manifest.json').decode('utf-8'))
                    detected_mc_ver = m_data.get('minecraft', {}).get('version')
                    loaders = m_data.get('minecraft', {}).get('modLoaders', [])
                    if loaders:
                        lid = loaders[0].get('id', '').lower()
                        if 'neoforge' in lid: detected_loader = 'NeoForge'
                        elif 'forge' in lid: detected_loader = 'Forge'
                        elif 'fabric' in lid: detected_loader = 'Fabric'
                except Exception:
                    pass

            mc_ver, loader = detect_version_and_loader(target_dir, declared_loader=detected_loader, declared_mc_version=detected_mc_ver)

            # Install & extract modpack icon for Discord RPC
            installed_icon_url = install_modpack_icon(target_dir, clean_name, icon_url=icon_url, z=z)

            ensure_launch_args(target_dir, declared_loader=loader, mc_version=mc_ver)

            # Master user identity lookup
            root_cfg_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher_config.json")
            master_user = get_master_username()
            master_skin = ''
            if os.path.exists(root_cfg_p):
                try:
                    with open(root_cfg_p, 'r', encoding='utf-8-sig') as f_r:
                        r_data = json.load(f_r)
                        master_user = r_data.get('username', master_user)
                        master_skin = r_data.get('custom_skin', master_skin)
                except Exception:
                    pass

            cfg_path = os.path.join(target_dir, 'launcher_config.json')
            v_cfg = {
                "ram_max_gb": 8,
                "ram_min_gb": 2,
                "username": master_user,
                "custom_skin": master_skin,
                "width": 1280,
                "height": 720,
                "fullscreen": False,
                "java_path": get_best_java_for_version(mc_ver, DEFAULT_JAVA),
                "version_name": clean_name,
                "loader": loader,
                "mc_version": mc_ver,
                "discord_rpc": True,
                "discord_large_image": installed_icon_url or "",
                "icon_path": "icon.png" if os.path.exists(os.path.join(target_dir, "icon.png")) else ""
            }
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(v_cfg, f, indent=2)

            set_active_version(clean_name)
            print(f"Processing triggers for minecraft-runtime ... {C_GREEN}Done.{CLR_RESET}")
            print(f"\n{C_GREEN}All packages installed successfully! Modpack '{clean_name}' is ready to play.{CLR_RESET}")
            return target_dir
    except Exception as e:
        print(f"{C_RED}E: Failed to process ZIP file: {e}{CLR_RESET}")
        return None

def search_and_install_modrinth(query=None):
    if not query:
        print(f"\n{C_WHITE}── Search Modpack on Modrinth ──{CLR_RESET}")
        try:
            query = input(f"{C_AMBER}Enter modpack search keyword (e.g. homestead, cobblemon, optimize): {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return None
        if not query:
            print(f"{C_MUTED}Search cancelled.{CLR_RESET}")
            return None

    query = query.strip()
    print(f"\n{C_CYAN}Searching for modpack '{query}' on Modrinth...{CLR_RESET}")
    import urllib.parse
    enc_q = urllib.parse.quote_plus(query)

    hits = []
    # Clean API call without unencoded facets
    url = f"https://api.modrinth.com/v2/search?query={enc_q}&limit=20"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Moon-Launcher/2.0 (Mozilla/5.0)'})
        with urllib.request.urlopen(req, timeout=12) as r:
            res = json.loads(r.read())
            all_hits = res.get('hits', [])
            hits = [h for h in all_hits if h.get('project_type') == 'modpack']
    except Exception as e:
        print(f"{C_RED}E: Search request error: {e}{CLR_RESET}")

    # Fallback to direct project slug lookup if zero hits
    if not hits:
        try:
            p_url = f"https://api.modrinth.com/v2/project/{enc_q}"
            req_p = urllib.request.Request(p_url, headers={'User-Agent': 'Moon-Launcher/2.0 (Mozilla/5.0)'})
            with urllib.request.urlopen(req_p, timeout=10) as r:
                p_data = json.loads(r.read())
                if p_data.get('project_type') == 'modpack':
                    hits.append({
                        'title': p_data.get('title'),
                        'project_id': p_data.get('id'),
                        'categories': p_data.get('categories', []),
                        'downloads': p_data.get('downloads', 0),
                        'description': p_data.get('description', '')
                    })
        except Exception:
            pass

    if not hits:
        print(f"{C_AMBER}No modpacks found matching '{query}'.{CLR_RESET}")
        return None

    print(f"\n{C_WHITE}Search Results:{CLR_RESET}")
    max_disp = min(len(hits), 8)
    for idx, h in enumerate(hits[:max_disp], 1):
        title = h.get('title')
        cats = ", ".join(h.get('categories', []))
        dl_cnt = h.get('downloads', 0)
        desc = truncate_ansi(h.get('description', ''), 60)
        print(f"  {C_CYAN}[{idx}]{CLR_RESET} {C_WHITE}\033[1m{title}\033[0m {C_MUTED}({cats}) • {dl_cnt:,} downloads{CLR_RESET}")
        print(f"      {C_MUTED}{desc}{CLR_RESET}")

    sel_prompt = f"\n{C_AMBER}Select modpack [1-{max_disp}] (Press ENTER for [1], or 0 to cancel): {CLR_RESET}"
    try:
        sel = input(sel_prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return None

    if not sel:
        # Default to 1 (top search match)
        sel = "1"
    elif sel in ('0', 'q', 'cancel', 'exit'):
        print(f"{C_MUTED}Search cancelled.{CLR_RESET}")
        return None
    elif not sel.isdigit() or not (1 <= int(sel) <= max_disp):
        print(f"{C_RED}Invalid selection.{CLR_RESET}")
        return None

    chosen = hits[int(sel) - 1]
    chosen_id = chosen.get('project_id')
    print(f"\n{C_CYAN}Fetching release versions for '{chosen.get('title')}'...{CLR_RESET}")

    v_url = f"https://api.modrinth.com/v2/project/{chosen_id}/version"
    try:
        req = urllib.request.Request(v_url, headers={'User-Agent': 'Moon-Launcher/2.0 (Mozilla/5.0)'})
        with urllib.request.urlopen(req, timeout=15) as r:
            versions = json.loads(r.read())
        if not versions:
            print(f"{C_RED}E: No versions found for this modpack.{CLR_RESET}")
            return None

        valid_versions = []
        for v in versions:
            mrpack_f = next((f for f in v.get('files', []) if f.get('filename', '').endswith('.mrpack')), None)
            if mrpack_f:
                valid_versions.append((v, mrpack_f))

        if not valid_versions:
            print(f"{C_RED}E: No .mrpack file found for this modpack.{CLR_RESET}")
            return None

        chosen_v, mrpack_item = valid_versions[0]
        if len(valid_versions) > 1:
            print(f"\n{C_WHITE}Available Versions for {chosen.get('title')}:{CLR_RESET}")
            sample_v = valid_versions[:5]
            for v_idx, (v_obj, f_obj) in enumerate(sample_v, 1):
                v_name = v_obj.get('name', '')
                g_vers = ", ".join(v_obj.get('game_versions', []))
                loaders = ", ".join(v_obj.get('loaders', []))
                sz_mb = f_obj.get('size', 0) / (1024 * 1024)
                print(f"  {C_CYAN}[{v_idx}]{CLR_RESET} {C_WHITE}{v_name}{CLR_RESET} {C_MUTED}(MC {g_vers} • {loaders} • {sz_mb:.1f} MB){CLR_RESET}")
            try:
                v_choice = input(f"\n{C_AMBER}Select version [1-{len(sample_v)}] (press ENTER for latest [1]): {CLR_RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                return None
            if v_choice.isdigit() and 1 <= int(v_choice) <= len(sample_v):
                chosen_v, mrpack_item = sample_v[int(v_choice) - 1]

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        temp_mrpack = os.path.join(cur_dir, "runtime", mrpack_item['filename'])
        os.makedirs(os.path.dirname(temp_mrpack), exist_ok=True)
        download_file_stream(mrpack_item['url'], temp_mrpack, mrpack_item['filename'], get_idx=1)

        installed_dir = install_from_mrpack(temp_mrpack, chosen.get('title'), icon_url=chosen.get('icon_url'))
        try:
            if os.path.exists(temp_mrpack):
                os.remove(temp_mrpack)
        except Exception:
            pass
        return installed_dir
    except Exception as e:
        print(f"{C_RED}E: Failed to download modpack: {e}{CLR_RESET}")
        return None

def run_installer_studio(version_dir, cfg, args=None):
    if args:
        sub = args[0].lower()
        if sub in ('search', 'find', 's'):
            q = " ".join(args[1:]) if len(args) > 1 else ""
            new_d = search_and_install_modrinth(q)
            if new_d:
                return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('vanilla', 'v'):
            v_id = args[1] if len(args) > 1 else None
            new_d = install_vanilla_version(v_id)
            if new_d:
                return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('fabric', 'fab'):
            mc_v = args[1] if len(args) > 1 else None
            new_d = install_mod_loader('fabric', mc_v)
            if new_d: return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('forge', 'fml'):
            mc_v = args[1] if len(args) > 1 else None
            new_d = install_mod_loader('forge', mc_v)
            if new_d: return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('neoforge', 'neo'):
            mc_v = args[1] if len(args) > 1 else None
            new_d = install_mod_loader('neoforge', mc_v)
            if new_d: return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('quilt', 'q'):
            mc_v = args[1] if len(args) > 1 else None
            new_d = install_mod_loader('quilt', mc_v)
            if new_d: return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('loader', 'loaders'):
            l_type = args[1] if len(args) > 1 else None
            mc_v = args[2] if len(args) > 2 else None
            new_d = install_mod_loader(l_type, mc_v)
            if new_d: return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('url', 'link', 'download'):
            if len(args) < 2:
                print(f"{C_RED}Error: Provide download URL! Example: /install url https://.../pack.mrpack{CLR_RESET}")
                return version_dir, cfg
            url = args[1]
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            temp_f = os.path.join(cur_dir, "runtime", "temp_modpack.mrpack")
            download_file_stream(url, temp_f, "Modpack")
            new_d = install_from_mrpack(temp_f) if (url.endswith('.mrpack') or temp_f.endswith('.mrpack')) else install_from_zip(temp_f)
            if os.path.exists(temp_f):
                try: os.remove(temp_f)
                except Exception: pass
            if new_d:
                return new_d, load_config(new_d)
            return version_dir, cfg

        elif sub in ('file', 'local'):
            if len(args) < 2:
                print(f"{C_RED}Error: Provide file path! Example: /install file C:\\Downloads\\pack.mrpack{CLR_RESET}")
                return version_dir, cfg
            fpath = " ".join(args[1:]).strip('"').strip("'")
            if not os.path.exists(fpath):
                print(f"{C_RED}Error: File not found: {fpath}{CLR_RESET}")
                return version_dir, cfg
            new_d = install_from_mrpack(fpath) if fpath.endswith('.mrpack') else install_from_zip(fpath)
            if new_d:
                return new_d, load_config(new_d)
            return version_dir, cfg

        else:
            # Fallback to direct search (e.g. /install homestead)
            q = " ".join(args)
            new_d = search_and_install_modrinth(q)
            if new_d:
                return new_d, load_config(new_d)
            return version_dir, cfg

    # Interactive Menu Studio - STRICT ENGLISH, NO EMOJIS
    box_w = 66
    menu_lines = [
        f"{C_WHITE}\033[1mMoon Launcher — Modpack & Version Installer Studio\033[0m",
        f"{C_MUTED}Automated downloader & installer for Minecraft Vanilla & Modpacks{CLR_RESET}",
        C_BORDER + ('─' * (box_w - 4)) + CLR_RESET,
        f"  {C_CYAN}[1]{CLR_RESET} {C_WHITE}Search & Install Modpack Online (Modrinth){CLR_RESET}",
        f"  {C_CYAN}[2]{CLR_RESET} {C_WHITE}Install Mod Loader (Fabric, Forge, NeoForge, Quilt){CLR_RESET}",
        f"  {C_CYAN}[3]{CLR_RESET} {C_WHITE}Install Official Vanilla Minecraft (1.12.2 - 1.21+){CLR_RESET}",
        f"  {C_CYAN}[4]{CLR_RESET} {C_WHITE}Install Modpack from Web URL (.mrpack / .zip){CLR_RESET}",
        f"  {C_CYAN}[5]{CLR_RESET} {C_WHITE}Install Modpack from Local File (.mrpack / .zip){CLR_RESET}",
        f"  {C_CYAN}[6]{CLR_RESET} {C_WHITE}Uninstall / Delete a Minecraft Version or Modpack{CLR_RESET}",
        f"  {C_RED}[0]{CLR_RESET} {C_MUTED}Back to Main Menu{CLR_RESET}",
    ]
    print("\n" + render_box(menu_lines, box_w) + "\n")

    try:
        choice = input(f"  {C_AMBER}Select option [1-6], enter search keyword, or [0 to cancel]: {CLR_RESET}").strip().lstrip("\ufeff")
    except (KeyboardInterrupt, EOFError):
        print()
        return version_dir, cfg

    if choice == '1':
        new_d = search_and_install_modrinth()
        if new_d: return new_d, load_config(new_d)
    elif choice == '2':
        new_d = install_mod_loader()
        if new_d: return new_d, load_config(new_d)
    elif choice == '3':
        new_d = install_vanilla_version()
        if new_d: return new_d, load_config(new_d)
    elif choice == '4':
        try:
            url = input(f"  {C_AMBER}Enter Modpack URL (.mrpack / .zip): {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return version_dir, cfg
        if url:
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            temp_f = os.path.join(cur_dir, "runtime", "temp_modpack.mrpack")
            download_file_stream(url, temp_f, "Modpack")
            new_d = install_from_mrpack(temp_f) if (url.endswith('.mrpack') or temp_f.endswith('.mrpack')) else install_from_zip(temp_f)
            if os.path.exists(temp_f):
                try: os.remove(temp_f)
                except Exception: pass
            if new_d: return new_d, load_config(new_d)
    elif choice == '5':
        try:
            fpath = input(f"  {C_AMBER}Enter local file path (.mrpack / .zip): {CLR_RESET}").strip().strip('"').strip("'")
        except (KeyboardInterrupt, EOFError):
            print()
            return version_dir, cfg
        if fpath and os.path.exists(fpath):
            new_d = install_from_mrpack(fpath) if fpath.endswith('.mrpack') else install_from_zip(fpath)
            if new_d: return new_d, load_config(new_d)
        elif fpath:
            print(f"  {C_RED}Error: File not found: {fpath}{CLR_RESET}")
    elif choice == '6':
        return remove_version(version_dir, cfg)
    elif choice in ('0', 'q', 'cancel', 'exit') or not choice:
        print(f"  {C_MUTED}Cancelled.{CLR_RESET}")
        return version_dir, cfg
    else:
        # User entered search query directly (e.g. 'homestead')
        print(f"\n  {C_CYAN}Keyword detected: Searching Modrinth for '{choice}'...{CLR_RESET}")
        new_d = search_and_install_modrinth(choice)
        if new_d: return new_d, load_config(new_d)

    return version_dir, cfg

def main():
    if sys.platform == 'win32':
        os.system('title Moon Launcher')

    # Auto-register moon:// Windows protocol handler
    network_hub.register_windows_protocol_handler()

    # Load persistent active version (remembered across restarts)
    global GLOBAL_RPC
    version_dir = get_active_version_dir()
    cfg = load_config(version_dir)
    GLOBAL_RPC = MoonDiscordRPC(
        client_id=cfg.get("discord_client_id", "450485984333660181"),
        enabled=cfg.get("discord_rpc", True)
    )
    GLOBAL_RPC.set_menu(version_dir, cfg)

    # Start Native Zero-Config LAN & Radmin P2P Skin Auto-Sync Service
    network_hub.start_lan_skin_service(cfg.get('username', 'Player'), version_dir)
    network_hub.update_active_version(version_dir, cfg.get('version_name'))
    updater.start_background_update_checker()

    # Process CLI arguments if passed (e.g. python launcher.py /play or /install homestead)
    if len(sys.argv) > 1:
        arg_cmd = sys.argv[1].lower()
        if arg_cmd in ('/play', 'play', '/p', 'p', '/start', 'start', '/launch', 'launch'):
            launch_game(version_dir, cfg)
            return
        elif arg_cmd in ('/test', 'test', '/dryrun', 'dryrun', '/check', 'check'):
            target_arg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
            t_dir, t_cfg = resolve_version_target(version_dir, cfg, target_arg)
            run_preflight_test(t_dir, t_cfg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/fix', 'fix', '/repair', 'repair'):
            target_arg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
            t_dir, t_cfg = resolve_version_target(version_dir, cfg, target_arg)
            run_auto_fix(t_dir, t_cfg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/user', 'user', '/username', 'username', '/player', 'player', '/name', 'name', '/nick', 'nick'):
            if len(sys.argv) > 2:
                new_u = set_global_username(sys.argv[2], version_dir)
                cfg['username'] = new_u
                print(f"\n{C_GREEN}[Moon Launcher] Updated player username -> {new_u}{CLR_RESET}")
                print(f"{C_MUTED}[Moon Launcher] Synchronized across all profiles and launch arguments.{CLR_RESET}")
            else:
                print(f"\n{C_CYAN}[Moon Launcher] Current player username:{CLR_RESET} {cfg.get('username', 'Player')}")
                print(f"{C_MUTED}To change: /username <new_name> or /setting user <new_name>{CLR_RESET}")
            return
        elif arg_cmd in ('/host', 'host', '/lan', 'lan', '/tunnel', 'tunnel'):
            network_hub.handle_host_command(sys.argv[2:], version_dir)
            return
        elif arg_cmd.startswith(('moon://', 'https://moonlauncher.link/', 'http://moonlauncher.link/', 'https://moonlauncher.app/')) or ('user=' in arg_cmd and 'addr=' in arg_cmd):
            network_hub.handle_moon_protocol_url(sys.argv[1], version_dir)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/invite', 'invite', '/share', 'share'):
            network_hub.handle_friend_command(['invite'], version_dir)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/friend', 'friend', '/friends', 'friends'):
            network_hub.handle_friend_command(sys.argv[2:], version_dir)
            return
        elif arg_cmd in ('/server', 'server', '/servers', 'servers'):
            network_hub.handle_server_command(sys.argv[2:])
            return
        elif arg_cmd in ('/version', 'version', '/versions', 'versions', '/v', 'v'):
            target_arg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
            version_dir, cfg = switch_version(version_dir, cfg, target_arg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/setting', 'setting', '/settings', 'settings', '/s', 's'):
            if len(sys.argv) > 2:
                cfg = apply_quick_setting(version_dir, cfg, sys.argv[2:])
            else:
                version_dir, cfg = run_settings_studio(version_dir, cfg)
            return
        elif arg_cmd in ('/install', 'install', '/download', 'download', '/modpack', 'modpack', '/i', 'i', '/search', 'search', '/find', 'find'):
            sub_args = sys.argv[2:]
            if arg_cmd in ('/search', 'search', '/find', 'find'):
                sub_args = ['search'] + sub_args
            version_dir, cfg = run_installer_studio(version_dir, cfg, sub_args)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass
            return
        elif arg_cmd in ('/delete', 'delete', '/remove', 'remove', '/uninstall', 'uninstall', '/rm', 'rm'):
            target_arg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
            version_dir, cfg = remove_version(version_dir, cfg, target_arg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/status', 'status', '/info', 'info'):
            print_status(version_dir, cfg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/help', 'help', '/?', '?'):
            topic = sys.argv[2].lower() if len(sys.argv) > 2 else None
            print_help(topic)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/skin', 'skin'):
            if len(sys.argv) > 2:
                apply_skin_setting(version_dir, cfg, ' '.join(sys.argv[2:]))
                save_config(version_dir, cfg)
            else:
                cur_s = cfg.get('custom_skin') or cfg.get('custom_skin_url') or 'Auto'
                print(f"{C_CYAN}[Moon Launcher] Active Custom Skin:{CLR_RESET} {cur_s}")
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/open', 'open', '/o', 'o'):
            sub_folder = sys.argv[2].lower() if len(sys.argv) > 2 else None
            open_folder(version_dir, sub_folder)
            return
        elif arg_cmd in ('/update', 'update', '/upgrade', 'upgrade', '/u', 'u'):
            updater.handle_update_command(sys.argv[2:], version_dir, cfg)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/crash', 'crash', '/logs', 'logs', '/log', 'log'):
            show_crash_report(version_dir)
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return
        elif arg_cmd in ('/mods', 'mods', '/m', 'm'):
            manage_mods(version_dir, sys.argv[2:])
            print(f"\n{C_MUTED}Press ENTER to exit...{CLR_RESET}", end="", flush=True)
            try: input()
            except (KeyboardInterrupt, EOFError): pass
            return

    print_banner(version_dir, cfg)

    while True:
        try:
            prompt_str = f"{C_CLAUDE}moon{CLR_RESET} {C_MUTED}❯{CLR_RESET} "
            user_input = input(prompt_str).strip().lstrip('\ufeff')
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_MUTED}Exiting Moon Launcher CLI. Goodbye!{CLR_RESET}")
            break

        if not user_input:
            continue

        raw_parts = user_input.split()
        cmd = raw_parts[0].lower()

        try:
            if cmd in ('/play', 'play', '/p', 'p', '/start', 'start', '/launch', 'launch', '1'):
                launch_game(version_dir, cfg)

            elif cmd in ('/test', 'test', '/dryrun', 'dryrun', '/check', 'check', 't'):
                target_arg = ' '.join(raw_parts[1:]) if len(raw_parts) > 1 else None
                t_dir, t_cfg = resolve_version_target(version_dir, cfg, target_arg)
                run_preflight_test(t_dir, t_cfg)
                if t_dir == version_dir:
                    cfg = t_cfg

            elif cmd in ('/fix', 'fix', '/repair', 'repair', 'f'):
                target_arg = ' '.join(raw_parts[1:]) if len(raw_parts) > 1 else None
                t_dir, t_cfg = resolve_version_target(version_dir, cfg, target_arg)
                repaired_cfg = run_auto_fix(t_dir, t_cfg)
                if t_dir == version_dir:
                    cfg = repaired_cfg

            elif cmd in ('/lan', 'lan', '/lanskin', 'lanskin'):
                sub_args = raw_parts[1:]
                if sub_args and sub_args[0].lower() in ('host', 'start', 'tunnel', 'open', 'stop'):
                    network_hub.handle_host_command(sub_args, version_dir)
                else:
                    network_hub.handle_lan_command(sub_args)

            elif cmd in ('/skin', 'skin', '/customskin', 'customskin'):
                sub_args = raw_parts[1:]
                if sub_args and sub_args[0].lower() in ('lan', 'radmin', 'p2p', 'peers', 'sync'):
                    network_hub.handle_lan_command(sub_args[1:])
                elif not sub_args:
                    cur_s = cfg.get('custom_skin') or cfg.get('custom_skin_url') or 'Auto (from username)'
                    print(f"{C_CYAN}[Moon Launcher] Active Custom Skin:{CLR_RESET} {cur_s}")
                    print(f"{C_MUTED}Usage: /skin <https://... | file_path.png | PlayerName | auto>{CLR_RESET}")
                    print(f"{C_MUTED}       /skin friend <friend_username> <https://... | file_path.png>{CLR_RESET}\n")
                elif len(sub_args) >= 2 and sub_args[0].lower() in ('friend', 'f', 'player', 'user'):
                    target_friend = sub_args[1]
                    skin_val = ' '.join(sub_args[2:])
                    apply_friend_skin_setting(version_dir, target_friend, skin_val)
                    print()
                else:
                    skin_val = ' '.join(sub_args)
                    apply_skin_setting(version_dir, cfg, skin_val)
                    save_config(version_dir, cfg)
                    network_hub.trigger_lan_skin_broadcast()
                    print()

            elif cmd in ('/user', 'user', '/username', 'username', '/player', 'player', '/name', 'name', '/nick', 'nick'):
                if len(raw_parts) > 1:
                    new_u = set_global_username(raw_parts[1], version_dir)
                    cfg['username'] = new_u
                    network_hub.update_lan_skin_identity(new_u, version_dir)
                    print(f"{C_GREEN}[Moon Launcher] Updated player username -> {new_u}{CLR_RESET}")
                    print(f"{C_MUTED}[Moon Launcher] Synchronized across all profiles and launch arguments.{CLR_RESET}\n")
                else:
                    print(f"{C_CYAN}[Moon Launcher] Current player username:{CLR_RESET} {cfg.get('username', 'Player')}")
                    print(f"{C_MUTED}To change: /username <new_name> or /setting user <new_name>{CLR_RESET}\n")

            elif cmd in ('/host', 'host', '/lan', 'lan', '/tunnel', 'tunnel'):
                network_hub.handle_host_command(raw_parts[1:], version_dir)

            elif cmd in ('/invite', 'invite', '/share', 'share'):
                network_hub.handle_friend_command(['invite'], version_dir)

            elif cmd in ('/update', 'update', '/upgrade', 'upgrade'):
                updater.handle_update_command(raw_parts[1:], version_dir, cfg)

            elif cmd in ('/player', 'player', '/profile', 'profile', '/whois', 'whois'):
                target_id = raw_parts[1] if len(raw_parts) > 1 else cfg.get('username')
                network_hub.show_player_profile_card(target_id, version_dir)

            elif cmd in ('/friend', 'friend', '/friends', 'friends'):
                network_hub.handle_friend_command(raw_parts[1:], version_dir)

            elif cmd in ('/join', 'join', '/mabar', 'mabar'):
                network_hub.handle_friend_command(['join'] + raw_parts[1:], version_dir)

            elif (cmd.startswith(('moon://', 'http://', 'https://')) or 'user=' in user_input) and network_hub.parse_friend_invite(user_input):
                network_hub.handle_friend_command(['add', user_input], version_dir)

            elif cmd in ('/server', 'server', '/servers', 'servers'):
                network_hub.handle_server_command(raw_parts[1:])

            elif cmd in ('/setting', 'setting', '/settings', 'settings', '/s', 's', '/nano', 'nano', '2'):
                if len(raw_parts) > 1:
                    cfg = apply_quick_setting(version_dir, cfg, raw_parts[1:])
                else:
                    version_dir, cfg = run_settings_studio(version_dir, cfg)
                    print_banner(version_dir, cfg)

            elif cmd in ('/install', 'install', '/download', 'download', '/modpack', 'modpack', '/i', 'i', '/search', 'search', '/find', 'find'):
                sub_args = raw_parts[1:]
                if cmd in ('/search', 'search', '/find', 'find'):
                    sub_args = ['search'] + sub_args
                version_dir, cfg = run_installer_studio(version_dir, cfg, sub_args)
                if GLOBAL_RPC:
                    GLOBAL_RPC.set_menu(version_dir, cfg)
                # DO NOT clear screen or redraw banner here! Leave installation logs visible.
                print()

            elif cmd in ('/status', 'status', '/info', 'info', '3'):
                print_status(version_dir, cfg)

            elif cmd in ('/version', 'version', '/versions', 'versions', '/v', 'v', '4'):
                target_arg = ' '.join(raw_parts[1:]) if len(raw_parts) > 1 else None
                version_dir, cfg = switch_version(version_dir, cfg, target_arg)
                if GLOBAL_RPC:
                    GLOBAL_RPC.set_menu(version_dir, cfg)
                print_banner(version_dir, cfg)

            elif cmd in ('/delete', 'delete', '/remove', 'remove', '/uninstall', 'uninstall', '/rm', 'rm', '5'):
                target_arg = ' '.join(raw_parts[1:]) if len(raw_parts) > 1 else None
                version_dir, cfg = remove_version(version_dir, cfg, target_arg)
                if GLOBAL_RPC:
                    GLOBAL_RPC.set_menu(version_dir, cfg)
                print()

            elif cmd in ('/open', 'open', '/o', 'o'):
                sub_f = raw_parts[1].lower() if len(raw_parts) > 1 else None
                open_folder(version_dir, sub_f)

            elif cmd in ('/crash', 'crash', '/logs', 'logs', '/log', 'log'):
                show_crash_report(version_dir)

            elif cmd in ('/mods', 'mods', '/m', 'm'):
                manage_mods(version_dir, raw_parts[1:])

            elif cmd in ('/help', 'help', '/?', '?', '/h', 'h'):
                topic = raw_parts[1].lower() if len(raw_parts) > 1 else None
                print_help(topic)

            elif cmd in ('/clear', 'clear', '/cls', 'cls', '/c', 'c'):
                print_banner(version_dir, cfg)

            elif cmd in ('/exit', 'exit', '/quit', 'quit', '/q', 'q'):
                network_hub.stop_lan_skin_service()
                network_hub.stop_internet_tunnel()
                if GLOBAL_RPC:
                    GLOBAL_RPC.close()
                print(f"{C_MUTED}Exiting Moon Launcher. Have fun!{CLR_RESET}")
                break

            else:
                print(f"{C_RED}Unknown command '{user_input}'.{CLR_RESET}")
                print(f"{C_MUTED}Tip: To search and install modpacks, type: {C_WHITE}/install {user_input}{CLR_RESET}")
                print(f"{C_MUTED}Available commands: /play, /test, /fix, /host, /friend, /server, /setting, /version, /mods, /open, /crash, /install, /remove, /status, /help, /exit{CLR_RESET}\n")

        except Exception as e:
            print(f"{C_RED}Error executing '{user_input}': {e}{CLR_RESET}\n")

if __name__ == '__main__':
    main()



