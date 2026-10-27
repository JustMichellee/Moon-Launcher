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
    candidates = [
        r"E:\TLauncher\runtime\java-runtime-gamma\windows\java-runtime-gamma\bin\javaw.exe",
        os.path.expandvars(r"%APPDATA%\.tlauncher\starter\jre_default\jre-21.0.11-windows-x64\bin\javaw.exe"),
        os.path.expandvars(r"%APPDATA%\.minecraft\runtime\java-runtime-gamma\windows\java-runtime-gamma\bin\javaw.exe"),
        r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    import shutil
    w = shutil.which("javaw") or shutil.which("java")
    if w:
        return w
    return candidates[0]

DEFAULT_JAVA = detect_best_java()
BASE_VERSIONS_DIR = r"E:\TLauncher\versions" if os.path.exists(r"E:\TLauncher\versions") else os.path.expandvars(r"%APPDATA%\.minecraft\versions")
GLOBAL_STATE_FILE = os.path.expandvars(r"%APPDATA%\.minecraft\moon_launcher_state.json")

def get_possible_version_roots():
    roots = []
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(cur_dir)
    for d in (cur_dir, parent_dir):
        ml = os.path.join(d, "mod_list")
        if os.path.exists(ml) and ml not in roots:
            roots.append(ml)
    if os.path.exists(cur_dir) and cur_dir not in roots:
        roots.append(cur_dir)
    if os.path.exists(parent_dir) and parent_dir not in roots:
        roots.append(parent_dir)
    if os.path.exists(r"E:\TLauncher\versions"):
        roots.append(r"E:\TLauncher\versions")
    appdata_mc = os.path.expandvars(r"%APPDATA%\.minecraft\versions")
    if os.path.exists(appdata_mc):
        roots.append(appdata_mc)
    return roots

# ==============================================================================
# MODPACK / VERSION REGISTRY
# Daftar modpack yang tampil di menu /version.
# Tambahkan entri baru di sini kapan saja ingin memunculkan modpack lain.
# ==============================================================================
REGISTERED_VERSIONS = [
    {
        "name": "Cursed Walking",
        "aliases": ["CursedWalkingZS_Clean", "Cursed Walking", "Cursed Walking 1.20.1", "DeadZone 1.20.1 Forge", "DeadZone"],
    },
    {
        "name": "Prominence II",
        "aliases": ["Prominence_ II Hasturian Era", "Prominence II", "Prominence II [RPG]", "Prominence_II_Hasturian_Era", "prominence-2-hasturian-era", "prominence II"],
    },
    {
        "name": "Homestead",
        "aliases": ["Homestead - A Cozy Survival Experience", "Homestead"],
    },
    # Nanti bisa kamu tambahkan modpack baru di sini, contoh:
    # {
    #     "name": "DeadZone 1.20.1 Forge",
    #     "aliases": ["DeadZone 1.20.1 Forge"],
    # },
    # {
    #     "name": "DeceasedCraft",
    #     "aliases": ["DeceasedCraft", "DeceasedCraft 1.20.1"],
    # },
]

def find_version_dir_by_name(name):
    if not name:
        return None
    # 1. Cek dari alias modpack terdaftar
    for entry in REGISTERED_VERSIONS:
        if name.lower() == entry["name"].lower() or any(name.lower() == a.lower() for a in entry["aliases"]):
            for alias in entry["aliases"]:
                for r in get_possible_version_roots():
                    cand = os.path.join(r, alias)
                    if os.path.isdir(cand) and (os.path.exists(os.path.join(cand, "launch_args.txt")) or os.path.exists(os.path.join(cand, "mods"))):
                        return cand
    # 2. Cek nama folder langsung
    for r in get_possible_version_roots():
        cand = os.path.join(r, name)
        if os.path.isdir(cand) and (os.path.exists(os.path.join(cand, "launch_args.txt")) or os.path.exists(os.path.join(cand, "mods"))):
            return cand
    return None

def get_all_available_versions():
    """
    Returns registered available Minecraft versions/modpacks.
    Hanya menampilkan modpack yang ada di REGISTERED_VERSIONS agar rapi.
    """
    found = {}
    for entry in REGISTERED_VERSIONS:
        name = entry["name"]
        for alias in entry["aliases"]:
            v_dir = find_version_dir_by_name(alias)
            if v_dir:
                found[name] = v_dir
                break
    return found

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


# ==============================================================================
# DISCORD RICH PRESENCE ENGINE (ZERO-DEPENDENCY DIRECT IPC)
# ==============================================================================

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

    def _get_modpack_icon(self, v_name, cfg):
        if cfg.get('discord_large_image'):
            return cfg['discord_large_image']
        v_lower = (v_name or '').lower()

        # 1. Specific popular modpacks
        if 'prominence' in v_lower:
            return "https://media.forgecdn.net/avatars/1969/863/639217114177376898.webp"
        if 'homestead' in v_lower:
            return "https://media.forgecdn.net/avatars/thumbnails/791/6/256/256/638146943952272835.png"

        # 2. Horror / Zombie / Apocalypse
        if any(k in v_lower for k in ('zombie', 'deadzone', 'cursed', 'infection', 'apocalypse', 'walking', 'undead')):
            return "https://mc-heads.net/avatar/Zombie.png"
        if any(k in v_lower for k in ('nightfall', 'fear', 'darkness', 'horror', 'spooky')):
            return "https://mc-heads.net/avatar/MHF_Moon.png"

        # 3. Anime & Themed
        if any(k in v_lower for k in ('tensura', 'slime', 'rimuru')):
            return "https://mc-heads.net/avatar/Rimuru.png"
        if any(k in v_lower for k in ('jujutsu', 'jjk', 'gojo', 'sukuna')):
            return "https://mc-heads.net/avatar/Gojo.png"
        if any(k in v_lower for k in ('piece', 'luffy', 'pirate')):
            return "https://mc-heads.net/avatar/Luffy.png"
        if any(k in v_lower for k in ('slayer', 'kimetsu', 'tanjiro', 'demonslayer')):
            return "https://mc-heads.net/avatar/Tanjiro.png"
        if any(k in v_lower for k in ('naruto', 'shinobi', 'ninja')):
            return "https://mc-heads.net/avatar/Naruto.png"
        if any(k in v_lower for k in ('cobblemon', 'pixelmon', 'pokemon', 'pokecube')):
            return "https://mc-heads.net/avatar/Pikachu.png"

        # 4. RPG / Magic / Tech
        if any(k in v_lower for k in ('medieval', 'knight', 'kingdom', 'crusade', 'realm')):
            return "https://mc-heads.net/avatar/Knight.png"
        if any(k in v_lower for k in ('magic', 'wizard', 'witch', 'sorcery', 'spell', 'ars_nouveau', 'iron_spell')):
            return "https://mc-heads.net/avatar/Witch.png"
        if any(k in v_lower for k in ('create', 'tech', 'factory', 'industrial', 'automation', 'engineer')):
            return "https://mc-heads.net/avatar/Iron_Golem.png"

        # Fallback default: official chest icon
        return "https://mc-heads.net/avatar/MHF_Chest.png"

    def _get_player_avatar(self, username, cfg):
        if cfg.get('discord_small_image'):
            return cfg['discord_small_image']
        if username and username.lower() == 'epithap':
            return 'https://files.catbox.moe/wdhyhz.png'
        if username and username.strip():
            return f"https://mc-heads.net/avatar/{username.strip()}.png"
        return "steve"

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
        saves_dir = os.path.join(version_dir, 'saves')
        if not os.path.isdir(saves_dir):
            return None
        latest_world = None
        latest_mtime = 0
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
            return f"Mabar (Radmin): {h}:{p}"
        elif h.startswith('25.'):
            return f"Mabar (Hamachi): {h}:{p}"
        elif h.startswith(('192.168.', '10.', '172.')):
            return f"Mabar (LAN): {h}:{p}"
        elif p == '25565':
            return f"Mabar: {h}"
        return f"Mabar: {h}:{p}"


    def set_menu(self, version_dir, cfg):
        if not self.enabled:
            return
        v_name = cfg.get('version_name', os.path.basename(version_dir))
        v_info = detect_version_info(version_dir, v_name)
        mod_count = count_mods(version_dir)
        user = cfg.get('username', 'Player')

        large_icon = self._get_modpack_icon(v_name, cfg)
        small_icon = self._get_player_avatar(user, cfg)

        act = {
            'details': "In Moon Launcher Studio",
            'state': f"Modpack: {v_name}",
            'assets': {
                'large_image': large_icon,
                'large_text': f"{v_info['formatted']} ({mod_count} mods)",
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

        large_icon = self._get_modpack_icon(v_name, cfg)
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

            current_loc = None
            last_disconnect_time = 0
            last_checked_saves = 0

            re_connect = re.compile(r'Connecting to ([^,]+),\s*([0-9]+)')
            re_sp_start = re.compile(r'Starting integrated minecraft server version')
            re_disconnect = re.compile(r'Stopping JEI|Lost connection|Disconnected|Saving chunks for level')

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
                                m_c = re_connect.search(line)
                                if m_c:
                                    server_loc = self._format_server(m_c.group(1), m_c.group(2))
                                    if current_loc != server_loc:
                                        current_loc = server_loc
                                        changed = True
                                elif re_sp_start.search(line):
                                    w_name = self._get_active_world(version_dir, max(last_disconnect_time, game_start_time - 15))
                                    sp_loc = f"World: {w_name}" if w_name else "In Singleplayer"
                                    if current_loc != sp_loc:
                                        current_loc = sp_loc
                                        changed = True
                                elif re_disconnect.search(line):
                                    last_disconnect_time = now
                                    if current_loc != "In Main Menu":
                                        current_loc = "In Main Menu"
                                        changed = True
                        elif curr_size < last_pos:
                            last_pos = 0
                    except Exception:
                        pass

                # 2. Check active singleplayer saves periodically if not in multiplayer
                if (now - last_checked_saves) >= 4:
                    last_checked_saves = now
                    if not (current_loc and current_loc.startswith("Mabar")):
                        w_name = self._get_active_world(version_dir, max(last_disconnect_time, game_start_time - 15))
                        if w_name:
                            sp_loc = f"World: {w_name}"
                            if current_loc != sp_loc:
                                current_loc = sp_loc
                                changed = True
                        elif current_loc is None and (now - game_start_time) > 40:
                            current_loc = "In Main Menu"
                            changed = True

                if changed and current_loc:
                    with self.lock:
                        if self.current_state:
                            self.current_state['state'] = current_loc
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
    if "Cursed Walking" in all_v:
        return all_v["Cursed Walking"]
    if "DeadZone 1.20.1 Forge" in all_v:
        return all_v["DeadZone 1.20.1 Forge"]
    if all_v:
        return list(all_v.values())[0]

    return script_dir

def set_active_version(new_name):
    """Saves the chosen active version to global state file permanently."""
    try:
        os.makedirs(os.path.dirname(GLOBAL_STATE_FILE), exist_ok=True)
        with open(GLOBAL_STATE_FILE, 'w', encoding='utf-8-sig') as f:
            json.dump({
                'active_version': new_name,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2)
    except Exception as e:
        print(f"{C_RED}Warning: Could not save persistent active version: {e}{CLR_RESET}")

def ensure_launch_args(target_dir, template_dir=None):
    """Ensures target version directory has a valid launch_args.txt file."""
    args_path = os.path.join(target_dir, 'launch_args.txt')
    if os.path.exists(args_path):
        return True

    candidates = []
    if template_dir and os.path.exists(os.path.join(template_dir, 'launch_args.txt')):
        candidates.append(os.path.join(template_dir, 'launch_args.txt'))
    candidates.append(os.path.join(BASE_VERSIONS_DIR, 'DeadZone 1.20.1 Forge', 'launch_args.txt'))
    candidates.append(os.path.join(BASE_VERSIONS_DIR, 'NightfallCraft 2.2.9.7', 'launch_args.txt'))

    for c in candidates:
        if os.path.exists(c):
            try:
                with open(c, 'r', encoding='utf-8-sig') as f:
                    content = f.read()
                old_v = os.path.basename(os.path.dirname(c))
                new_v = os.path.basename(target_dir)
                new_content = content.replace(f"--version\n{old_v}", f"--version\n{new_v}")
                with open(args_path, 'w', encoding='utf-8-sig') as f:
                    f.write(new_content)
                return True
            except Exception:
                pass
    return False

def get_current_dir():
    return get_active_version_dir()

def get_config_path(version_dir):
    return os.path.join(version_dir, 'launcher_config.json')

def load_config(version_dir):
    cfg_path = get_config_path(version_dir)
    v_name = os.path.basename(version_dir)
    default_cfg = {
        'ram_max_gb': 8,
        'ram_min_gb': 2,
        'username': 'Epithap',
        'width': 1280,
        'height': 720,
        'fullscreen': False,
        'java_path': DEFAULT_JAVA,
        'version_name': v_name
    }

    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass

    if not os.path.exists(default_cfg.get('java_path', '')):
        default_cfg['java_path'] = DEFAULT_JAVA
    default_cfg['version_name'] = v_name
    return default_cfg

def save_config(version_dir, cfg):
    cfg_path = get_config_path(version_dir)
    try:
        with open(cfg_path, 'w', encoding='utf-8-sig') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"{C_RED}Failed to save configuration: {e}{CLR_RESET}")
    update_launch_args(version_dir, cfg)

def update_launch_args(version_dir, cfg):
    args_path = os.path.join(version_dir, 'launch_args.txt')
    if not os.path.exists(args_path):
        return False

    with open(args_path, 'r', encoding='utf-8-sig') as f:
        lines = [l.rstrip('\r\n') for l in f.readlines()]

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('-Xms'):
            new_lines.append(f"-Xms{cfg['ram_min_gb']}G")
        elif line.startswith('-Xmx'):
            new_lines.append(f"-Xmx{cfg['ram_max_gb']}G")
        elif line == '--username':
            new_lines.append(line)
            i += 1
            new_lines.append(str(cfg['username']))
        elif line == '--width':
            new_lines.append(line)
            i += 1
            new_lines.append(str(cfg['width']))
        elif line == '--height':
            new_lines.append(line)
            i += 1
            new_lines.append(str(cfg['height']))
        elif line == '--version':
            new_lines.append(line)
            i += 1
            new_lines.append(str(cfg.get('version_name', os.path.basename(version_dir))))
        else:
            new_lines.append(line)
        i += 1

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
    Returns formatted string: 'Modpack_Name (1.20.1, Forge 47.4.4)'
    """
    if not v_name:
        v_name = os.path.basename(version_dir) if version_dir else 'NightfallCraft 2.2.9.7'

    mc_ver = "1.20.1"
    loader_name = "Forge"
    loader_ver = "47.4.4"

    target_dir = version_dir
    if not target_dir or not os.path.exists(target_dir):
        candidate = os.path.join(BASE_VERSIONS_DIR, v_name)
        if os.path.exists(candidate):
            target_dir = candidate

    if target_dir and os.path.exists(target_dir):
        args_p = os.path.join(target_dir, 'launch_args.txt')
        if os.path.exists(args_p):
            try:
                with open(args_p, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    args_text = f.read()

                m_neo = re.search(r'neoforge[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)', args_text, re.I)
                if m_neo:
                    mc_ver = m_neo.group(1)
                    loader_name = "NeoForge"
                    loader_ver = m_neo.group(2)
                else:
                    m_fml = re.search(r'fmlloader[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)', args_text, re.I)
                    if m_fml:
                        mc_ver = m_fml.group(1)
                        loader_name = "Forge"
                        loader_ver = m_fml.group(2)
                    else:
                        m_fab = re.search(r'fabric[\/:\-]loader[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)', args_text, re.I)
                        if m_fab:
                            loader_name = "Fabric"
                            loader_ver = m_fab.group(1)
                            m_mc = re.search(r'minecraft[\/:\-]+([0-9]+\.[0-9]+(?:\.[0-9]+)?)', args_text, re.I)
                            if m_mc:
                                mc_ver = m_mc.group(1)
            except Exception:
                pass

        json_path = os.path.join(target_dir, f"{v_name}.json")
        if not os.path.exists(json_path):
            try:
                for f in os.listdir(target_dir):
                    if f.endswith('.json') and not f.startswith('launcher_config') and not f.startswith('user'):
                        json_path = os.path.join(target_dir, f)
                        break
            except Exception:
                pass

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    jdata = json.load(f)
                for lib in jdata.get('libraries', []):
                    lname = lib.get('name', '')
                    if 'fmlloader' in lname:
                        parts = lname.split(':')
                        if len(parts) >= 3 and '-' in parts[2]:
                            mc_p, f_p = parts[2].split('-', 1)
                            mc_ver = mc_p
                            loader_name = "Forge"
                            loader_ver = f_p
                    elif 'neoforge' in lname and ':' in lname:
                        parts = lname.split(':')
                        if len(parts) >= 3:
                            loader_name = "NeoForge"
                            loader_ver = parts[2]
                    elif 'fabric-loader' in lname and ':' in lname:
                        parts = lname.split(':')
                        if len(parts) >= 3:
                            loader_name = "Fabric"
                            loader_ver = parts[2]
            except Exception:
                pass

    return {
        'title': v_name,
        'mc_version': mc_ver,
        'loader_name': loader_name,
        'loader_version': loader_ver,
        'formatted': f"{v_name} ({mc_ver}, {loader_name} {loader_ver})"
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

    fields_meta = [
        ("Maximum Memory (RAM)",   f"{cfg['ram_max_gb']} GB",       "Rec: 8 - 12 GB",       f"{cfg['ram_max_gb']} GB"),
        ("Initial Memory (Min)",   f"{cfg['ram_min_gb']} GB",       "Fast JVM startup",     f"{cfg['ram_min_gb']} GB"),
        ("Player Username",        f"{cfg['username']}",            "In-game player ID",    f"{cfg['username']}"),
        ("Display Resolution",     res_str,                         "Default window size",  res_str),
        ("Fullscreen Display",     full_str,                        "Exclusive display",    full_plain),
        ("Active Profile",         v_name,                          "Active game profile",  v_name),
        ("Java 17 Runtime",        java_plain,                      "javaw.exe binary",     java_plain)
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
            f"Active: {detect_version_info(BASE_VERSIONS_DIR, v_name)['formatted']}",
            f"{C_CYAN}< / >{C_MUTED} Cycle profiles  │  {C_AMBER}[S]{C_MUTED} Save active profile permanently{CLR_RESET}"
        ),
        (
            "Java 17 Runtime",
            "Java 17 64-bit runtime binary (javaw.exe) required for modern Minecraft.",
            f"{C_CYAN}< / >{C_MUTED} Toggle Bundled vs System  │  {C_AMBER}[ENTER]{C_MUTED} Custom path{CLR_RESET}"
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
                    selected_idx = (selected_idx - 1) % 7
                    status_msg = ""
                elif ch2 == b'P':  # Down
                    selected_idx = (selected_idx + 1) % 7
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
                    target_dir = os.path.join(BASE_VERSIONS_DIR, temp_cfg.get('version_name', ''))
                    if not os.path.exists(target_dir):
                        target_dir = current_target_dir
                    save_config(target_dir, temp_cfg)
                    set_active_version(temp_cfg.get('version_name', os.path.basename(target_dir)))
                    ensure_launch_args(target_dir, current_target_dir)
                    cfg.update(temp_cfg)
                    current_target_dir = target_dir
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
            target_dir = current_target_dir
            if temp_cfg.get('version_name') and temp_cfg.get('version_name') != os.path.basename(current_target_dir):
                new_dir = os.path.join(BASE_VERSIONS_DIR, temp_cfg['version_name'])
                if os.path.exists(new_dir):
                    target_dir = new_dir
                    set_active_version(temp_cfg['version_name'])
                    ensure_launch_args(target_dir, current_target_dir)

            save_config(target_dir, temp_cfg)
            cfg.update(temp_cfg)
            current_target_dir = target_dir
            is_modified = False
            status_msg = "[OK] Configuration saved & active version updated!"

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
        elif ch >= b'1' and ch <= b'7':
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
                draw_studio_screen(temp_cfg, selected_idx, is_modified, "Edit Player Username")
                print(f"  {C_CYAN}Current Name:{CLR_RESET} {temp_cfg['username']}")
                new_val = input(f"  {C_AMBER}Enter new username [or press ENTER to keep]: {CLR_RESET}").strip()
                if new_val:
                    clean_name = new_val.replace(' ', '_')
                    temp_cfg['username'] = clean_name
                    is_modified = True
                    status_msg = f"Username updated to: {clean_name}"
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

    if temp_cfg.get('version_name') and temp_cfg.get('version_name') != os.path.basename(current_target_dir):
        new_dir = os.path.join(BASE_VERSIONS_DIR, temp_cfg['version_name'])
        if os.path.exists(new_dir):
            current_target_dir = new_dir
            set_active_version(temp_cfg['version_name'])

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

    elif key in ('user', 'username', 'player'):
        clean_user = val.replace(' ', '_')
        cfg['username'] = clean_user
        save_config(version_dir, cfg)
        print(f"{C_GREEN}[Moon Launcher] Updated username -> {clean_user}{CLR_RESET}")

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
        print(f"{C_RED}Unknown setting key '{key}'. Available: ram, minram, user, width, height, res, fullscreen, java{CLR_RESET}")

    return cfg

def print_banner(version_dir, cfg):
    os.system('cls' if sys.platform == 'win32' else 'clear')
    if sys.platform == 'win32':
        os.system('title Moon Launcher')

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
    print(f"  {C_MUTED}Quick Commands:{CLR_RESET} {C_CYAN}/play{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_AMBER}/setting{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_PURPLE}/status{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_BLUE}/version{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_MUTED}/help{CLR_RESET} {C_MUTED}•{CLR_RESET} {C_RED}/exit{CLR_RESET}")
    print(f"{C_BORDER}{'─' * (box_w + 4)}{CLR_RESET}")

def print_help():
    print(f"\n{C_WHITE}Command Reference:{CLR_RESET}")
    cmds = [
        ("/play", "Launch Minecraft & active mods directly"),
        ("/setting", "Open Moon Settings Studio (RAM, resolution, player, profiles)"),
        ("/setting <key> <val>", "Quick config edit (e.g. /setting ram 12, /setting user Epithap)"),
        ("/status", "System diagnostics (JVM, RAM, natives, and modpack)"),
        ("/version", "Switch installation profile (saved permanently across runs)"),
        ("/mods [filter]", "List and search installed mods"),
        ("/clear", "Clear screen and redraw banner"),
        ("/exit", "Exit Moon Launcher CLI")
    ]
    for c, desc in cmds:
        print(f"  {C_CYAN}{c:<22}{CLR_RESET} {C_MUTED}—{CLR_RESET} {desc}")
    print()

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
    print(f"  Natives Directory      : {C_GREEN}Available{CLR_RESET}" if natives_ok else f"  Natives Directory      : {C_RED}Missing{CLR_RESET}")
    print(f"  launch_args.txt        : {C_GREEN}Present & Synchronized{CLR_RESET}" if has_args else f"  launch_args.txt        : {C_RED}Missing{CLR_RESET}")
    print(f"  Config File            : {C_CYAN}{get_config_path(version_dir)}{CLR_RESET}")
    print(f"  Java Runtime Status    : {C_GREEN}Valid ({j_msg}){CLR_RESET}" if j_ok else f"  Java Runtime Status    : {C_RED}Invalid / Not Found ({cfg['java_path']}){CLR_RESET}")
    print(f"  Configured Max Memory  : {C_AMBER}{cfg['ram_max_gb']} GB (-Xmx{cfg['ram_max_gb']}G){CLR_RESET}")
    print(f"  Configured Min Memory  : {C_MUTED}{cfg['ram_min_gb']} GB (-Xms{cfg['ram_min_gb']}G){CLR_RESET}")
    rpc_st = f"{C_GREEN}Active & Synchronized{CLR_RESET}" if (GLOBAL_RPC and GLOBAL_RPC.connected) else f"{C_CYAN}Enabled{CLR_RESET}"
    print(f"  Discord Rich Presence  : {rpc_st}")
    print()

def list_mods(version_dir, filter_query=""):
    mods_dir = os.path.join(version_dir, 'mods')
    if not os.path.exists(mods_dir):
        print(f"{C_RED}Mods directory not found: {mods_dir}{CLR_RESET}")
        return

    jars = [f for f in sorted(os.listdir(mods_dir)) if f.endswith('.jar')]
    if filter_query:
        query = filter_query.lower()
        jars = [f for f in jars if query in f.lower()]

    print(f"\n{C_WHITE}Installed Mods ({len(jars)} total){CLR_RESET}" + (f" matching '{filter_query}':" if filter_query else ":"))
    for idx, j in enumerate(jars, 1):
        print(f"  {C_MUTED}{idx:3d}.{CLR_RESET} {C_CYAN}{j}{CLR_RESET}")
    print()

def launch_game(version_dir, cfg):
    box_w = 66
    j_path = cfg['java_path']
    if not os.path.exists(j_path):
        err_lines = [
            f"{C_RED}X Java Runtime not found at:{CLR_RESET}",
            f"{C_MUTED}{j_path}{CLR_RESET}",
            f"{C_AMBER}Please run /setting to adjust your java_path.{CLR_RESET}"
        ]
        print("\n" + render_box(err_lines, box_w) + "\n")
        return False

    ensure_launch_args(version_dir)
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
            l = l.strip().lstrip('\ufeff')
            if not l:
                continue
            if len(l) >= 2 and l[0] == '"' and l[-1] == '"':
                l = l[1:-1]
            launch_args.append(l)

    full_cmd = [j_path] + launch_args
    if cfg.get('fullscreen', False):
        full_cmd.append('--fullscreen')

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
            cwd=version_dir if os.path.exists(version_dir) else (r"E:\TLauncher" if os.path.exists(r"E:\TLauncher") else os.path.expandvars(r"%APPDATA%\.minecraft")),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        if GLOBAL_RPC:
            GLOBAL_RPC.set_playing(version_dir, cfg, proc)
        launch_lines = [
            f"{C_GREEN}[OK] Game launched successfully! (PID: {proc.pid}){CLR_RESET}",
            "",
            f"{C_MUTED}Game is running in the background.{CLR_RESET}",
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

def switch_version(curr_dir, cfg):
    avail_map = get_all_available_versions()
    avail = list(avail_map.keys())

    if not avail:
        print(f"\n{C_RED}No registered versions found!{CLR_RESET}\n")
        return curr_dir, cfg

    print(f"\n{C_WHITE}Select Minecraft Installation Version:{CLR_RESET}")
    for idx, v in enumerate(avail, 1):
        target_dir = avail_map[v]
        is_active = (target_dir == curr_dir or v.lower() == cfg.get('version_name', '').lower())
        mark = f"{C_GREEN}[ACTIVE]{CLR_RESET}" if is_active else ""
        print(f"  {C_CYAN}[{idx:2d}]{CLR_RESET} {v} {mark}")

    choice = input(f"\n{C_AMBER}Enter selection number (or press ENTER to cancel): {CLR_RESET}").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(avail):
        new_name = avail[int(choice) - 1]
        new_dir = avail_map[new_name]
        cfg['version_name'] = new_name
        save_config(new_dir, cfg)
        set_active_version(new_name)
        ensure_launch_args(new_dir, curr_dir)
        print(f"{C_GREEN}[OK] Switched and saved active version to: {new_name}{CLR_RESET}")
        time.sleep(1)
        return new_dir, load_config(new_dir)
    return curr_dir, cfg

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

def main():
    if sys.platform == 'win32':
        os.system('title Moon Launcher')

    # Load persistent active version (remembered across restarts)
    global GLOBAL_RPC
    version_dir = get_active_version_dir()
    cfg = load_config(version_dir)
    GLOBAL_RPC = MoonDiscordRPC(
        client_id=cfg.get("discord_client_id", "450485984333660181"),
        enabled=cfg.get("discord_rpc", True)
    )
    GLOBAL_RPC.set_menu(version_dir, cfg)

    # Process CLI arguments if passed (e.g. python launcher.py /play or /status)
    if len(sys.argv) > 1:
        arg_cmd = sys.argv[1].lower()
        if arg_cmd in ('/play', 'play', '/p', 'p', '/start', 'start', '/launch', 'launch'):
            launch_game(version_dir, cfg)
            return
        elif arg_cmd in ('/setting', 'setting', '/settings', 'settings', '/s', 's'):
            if len(sys.argv) > 2:
                cfg = apply_quick_setting(version_dir, cfg, sys.argv[2:])
            else:
                version_dir, cfg = run_settings_studio(version_dir, cfg)
            return
        elif arg_cmd in ('/status', 'status', '/info', 'info'):
            print_status(version_dir, cfg)
            return
        elif arg_cmd in ('/help', 'help', '/?', '?'):
            print_help()
            return
        elif arg_cmd in ('/mods', 'mods'):
            query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
            list_mods(version_dir, query)
            return

    print_banner(version_dir, cfg)

    while True:
        try:
            prompt_str = f"{C_CLAUDE}moon{CLR_RESET} {C_MUTED}❯{CLR_RESET} "
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_MUTED}Exiting Moon Launcher CLI. Goodbye!{CLR_RESET}")
            break

        if not user_input:
            continue

        raw_parts = user_input.split()
        cmd = raw_parts[0].lower()

        if cmd in ('/play', 'play', '/p', 'p', '/start', 'start', '/launch', 'launch', '1'):
            launch_game(version_dir, cfg)

        elif cmd in ('/setting', 'setting', '/settings', 'settings', '/s', 's', '/nano', 'nano', '2'):
            if len(raw_parts) > 1:
                cfg = apply_quick_setting(version_dir, cfg, raw_parts[1:])
            else:
                version_dir, cfg = run_settings_studio(version_dir, cfg)
                print_banner(version_dir, cfg)

        elif cmd in ('/status', 'status', '/info', 'info', '3'):
            print_status(version_dir, cfg)

        elif cmd in ('/version', 'version', '/versions', 'versions', '/v', 'v', '4'):
            version_dir, cfg = switch_version(version_dir, cfg)
            if GLOBAL_RPC:
                GLOBAL_RPC.set_menu(version_dir, cfg)
            print_banner(version_dir, cfg)

        elif cmd in ('/mods', 'mods', '/m', 'm'):
            query = ' '.join(raw_parts[1:]) if len(raw_parts) > 1 else ''
            list_mods(version_dir, query)

        elif cmd in ('/help', 'help', '/?', '?', '/h', 'h'):
            print_help()

        elif cmd in ('/clear', 'clear', '/cls', 'cls', '/c', 'c'):
            print_banner(version_dir, cfg)

        elif cmd in ('/exit', 'exit', '/quit', 'quit', '/q', 'q'):
            if GLOBAL_RPC:
                GLOBAL_RPC.close()
            print(f"{C_MUTED}Exiting Moon Launcher. Have fun!{CLR_RESET}")
            break

        else:
            print(f"{C_RED}Unknown command '{user_input}'.{CLR_RESET} {C_MUTED}Type /play to start, /setting for config editor, or /help for commands.{CLR_RESET}\n")

if __name__ == '__main__':
    main()



