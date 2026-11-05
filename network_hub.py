"""
Moon Launcher - Network Hub & Multiplayer Engine
Provides native Internet Tunneling (/host), LAN Discovery, and Friends/Servers Management (/friend, /server).
Strictly 100% English UI text and zero emojis.
"""

import os
import sys
import time
import json
import socket
import struct
import re
import threading
import subprocess
import urllib.request
import urllib.parse
import base64
if sys.platform == 'win32':
    import winreg

# ANSI Colors matching Moon Launcher styling
C_CLAUDE = "\033[38;2;217;119;87m"
C_PURPLE = "\033[38;2;168;85;247m"
C_CYAN   = "\033[38;2;56;189;248m"
C_GREEN  = "\033[38;2;34;197;94m"
C_AMBER  = "\033[38;2;245;158;11m"
C_RED    = "\033[38;2;239;68;68m"
C_WHITE  = "\033[38;2;243;244;246m"
C_MUTED  = "\033[38;2;107;114;128m"
C_BORDER = "\033[38;2;55;65;81m"
CLR_RESET= "\033[0m"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRIENDS_FILE = os.path.join(BASE_DIR, "friends.json")
RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")
PLAYIT_EXE = os.path.join(RUNTIME_DIR, "playit.exe")
PLAYIT_LOG = os.path.join(RUNTIME_DIR, "playit.log")
PLAYIT_URL = "https://github.com/playit-cloud/playit-agent/releases/download/v0.15.26/playit-windows-x86_64-signed.exe"

# Global Tunnel Process State
TUNNEL_LOCK = threading.Lock()
TUNNEL_PROC = None
TUNNEL_LOCAL_PORT = 25565
TUNNEL_PUBLIC_ADDR = None
TUNNEL_CLAIM_URL = None
TUNNEL_START_TIME = None

# ==============================================================================
# UI RENDERING UTILITIES
# ==============================================================================

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def get_visible_width(text):
    return len(strip_ansi(text))

def render_box(lines, width=68, title=None):
    top = f"{C_BORDER}╭{'─' * (width - 2)}╮{CLR_RESET}"
    bottom = f"{C_BORDER}╰{'─' * (width - 2)}╯{CLR_RESET}"
    out = [top]
    if title:
        v_title = f" {title} "
        t_len = get_visible_width(v_title)
        out[0] = f"{C_BORDER}╭─{C_WHITE}\033[1m{v_title}{CLR_RESET}{C_BORDER}{'─' * max(0, width - 4 - t_len)}╮{CLR_RESET}"

    for l in lines:
        v_w = get_visible_width(l)
        pad = max(0, width - 4 - v_w)
        out.append(f"{C_BORDER}│{CLR_RESET}  {l}{' ' * pad}{C_BORDER}│{CLR_RESET}")
    out.append(bottom)
    return "\n".join(out)

# ==============================================================================
# CLIPBOARD & PROTOCOL UTILITIES
# ==============================================================================

def copy_to_clipboard(text):
    """Copies text to Windows system clipboard silently using built-in clip.exe or PowerShell."""
    if not text or sys.platform != 'win32':
        return False
    try:
        p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        p.communicate(input=text.encode('utf-16le'))
        if p.returncode == 0:
            return True
    except Exception:
        pass
    try:
        cmd = f'Set-Clipboard -Value "{text}"'
        res = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        return res.returncode == 0
    except Exception:
        pass
    return False

def get_clipboard_text():
    """Reads text from Windows system clipboard."""
    if sys.platform == 'win32':
        try:
            res = subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], capture_output=True, text=True, timeout=2, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            return res.stdout.strip()
        except Exception:
            pass
    return ""

def register_windows_protocol_handler():
    """Registers moon:// URL protocol handler in HKCU (no admin privileges needed)."""
    if sys.platform != 'win32':
        return False
    try:
        py_exe = sys.executable
        target_py = os.path.join(BASE_DIR, "launcher.py")
        cmd_str = f'"{py_exe}" "{target_py}" "%1"'
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\moon")
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Moon Launcher Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        cmd_key = winreg.CreateKey(key, r"shell\open\command")
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)
        winreg.CloseKey(cmd_key)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def handle_moon_protocol_url(url_str, version_dir=None):
    """
    Handles moon:// protocol URLs launched from web browser or OS.
    Supported formats:
    - moon://install/<slug_or_id>
    - moon://join/<server_addr>
    - moon://friend/add?user=...&addr=...
    - moon://player/<player_id>
    - moon://home
    """
    raw = str(url_str).strip().strip('"').strip("'")
    print(f"\n{C_WHITE}Handling Moon Protocol URL: {C_CYAN}{raw}{CLR_RESET}")
    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception as e:
        print(f"{C_RED}Invalid URL: {e}{CLR_RESET}")
        return False

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.strip('/')

    action = netloc if scheme == 'moon' else ''
    if not action:
        parts = [p for p in path.split('/') if p]
        if parts:
            action = parts[0].lower()
            target = parts[1] if len(parts) > 1 else ""
        else:
            target = ""
    else:
        target = path

    target = target.strip('/')

    if action in ('install', 'download', 'modpack', 'mod', 'shader', 'resourcepack'):
        p_type = action if action in ('mod', 'shader', 'resourcepack', 'modpack') else None
        slug = target
        if not slug and '/' in target:
            slug = target.split('/')[-1]
        print(f"\n{C_CYAN}Installing package '{slug}' from protocol URL...{CLR_RESET}")
        import launcher
        res = launcher.install_modrinth_package(slug, project_type=p_type, version_dir=version_dir, non_interactive=False)
        return res.get("success", False) if isinstance(res, dict) else bool(res)

    elif action in ('join', 'connect', 'play'):
        addr = target or parsed.netloc
        print(f"\n{C_GREEN}Direct joining server: {addr}...{CLR_RESET}")
        import launcher
        cfg = launcher.load_config(version_dir) if version_dir else {}
        launcher.launch_game(version_dir, cfg, direct_server=addr)
        return True

    elif action in ('home', 'dashboard', 'gui', 'launcher'):
        print(f"\n{C_CYAN}Launching Moon Launcher Desktop Studio...{CLR_RESET}")
        gui_script = os.path.join(BASE_DIR, "gui_app.py")
        subprocess.Popen([sys.executable, gui_script], cwd=BASE_DIR)
        return True

    else:
        invite_data = parse_friend_invite(raw)
        if invite_data:
            handle_friend_command(['add', invite_data.get('user', ''), invite_data.get('addr', '')], active_version_dir=version_dir)
            return True
        print(f"{C_AMBER}Unknown action in protocol URL: {action}{CLR_RESET}")
        return False

def generate_friend_invite_link(username, server_address=None, note=None):
    """Generates both Universal Web and Direct Moon Protocol invite links."""
    clean_user = str(username).strip()
    params = {"user": clean_user}
    if server_address:
        params["addr"] = str(server_address).strip()
    if note:
        params["note"] = str(note).strip()
    qs = urllib.parse.urlencode(params)

    web_link = f"https://moonlauncher.link/add?{qs}"
    moon_link = f"moon://friend/add?{qs}"

    # Compact token
    json_b = json.dumps(params).encode('utf-8')
    b64_tok = base64.urlsafe_b64encode(json_b).decode('ascii').rstrip('=')
    token_link = f"moon:invite:{b64_tok}"

    return {
        "user": clean_user,
        "addr": server_address or "",
        "web_link": web_link,
        "moon_link": moon_link,
        "token_link": token_link
    }

def parse_friend_invite(text):
    """
    Parses a friend invite from URL (moon:// or https://) or token string.
    Returns dict with keys: username, address, note, or None if invalid.
    """
    if not text:
        return None
    raw = str(text).strip()

    # 1. Check for URL structure (moon://... or http(s)://...)
    url_m = re.search(r'(moon://[^\s"\'<>]+|https?://[^\s"\'<>]+)', raw)
    if url_m:
        target_url = url_m.group(1)
        try:
            parsed = urllib.parse.urlparse(target_url)
            qs = urllib.parse.parse_qs(parsed.query)
            user_list = qs.get('user', qs.get('u', qs.get('name', qs.get('username', []))))
            addr_list = qs.get('addr', qs.get('server', qs.get('ip', qs.get('s', []))))
            note_list = qs.get('note', qs.get('n', []))

            u_val = user_list[0] if user_list else ""
            a_val = addr_list[0] if addr_list else ""
            n_val = note_list[0] if note_list else ""

            # Check path segments if query parameter had no username (e.g. moon://friend/add/Michelle)
            if not u_val:
                segs = [s for s in parsed.path.split('/') if s and s.lower() not in ('add', 'friend', 'invite', 'join')]
                if segs:
                    u_val = segs[0]

            if u_val:
                return {
                    "username": u_val.strip().replace(" ", "_"),
                    "address": a_val.strip(),
                    "note": n_val.strip() or "Added via Invite Link"
                }
        except Exception:
            pass

    # 2. Check base64 token format
    tok_m = re.search(r'moon:(?:invite|friend):([a-zA-Z0-9_\-=]+)', raw)
    if tok_m:
        try:
            tok = tok_m.group(1)
            pad = len(tok) % 4
            if pad:
                tok += '=' * (4 - pad)
            dec = base64.urlsafe_b64decode(tok).decode('utf-8')
            d = json.loads(dec)
            u_val = d.get('user') or d.get('u') or d.get('name')
            if u_val:
                return {
                    "username": str(u_val).strip().replace(" ", "_"),
                    "address": str(d.get('addr') or d.get('server') or d.get('ip') or "").strip(),
                    "note": str(d.get('note') or "Added via Invite Token").strip()
                }
        except Exception:
            pass

    return None

def add_friend_from_invite(invite, data=None):
    """
    Saves the parsed invite into contacts, optionally saves server to server manager,
    pings the server, and prints a formatted confirmation box.
    """
    if not invite or not invite.get("username"):
        return False
    if data is None:
        data = load_network_data()
    friends = data.setdefault("friends", [])
    servers = data.setdefault("servers", [])

    u_name = invite["username"]
    addr = invite.get("address", "")
    note = invite.get("note", "Added via Invite Link")

    # Check existing friend
    matched = next((f for f in friends if f.get("username", "").lower() == u_name.lower()), None)
    if matched:
        if addr:
            matched["address"] = addr
        if note:
            matched["note"] = note
    else:
        friends.append({
            "username": u_name,
            "address": addr,
            "note": note,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    # If server address is included, also ensure server is listed in Servers manager
    srv_added = False
    if addr:
        existing_srv = next((s for s in servers if s.get("address", "").lower() == addr.lower()), None)
        if not existing_srv:
            servers.append({
                "name": f"{u_name}'s World",
                "address": addr,
                "category": f"Friend ({u_name})"
            })
            srv_added = True

    save_network_data(data)

    box_w = 68
    lines = [
        f"{C_GREEN}\033[1m[OK] Friend Added Successfully via Invite Link!\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"  {C_WHITE}* Player Name     :{CLR_RESET} {C_CYAN}{u_name}{CLR_RESET}",
    ]
    if addr:
        lines.append(f"  {C_WHITE}* Server Address  :{CLR_RESET} {C_WHITE}{addr}{CLR_RESET}")
        p_res = ping_minecraft_server(addr, timeout=2.0)
        if p_res["online"]:
            lines.append(f"  {C_WHITE}* Live Status     :{CLR_RESET} {C_GREEN}ONLINE ({p_res['latency']}ms • {p_res['players_online']}/{p_res['players_max']} players){CLR_RESET}")
            if p_res["motd"]:
                lines.append(f"  {C_WHITE}* MOTD            :{CLR_RESET} {C_MUTED}{p_res['motd']}{CLR_RESET}")
        else:
            lines.append(f"  {C_WHITE}* Live Status     :{CLR_RESET} {C_AMBER}OFFLINE or Host World not open yet{CLR_RESET}")
        if srv_added:
            lines.append(f"  {C_WHITE}* Saved to Server :{CLR_RESET} {C_GREEN}Yes (Saved to /server list){CLR_RESET}")
    else:
        lines.append(f"  {C_WHITE}* Server Address  :{CLR_RESET} {C_MUTED}None provided in link{CLR_RESET}")

    lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
    if addr:
        lines.append(f"{C_CYAN}Ready to play together! Launch Minecraft and connect to {addr}!{CLR_RESET}")
    else:
        lines.append(f"{C_MUTED}Tip: When {u_name} opens their world via /host, ask for their updated link.{CLR_RESET}")

    print("\n" + render_box(lines, box_w, title="Friend Added") + "\n")
    return True

# ==============================================================================
# DATA STORAGE (friends.json)
# ==============================================================================

def load_network_data():
    if not os.path.exists(FRIENDS_FILE):
        default_data = {
            "friends": [
                {
                    "username": "Michelle",
                    "address": "",
                    "note": "Primary Profile",
                    "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            ],
            "servers": [
                {
                    "name": "Hypixel Network",
                    "address": "mc.hypixel.net:25565",
                    "category": "Minigames"
                },
                {
                    "name": "CubeCraft Games",
                    "address": "play.cubecraft.net:25565",
                    "category": "Survival & Bedwars"
                }
            ]
        }
        save_network_data(default_data)
        return default_data

    try:
        with open(FRIENDS_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {"friends": [], "servers": []}

def save_network_data(data):
    try:
        with open(FRIENDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"{C_RED}Failed to save friends.json: {e}{CLR_RESET}")
        return False

# ==============================================================================
# MINECRAFT SERVER LIST PING (SLP) PROTOCOL
# ==============================================================================

def ping_minecraft_server(host, port=25565, timeout=2.5):
    """
    Direct TCP handshake to query server status, latency, player count, and MOTD.
    Pure Python socket implementation without third-party dependencies.
    """
    if ":" in host:
        parts = host.split(":", 1)
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    start_time = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, int(port)))

        def pack_varint(val):
            out = bytearray()
            while True:
                part = val & 0x7F
                val >>= 7
                out.append(part | (0x80 if val > 0 else 0))
                if val == 0:
                    break
            return bytes(out)

        def read_varint(sock):
            val = 0
            for i in range(5):
                b = sock.recv(1)
                if not b:
                    raise ConnectionResetError("Connection lost")
                byte = b[0]
                val |= (byte & 0x7F) << (7 * i)
                if not (byte & 0x80):
                    break
            return val

        host_bytes = host.encode('utf-8')
        handshake_payload = (
            b'\x00' +
            pack_varint(765) +
            pack_varint(len(host_bytes)) + host_bytes +
            struct.pack('>H', int(port)) +
            b'\x01'
        )
        s.sendall(pack_varint(len(handshake_payload)) + handshake_payload)
        s.sendall(b'\x01\x00') # Status request

        packet_len = read_varint(s)
        packet_id = read_varint(s)
        if packet_id != 0:
            raise ValueError("Invalid packet id")

        json_len = read_varint(s)
        received_data = bytearray()
        while len(received_data) < json_len:
            chunk = s.recv(min(4096, json_len - len(received_data)))
            if not chunk:
                break
            received_data.extend(chunk)

        latency = int((time.time() - start_time) * 1000)
        s.close()

        raw_json = json.loads(received_data.decode('utf-8', errors='ignore'))
        desc = raw_json.get('description', '')
        motd_text = desc.get('text', '') if isinstance(desc, dict) else str(desc)
        motd_clean = re.sub(r'§[0-9a-fk-or]', '', motd_text).strip()

        p_info = raw_json.get('players', {})
        online_p = p_info.get('online', 0)
        max_p = p_info.get('max', 0)
        ver_name = raw_json.get('version', {}).get('name', 'Minecraft')

        return {
            "online": True,
            "latency": latency,
            "motd": motd_clean[:45] or "Minecraft Server",
            "players_online": online_p,
            "players_max": max_p,
            "version": ver_name[:25]
        }
    except Exception as e:
        return {
            "online": False,
            "latency": 0,
            "motd": str(e)[:35],
            "players_online": 0,
            "players_max": 0,
            "version": ""
        }

# ==============================================================================
# LAN AUTO-DISCOVERY (UDP Multicast Listener)
# ==============================================================================

def scan_lan_worlds(timeout=2.0):
    """
    Listens on Minecraft LAN multicast group 224.0.2.60:4445 for open worlds.
    Returns list of discovered hosts: [{"world": str, "host_ip": str, "port": int}]
    """
    discovered = []
    seen = set()
    multicast_group = '224.0.2.60'
    server_address = ('', 4445)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(server_address)

        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        t_end = time.time() + timeout
        while time.time() < t_end:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode('utf-8', errors='ignore')
                motd_m = re.search(r'\[MOTD\](.*?)\[/MOTD\]', text)
                ad_m = re.search(r'\[AD\](.*?)\[/AD\]', text)
                if ad_m:
                    port = int(ad_m.group(1).strip())
                    world = motd_m.group(1).strip() if motd_m else "Minecraft LAN World"
                    key = (addr[0], port)
                    if key not in seen:
                        seen.add(key)
                        discovered.append({
                            "world": world,
                            "host_ip": addr[0],
                            "port": port
                        })
            except socket.timeout:
                break
            except Exception:
                break
        sock.close()
    except Exception:
        pass

    return discovered

# ==============================================================================
# NATIVE INTERNET TUNNEL ENGINE (Playit.gg Anycast Relay)
# ==============================================================================

def ensure_playit_binary():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    if os.path.exists(PLAYIT_EXE) and os.path.getsize(PLAYIT_EXE) > 1000000:
        return True

    print(f"\n{C_CYAN}[Moon Launcher] Downloading Playit Anycast Tunnel Agent...{CLR_RESET}")
    try:
        req = urllib.request.Request(PLAYIT_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp, open(PLAYIT_EXE, 'wb') as out_f:
            out_f.write(resp.read())
        print(f"{C_GREEN}[Moon Launcher] Tunnel agent installed successfully ({os.path.getsize(PLAYIT_EXE)} bytes).{CLR_RESET}")
        return True
    except Exception as e:
        print(f"{C_RED}[Moon Launcher] Failed to download tunnel binary: {e}{CLR_RESET}")
        return False

def detect_active_minecraft_port(version_dir=None):
    """Detects active Minecraft LAN hosting port from latest.log or defaults to 25565."""
    if version_dir:
        log_path = os.path.join(version_dir, "logs", "latest.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-60:]
                for l in reversed(lines):
                    m = re.search(r'(?:Started on|Hosting on port|Hosted on port|Local game hosted on port)\s*(\d{4,5})', l, re.IGNORECASE)
                    if m:
                        return int(m.group(1))
            except Exception:
                pass
    return 25565

def start_internet_tunnel(local_port=25565):
    global TUNNEL_PROC, TUNNEL_LOCAL_PORT, TUNNEL_PUBLIC_ADDR, TUNNEL_CLAIM_URL, TUNNEL_START_TIME

    with TUNNEL_LOCK:
        if TUNNEL_PROC and TUNNEL_PROC.poll() is None:
            return True, TUNNEL_PUBLIC_ADDR, TUNNEL_CLAIM_URL

        if not ensure_playit_binary():
            return False, None, None

        TUNNEL_LOCAL_PORT = int(local_port)
        TUNNEL_PUBLIC_ADDR = None
        TUNNEL_CLAIM_URL = None
        TUNNEL_START_TIME = time.time()

        # Clean previous log file
        try:
            if os.path.exists(PLAYIT_LOG):
                os.remove(PLAYIT_LOG)
        except Exception:
            pass

        try:
            log_fp = open(PLAYIT_LOG, "w", encoding="utf-8")
            cmd = [PLAYIT_EXE, "start"]
            TUNNEL_PROC = subprocess.Popen(
                cmd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=RUNTIME_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
        except Exception as e:
            return False, str(e), None

    # Wait up to 8 seconds to parse claim URL or active tunnel domain from log
    time.sleep(1.5)
    for _ in range(12):
        if os.path.exists(PLAYIT_LOG):
            try:
                with open(PLAYIT_LOG, "r", encoding="utf-8", errors="ignore") as f:
                    log_text = f.read()

                # Search for claim URL if agent is not claimed yet
                claim_m = re.search(r'(https://playit\.gg/claim/[a-zA-Z0-9_-]+)', log_text)
                if claim_m:
                    TUNNEL_CLAIM_URL = claim_m.group(1)

                # Search for assigned address (e.g. *.playit.gg:12345 or *.gl.joinmc.link:25565)
                addr_m = re.search(r'([a-zA-Z0-9\.\-_]+\.(?:playit\.gg|joinmc\.link|at\.ply\.gg):\d+)', log_text)
                if addr_m:
                    TUNNEL_PUBLIC_ADDR = addr_m.group(1)
                    break
            except Exception:
                pass
        time.sleep(0.5)

    return True, TUNNEL_PUBLIC_ADDR, TUNNEL_CLAIM_URL

def stop_internet_tunnel():
    global TUNNEL_PROC, TUNNEL_PUBLIC_ADDR, TUNNEL_CLAIM_URL
    with TUNNEL_LOCK:
        if TUNNEL_PROC:
            try:
                TUNNEL_PROC.terminate()
                TUNNEL_PROC.wait(timeout=2)
            except Exception:
                try: TUNNEL_PROC.kill()
                except Exception: pass
            TUNNEL_PROC = None
        TUNNEL_PUBLIC_ADDR = None
        TUNNEL_CLAIM_URL = None
    return True

def get_tunnel_status():
    with TUNNEL_LOCK:
        is_running = TUNNEL_PROC is not None and TUNNEL_PROC.poll() is None
        return {
            "running": is_running,
            "local_port": TUNNEL_LOCAL_PORT,
            "public_address": TUNNEL_PUBLIC_ADDR,
            "claim_url": TUNNEL_CLAIM_URL,
            "uptime_seconds": int(time.time() - TUNNEL_START_TIME) if is_running and TUNNEL_START_TIME else 0
        }

# ==============================================================================
# COMMAND HANDLER: /friend
# ==============================================================================

def handle_friend_command(args, active_version_dir=None):
    """
    Handles /friend commands using the unique MOON-XXXX ID system:
    - /friend (or /friend list) -> Displays contacts with Moon ID & live status
    - /friend invite -> Displays shareable invite link & your Moon ID
    - /friend add <MOON-ID> [optional_addr] -> Resolves & adds friend via Moon ID
    - /friend remove <MOON-ID or name> -> Removes friend
    - /friend join <name or ID> -> Connects to friend's world
    - /friend ping <name or ID> -> Pings server/status
    """
    data = load_network_data()
    raw_friends = data.get("friends", [])

    # Filter out current active username & Moon ID
    my_uname = ""
    my_moon_id = get_or_create_moon_id()
    try:
        import launcher
        my_uname = launcher.load_config().get("username", "").strip().lower()
    except Exception:
        pass

    friends = [
        f for f in raw_friends
        if (isinstance(f, dict) and f.get("username", "").strip().lower() != my_uname and f.get("player_id", "").strip().upper() != my_moon_id and f.get("note") != "Primary Profile")
        or (isinstance(f, str) and f.strip().lower() != my_uname)
    ]

    if not args or args[0].lower() in ("list", "ls", "show"):
        # Display Friends Table
        box_w = 72
        lines_box = [
            f"{C_WHITE}Player Friends & Multiplayer Contacts",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Your Moon ID :{CLR_RESET} {C_GREEN}\033[1m{my_moon_id}\033[0m {C_MUTED}(Share with friends to connect!){CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]

        if not friends:
            lines_box.append(f"{C_MUTED}No friends added yet.{CLR_RESET}")
            lines_box.append(f"{C_MUTED}Add friends by Moon ID: {C_CYAN}/friend add <MOON-XXXX>{CLR_RESET}")
            lines_box.append(f"{C_MUTED}Example: {C_WHITE}/friend add MOON-4821{CLR_RESET}")
        else:
            lines_box.append(f"  {C_MUTED}{'STATUS':<9} {'MOON ID':<11} {'USERNAME':<16} {'ACTIVITY / ADDRESS'}{CLR_RESET}")
            lines_box.append(f"  {C_MUTED}{'─'*8}  {'─'*10}  {'─'*15}  {'─'*24}{CLR_RESET}")
            for idx, f_item in enumerate(friends, 1):
                if isinstance(f_item, str):
                    p_id = f"MOON-{abs(hash(f_item)) % 9000 + 1000}"
                    u_name = f_item
                    addr = ""
                    note = ""
                else:
                    p_id = f_item.get("player_id") or f"MOON-{abs(hash(f_item.get('username', ''))) % 9000 + 1000}"
                    u_name = f_item.get("username", p_id)
                    addr = f_item.get("address", "")
                    note = f_item.get("note", "")

                status_tag = f"{C_MUTED}[OFFLINE]{CLR_RESET}"
                ping_detail = f"{C_MUTED}Offline{CLR_RESET}"

                peer_meta = None
                with CLOUD_PEERS_LOCK:
                    peer_meta = CLOUD_PEERS.get(p_id.lower()) or CLOUD_PEERS.get(u_name.lower())
                if not peer_meta:
                    with LAN_PEERS_LOCK:
                        peer_meta = next((p for uname, p in LAN_PEERS.items() if uname.lower() == u_name.lower()), None)

                if peer_meta and peer_meta.get("version_name"):
                    v_name = peer_meta.get("version_name")
                    m_cnt = peer_meta.get("mod_count", 0)
                    status_tag = f"{C_GREEN}[PLAYING]{CLR_RESET}"
                    ping_detail = f"{C_WHITE}{v_name}{CLR_RESET} ({m_cnt} mods)"
                elif peer_meta and peer_meta.get("status") in ("online", "in_game"):
                    status_tag = f"{C_CYAN}[ONLINE ]{CLR_RESET}"
                    ping_detail = f"{C_CYAN}In Launcher{CLR_RESET}"
                elif addr:
                    p_res = ping_minecraft_server(addr, timeout=1.2)
                    if p_res["online"]:
                        status_tag = f"{C_GREEN}[ONLINE ]{CLR_RESET}"
                        ping_detail = f"{C_GREEN}{p_res['latency']}ms{CLR_RESET} ({p_res['players_online']} players)"
                    else:
                        status_tag = f"{C_RED}[IDLE   ]{CLR_RESET}"
                        ping_detail = f"{C_MUTED}{addr}{CLR_RESET}"

                p_id_str = f"{p_id:<11}"
                u_name_str = f"{u_name:<16}"
                lines_box.append(f"  {status_tag} {C_AMBER}{p_id_str}{CLR_RESET} {C_CYAN}{u_name_str}{CLR_RESET} {ping_detail}")
                if peer_meta and peer_meta.get("version_name"):
                    lines_box.append(f"     {C_CYAN}↳ Join: Type /friend join {p_id}{CLR_RESET}")
                if note:
                    lines_box.append(f"     {C_MUTED}* Note: {note}{CLR_RESET}")

        lines_box.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines_box.append(f"{C_MUTED}Commands: {C_WHITE}/friend add <MOON-XXXX>{C_MUTED}  •  {C_WHITE}/friend remove <MOON-ID>{CLR_RESET}")
        lines_box.append(f"{C_MUTED}          {C_WHITE}/friend join <name/ID>{C_MUTED}   •  {C_WHITE}/friend invite{CLR_RESET}")
        print("\n" + render_box(lines_box, box_w, title="Friends Hub") + "\n")
        return

    sub = args[0].lower()

    # If first argument is directly an invite link or token
    if sub.startswith(('moon://', 'http://', 'https://')) or parse_friend_invite(args[0]):
        inv = parse_friend_invite(args[0])
        if inv:
            add_friend_from_invite(inv, data)
            return

    # /friend invite / share / link
    if sub in ("invite", "share", "link", "getlink", "code"):
        username = "Player"
        script_dir = BASE_DIR
        local_cfg = os.path.join(script_dir, "launcher_config.json")
        if active_version_dir and os.path.exists(os.path.join(active_version_dir, "launcher_config.json")):
            try:
                with open(os.path.join(active_version_dir, "launcher_config.json"), "r", encoding="utf-8-sig") as f:
                    username = json.load(f).get("username") or username
            except Exception: pass
        elif os.path.exists(local_cfg):
            try:
                with open(local_cfg, "r", encoding="utf-8-sig") as f:
                    username = json.load(f).get("username") or username
            except Exception: pass

        t_status = get_tunnel_status()
        server_addr = t_status.get("public_address") if t_status.get("running") else None

        invite = generate_friend_invite_link(username, server_address=server_addr)
        copied = copy_to_clipboard(invite["web_link"])

        box_w = 70
        lines_box = [
            f"{C_WHITE}\033[1mFriend & Multiplayer Invite Link\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Your Moon ID    :{CLR_RESET} {C_GREEN}\033[1m{my_moon_id}\033[0m",
            f"  {C_WHITE}* Player Profile  :{CLR_RESET} {C_CYAN}\033[1m{username}\033[0m",
        ]
        if server_addr:
            lines_box.append(f"  {C_WHITE}* Live Server     :{CLR_RESET} {C_GREEN}{server_addr} (Tunnel Active){CLR_RESET}")
        else:
            lines_box.append(f"  {C_WHITE}* Live Server     :{CLR_RESET} {C_MUTED}None (Start /host to include your game world){CLR_RESET}")

        lines_box.extend([
            f"",
            f"  {C_WHITE}\033[1mShareable Web Link:\033[0m",
            f"  {C_CYAN}{invite['web_link']}{CLR_RESET}",
            f"",
            f"  {C_WHITE}\033[1mDirect Moon Protocol:\033[0m",
            f"  {C_MUTED}{invite['moon_link']}{CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        ])
        if copied:
            lines_box.append(f"  {C_GREEN}[COPIED TO CLIPBOARD]{CLR_RESET} {C_WHITE}Press Ctrl+V to share on Discord or WhatsApp!{CLR_RESET}")
        else:
            lines_box.append(f"  {C_MUTED}Copy and send your Moon ID ({my_moon_id}) or link to friends!{CLR_RESET}")
        lines_box.append(f"  {C_MUTED}Friends can add you instantly via: /friend add {my_moon_id}{CLR_RESET}")

        print("\n" + render_box(lines_box, box_w, title="Invite Link") + "\n")
        return

    # /friend add <MOON-ID> [address]
    elif sub in ("add", "new", "+"):
        if len(args) < 2:
            clip = get_clipboard_text()
            inv = parse_friend_invite(clip)
            if inv:
                print(f"\n{C_CYAN}Found Friend Invite in Clipboard:{CLR_RESET}")
                print(f"  Player : {C_WHITE}{inv.get('username')}{CLR_RESET}")
                if inv.get('address'):
                    print(f"  Server : {C_GREEN}{inv['address']}{CLR_RESET}")
                try:
                    ans = input(f"\n{C_AMBER}Add this friend to your contacts? [Y/n]: {CLR_RESET}").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
                if ans in ('', 'y', 'yes'):
                    add_friend_from_invite(inv, data)
                    return
                else:
                    print(f"{C_MUTED}Cancelled.{CLR_RESET}\n")
                    return

            print(f"\n{C_RED}Usage: /friend add <MOON-XXXX> [optional_server_ip:port]{CLR_RESET}")
            print(f"{C_MUTED}Example: /friend add MOON-4821{CLR_RESET}\n")
            return

        inv = parse_friend_invite(args[1])
        if inv:
            add_friend_from_invite(inv, data)
            return

        target_input = args[1].strip()
        resolved = resolve_player_by_moon_id(target_input)
        if not resolved:
            clean_id = target_input.upper()
            if not clean_id.startswith("MOON-") and clean_id.isalnum() and len(clean_id) <= 6:
                clean_id = f"MOON-{clean_id}"
            resolved = {"player_id": clean_id, "username": clean_id, "status": "offline"}

        friend_id = resolved.get("player_id")
        friend_uname = resolved.get("username", friend_id)
        addr = args[2].strip() if len(args) > 2 else resolved.get("server_addr", "")

        # Check existing
        all_friends = data.setdefault("friends", [])
        for item in all_friends:
            if isinstance(item, dict) and (item.get("player_id", "").upper() == friend_id.upper() or item.get("username", "").lower() == friend_uname.lower()):
                item["player_id"] = friend_id
                item["username"] = friend_uname
                if addr: item["address"] = addr
                save_network_data(data)
                print(f"\n{C_GREEN}[OK] Updated contact for friend {friend_id} ({friend_uname})!{CLR_RESET}\n")
                return

        all_friends.append({
            "player_id": friend_id,
            "username": friend_uname,
            "address": addr,
            "note": "",
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        save_network_data(data)

        box_w = 68
        lines_box = [
            f"{C_GREEN}\033[1m[OK] Friend Added by Moon ID!\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Moon ID         :{CLR_RESET} {C_AMBER}\033[1m{friend_id}\033[0m",
            f"  {C_WHITE}* Player Name     :{CLR_RESET} {C_CYAN}{friend_uname}{CLR_RESET}",
            f"  {C_WHITE}* Status          :{CLR_RESET} {C_GREEN if resolved.get('status') in ('online', 'playing') else C_MUTED}{resolved.get('status', 'offline').upper()}{CLR_RESET}",
        ]
        if addr:
            lines_box.append(f"  {C_WHITE}* Server Address  :{CLR_RESET} {C_WHITE}{addr}{CLR_RESET}")
        lines_box.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        print("\n" + render_box(lines_box, box_w, title="Friend Added") + "\n")

    # /friend remove <MOON-ID or name>
    elif sub in ("remove", "delete", "rm", "-"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /friend remove <MOON-XXXX or username>{CLR_RESET}\n")
            return
        target = args[1].strip().lower()
        new_friends = [
            f for f in data.get("friends", [])
            if (isinstance(f, dict) and f.get("player_id", "").lower() != target and f.get("username", "").lower() != target)
            or (isinstance(f, str) and f.lower() != target)
        ]
        if len(new_friends) == len(data.get("friends", [])):
            print(f"\n{C_AMBER}Friend '{args[1]}' not found in contact list.{CLR_RESET}\n")
        else:
            data["friends"] = new_friends
            save_network_data(data)
            print(f"\n{C_GREEN}[OK] Removed '{args[1]}' from your friends list.{CLR_RESET}\n")

    # /friend join <name or ID>
    elif sub in ("join", "connect", "play"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /friend join <MOON-ID or username>{CLR_RESET}\n")
            return
        target_name = args[1].strip()
        peer_meta = None
        with CLOUD_PEERS_LOCK:
            peer_meta = CLOUD_PEERS.get(target_name.lower())
        if not peer_meta:
            with LAN_PEERS_LOCK:
                peer_meta = next((p for uname, p in LAN_PEERS.items() if uname.lower() == target_name.lower()), None)
        if not peer_meta:
            peer_meta = resolve_player_by_moon_id(target_name)

        if not peer_meta or not peer_meta.get("server_addr"):
            print(f"\n{C_AMBER}Friend '{target_name}' is not currently hosting an accessible world tunnel.{CLR_RESET}\n")
            return

        target_srv = peer_meta["server_addr"]
        print(f"\n{C_GREEN}[Connecting] Joining {target_name}'s game at {target_srv}...{CLR_RESET}\n")
        import launcher
        cfg = launcher.load_config()
        launcher.launch_minecraft(active_version_dir, cfg, direct_server=target_srv)


def get_or_create_moon_id(username=None):
    """
    Retrieves or generates a persistent, unique Moon ID for the player (e.g. MOON-4821).
    Stores it in launcher_config.json so it remains static across sessions.
    """
    config_path = os.path.join(BASE_DIR, "launcher_config.json")
    cfg = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    existing_id = cfg.get("moon_id") or cfg.get("player_id")
    if existing_id and str(existing_id).upper().startswith("MOON-"):
        return str(existing_id).upper()

    u_name = username or cfg.get("username") or "Player"
    code = abs(hash(u_name)) % 9000 + 1000
    new_id = f"MOON-{code}"
    cfg["moon_id"] = new_id
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
    return new_id


def resolve_player_by_moon_id(moon_id_or_input):
    """
    Looks up player information by MOON-XXXX ID (or username fallback)
    from Supabase presence & players tables and local peers.
    Returns dict: {'player_id': ..., 'username': ..., 'status': ..., 'version_name': ..., 'server_addr': ...}
    """
    raw = str(moon_id_or_input).strip()
    if not raw:
        return None

    clean_id = raw.upper()
    if not clean_id.startswith("MOON-") and clean_id.isalnum() and len(clean_id) <= 6:
        clean_id = f"MOON-{clean_id}"

    # 1. Query Supabase
    sb_url, sb_key = get_supabase_config()
    if sb_url and sb_key:
        try:
            # Query presence table by player_id
            endpoint = f"presence?player_id=eq.{urllib.parse.quote(clean_id)}"
            res = supabase_api_request(endpoint, method="GET")
            if isinstance(res, list) and res:
                item = res[0]
                return {
                    "player_id": item.get("player_id", clean_id),
                    "username": item.get("username", clean_id),
                    "status": item.get("status", "online"),
                    "version_name": item.get("version_name", ""),
                    "server_addr": item.get("server_addr", "")
                }

            # Query players table by player_id
            p_res = supabase_api_request(f"players?player_id=eq.{urllib.parse.quote(clean_id)}", method="GET")
            if isinstance(p_res, list) and p_res:
                p_item = p_res[0]
                return {
                    "player_id": p_item.get("player_id", clean_id),
                    "username": p_item.get("username", clean_id),
                    "status": "offline",
                    "skin_url": p_item.get("skin_url", "")
                }

            # If user typed username, check presence & players by username
            u_res = supabase_api_request(f"presence?username=ilike.{urllib.parse.quote(raw)}", method="GET")
            if isinstance(u_res, list) and u_res:
                u_item = u_res[0]
                return {
                    "player_id": u_item.get("player_id", f"MOON-{abs(hash(raw)) % 9000 + 1000}"),
                    "username": u_item.get("username", raw),
                    "status": u_item.get("status", "online"),
                    "version_name": u_item.get("version_name", ""),
                    "server_addr": u_item.get("server_addr", "")
                }
            p_u_res = supabase_api_request(f"players?username=ilike.{urllib.parse.quote(raw)}", method="GET")
            if isinstance(p_u_res, list) and p_u_res:
                pu_item = p_u_res[0]
                return {
                    "player_id": pu_item.get("player_id", f"MOON-{abs(hash(raw)) % 9000 + 1000}"),
                    "username": pu_item.get("username", raw),
                    "status": "offline",
                    "skin_url": pu_item.get("skin_url", "")
                }
        except Exception:
            pass

    # 2. Local peers cache
    with CLOUD_PEERS_LOCK:
        for uname, p in CLOUD_PEERS.items():
            if (p.get("player_id") and p.get("player_id").upper() == clean_id) or uname.lower() == raw.lower():
                return {
                    "player_id": p.get("player_id", clean_id),
                    "username": p.get("username", uname),
                    "status": p.get("status", "online"),
                    "version_name": p.get("version_name", ""),
                    "server_addr": p.get("server_addr", "")
                }

    # 3. Fallback when offline
    if clean_id.startswith("MOON-"):
        return {
            "player_id": clean_id,
            "username": clean_id,
            "status": "offline"
        }
    return None


# ==============================================================================
# SUPABASE CLOUD PRESENCE & MATCHMAKING ENGINE
# ==============================================================================

def get_supabase_config():
    """Retrieves configured Supabase URL and Anon Key from launcher config or environment."""
    url = os.environ.get("MOON_SUPABASE_URL", "")
    key = os.environ.get("MOON_SUPABASE_KEY", "")
    
    if not url or not key:
        try:
            cfg_path = os.path.join(BASE_DIR, "launcher_config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                    d = json.load(f)
                    url = url or d.get("supabase_url", "")
                    key = key or d.get("supabase_key", "")
        except Exception:
            pass
            
    DEFAULT_URL = "https://fcozsefkufbvztgniuwk.supabase.co"
    DEFAULT_KEY = "sb_publishable_4NvjQ6A6TS9fBAFQpjWyaA_WjgP8BuZ"
    if not url:
        url = DEFAULT_URL
    if not key:
        key = DEFAULT_KEY
            
    return url.strip().rstrip('/'), key.strip()

def set_supabase_config(url, key):
    """Saves Supabase credentials into launcher_config.json."""
    try:
        cfg_path = os.path.join(BASE_DIR, "launcher_config.json")
        cfg = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        cfg["supabase_url"] = str(url).strip().rstrip('/')
        cfg["supabase_key"] = str(key).strip()
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception:
        return False

def supabase_api_request(endpoint, method="GET", payload=None, extra_headers=None):
    """Executes a HTTPS REST request against Supabase PostgREST API."""
    sb_url, sb_key = get_supabase_config()
    if not sb_url or not sb_key:
        return None
        
    target = f"{sb_url}/rest/v1/{endpoint}"
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "User-Agent": "Moon-Launcher-Cloud/1.0"
    }
    if extra_headers:
        headers.update(extra_headers)
        
    req = urllib.request.Request(target, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            raw = resp.read().decode('utf-8')
            return json.loads(raw) if raw.strip() else {}
    except Exception:
        return None

def cloud_update_presence(username=None):
    """Pushes active player presence, modpack, and server address to Supabase cloud."""
    sb_url, sb_key = get_supabase_config()
    if not sb_url or not sb_key:
        return False
        
    u_name = username or LAN_ACTIVE_USER or "Player"
    v_dir = LAN_ACTIVE_VERSION_DIR
    m = get_active_modpack_manifest(v_dir) if (v_dir and "get_active_modpack_manifest" in globals()) else None
    v_name = m["version_name"] if m else (LAN_ACTIVE_VERSION_NAME or "Vanilla 1.20.1")
    mc_ver = m["mc_version"] if m else "1.20.1"
    loader = m["loader"] if m else "Forge"
    m_cnt = m["mod_count"] if m else 0
    
    t_status = get_tunnel_status()
    pub_addr = t_status.get("public_address") if t_status.get("running") else ""
    is_hosting = bool(pub_addr)
    status_str = "hosting" if is_hosting else "online"
    
    player_id = get_or_create_moon_id(u_name)
    
    # 1. Upsert public.players
    payload_p = {
        "player_id": player_id,
        "username": u_name,
        "tag": u_name[:3].upper() + "-" + player_id.replace("MOON-", ""),
        "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    supabase_api_request("players", method="POST", payload=payload_p, extra_headers={"Prefer": "resolution=merge-duplicates"})

    # Clean up any stale presence records with the same player_id but previous username
    try:
        supabase_api_request(f'presence?player_id=eq.{player_id}&username=neq.{u_name}', method='DELETE')
    except Exception:
        pass

    # 2. Upsert public.presence
    payload_sb = {
        "username": u_name,
        "player_id": player_id,
        "status": status_str,
        "version_name": v_name,
        "mc_version": mc_ver,
        "loader": loader,
        "mod_count": m_cnt,
        "server_addr": pub_addr or "",
        "tunnel_active": is_hosting,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    res = supabase_api_request("presence", method="POST", payload=payload_sb, extra_headers={"Prefer": "resolution=merge-duplicates"})
    return res is not None

def cloud_get_friends_presence(usernames_or_ids):
    """Fetches real-time status of given usernames or Moon IDs from Supabase presence table."""
    if not usernames_or_ids:
        return {}
    sb_url, sb_key = get_supabase_config()
    if not sb_url or not sb_key:
        return {}
        
    names_quoted = ",".join(f'"{u}"' for u in usernames_or_ids)
    endpoint = f"presence?or=(username.in.({urllib.parse.quote(names_quoted)}),player_id.in.({urllib.parse.quote(names_quoted)}))"
    res = supabase_api_request(endpoint, method="GET")
    
    if isinstance(res, list):
        now = time.time()
        mapping = {}
        with CLOUD_PEERS_LOCK:
            for item in res:
                uname = item.get("username")
                p_id = item.get("player_id")
                info = {
                    "player_id": p_id,
                    "username": uname,
                    "status": item.get("status", "online"),
                    "version_name": item.get("version_name", ""),
                    "mc_version": item.get("mc_version", ""),
                    "loader": item.get("loader", ""),
                    "mod_count": item.get("mod_count", 0),
                    "server_addr": item.get("server_addr", ""),
                    "last_seen": now
                }
                if uname:
                    CLOUD_PEERS[uname.lower()] = info
                    mapping[uname.lower()] = info
                if p_id:
                    CLOUD_PEERS[p_id.lower()] = info
                    mapping[p_id.lower()] = info
        return mapping
    return {}

def _cloud_presence_loop():
    """Background loop that periodically refreshes player presence and friends status."""
    global CLOUD_SYNC_RUNNING
    while CLOUD_SYNC_RUNNING:
        try:
            cloud_update_presence()
            d = load_network_data()
            f_ids = [f.get("player_id") or f.get("username") for f in d.get("friends", []) if isinstance(f, dict)]
            if f_ids:
                cloud_get_friends_presence(f_ids)
        except Exception:
            pass
        time.sleep(25.0)

def start_cloud_presence_service(username=None):
    """Starts the background Supabase cloud presence service."""
    global CLOUD_SYNC_RUNNING
    sb_url, sb_key = get_supabase_config()
    if not sb_url or not sb_key:
        return False
        
    if CLOUD_SYNC_RUNNING:
        return True
        
    CLOUD_SYNC_RUNNING = True
    t = threading.Thread(target=_cloud_presence_loop, daemon=True, name="MoonCloudPresence")
    t.start()
    return True

def handle_cloud_command(args=None):
    """CLI handler for /cloud commands to configure or check Supabase cloud status."""
    box_w = 68
    url, key = get_supabase_config()
    sub = args[0].lower() if args else "status"

    if sub in ("setup", "config", "set"):
        print(f"\n{C_WHITE}\033[1mMoon Launcher Cloud Setup (Supabase)\033[0m")
        print(f"{C_MUTED}Enter your Supabase Project URL and Anon Public Key from supabase.com:{CLR_RESET}\n")
        try:
            new_url = input(f"{C_CYAN}Supabase Project URL (e.g. https://xyz.supabase.co): {CLR_RESET}").strip()
            new_key = input(f"{C_CYAN}Supabase Anon Public Key (eyJh...): {CLR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if new_url and new_key:
            if set_supabase_config(new_url, new_key):
                start_cloud_presence_service()
                print(f"\n{C_GREEN}[OK] Supabase Cloud configured successfully!{CLR_RESET}\n")
            else:
                print(f"\n{C_RED}[Error] Failed to save cloud configuration.{CLR_RESET}\n")
        else:
            print(f"\n{C_AMBER}Setup cancelled. Both URL and Key are required.{CLR_RESET}\n")
        return

    # Status
    lines = [
        f"{C_WHITE}\033[1mMoon Cloud Presence & Global Friends Status\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
    ]
    if url and key:
        masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        lines.append(f"  {C_WHITE}* Cloud Service  :{CLR_RESET} {C_GREEN}CONNECTED (Supabase REST & Realtime){CLR_RESET}")
        lines.append(f"  {C_WHITE}* Project URL    :{CLR_RESET} {C_CYAN}{url}{CLR_RESET}")
        lines.append(f"  {C_WHITE}* API Key        :{CLR_RESET} {C_MUTED}{masked_key}{CLR_RESET}")
        with CLOUD_PEERS_LOCK:
            online_cnt = len(CLOUD_PEERS)
        lines.append(f"  {C_WHITE}* Global Peers   :{CLR_RESET} {C_GREEN}{online_cnt} players tracked online{CLR_RESET}")
        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines.append(f"{C_MUTED}Commands: /cloud setup (Reconfigure) • /friend list (View Friends){CLR_RESET}")
    else:
        lines.append(f"  {C_WHITE}* Cloud Service  :{CLR_RESET} {C_AMBER}NOT CONFIGURED (Running local LAN mode){CLR_RESET}")
        lines.append(f"  {C_WHITE}* Description    :{CLR_RESET} {C_MUTED}Connect to Supabase to enable global friends & mabar without Radmin!{CLR_RESET}")
        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines.append(f"{C_CYAN}To connect your free Supabase database:{CLR_RESET}")
        lines.append(f"  Type: {C_GREEN}/cloud setup{CLR_RESET}")

    print("\n" + render_box(lines, box_w, title="Cloud Hub") + "\n")

def handle_host_command(args, active_version_dir=None):
    """
    Handles /host commands:
    - /host (or /host status)
    - /host start [port]
    - /host stop
    - /host scan
    """
    sub = args[0].lower() if args else "status"

    if sub in ("status", "info"):
        st = get_tunnel_status()
        box_w = 68
        lines = [
            f"{C_WHITE}\033[1mInternet Multiplayer Host & Tunnel Status\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        if st["running"]:
            lines.append(f"  {C_GREEN}* State         : TUNNEL ACTIVE (Online){CLR_RESET}")
            lines.append(f"  {C_WHITE}* Local Port    : {st['local_port']}{CLR_RESET}")
            if st["public_address"]:
                lines.append(f"  {C_CYAN}\033[1m* Public Address: {st['public_address']}\033[0m")
            elif st["claim_url"]:
                lines.append(f"  {C_AMBER}* Setup Link    : {st['claim_url']}{CLR_RESET}")
                lines.append(f"  {C_MUTED}  (Open link once in browser to register free tunnel){CLR_RESET}")
            else:
                lines.append(f"  {C_AMBER}* Public Address: Negotiating Anycast Route...{CLR_RESET}")
            lines.append(f"  {C_MUTED}* Uptime        : {st['uptime_seconds']} seconds{CLR_RESET}")
            lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
            lines.append(f"{C_MUTED}Share public address with friends to let them join without Radmin!{CLR_RESET}")
            lines.append(f"{C_MUTED}To stop hosting: /host stop{CLR_RESET}")
        else:
            auto_p = detect_active_minecraft_port(active_version_dir)
            lines.append(f"  {C_MUTED}* State         : Idle (Tunnel Not Running){CLR_RESET}")
            lines.append(f"  {C_WHITE}* Detected Port : {auto_p}{CLR_RESET}")
            lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
            lines.append(f"{C_CYAN}To host game for friends over Internet (No Radmin needed):{CLR_RESET}")
            lines.append(f"  1. In Minecraft, press ESC -> Open to LAN")
            lines.append(f"  2. In Moon Launcher, type: {C_GREEN}/host start{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Host Engine") + "\n")

    elif sub in ("start", "up", "on", "enable"):
        port = int(args[1]) if len(args) > 1 and args[1].isdigit() else detect_active_minecraft_port(active_version_dir)
        print(f"\n{C_CYAN}[Moon Launcher] Activating Global Internet Tunnel for port {port}...{CLR_RESET}")
        ok, pub_addr, claim_url = start_internet_tunnel(port)
        box_w = 68
        if ok:
            lines = [
                f"{C_GREEN}[PASS] Global Internet Tunnel Activated!{CLR_RESET}",
                f"{C_WHITE}Local Port      :{CLR_RESET} {port}",
                f"{C_WHITE}Network Mode    :{CLR_RESET} Anycast Cloud Relay (No Radmin / No Port Forward)"
            ]
            if pub_addr:
                lines.append(f"{C_CYAN}\033[1mPublic Address  : {pub_addr}\033[0m")
                lines.append("")
                lines.append(f"{C_MUTED}Friends can paste this address into standard Minecraft Multiplayer!{CLR_RESET}")
            elif claim_url:
                lines.append(f"{C_AMBER}Claim / Setup   :{CLR_RESET} {claim_url}")
                lines.append(f"{C_MUTED}Open link in browser to claim your tunnel. Address activates automatically!{CLR_RESET}")
            else:
                lines.append(f"{C_MUTED}Tunnel initialized. Run {C_WHITE}/host status{C_MUTED} to view connect domain.{CLR_RESET}")
            lines.append(f"{C_MUTED}To stop tunnel at any time, type: {C_WHITE}/host stop{CLR_RESET}")
            print("\n" + render_box(lines, box_w, title="Tunnel Online") + "\n")
        else:
            print(f"\n{C_RED}[FAIL] Could not start tunnel: {pub_addr}{CLR_RESET}\n")

    elif sub in ("stop", "down", "off", "disable", "kill"):
        stop_internet_tunnel()
        print(f"\n{C_GREEN}[Moon Launcher] Host tunnel stopped. Local port closed.{CLR_RESET}\n")

    elif sub in ("scan", "discover", "lan"):
        print(f"\n{C_CYAN}[Moon Launcher] Scanning local network and virtual LAN for open Minecraft worlds...{CLR_RESET}")
        found = scan_lan_worlds(timeout=2.0)
        box_w = 68
        lines = [
            f"{C_WHITE}\033[1mLocal Network & LAN Discovery\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        if not found:
            lines.append(f"{C_MUTED}No active LAN broadcasts found in the last 2 seconds.{CLR_RESET}")
            lines.append(f"{C_MUTED}Make sure host pressed 'Open to LAN' in game.{CLR_RESET}")
        else:
            for item in found:
                addr_str = f"{item['host_ip']}:{item['port']}"
                lines.append(f"  {C_GREEN}* Found:{CLR_RESET} {C_WHITE}{item['world']}{CLR_RESET}")
                lines.append(f"    {C_CYAN}Address:{CLR_RESET} {addr_str}")
                lines.append(f"    {C_MUTED}Add to contacts: /friend add <name> {addr_str}{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="LAN Discovery") + "\n")

    else:
        print(f"\n{C_RED}Unknown host command. Available: status, start [port], stop, scan{CLR_RESET}\n")

# ==============================================================================
# COMMAND HANDLER: /server
# ==============================================================================

def handle_server_command(args):
    """
    Handles /server commands:
    - /server (or /server list)
    - /server add <name> <ip:port>
    - /server remove <name>
    - /server ping <ip:port>
    """
    data = load_network_data()
    servers = data.get("servers", [])

    if not args or args[0].lower() in ("list", "ls", "show"):
        box_w = 68
        lines = [
            f"{C_WHITE}\033[1mFavorite Multiplayer Servers\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        if not servers:
            lines.append(f"{C_MUTED}No servers saved.{CLR_RESET}")
            lines.append(f"{C_MUTED}Save servers via: /server add <label> <ip:port>{CLR_RESET}")
        else:
            for item in servers:
                s_name = item.get("name", "Server")
                s_addr = item.get("address", "")
                p_res = ping_minecraft_server(s_addr, timeout=1.5)
                if p_res["online"]:
                    st = f"{C_GREEN}[ONLINE]{CLR_RESET}"
                    det = f"{C_GREEN}{p_res['latency']}ms{CLR_RESET} • {p_res['players_online']} players"
                else:
                    st = f"{C_RED}[IDLE]{CLR_RESET}"
                    det = f"{C_MUTED}Unreachable{CLR_RESET}"

                lines.append(f"  {st} {C_CYAN}{s_name:<20}{CLR_RESET} {det}")
                lines.append(f"     {C_WHITE}Address:{CLR_RESET} {s_addr}")

        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines.append(f"{C_MUTED}Commands: /server add <name> <ip> • /server ping <ip> • /server remove <name>{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Server Browser") + "\n")
        return

    sub = args[0].lower()

    if sub in ("add", "new", "+"):
        if len(args) < 3:
            print(f"\n{C_RED}Usage: /server add <label> <ip:port>{CLR_RESET}\n")
            return
        label = args[1].strip()
        addr = args[2].strip()
        servers.append({"name": label, "address": addr})
        data["servers"] = servers
        save_network_data(data)
        print(f"\n{C_GREEN}[OK] Saved server '{label}' ({addr}) to favorites!{CLR_RESET}\n")

    elif sub in ("remove", "delete", "rm", "-"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /server remove <label>{CLR_RESET}\n")
            return
        label = args[1].lower()
        new_s = [s for s in servers if s.get("name", "").lower() != label and s.get("address", "").lower() != label]
        if len(new_s) == len(servers):
            print(f"\n{C_AMBER}Server '{args[1]}' not found in list.{CLR_RESET}\n")
        else:
            data["servers"] = new_s
            save_network_data(data)
            print(f"\n{C_GREEN}[OK] Removed '{args[1]}' from servers list.{CLR_RESET}\n")

    elif sub in ("ping", "check"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /server ping <ip:port>{CLR_RESET}\n")
            return
        addr = args[1].strip()
        print(f"\n{C_CYAN}Querying Minecraft server {addr}...{CLR_RESET}")
        p_res = ping_minecraft_server(addr, timeout=3.0)
        box_w = 66
        if p_res["online"]:
            lines = [
                f"{C_GREEN}[PASS] Server is ONLINE!{CLR_RESET}",
                f"{C_WHITE}Address     :{CLR_RESET} {addr}",
                f"{C_WHITE}Latency     :{CLR_RESET} {p_res['latency']} ms",
                f"{C_WHITE}Players     :{CLR_RESET} {p_res['players_online']} / {p_res['players_max']}",
                f"{C_WHITE}Version     :{CLR_RESET} {p_res['version']}",
                f"{C_WHITE}MOTD        :{CLR_RESET} {p_res['motd']}"
            ]
        else:
            lines = [
                f"{C_RED}[FAIL] Server is OFFLINE or Unreachable{CLR_RESET}",
                f"{C_WHITE}Address     :{CLR_RESET} {addr}",
                f"{C_MUTED}Reason: {p_res['motd']}{CLR_RESET}"
            ]
        print("\n" + render_box(lines, box_w, title="Server Query") + "\n")
    else:
        print(f"\n{C_RED}Unknown server command. Available: list, add, remove, ping{CLR_RESET}\n")


# ==============================================================================
# NATIVE ZERO-CONFIG LAN & RADMIN P2P SKIN AUTO-SYNC ENGINE
# ==============================================================================

import hashlib
import shutil

LAN_SYNC_UDP_PORT = 25564
LAN_SYNC_TCP_BASE = 25564
LAN_SYNC_RUNNING = False
LAN_TCP_PORT = None
LAN_TCP_SOCKET = None
LAN_UDP_SOCKET = None
LAN_ACTIVE_USER = None
LAN_ACTIVE_VERSION_DIR = None
LAN_PEERS_LOCK = threading.Lock()
LAN_PEERS = {}  # {username: {'ip': str, 'port': int, 'hash': str, 'last_seen': float, 'synced': bool}}
LAN_TRIGGER_EVENT = threading.Event()
CLOUD_PEERS_LOCK = threading.Lock()
CLOUD_PEERS = {}  # {username: {'status': str, 'version_name': str, 'server_addr': str, 'last_seen': float}}
CLOUD_SYNC_RUNNING = False

def get_broadcast_targets():
    """Detects local broadcast targets across WiFi, Ethernet, and virtual LANs (Radmin VPN, Tailscale, ZeroTier)."""
    targets = {'255.255.255.255'}
    try:
        out = subprocess.check_output('ipconfig', text=True, encoding='cp437', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        ips = re.findall(r'IPv4 Address[^\:]*:\s*([0-9\.]+)', out)
        for ip in ips:
            parts = ip.split('.')
            if len(parts) == 4:
                targets.add(f"{parts[0]}.{parts[1]}.{parts[2]}.255")
                if parts[0] == '26':
                    targets.add("26.255.255.255")
                    targets.add(f"26.{parts[1]}.{parts[2]}.255")
    except Exception:
        pass
    return list(targets)

def get_local_skin_payload(username=None):
    """Retrieves the local skin binary and MD5 hash for the given username."""
    u = username or LAN_ACTIVE_USER
    if not u:
        return None, ""
    skins_dir = os.path.join(BASE_DIR, "skins")
    skin_file = os.path.join(skins_dir, f"{u}.png")
    if os.path.exists(skin_file) and os.path.getsize(skin_file) > 50:
        try:
            with open(skin_file, "rb") as f:
                data = f.read()
            if data.startswith(b'\x89PNG'):
                return data, hashlib.md5(data).hexdigest()
        except Exception:
            pass
    return None, ""

def distribute_peer_skin(peer_username, skin_bytes, version_dir=None):
    """Saves a peer's skin and distributes it to all CustomSkinLoader folders."""
    if not peer_username or not skin_bytes or not skin_bytes.startswith(b'\x89PNG'):
        return False
    try:
        skins_dir = os.path.join(BASE_DIR, "skins")
        os.makedirs(skins_dir, exist_ok=True)
        master_dest = os.path.join(skins_dir, f"{peer_username}.png")
        with open(master_dest, "wb") as f:
            f.write(skin_bytes)

        target_dirs = []
        v_dir = version_dir or LAN_ACTIVE_VERSION_DIR
        if v_dir and os.path.exists(v_dir):
            target_dirs.extend([
                os.path.join(v_dir, "CustomSkinLoader", "LocalSkin", "skins"),
                os.path.join(v_dir, "LocalSkin", "skins"),
                os.path.join(v_dir, "skins")
            ])

        versions_root = os.path.join(BASE_DIR, "versions")
        if os.path.exists(versions_root):
            for v_name in os.listdir(versions_root):
                v_path = os.path.join(versions_root, v_name)
                if os.path.isdir(v_path):
                    target_dirs.append(os.path.join(v_path, "CustomSkinLoader", "LocalSkin", "skins"))
                    target_dirs.append(os.path.join(v_path, "LocalSkin", "skins"))

        appdata_mc = os.path.expandvars(r"%APPDATA%\.minecraft")
        target_dirs.append(os.path.join(appdata_mc, "CustomSkinLoader", "LocalSkin", "skins"))
        target_dirs.append(os.path.join(appdata_mc, "LocalSkin", "skins"))

        for t in target_dirs:
            try:
                os.makedirs(t, exist_ok=True)
                dest = os.path.join(t, f"{peer_username}.png")
                shutil.copyfile(master_dest, dest)
            except Exception:
                pass
        return True
    except Exception:
        return False


def get_active_modpack_manifest(v_dir=None):
    """Scans and generates a file manifest of the active modpack (mods and configs)."""
    target = v_dir or LAN_ACTIVE_VERSION_DIR
    if not target or not os.path.exists(target):
        return None
    v_name = os.path.basename(target)
    mods_dir = os.path.join(target, "mods")
    config_dir = os.path.join(target, "config")
    
    files = []
    total_size = 0
    if os.path.exists(mods_dir):
        for f in sorted(os.listdir(mods_dir)):
            if f.endswith('.jar'):
                fp = os.path.join(mods_dir, f)
                sz = os.path.getsize(fp)
                files.append({"path": f"mods/{f}", "size": sz})
                total_size += sz

    if os.path.exists(config_dir):
        for root, dirs, f_list in os.walk(config_dir):
            for f in f_list:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, target).replace("\\", "/")
                sz = os.path.getsize(fp)
                files.append({"path": rel, "size": sz})
                total_size += sz

    mc_ver = "1.20.1"
    loader = "Forge"
    cfg_file = os.path.join(target, "launcher_config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as cf:
                d = json.load(cf)
                mc_ver = d.get("mc_version", mc_ver)
                loader = d.get("loader", loader)
        except Exception:
            pass

    return {
        "version_name": v_name,
        "mc_version": mc_ver,
        "loader": loader,
        "mod_count": len([i for i in files if i["path"].startswith("mods/")]),
        "total_files": len(files),
        "total_size": total_size,
        "files": files
    }

def sync_modpack_from_peer(peer_ip, peer_port, versions_root=None):
    """
    Connects to peer P2P server, requests active modpack manifest,
    and selectively downloads missing/updated mods and configs with a live progress bar.
    """
    v_root = versions_root or os.path.join(BASE_DIR, "versions")
    base_url = f"http://{peer_ip}:{peer_port}"
    
    try:
        req = urllib.request.Request(f"{base_url}/modpack/manifest", headers={"User-Agent": "Moon-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"\n{C_RED}[Moon P2P] Could not reach friend's launcher on {base_url}: {e}{CLR_RESET}\n")
        return None
        
    v_name = manifest.get("version_name")
    if not v_name:
        return None
        
    target_v_dir = os.path.join(v_root, v_name)
    os.makedirs(target_v_dir, exist_ok=True)
    
    files = manifest.get("files", [])
    to_download = []
    download_bytes = 0
    for item in files:
        rel = item["path"]
        sz = item["size"]
        dest = os.path.join(target_v_dir, rel.replace("/", os.sep))
        if not os.path.exists(dest) or os.path.getsize(dest) != sz:
            to_download.append((rel, sz, dest))
            download_bytes += sz
            
    print(f"\n{C_CYAN}[Moon P2P] Syncing custom modpack '{v_name}' ({len(to_download)} files to download, {download_bytes / (1024*1024):.1f} MB)...{CLR_RESET}")
    
    transferred = 0
    t0 = time.time()
    for idx, (rel, sz, dest) in enumerate(to_download, 1):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        f_url = f"{base_url}/modpack/file?path={urllib.parse.quote(rel)}"
        req = urllib.request.Request(f_url, headers={"User-Agent": "Moon-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            with open(dest, "wb") as f_out:
                while chunk := resp.read(65536):
                    f_out.write(chunk)
                    transferred += len(chunk)
                    
        pct = min(100, int((transferred / max(1, download_bytes)) * 100))
        speed = (transferred / max(0.1, time.time() - t0)) / (1024 * 1024)
        bar_len = 24
        filled = int(bar_len * (pct / 100))
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{C_GREEN}{bar}{CLR_RESET}] {pct}% ({transferred / (1024*1024):.1f}/{download_bytes / (1024*1024):.1f} MB, {speed:.1f} MB/s) {os.path.basename(rel)[:24]:<24}", end="", flush=True)
        
    print(f"\n{C_GREEN}[Moon P2P] Modpack '{v_name}' successfully synchronized!{CLR_RESET}\n")
    return target_v_dir

def _lan_tcp_server_loop():
    """Lightweight HTTP server serving local player skin to requesting peers."""
    global LAN_TCP_SOCKET, LAN_TCP_PORT, LAN_SYNC_RUNNING
    while LAN_SYNC_RUNNING and LAN_TCP_SOCKET:
        try:
            conn, addr = LAN_TCP_SOCKET.accept()
            req = conn.recv(1024).decode('utf-8', errors='ignore')
            lines = req.splitlines()
            if lines and lines[0].startswith("GET"):
                path = lines[0].split()[1] if len(lines[0].split()) > 1 else ""
                target_user = LAN_ACTIVE_USER
                if path.startswith("/skin/"):
                    req_u = path.split("/skin/")[1].strip()
                    if req_u and req_u != "raw":
                        target_user = req_u.replace(".png", "")
                
                skin_data, _ = get_local_skin_payload(target_user)
                if skin_data:
                    resp = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: image/png\r\n"
                        b"Content-Length: " + str(len(skin_data)).encode() + b"\r\n"
                        b"Connection: close\r\n\r\n" + skin_data
                    )
                    conn.sendall(resp)
                else:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
            conn.close()
        except Exception:
            if not LAN_SYNC_RUNNING:
                break

def _lan_udp_loop():
    """Listens for peer beacons on LAN/Radmin and sends periodic discovery broadcasts."""
    global LAN_UDP_SOCKET, LAN_SYNC_RUNNING, LAN_ACTIVE_USER, LAN_TCP_PORT
    last_broadcast = 0
    broadcast_interval = 8.0

    while LAN_SYNC_RUNNING and LAN_UDP_SOCKET:
        now = time.time()
        if now - last_broadcast >= broadcast_interval or LAN_TRIGGER_EVENT.is_set():
            LAN_TRIGGER_EVENT.clear()
            last_broadcast = now
            _, my_hash = get_local_skin_payload(LAN_ACTIVE_USER)
            if LAN_ACTIVE_USER and LAN_TCP_PORT:
                payload = json.dumps({
                    "magic": "MOON_SKIN_V1",
                    "user": LAN_ACTIVE_USER,
                    "hash": my_hash or "",
                    "port": LAN_TCP_PORT
                }).encode('utf-8')
                for b_target in get_broadcast_targets():
                    try:
                        LAN_UDP_SOCKET.sendto(payload, (b_target, LAN_SYNC_UDP_PORT))
                    except Exception:
                        pass

        try:
            data, (remote_ip, remote_port) = LAN_UDP_SOCKET.recvfrom(4096)
            msg = json.loads(data.decode('utf-8'))
            if msg.get("magic") == "MOON_SKIN_V1":
                peer_user = str(msg.get("user", "")).strip()
                peer_hash = str(msg.get("hash", "")).strip()
                peer_tcp = int(msg.get("port", 0))

                if peer_user and LAN_ACTIVE_USER and peer_user.lower() != LAN_ACTIVE_USER.lower() and peer_tcp > 0:
                    with LAN_PEERS_LOCK:
                        peer_info = LAN_PEERS.setdefault(peer_user, {
                            "ip": remote_ip,
                            "port": peer_tcp,
                            "hash": peer_hash,
                            "last_seen": now,
                            "synced": False
                        })
                        peer_info["ip"] = remote_ip
                        peer_info["port"] = peer_tcp
                        peer_info["last_seen"] = now

                    _, local_hash = get_local_skin_payload(peer_user)
                    if peer_hash and (local_hash != peer_hash):
                        try:
                            ip_call = "127.0.0.1" if remote_ip in ("127.0.0.1", "0.0.0.0") else remote_ip
                            url = f"http://{ip_call}:{peer_tcp}/skin/raw"
                            req = urllib.request.Request(url, headers={'User-Agent': 'MoonLauncher-P2P/1.0'})
                            with urllib.request.urlopen(req, timeout=3.5) as resp:
                                skin_bytes = resp.read()
                            
                            if skin_bytes.startswith(b'\x89PNG'):
                                if distribute_peer_skin(peer_user, skin_bytes, LAN_ACTIVE_VERSION_DIR):
                                    with LAN_PEERS_LOCK:
                                        LAN_PEERS[peer_user]["hash"] = peer_hash
                                        LAN_PEERS[peer_user]["synced"] = True
                                    print(f"\n{C_GREEN}[Moon LAN] Auto-synced custom skin for '{peer_user}' ({remote_ip})!{CLR_RESET}\n", end="", flush=True)

                                    _, my_hash = get_local_skin_payload(LAN_ACTIVE_USER)
                                    reply_payload = json.dumps({
                                        "magic": "MOON_SKIN_V1",
                                        "user": LAN_ACTIVE_USER,
                                        "hash": my_hash or "",
                                        "port": LAN_TCP_PORT
                                    }).encode('utf-8')
                                    LAN_UDP_SOCKET.sendto(reply_payload, (remote_ip, LAN_SYNC_UDP_PORT))
                        except Exception:
                            pass
        except socket.timeout:
            continue
        except Exception:
            if not LAN_SYNC_RUNNING:
                break

def start_lan_skin_service(username=None, version_dir=None):
    """Starts the native LAN & Radmin P2P Skin Auto-Sync service in background."""
    global LAN_SYNC_RUNNING, LAN_TCP_SOCKET, LAN_TCP_PORT, LAN_UDP_SOCKET
    global LAN_ACTIVE_USER, LAN_ACTIVE_VERSION_DIR

    if LAN_SYNC_RUNNING:
        update_lan_skin_identity(username, version_dir)
        return

    LAN_ACTIVE_USER = username or "Player"
    LAN_ACTIVE_VERSION_DIR = version_dir
    LAN_SYNC_RUNNING = True

    LAN_TCP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    LAN_TCP_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    LAN_TCP_PORT = None
    for p in range(LAN_SYNC_TCP_BASE, LAN_SYNC_TCP_BASE + 20):
        try:
            LAN_TCP_SOCKET.bind(('0.0.0.0', p))
            LAN_TCP_PORT = p
            LAN_TCP_SOCKET.listen(10)
            break
        except Exception:
            continue

    if not LAN_TCP_PORT:
        LAN_SYNC_RUNNING = False
        return

    try:
        LAN_UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        LAN_UDP_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        LAN_UDP_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        LAN_UDP_SOCKET.bind(('0.0.0.0', LAN_SYNC_UDP_PORT))
        LAN_UDP_SOCKET.settimeout(0.5)
    except Exception:
        LAN_SYNC_RUNNING = False
        try: LAN_TCP_SOCKET.close()
        except Exception: pass
        return

    t_tcp = threading.Thread(target=_lan_tcp_server_loop, daemon=True, name="MoonLanTCP")
    t_udp = threading.Thread(target=_lan_udp_loop, daemon=True, name="MoonLanUDP")
    t_tcp.start()
    t_udp.start()
    LAN_TRIGGER_EVENT.set()

def update_lan_skin_identity(username=None, version_dir=None, version_name=None):
    """Updates the active user identity and profile version."""
    global LAN_ACTIVE_USER, LAN_ACTIVE_VERSION_DIR, LAN_ACTIVE_VERSION_NAME
    if username:
        LAN_ACTIVE_USER = username
    if version_dir:
        LAN_ACTIVE_VERSION_DIR = version_dir
    if version_name:
        LAN_ACTIVE_VERSION_NAME = version_name
    elif version_dir and not LAN_ACTIVE_VERSION_NAME:
        LAN_ACTIVE_VERSION_NAME = os.path.basename(version_dir)
    trigger_lan_skin_broadcast()

def update_active_version(version_dir, version_name=None):
    """Public hook to update active modpack context across P2P and LAN beacons."""
    update_lan_skin_identity(None, version_dir, version_name)

def trigger_lan_skin_broadcast():
    """Forces an immediate discovery probe across all LAN and Radmin networks."""
    LAN_TRIGGER_EVENT.set()

def stop_lan_skin_service():
    """Stops the LAN Skin Sync daemon."""
    global LAN_SYNC_RUNNING, LAN_TCP_SOCKET, LAN_UDP_SOCKET
    LAN_SYNC_RUNNING = False
    if LAN_TCP_SOCKET:
        try: LAN_TCP_SOCKET.close()
        except Exception: pass
        LAN_TCP_SOCKET = None
    if LAN_UDP_SOCKET:
        try: LAN_UDP_SOCKET.close()
        except Exception: pass
        LAN_UDP_SOCKET = None

def get_lan_skin_peers():
    """Returns a list of currently detected LAN & Radmin peers."""
    with LAN_PEERS_LOCK:
        return [
            {"username": k, **v}
            for k, v in LAN_PEERS.items()
        ]

def handle_lan_command(args=None):
    """CLI handler for /lan or /skin lan."""
    box_w = 68
    b_targets = get_broadcast_targets()
    subnets = []
    has_radmin = False
    for t in b_targets:
        if t.startswith("26."):
            has_radmin = True
        elif t != "255.255.255.255":
            subnets.append(t)
    
    net_type = "WiFi / Local LAN"
    if has_radmin:
        net_type += " + Radmin VPN"

    status_str = f"{C_GREEN}Active & Listening{CLR_RESET}" if LAN_SYNC_RUNNING else f"{C_RED}Stopped{CLR_RESET}"
    _, own_hash = get_local_skin_payload(LAN_ACTIVE_USER)
    skin_status = f"{C_GREEN}Loaded ({own_hash[:8]}...){CLR_RESET}" if own_hash else f"{C_AMBER}No local skin file{CLR_RESET}"

    lines = [
        f"{C_PURPLE}\033[1mMoon Launcher - Native LAN & Radmin Skin P2P Engine\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"  {C_WHITE}* Service Status   :{CLR_RESET} {status_str}",
        f"  {C_WHITE}* Network Subnets  :{CLR_RESET} {C_CYAN}{net_type}{CLR_RESET}",
        f"  {C_WHITE}* UDP Broadcast Port:{CLR_RESET} {C_WHITE}{LAN_SYNC_UDP_PORT}{CLR_RESET} (Multi-Interface)",
        f"  {C_WHITE}* TCP HTTP Port    :{CLR_RESET} {C_WHITE}{LAN_TCP_PORT or 'Offline'}{CLR_RESET}",
        f"  {C_WHITE}* Active Username  :{CLR_RESET} {C_CYAN}{LAN_ACTIVE_USER or 'Unknown'}{CLR_RESET}",
        f"  {C_WHITE}* Local Skin File  :{CLR_RESET} {skin_status}",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"{C_WHITE}\033[1mDISCOVERED PEERS (AUTO-SYNCED):\033[0m"
    ]

    peers = get_lan_skin_peers()
    if not peers:
        lines.append(f"  {C_MUTED}No other Moon Launcher players detected on LAN yet.{CLR_RESET}")
        lines.append(f"  {C_MUTED}Peers will appear automatically when connected to WiFi or Radmin.{CLR_RESET}")
    else:
        for p in peers:
            u = p["username"]
            ip = p["ip"]
            age = int(time.time() - p.get("last_seen", 0))
            age_str = f"{age}s ago" if age < 60 else f"{age // 60}m ago"
            lines.append(f"  {C_GREEN}* {u:<16}{CLR_RESET} {C_WHITE}IP: {ip:<15}{CLR_RESET} {C_MUTED}(Seen: {age_str}){CLR_RESET}")

    lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
    lines.append(f"{C_MUTED}Commands: /lan sync (probe network) • /skin friend <name> <url>{CLR_RESET}")
    print("\n" + render_box(lines, box_w, title="LAN & Radmin Skin Hub") + "\n")

    if args and args[0].lower() in ("sync", "probe", "scan", "refresh"):
        print(f"{C_CYAN}[Moon LAN] Broadcasting discovery beacon across all network interfaces...{CLR_RESET}")
        trigger_lan_skin_broadcast()
        time.sleep(0.5)
        print(f"{C_GREEN}[Moon LAN] Probe complete!{CLR_RESET}\n")
