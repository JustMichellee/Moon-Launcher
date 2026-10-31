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
import zipfile
import io
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
        out[0] = f"{C_BORDER}╭─{C_WHITE}\033[1m{v_title}{CLR_RESET}{C_BORDER}{'─' * max(0, width - 3 - t_len)}╮{CLR_RESET}"

    for l in lines:
        s = strip_ansi(str(l)).strip()
        if len(s) > 0 and all(c in '─-=' for c in s):
            # Dynamic separator line matching exact box width with T-junctions
            out.append(f"{C_BORDER}├{'─' * (width - 2)}┤{CLR_RESET}")
        else:
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
        res = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        return res.returncode == 0
    except Exception:
        pass
    return False

def get_clipboard_text():
    """Reads text from Windows system clipboard."""
    if sys.platform == 'win32':
        try:
            res = subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], capture_output=True, text=True, timeout=2)
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

    # Attempt bidirectional mutual handshake to peer's Moon Launcher
    peer_ip = None
    peer_port = 25570
    if addr and ":" in addr:
        peer_ip = addr.split(":")[0]
    with LAN_PEERS_LOCK:
        for uname, p in LAN_PEERS.items():
            if uname.lower() == u_name.lower():
                peer_ip = p.get("ip")
                peer_port = p.get("port", 25570)
                break

    handshake_result = send_mutual_handshake(peer_ip, peer_port, LAN_ACTIVE_USER, addr) if peer_ip else None

    box_w = 68
    lines = [
        f"{C_GREEN}\033[1m[OK] Friend Added Successfully!\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"  {C_WHITE}* Player Name     :{CLR_RESET} {C_CYAN}{u_name}{CLR_RESET}",
    ]
    if handshake_result and handshake_result.get("status") == "ok":
        lines.append(f"  {C_WHITE}* Mutual Friendship:{CLR_RESET} {C_GREEN}Confirmed! ({u_name} added you back){CLR_RESET}")
    elif peer_ip:
        lines.append(f"  {C_WHITE}* Mutual Handshake:{CLR_RESET} {C_MUTED}Dispatched to {peer_ip}:{peer_port}{CLR_RESET}")
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
            "friends": [],
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
            data = json.load(f)
            if "friends" in data:
                cleaned = [f for f in data["friends"] if f.get("note") != "Primary Profile" and f.get("username", "").lower() not in ("michelle", "alex")]
                if len(cleaned) != len(data["friends"]):
                    data["friends"] = cleaned
                    save_network_data(data)
            return data
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
    Handles /friend commands:
    - /friend (or /friend list)
    - /friend invite (or /friend share, /friend link) -> Generates & copies invite link
    - /friend add <link_or_name> [ip:port]
    - /friend remove <name>
    - /friend ping <name>
    - /friend note <name> <text>
    """
    data = load_network_data()
    raw_friends = data.get("friends", [])

    # Filter out current active username so players never see their own profile in friends list
    my_uname = ""
    try:
        import launcher
        my_uname = launcher.load_config().get("username", "").strip().lower()
    except Exception:
        pass

    friends = [
        f for f in raw_friends
        if f.get("username", "").strip().lower() != my_uname and f.get("note") != "Primary Profile"
    ]

    if not args or args[0].lower() in ("list", "ls", "show"):
        # Display Friends Table
        box_w = 68
        lines = [
            f"{C_WHITE}[1mPlayer Friends & Multiplayer Contacts[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]

        if not friends:
            lines.append(f"{C_MUTED}No friends added yet.{CLR_RESET}")
            lines.append(f"{C_MUTED}Add friends via link: {C_CYAN}/friend add <invite_link>{CLR_RESET}")
            lines.append(f"{C_MUTED}Share your invite link: {C_AMBER}/friend invite{CLR_RESET}")
        else:
            for idx, f_item in enumerate(friends, 1):
                u_name = f_item.get("username", "Unknown")
                addr = f_item.get("address", "")
                note = f_item.get("note", "")

                status_tag = f"{C_MUTED}[OFFLINE]{CLR_RESET}"
                ping_detail = f"{C_MUTED}No Address{CLR_RESET}"

                peer_meta = None
                with LAN_PEERS_LOCK:
                    peer_meta = next((p for uname, p in LAN_PEERS.items() if uname.lower() == u_name.lower()), None)

                if peer_meta and peer_meta.get("version_name"):
                    v_name = peer_meta.get("version_name")
                    m_cnt = peer_meta.get("mod_count", 0)
                    status_tag = f"{C_GREEN}[PLAYING]{CLR_RESET}"
                    ping_detail = f"{C_WHITE}{v_name}{CLR_RESET} ({m_cnt} mods)"
                elif addr:
                    p_res = ping_minecraft_server(addr, timeout=1.2)
                    if p_res["online"]:
                        status_tag = f"{C_GREEN}[ONLINE ]{CLR_RESET}"
                        ping_detail = f"{C_GREEN}{p_res['latency']}ms{CLR_RESET} ({p_res['players_online']} players)"
                    else:
                        status_tag = f"{C_RED}[IDLE   ]{CLR_RESET}"
                        ping_detail = f"{C_MUTED}{addr}{CLR_RESET}"

                u_name_padded = f"{u_name:<16}"
                name_col = f"{C_CYAN}{u_name_padded}{CLR_RESET}"
                lines.append(f"  {status_tag} {name_col} {ping_detail}")
                if peer_meta and peer_meta.get("version_name"):
                    lines.append(f"     {C_CYAN}↳ Join: Type /friend join {u_name}{CLR_RESET}")
                if note:
                    lines.append(f"     {C_MUTED}* Note: {note}{CLR_RESET}")

        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines.append(f"{C_MUTED}Commands: {C_WHITE}/friend join <name>{C_MUTED} • {C_WHITE}/friend sync <name>{CLR_RESET}")
        lines.append(f"{C_MUTED}          {C_WHITE}/friend invite{C_MUTED}      • {C_WHITE}/friend add <link>{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Friends Hub") + "\n")
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
        # Resolve active player username
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
        lines = [
            f"{C_WHITE}\033[1mFriend & Multiplayer Invite Link\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Player Profile  :{CLR_RESET} {C_CYAN}\033[1m{username}\033[0m",
        ]
        if server_addr:
            lines.append(f"  {C_WHITE}* Live Server     :{CLR_RESET} {C_GREEN}{server_addr} (Tunnel Active){CLR_RESET}")
        else:
            lines.append(f"  {C_WHITE}* Live Server     :{CLR_RESET} {C_MUTED}None (Start /host to include your game world){CLR_RESET}")

        lines.extend([
            f"",
            f"  {C_WHITE}\033[1mShareable Web Link:\033[0m",
            f"  {C_CYAN}{invite['web_link']}{CLR_RESET}",
            f"",
            f"  {C_WHITE}\033[1mDirect Moon Protocol:\033[0m",
            f"  {C_MUTED}{invite['moon_link']}{CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        ])
        if copied:
            lines.append(f"  {C_GREEN}[COPIED TO CLIPBOARD]{CLR_RESET} {C_WHITE}Press Ctrl+V to share on Discord or WhatsApp!{CLR_RESET}")
        else:
            lines.append(f"  {C_MUTED}Copy and send the link above to your friends!{CLR_RESET}")
        lines.append(f"  {C_MUTED}Your friends can paste this link into Moon Launcher to add you!{CLR_RESET}")

        print("\n" + render_box(lines, box_w, title="Invite Link") + "\n")
        return

    # /friend add <name_or_link> [address]
    elif sub in ("add", "new", "+"):
        if len(args) < 2:
            # Check clipboard for invite link
            clip = get_clipboard_text()
            inv = parse_friend_invite(clip)
            if inv:
                print(f"\n{C_CYAN}Found Friend Invite in Clipboard:{CLR_RESET}")
                print(f"  Player : {C_WHITE}{inv['username']}{CLR_RESET}")
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

            print(f"\n{C_RED}Usage: /friend add <username> [ip:port]{CLR_RESET}")
            print(f"{C_MUTED}Or paste an invite link: /friend add https://moonlauncher.link/add?user=...{CLR_RESET}\n")
            return

        # Check if argument 1 is an invite link or token
        inv = parse_friend_invite(args[1])
        if inv:
            add_friend_from_invite(inv, data)
            return

        u_name = args[1].strip().replace(" ", "_")
        addr = args[2].strip() if len(args) > 2 else ""

        # Check existing
        for item in friends:
            if item.get("username", "").lower() == u_name.lower():
                item["address"] = addr or item.get("address", "")
                save_network_data(data)
                print(f"\n{C_GREEN}[OK] Updated contact for friend '{u_name}'!{CLR_RESET}\n")
                return

        # Check LAN_PEERS for peer discovery info
        peer_ip = None
        peer_port = 25570
        with LAN_PEERS_LOCK:
            for uname, p in LAN_PEERS.items():
                if uname.lower() == u_name.lower():
                    peer_ip = p.get("ip")
                    peer_port = p.get("port", 25570)
                    if not addr:
                        addr = p.get("server_addr") or f"{peer_ip}:25565"
                    break

        if addr and ":" in addr and not peer_ip:
            peer_ip = addr.split(":")[0]

        friends.append({
            "username": u_name,
            "address": addr,
            "note": "",
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        save_network_data(data)

        # Dispatch mutual handshake
        hs_res = send_mutual_handshake(peer_ip, peer_port, LAN_ACTIVE_USER, addr) if peer_ip else None

        box_w = 68
        lines = [
            f"{C_GREEN}\033[1m[OK] Friend Added Successfully!\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Player Name     :{CLR_RESET} {C_CYAN}{u_name}{CLR_RESET}",
        ]
        if addr:
            lines.append(f"  {C_WHITE}* Address         :{CLR_RESET} {C_WHITE}{addr}{CLR_RESET}")
        if hs_res and hs_res.get("status") == "ok":
            lines.append(f"  {C_WHITE}* Mutual Friendship:{CLR_RESET} {C_GREEN}Confirmed! ({u_name} added you back){CLR_RESET}")
        elif peer_ip:
            lines.append(f"  {C_WHITE}* Mutual Handshake:{CLR_RESET} {C_MUTED}Dispatched to {peer_ip}:{peer_port}{CLR_RESET}")
        else:
            lines.append(f"  {C_WHITE}* Status          :{CLR_RESET} {C_MUTED}Saved locally (Peer offline or not yet detected){CLR_RESET}")
        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Friend Added") + "\n")

    # /friend remove <name>
    elif sub in ("remove", "delete", "rm", "-"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /friend remove <username>{CLR_RESET}\n")
            return
        u_name = args[1].lower()
        new_friends = [f for f in friends if f.get("username", "").lower() != u_name]
        if len(new_friends) == len(friends):
            print(f"\n{C_AMBER}Friend '{args[1]}' not found in contact list.{CLR_RESET}\n")
        else:
            data["friends"] = new_friends
            save_network_data(data)
            print(f"\n{C_GREEN}[OK] Removed '{args[1]}' from your friends list.{CLR_RESET}\n")

    # /friend ping <name>
    elif sub in ("ping", "check"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /friend ping <username>{CLR_RESET}\n")
            return
        target = args[1].lower()
        matched = next((f for f in friends if f.get("username", "").lower() == target), None)
        if not matched or not matched.get("address"):
            print(f"\n{C_AMBER}No server address saved for friend '{args[1]}'.{CLR_RESET}")
            print(f"{C_MUTED}Set address with: /friend add {args[1]} <ip:port>{CLR_RESET}\n")
            return

        addr = matched["address"]
        print(f"\n{C_CYAN}Pinging {matched['username']}'s server at {addr}...{CLR_RESET}")
        res = ping_minecraft_server(addr, timeout=3.0)
        box_w = 66
        if res["online"]:
            p_lines = [
                f"{C_GREEN}[PASS] Server is ONLINE!{CLR_RESET}",
                f"{C_WHITE}Host Friend :{CLR_RESET} {matched['username']}",
                f"{C_WHITE}Address     :{CLR_RESET} {addr}",
                f"{C_WHITE}Latency     :{CLR_RESET} {res['latency']} ms",
                f"{C_WHITE}Players     :{CLR_RESET} {res['players_online']} / {res['players_max']}",
                f"{C_WHITE}Version     :{CLR_RESET} {res['version']}",
                f"{C_WHITE}MOTD        :{CLR_RESET} {res['motd']}"
            ]
        else:
            p_lines = [
                f"{C_RED}[FAIL] Server is OFFLINE or Unreachable{CLR_RESET}",
                f"{C_WHITE}Host Friend :{CLR_RESET} {matched['username']}",
                f"{C_WHITE}Address     :{CLR_RESET} {addr}",
                f"{C_MUTED}Reason: {res['motd']}{CLR_RESET}"
            ]
        print("\n" + render_box(p_lines, box_w, title="Ping Results") + "\n")

    # /friend note <name> <text>
    elif sub in ("note", "memo"):
        if len(args) < 3:
            print(f"\n{C_RED}Usage: /friend note <username> <text>{CLR_RESET}\n")
            return
        target = args[1].lower()
        note_txt = " ".join(args[2:])
        matched = next((f for f in friends if f.get("username", "").lower() == target), None)
        if matched:
            matched["note"] = note_txt
            save_network_data(data)
            print(f"\n{C_GREEN}[OK] Note updated for '{matched['username']}': {note_txt}{CLR_RESET}\n")
        else:
            print(f"\n{C_AMBER}Friend '{args[1]}' not found in contacts.{CLR_RESET}\n")
    # /friend join <name> or /friend sync <name>
    elif sub in ("join", "sync", "mabar", "connect"):
        if len(args) < 2:
            print(f"\n{C_RED}Usage: /friend {sub} <username>{CLR_RESET}\n")
            return
        target_name = args[1].strip()
        peer_ip = None
        peer_port = None
        peer_ver = None
        peer_srv = None
        
        with LAN_PEERS_LOCK:
            for uname, p in LAN_PEERS.items():
                if uname.lower() == target_name.lower():
                    peer_ip = p.get("ip")
                    peer_port = p.get("port")
                    peer_ver = p.get("version_name")
                    peer_srv = p.get("server_addr")
                    break
                    
        matched_friend = next((f for f in friends if f.get("username", "").lower() == target_name.lower()), None)
        if not peer_ip and matched_friend and matched_friend.get("address"):
            addr_parts = matched_friend["address"].split(":")
            peer_ip = addr_parts[0]
            peer_port = 25570
            peer_srv = matched_friend["address"]
            
        if not peer_ip:
            print(f"\n{C_AMBER}Friend '{target_name}' is not detected on local network or contacts.{CLR_RESET}")
            print(f"{C_CYAN}If playing over Internet (No Radmin / Hamachi needed):{CLR_RESET}")
            print(f"  1. Ask {target_name} to run {C_WHITE}/host start{C_CYAN} in Moon Launcher")
            print(f"  2. Ask {target_name} to type {C_WHITE}/friend invite{C_CYAN} and send you the link")
            print(f"  3. Add the link: {C_GREEN}/friend add [invite_link]{CLR_RESET}")
            print(f"  4. Type {C_GREEN}/friend join {target_name}{CLR_RESET} to connect directly!\n")
            return
            
        box_w = 68
        try:
            req = urllib.request.Request(f"http://{peer_ip}:{peer_port}/modpack/info", headers={"User-Agent": "Moon-Launcher/1.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                peer_info = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"\n{C_RED}[Moon P2P] Failed to connect to {target_name}'s launcher: {e}{CLR_RESET}\n")
            return
            
        v_name = peer_info.get("version_name", "Unknown Modpack")
        mc_ver = peer_info.get("mc_version", "1.20.1")
        loader = peer_info.get("loader", "Forge")
        mod_cnt = peer_info.get("mod_count", 0)
        srv_target = peer_srv or peer_info.get("server_addr") or f"{peer_ip}:25565"
        if srv_target.startswith(":"):
            srv_target = f"{peer_ip}{srv_target}"
            
        info_lines = [
            f"{C_WHITE}\033[1mFriend Game Session Detected\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
            f"  {C_WHITE}* Player Name    :{CLR_RESET} {C_CYAN}{target_name}{CLR_RESET}",
            f"  {C_WHITE}* Active Modpack :{CLR_RESET} {C_WHITE}\033[1m{v_name}\033[0m ({loader} {mc_ver})",
            f"  {C_WHITE}* Total Mods     :{CLR_RESET} {C_AMBER}{mod_cnt} mods installed{CLR_RESET}",
            f"  {C_WHITE}* Target Server  :{CLR_RESET} {C_GREEN}{srv_target}{CLR_RESET}",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        print("\n" + render_box(info_lines, box_w, title="Friend Multiplayer") + "\n")
        
        v_dir = os.path.join(BASE_DIR, "versions", v_name)
        needs_sync = not os.path.exists(v_dir) or not os.path.exists(os.path.join(v_dir, "mods"))
        
        if needs_sync:
            print(f"{C_AMBER}[Moon P2P] Custom modpack '{v_name}' is not installed on your PC.{CLR_RESET}")
            ans = input(f"{C_WHITE}Request and download custom modpack directly from {target_name}? [Y/n]: {CLR_RESET}").strip().lower()
            if ans not in ('', 'y', 'yes'):
                print(f"{C_MUTED}Sync cancelled.{CLR_RESET}\n")
                return
            v_dir = sync_modpack_from_peer(peer_ip, peer_port)
            if not v_dir:
                print(f"{C_RED}[Moon P2P] Transfer failed! Cannot join.{CLR_RESET}\n")
                return
        elif sub == "sync":
            v_dir = sync_modpack_from_peer(peer_ip, peer_port)
            
        if sub == "sync":
            print(f"{C_GREEN}[OK] Modpack '{v_name}' is up to date!{CLR_RESET}\n")
            return
            
        import launcher
        cfg = launcher.load_config()
        cfg['version_name'] = v_name
        cfg['server'] = srv_target.split(":")[0]
        if ":" in srv_target:
            try: cfg['port'] = int(srv_target.split(":")[1])
            except Exception: pass
        launcher.save_config(cfg)
        
        print(f"\n{C_GREEN}Launching {v_name} and joining {target_name} at {srv_target}...{CLR_RESET}\n")
        launcher.launch_game(v_dir, cfg)

    # /friend nearby or /friend discover
    elif sub in ("nearby", "discover", "lan", "radar"):
        with LAN_PEERS_LOCK:
            nearby = [
                {"username": k, **v}
                for k, v in LAN_PEERS.items()
                if k.lower() != (LAN_ACTIVE_USER or "").lower()
            ]

        box_w = 68
        lines = [
            f"{C_WHITE}\033[1mDiscovered LAN & Radmin Peers\033[0m",
            f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
        ]
        if not nearby:
            lines.append(f"{C_MUTED}No other players detected on your local network or Radmin VPN.{CLR_RESET}")
            lines.append(f"{C_MUTED}Make sure your friends have Moon Launcher running on the same network.{CLR_RESET}")
        else:
            for p in nearby:
                p_name = p.get("username", "Unknown")
                p_ip = p.get("ip", "")
                p_ver = p.get("version_name") or "Unknown"
                p_mods = p.get("mod_count", 0)
                lines.append(f"  {C_GREEN}[ONLINE]{CLR_RESET} {C_CYAN}\033[1m{p_name:<16}\033[0m {C_WHITE}{p_ver}{CLR_RESET} ({p_mods} mods)")
                lines.append(f"           {C_MUTED}IP: {p_ip}:{p.get('port', 25570)}{CLR_RESET}")
                lines.append(f"           {C_CYAN}↳ Add: Type /friend add {p_name}{CLR_RESET}")

        lines.append(f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}")
        lines.append(f"{C_MUTED}Type /friend add <name> to add and establish mutual friendship!{CLR_RESET}")
        print("\n" + render_box(lines, box_w, title="Nearby Peers") + "\n")
        return

    else:
        print(f"\n{C_RED}Unknown friend command. Available: list, nearby, invite, add, remove, ping, note{CLR_RESET}\n")

# ==============================================================================
# COMMAND HANDLER: /host
# ==============================================================================

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
LAN_ACTIVE_VERSION_NAME = None
LAN_PEERS_LOCK = threading.Lock()
LAN_PEERS = {}  # {username: {'ip': str, 'port': int, 'hash': str, 'last_seen': float, 'synced': bool}}
LAN_TRIGGER_EVENT = threading.Event()

def get_broadcast_targets():
    """Detects local broadcast targets across WiFi, Ethernet, and virtual LANs (Radmin VPN, Tailscale, ZeroTier)."""
    targets = {'255.255.255.255'}
    try:
        out = subprocess.check_output('ipconfig', text=True, encoding='cp437', errors='ignore')
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


def resolve_clean_modpack_name(target_dir=None, candidate_name=None):
    """
    Resolves the clean, user-friendly modpack name instead of generic internal folder names like '1.20.1' or 'n'.
    """
    if candidate_name and candidate_name not in ("1.20.1", "1.12.2", "1.21.1", "n", "run", "client"):
        return candidate_name

    target = target_dir or LAN_ACTIVE_VERSION_DIR
    if not target:
        try:
            cfg_path = os.path.join(BASE_DIR, "launcher_config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg_v = json.load(f).get("version_name")
                    if cfg_v: return cfg_v
        except Exception:
            pass
        return "Custom Modpack"

    # 1. Check if target has a launcher_config.json
    local_cfg = os.path.join(target, "launcher_config.json")
    if os.path.exists(local_cfg):
        try:
            with open(local_cfg, "r", encoding="utf-8") as f:
                cfg_v = json.load(f).get("version_name")
                if cfg_v and cfg_v not in ("1.20.1", "1.12.2", "1.21.1", "n"):
                    return cfg_v
        except Exception:
            pass

    # 2. Check global launcher_config.json in BASE_DIR
    global_cfg = os.path.join(BASE_DIR, "launcher_config.json")
    if os.path.exists(global_cfg):
        try:
            with open(global_cfg, "r", encoding="utf-8") as f:
                cfg_v = json.load(f).get("version_name")
                if cfg_v and cfg_v not in ("1.20.1", "1.12.2", "1.21.1", "n"):
                    return cfg_v
        except Exception:
            pass

    # 3. Check for descriptor json file inside target (e.g. 'DeadZone 1.20.1 Forge.json')
    try:
        for f in os.listdir(target):
            if f.endswith(".json") and f not in ("launcher_config.json", "usercache.json", "usernamecache.json"):
                base_json = os.path.splitext(f)[0]
                if base_json not in ("1.20.1", "1.12.2", "1.21.1", "n"):
                    return base_json
    except Exception:
        pass

    # 4. Fallback to folder basename
    base = os.path.basename(os.path.normpath(target))
    return base if base else "Custom Modpack"

def generate_core_bundle_bytes(target_dir, v_name):
    """
    Compresses all configs, scripts, menus, and descriptors into an in-memory zip bundle.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        # 1. Essential root files
        for f in ["launch_args.txt", "launcher_config.json", "icon.png", "icon.webp", "options.txt"]:
            fp = os.path.join(target_dir, f)
            if os.path.exists(fp):
                zf.write(fp, f)
        # 2. Descriptors
        for f in os.listdir(target_dir):
            if f.endswith(".json") and f not in ("launcher_config.json", "usercache.json", "usernamecache.json"):
                zf.write(os.path.join(target_dir, f), f)
        # 3. Directories: configs, scripts, kubejs, menus, openloader
        for d in ["config", "defaultconfigs", "kubejs", "scripts", "patchouli_books", "openloader", "fancymenu_data"]:
            dp = os.path.join(target_dir, d)
            if os.path.exists(dp):
                for root, _, files in os.walk(dp):
                    for file in files:
                        full = os.path.join(root, file)
                        rel = os.path.relpath(full, target_dir).replace("\\", "/")
                        zf.write(full, rel)
    return buf.getvalue()

def setup_downloaded_modpack(target_v_dir, v_name, mc_ver, loader):
    """
    Ensures downloaded modpack is properly adapted and ready to launch immediately:
    1. Adapts launch_args.txt (sets --gameDir, -Djava.library.path, --username, --version).
    2. Self-heals natives for detected MC version.
    3. Self-heals client jar and libraries descriptor.
    4. Writes launcher_config.json inside version directory.
    5. Sets active profile in Moon Launcher so launcher UI and play commands recognize it.
    """
    norm_v_dir = target_v_dir.replace("\\", "/")
    norm_natives = f"{norm_v_dir}/natives"
    
    args_path = os.path.join(target_v_dir, "launch_args.txt")
    curr_user = LAN_ACTIVE_USER or "Player"
    try:
        import launcher
        curr_user = launcher.load_config().get("username", curr_user)
    except Exception:
        pass

    if os.path.exists(args_path):
        try:
            with open(args_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                content = f.read()
            lines = content.splitlines()
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("-Djava.library.path="):
                    new_lines.append(f"-Djava.library.path={norm_natives}")
                elif line.strip() == "--gameDir" and i + 1 < len(lines):
                    new_lines.append(line)
                    new_lines.append(f'"{norm_v_dir}"')
                    i += 1
                elif line.strip() == "--username" and i + 1 < len(lines):
                    new_lines.append(line)
                    new_lines.append(curr_user)
                    i += 1
                elif line.strip() == "--version" and i + 1 < len(lines):
                    new_lines.append(line)
                    new_lines.append(v_name)
                    i += 1
                else:
                    new_lines.append(line)
                i += 1
            with open(args_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
        except Exception:
            pass

    try:
        import launcher
        launcher.ensure_natives_for_version(target_v_dir, mc_ver)
        launcher.ensure_launch_args(target_v_dir, declared_loader=loader, mc_version=mc_ver)
        
        local_cfg = {
            "version_name": v_name,
            "mc_version": mc_ver,
            "loader": loader,
            "username": curr_user
        }
        launcher.save_config(target_v_dir, local_cfg)
        launcher.set_active_version(v_name)
    except Exception:
        pass

    update_active_version(target_v_dir, v_name)
    return target_v_dir

def send_mutual_handshake(peer_ip, peer_port, my_username, my_addr=""):
    """Sends a reciprocal friend handshake to peer's Moon Launcher TCP server."""
    if not peer_ip or not my_username:
        return None
    try:
        t_status = get_tunnel_status()
        pub_addr = my_addr or (t_status.get("public_address") if t_status.get("running") else "")
        url = f"http://{peer_ip}:{peer_port}/friend/handshake?user={urllib.parse.quote(my_username)}&addr={urllib.parse.quote(pub_addr)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Moon-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

def get_active_modpack_manifest(v_dir=None):
    """Scans and generates a file manifest of the active modpack with clean naming, bundle directories, and core bundle support."""
    target = v_dir or LAN_ACTIVE_VERSION_DIR
    if not target or not os.path.exists(target):
        return None
    v_name = resolve_clean_modpack_name(target, LAN_ACTIVE_VERSION_NAME)
    mods_dir = os.path.join(target, "mods")
    tacz_dir = os.path.join(target, "tacz")
    
    files = []
    total_size = 0
    if os.path.exists(mods_dir):
        for f in sorted(os.listdir(mods_dir)):
            if f.endswith('.jar'):
                fp = os.path.join(mods_dir, f)
                sz = os.path.getsize(fp)
                files.append({"path": f"mods/{f}", "size": sz, "is_dir": False})
                total_size += sz

    # TaCZ Gunpacks: Stream folders as high-speed directory bundles to avoid 20,000+ separate HTTP requests!
    if os.path.exists(tacz_dir):
        for item in sorted(os.listdir(tacz_dir)):
            ip = os.path.join(tacz_dir, item)
            if os.path.isdir(ip):
                sz = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(ip) for f in fs)
                cnt = sum(len(fs) for _, _, fs in os.walk(ip))
                files.append({"path": f"tacz/{item}", "size": sz, "is_dir": True, "file_count": cnt})
                total_size += sz
            elif item.endswith('.zip') or item.endswith('.toml'):
                sz = os.path.getsize(ip)
                files.append({"path": f"tacz/{item}", "size": sz, "is_dir": False})
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
    else:
        try:
            for f in os.listdir(target):
                if f.endswith(".json") and f not in ("usercache.json", "usernamecache.json"):
                    with open(os.path.join(target, f), "r", encoding="utf-8") as jf:
                        jd = json.load(jf)
                        if "inheritsFrom" in jd:
                            mc_ver = jd.get("inheritsFrom")
                        elif "id" in jd:
                            mc_ver = jd.get("id")
                    break
        except Exception:
            pass

    return {
        "version_name": v_name,
        "mc_version": mc_ver,
        "loader": loader,
        "mod_count": len([i for i in files if i["path"].startswith("mods/")]),
        "total_files": len(files),
        "total_size": total_size,
        "has_core_bundle": True,
        "files": files
    }

def sync_modpack_from_peer(peer_ip, peer_port, versions_root=None):
    """
    Connects to peer P2P server, requests active modpack manifest,
    downloads core bundle (configs, scripts, descriptors, launch args),
    and selectively streams differential mods and gunpacks with live progress.
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
    mc_ver = manifest.get("mc_version", "1.20.1")
    loader = manifest.get("loader", "Forge")
        
    target_v_dir = os.path.join(v_root, v_name)
    os.makedirs(target_v_dir, exist_ok=True)
    
    box_w = 68
    sync_banner = [
        f"{C_WHITE}\033[1mMoon P2P High-Speed Modpack Sync\033[0m",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}",
        f"  {C_WHITE}* Modpack Name   :{CLR_RESET} {C_CYAN}\033[1m{v_name}\033[0m",
        f"  {C_WHITE}* Version/Loader :{CLR_RESET} {C_WHITE}{mc_ver} ({loader}){CLR_RESET}",
        f"  {C_WHITE}* Target Folder  :{CLR_RESET} {C_MUTED}{target_v_dir}{CLR_RESET}",
        f"{C_BORDER}{'─' * (box_w - 4)}{CLR_RESET}"
    ]
    print("\n" + render_box(sync_banner, box_w, title="P2P Sync Engine") + "\n")

    # Step 1: Download & Extract Core Bundle (Configs, Scripts, Descriptors, Launch Args)
    if manifest.get("has_core_bundle", True):
        print(f"{C_CYAN}[1/2] Streaming core system bundle (configs, scripts, launch settings)...{CLR_RESET}")
        try:
            b_url = f"{base_url}/modpack/core_bundle"
            b_req = urllib.request.Request(b_url, headers={"User-Agent": "Moon-Launcher/1.0"})
            with urllib.request.urlopen(b_req, timeout=20.0) as b_resp:
                b_data = b_resp.read()
            with zipfile.ZipFile(io.BytesIO(b_data), "r") as zf:
                zf.extractall(target_v_dir)
            print(f"  {C_GREEN}✓ Extracted {len(b_data)/(1024*1024):.2f} MB core bundle in under 1 second!{CLR_RESET}\n")
        except Exception as e:
            print(f"  {C_AMBER}! Notice: Core bundle stream skipped ({e}), falling back to direct files.{CLR_RESET}\n")

    # Step 2: Differential Sync for Mods and Gunpacks
    files = manifest.get("files", [])
    to_download = []
    download_bytes = 0
    for item in files:
        rel = item["path"]
        sz = item["size"]
        is_d = item.get("is_dir", False)
        dest = os.path.join(target_v_dir, rel.replace("/", os.sep))
        
        need = False
        if is_d:
            if not os.path.exists(dest) or len(os.listdir(dest) if os.path.isdir(dest) else []) == 0:
                need = True
        else:
            if not os.path.exists(dest) or os.path.getsize(dest) != sz:
                need = True
                
        if need:
            to_download.append((rel, sz, dest, is_d))
            download_bytes += sz
            
    if to_download:
        print(f"{C_CYAN}[2/2] Syncing {len(to_download)} differential mod & gunpack packages ({download_bytes / (1024*1024):.1f} MB)...{CLR_RESET}")
        transferred = 0
        t0 = time.time()
        for idx, (rel, sz, dest, is_d) in enumerate(to_download, 1):
            if is_d:
                os.makedirs(dest, exist_ok=True)
                d_url = f"{base_url}/modpack/bundle_dir?dir={urllib.parse.quote(rel)}"
                req = urllib.request.Request(d_url, headers={"User-Agent": "Moon-Launcher/1.0"})
                with urllib.request.urlopen(req, timeout=60.0) as resp:
                    pkg_bytes = resp.read()
                    transferred += sz
                with zipfile.ZipFile(io.BytesIO(pkg_bytes), "r") as zf:
                    zf.extractall(dest)
            else:
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
            item_display = (f"[{os.path.basename(rel)}]" if is_d else os.path.basename(rel))[:24]
            print(f"\r  [{C_GREEN}{bar}{CLR_RESET}] {pct}% ({transferred / (1024*1024):.1f}/{download_bytes / (1024*1024):.1f} MB, {speed:.1f} MB/s) {item_display:<24}", end="", flush=True)
        print()
    else:
        print(f"{C_GREEN}[2/2] All mod and gunpack packages are already up-to-date!{CLR_RESET}\n")

    # Step 3: Self-heal and finalize installation
    print(f"{C_CYAN}[Moon P2P] Finalizing installation & runtime environment...{CLR_RESET}")
    setup_downloaded_modpack(target_v_dir, v_name, mc_ver, loader)
    print(f"{C_GREEN}[OK] Custom modpack '{v_name}' successfully installed and ready to play!{CLR_RESET}\n")
    return target_v_dir

def _lan_tcp_server_loop():
    """Lightweight HTTP server serving player skins and P2P modpack sync to peers."""
    global LAN_TCP_SOCKET, LAN_TCP_PORT, LAN_SYNC_RUNNING
    while LAN_SYNC_RUNNING and LAN_TCP_SOCKET:
        try:
            conn, addr = LAN_TCP_SOCKET.accept()
            req = conn.recv(2048).decode('utf-8', errors='ignore')
            lines = req.splitlines()
            if lines and lines[0].startswith("GET"):
                path = lines[0].split()[1] if len(lines[0].split()) > 1 else ""
                
                if path.startswith("/skin/"):
                    target_user = LAN_ACTIVE_USER
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
                elif path.startswith("/friend/handshake"):
                    # Mutual Handshake Endpoint: Automatically register reciprocal friendship
                    parsed_q = urllib.parse.urlparse(path)
                    qs = urllib.parse.parse_qs(parsed_q.query)
                    h_user = qs.get("user", [""])[0].strip()
                    h_addr = qs.get("addr", [""])[0].strip()
                    
                    if h_user and h_user.lower() != (LAN_ACTIVE_USER or "").lower():
                        n_data = load_network_data()
                        n_friends = n_data.setdefault("friends", [])
                        matched_f = next((f for f in n_friends if f.get("username", "").lower() == h_user.lower()), None)
                        if matched_f:
                            if h_addr: matched_f["address"] = h_addr
                        else:
                            n_friends.append({
                                "username": h_user,
                                "address": h_addr,
                                "note": "Mutual Friend (Handshake)",
                                "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                        save_network_data(n_data)
                        print(f"\n{C_GREEN}\033[1m[!] Mutual Friend Handshake:{CLR_RESET} {C_CYAN}{h_user}{CLR_RESET} {C_GREEN}added you as a friend!\033[0m\n", end="", flush=True)

                    hs_res = json.dumps({"status": "ok", "user": LAN_ACTIVE_USER}).encode("utf-8")
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(hs_res)).encode() + b"\r\nConnection: close\r\n\r\n" + hs_res)

                elif path.startswith("/modpack/bundle_dir?dir="):
                    rel_dir = urllib.parse.unquote(path.split("dir=", 1)[1].strip())
                    if LAN_ACTIVE_VERSION_DIR:
                        safe_rel = os.path.normpath(rel_dir).lstrip(r"\/")
                        target_dir = os.path.join(LAN_ACTIVE_VERSION_DIR, safe_rel)
                        if os.path.commonpath([LAN_ACTIVE_VERSION_DIR, target_dir]) == LAN_ACTIVE_VERSION_DIR and os.path.isdir(target_dir):
                            buf = io.BytesIO()
                            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                                for root, _, files in os.walk(target_dir):
                                    for file in files:
                                        full = os.path.join(root, file)
                                        rel = os.path.relpath(full, target_dir).replace("\\", "/")
                                        zf.write(full, rel)
                            b_bytes = buf.getvalue()
                            hdr = f"HTTP/1.1 200 OK\r\nContent-Type: application/zip\r\nContent-Length: {len(b_bytes)}\r\nConnection: close\r\n\r\n".encode()
                            conn.sendall(hdr + b_bytes)
                        else:
                            conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
                    else:
                        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")

                elif path == "/modpack/core_bundle":
                    target = LAN_ACTIVE_VERSION_DIR
                    if target and os.path.exists(target):
                        v_name = resolve_clean_modpack_name(target, LAN_ACTIVE_VERSION_NAME)
                        bundle_bytes = generate_core_bundle_bytes(target, v_name)
                        hdr = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/zip\r\n"
                            b"Content-Disposition: attachment; filename=core_bundle.zip\r\n"
                            b"Content-Length: " + str(len(bundle_bytes)).encode() + b"\r\n"
                            b"Connection: close\r\n\r\n"
                        )
                        conn.sendall(hdr + bundle_bytes)
                    else:
                        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")

                elif path == "/modpack/info":
                    m = get_active_modpack_manifest()
                    if m:
                        t_status = get_tunnel_status()
                        pub_addr = t_status.get("public_address") if t_status.get("running") else None
                        active_port = detect_active_minecraft_port(LAN_ACTIVE_VERSION_DIR)
                        info_body = json.dumps({
                            "status": "ok",
                            "user": LAN_ACTIVE_USER,
                            "version_name": m["version_name"],
                            "mc_version": m["mc_version"],
                            "loader": m["loader"],
                            "mod_count": m["mod_count"],
                            "total_size": m["total_size"],
                            "server_addr": pub_addr or (f"{addr[0]}:{active_port}" if active_port else "")
                        }).encode('utf-8')
                        resp = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Content-Length: " + str(len(info_body)).encode() + b"\r\n"
                            b"Connection: close\r\n\r\n" + info_body
                        )
                        conn.sendall(resp)
                    else:
                        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
                elif path == "/modpack/manifest":
                    m = get_active_modpack_manifest()
                    if m:
                        body = json.dumps(m).encode('utf-8')
                        resp = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                            b"Connection: close\r\n\r\n" + body
                        )
                        conn.sendall(resp)
                    else:
                        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
                elif path.startswith("/modpack/file?path="):
                    rel = urllib.parse.unquote(path.split("path=", 1)[1].strip())
                    if LAN_ACTIVE_VERSION_DIR:
                        safe_rel = os.path.normpath(rel).lstrip(r"\/")
                        target_file = os.path.join(LAN_ACTIVE_VERSION_DIR, safe_rel)
                        if os.path.commonpath([LAN_ACTIVE_VERSION_DIR, target_file]) == LAN_ACTIVE_VERSION_DIR and os.path.isfile(target_file):
                            sz = os.path.getsize(target_file)
                            hdr = f"HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {sz}\r\nConnection: close\r\n\r\n".encode()
                            conn.sendall(hdr)
                            with open(target_file, "rb") as f_in:
                                while chunk := f_in.read(65536):
                                    conn.sendall(chunk)
                        else:
                            conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
                    else:
                        conn.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
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
                m_info = get_active_modpack_manifest()
                t_status = get_tunnel_status()
                pub_addr = t_status.get("public_address") if t_status.get("running") else None
                active_port = detect_active_minecraft_port(LAN_ACTIVE_VERSION_DIR)
                payload = json.dumps({
                    "magic": "MOON_SKIN_V1",
                    "user": LAN_ACTIVE_USER,
                    "hash": my_hash or "",
                    "port": LAN_TCP_PORT,
                    "version_name": m_info["version_name"] if m_info else "",
                    "mc_version": m_info["mc_version"] if m_info else "",
                    "loader": m_info["loader"] if m_info else "",
                    "mod_count": m_info["mod_count"] if m_info else 0,
                    "server_addr": pub_addr or (f":{active_port}" if active_port else "")
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
                        if "version_name" in msg:
                            peer_info["version_name"] = str(msg.get("version_name", ""))
                            peer_info["mc_version"] = str(msg.get("mc_version", ""))
                            peer_info["loader"] = str(msg.get("loader", ""))
                            peer_info["mod_count"] = int(msg.get("mod_count", 0))
                            peer_info["server_addr"] = str(msg.get("server_addr", ""))

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
