"""
Moon Launcher Phase 2 QoL Engine:
- Playtime Tracker per instance (playtime.json)
- Smart Auto World Backup (saves/ zip with manifest dedup & rotation)
- Per-App Audio Preset Controller via Windows Core Audio (pycaw)
- Borderless Fullscreen Win32 Window Toggle & Fullbright Gamma helper
- Always-On-Top Click-Through Windows Transparent HUD Overlay (F8 hotkey)
"""

import ctypes
import ctypes.wintypes
import hashlib
import json
import os
import re
import sys
import threading
import time
import zipfile
from datetime import datetime

try:
    import psutil
except Exception:
    psutil = None

from paths import BASE_DIR

PLAYTIME_LOCK = threading.Lock()
PLAYTIME_PATH = os.path.join(BASE_DIR, "playtime.json")
_BORDERLESS_SAVED = {}

MUSIC_PROCS = {"spotify.exe", "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "discord.exe"}
GAME_PROCS = {"javaw.exe", "java.exe"}

PAT_F3C = re.compile(r"/execute\s+in\s+([a-z0-9_:-]+)\s+run\s+tp\s+@s\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", re.IGNORECASE)


def format_duration(total_seconds):
    sec = max(0, int(total_seconds or 0))
    hrs, rem = divmod(sec, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def load_playtime():
    with PLAYTIME_LOCK:
        if os.path.exists(PLAYTIME_PATH):
            try:
                with open(PLAYTIME_PATH, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("instances", {})
                        return data
            except Exception:
                pass
        return {"instances": {}}


def save_playtime(data):
    with PLAYTIME_LOCK:
        os.makedirs(os.path.dirname(PLAYTIME_PATH), exist_ok=True)
        with open(PLAYTIME_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def record_playtime(version_name, delta_seconds):
    v_name = str(version_name or "").strip()
    if not v_name or delta_seconds < 1:
        return load_playtime()
    data = load_playtime()
    inst = data["instances"].setdefault(v_name, {"total_seconds": 0, "sessions": 0, "last_played": ""})
    inst["total_seconds"] = int(inst.get("total_seconds", 0)) + int(delta_seconds)
    inst["sessions"] = int(inst.get("sessions", 0)) + 1
    inst["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_playtime(data)
    return data


def get_playtime_summary(version_name=None):
    data = load_playtime()
    instances = data.get("instances", {})
    total_all = sum(int(v.get("total_seconds", 0)) for v in instances.values() if isinstance(v, dict))
    active_entry = instances.get(str(version_name or ""), {}) if version_name else {}
    return {
        "total_all_seconds": total_all,
        "total_all_formatted": format_duration(total_all),
        "instance_seconds": int(active_entry.get("total_seconds", 0)),
        "instance_formatted": format_duration(active_entry.get("total_seconds", 0)),
        "instance_sessions": int(active_entry.get("sessions", 0)),
        "last_played": active_entry.get("last_played", ""),
        "instances": instances,
    }


def _compute_saves_signature(saves_dir):
    h = hashlib.sha1()
    count = 0
    for root, dirs, files in os.walk(saves_dir):
        dirs.sort()
        files.sort()
        for fn in files:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, saves_dir)
            try:
                st = os.stat(fp)
                h.update(f"{rel}|{st.st_size}|{int(st.st_mtime)}\n".encode("utf-8", errors="ignore"))
                count += 1
            except Exception:
                pass
    return h.hexdigest(), count


def backup_instance_saves(version_dir, max_keep=4, force=False):
    if not version_dir or not os.path.isdir(version_dir):
        return {"success": False, "error": "Instance directory not found"}
    saves_dir = os.path.join(version_dir, "saves")
    if not os.path.isdir(saves_dir):
        return {"success": True, "skipped": True, "reason": "No saves directory yet"}

    world_dirs = [d for d in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, d))]
    if not world_dirs:
        return {"success": True, "skipped": True, "reason": "No worlds inside saves/"}

    backups_dir = os.path.join(version_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    meta_path = os.path.join(backups_dir, ".last_backup.json")

    sig, file_count = _compute_saves_signature(saves_dir)
    if not force and os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                old_sig = json.load(mf).get("signature")
            if old_sig == sig:
                return {"success": True, "skipped": True, "reason": "Worlds unchanged since last backup"}
        except Exception:
            pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"saves_{ts}.zip"
    zip_path = os.path.join(backups_dir, zip_name)

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(saves_dir):
                for fn in files:
                    if fn.lower() == "session.lock":
                        continue
                    fp = os.path.join(root, fn)
                    arc = os.path.relpath(fp, saves_dir)
                    try:
                        zf.write(fp, arc)
                    except PermissionError:
                        pass

        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump({"signature": sig, "file_count": file_count, "last_file": zip_name, "created_at": ts}, mf, indent=2)

        # Prune older backups keeping only max_keep newest
        zips = sorted(
            [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.startswith("saves_") and f.endswith(".zip")],
            key=lambda p: os.path.getmtime(p),
            reverse=True,
        )
        for old_z in zips[max(1, int(max_keep)):]:
            try:
                os.remove(old_z)
            except Exception:
                pass

        return {
            "success": True,
            "skipped": False,
            "file": zip_name,
            "path": zip_path,
            "worlds": len(world_dirs),
            "size_kb": max(1, os.path.getsize(zip_path) // 1024),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_instance_backups(version_dir):
    if not version_dir:
        return []
    bdir = os.path.join(version_dir, "backups")
    if not os.path.isdir(bdir):
        return []
    out = []
    for fn in sorted(os.listdir(bdir), reverse=True):
        if fn.startswith("saves_") and fn.endswith(".zip"):
            fp = os.path.join(bdir, fn)
            out.append({
                "name": fn,
                "size_kb": max(1, os.path.getsize(fp) // 1024),
                "modified": int(os.path.getmtime(fp)),
            })
    return out


def get_gamma_state(version_dir):
    if not version_dir:
        return {"enabled": False, "gamma": 1.0}
    opt = os.path.join(version_dir, "options.txt")
    if not os.path.exists(opt):
        return {"enabled": False, "gamma": 1.0}
    try:
        with open(opt, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("gamma:"):
                    val = float(line.split(":", 1)[1].strip())
                    return {"enabled": val >= 5.0, "gamma": val}
    except Exception:
        pass
    return {"enabled": False, "gamma": 1.0}


def set_gamma_boost(version_dir, enabled=None):
    if not version_dir or not os.path.isdir(version_dir):
        return {"success": False, "error": "Instance directory not found"}
    opt = os.path.join(version_dir, "options.txt")
    current = get_gamma_state(version_dir)["enabled"]
    target_enabled = (not current) if enabled is None else bool(enabled)
    target_val = "15.0" if target_enabled else "1.0"

    lines = []
    found = False
    if os.path.exists(opt):
        with open(opt, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("gamma:"):
                    lines.append(f"gamma:{target_val}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"gamma:{target_val}\n")

    try:
        with open(opt, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return {"success": True, "enabled": target_enabled, "gamma": float(target_val)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _find_game_pid(explicit_pid=None):
    if explicit_pid and psutil:
        try:
            p = psutil.Process(int(explicit_pid))
            if p.is_running():
                return p.pid
        except Exception:
            pass
    if psutil:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                nm = (p.info.get("name") or "").lower()
                if nm in GAME_PROCS:
                    # Prefer process with visible Minecraft window or cmdline
                    cmd = " ".join(p.cmdline() or []).lower()
                    if "minecraft" in cmd or "fabric" in cmd or "forge" in cmd or "lwjgl" in cmd:
                        return p.info["pid"]
            except Exception:
                pass
    return int(explicit_pid) if explicit_pid else None


def find_minecraft_window_hwnd(target_pid=None):
    if sys.platform != "win32":
        return 0
    user32 = ctypes.windll.user32
    pid_target = _find_game_pid(target_pid)
    matched = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        win_pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
        if pid_target and win_pid.value == pid_target:
            matched.insert(0, hwnd)
            return False
        if "minecraft" in title.lower():
            matched.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)
    return matched[0] if matched else 0


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", ctypes.wintypes.RECT),
        ("rcWork", ctypes.wintypes.RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


def toggle_borderless_window(target_pid=None):
    if sys.platform != "win32":
        return {"success": False, "error": "Windows only"}
    hwnd = find_minecraft_window_hwnd(target_pid)
    if not hwnd:
        return {"success": False, "error": "No running Minecraft window detected"}

    user32 = ctypes.windll.user32
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_SYSMENU = 0x00080000
    CHROME_MASK = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040

    cur_style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    is_currently_bordered = bool(cur_style & WS_CAPTION)

    if is_currently_bordered:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        _BORDERLESS_SAVED[hwnd] = (cur_style, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

        hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        mr = mi.rcMonitor
        user32.SetWindowLongW(hwnd, GWL_STYLE, cur_style & ~CHROME_MASK)
        user32.SetWindowPos(
            hwnd, 0, mr.left, mr.top, mr.right - mr.left, mr.bottom - mr.top,
            SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
        )
        return {"success": True, "borderless": True}
    else:
        saved = _BORDERLESS_SAVED.pop(hwnd, None)
        new_style = saved[0] if saved else (cur_style | CHROME_MASK)
        x, y, w, h = (saved[1], saved[2], saved[3], saved[4]) if saved else (100, 80, 1280, 720)
        user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
        user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        return {"success": True, "borderless": False}


def apply_audio_preset(preset="normal"):
    if sys.platform != "win32":
        return {"success": False, "error": "Windows only"}
    try:
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    except Exception as e:
        return {"success": False, "error": f"Audio mixer unavailable: {e}"}

    presets = {
        "normal": (1.0, 1.0, False, "Normal (MC 100% / Music 100%)"),
        "pvp_focus": (1.0, 0.15, False, "PvP Focus (MC 100% / Music 15%)"),
        "chill": (0.45, 0.90, False, "Chill (MC 45% / Music 90%)"),
        "mute_game": (0.0, 1.0, True, "Mute Game (MC 0%)"),
    }
    p_key = str(preset or "normal").strip().lower()
    mc_vol, music_vol, mc_mute, label = presets.get(p_key, presets["normal"])

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)
    updated_game = 0
    updated_music = 0
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if not session.Process:
                continue
            pname = (session.Process.name() or "").lower()
            vol = session._ctl.QueryInterface(ISimpleAudioVolume)
            if pname in GAME_PROCS:
                vol.SetMute(1 if mc_mute else 0, None)
                vol.SetMasterVolume(float(mc_vol), None)
                updated_game += 1
            elif pname in MUSIC_PROCS:
                vol.SetMute(0, None)
                vol.SetMasterVolume(float(music_vol), None)
                updated_music += 1
        return {
            "success": True,
            "preset": p_key,
            "label": label,
            "game_sessions": updated_game,
            "music_sessions": updated_music,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        try:
            ole32.CoUninitialize()
        except Exception:
            pass


def _read_clipboard_unicode():
    if sys.platform != "win32":
        return ""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    CF_UNICODETEXT = 13
    if not user32.OpenClipboard(0):
        return ""
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        ptr = kernel32.GlobalLock(h)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h)
    except Exception:
        return ""
    finally:
        user32.CloseClipboard()


class MoonHudOverlay:
    """Transparent click-through Always-On-Top HUD Overlay for Minecraft on Windows."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_evt = threading.Event()
        self._enabled = False
        self._pin_visible = False
        self._manual_hidden = False
        self._target_pid = None
        self._version_name = "Minecraft"
        self._server_addr = ""
        self._audio_preset = "normal"
        self._last_coords = ""
        self._last_ping_ms = None
        self._last_ping_check = 0.0
        self._session_start = None

    def set_context(self, pid=None, version_name=None, server_addr=None):
        with self._lock:
            if pid:
                if self._target_pid != pid:
                    self._session_start = time.time()
                self._target_pid = pid
            if version_name:
                self._version_name = str(version_name)
            if server_addr is not None:
                self._server_addr = str(server_addr)

    def set_audio_preset_label(self, preset):
        with self._lock:
            self._audio_preset = str(preset or "normal")

    def start(self, pid=None, version_name=None, pin_visible=False):
        self.set_context(pid=pid, version_name=version_name)
        with self._lock:
            self._pin_visible = bool(pin_visible)
            self._manual_hidden = False
            self._enabled = True
            if self._session_start is None:
                self._session_start = time.time()
            if self._thread and self._thread.is_alive():
                return self.status()
            self._stop_evt.clear()
            self._thread = threading.Thread(target=self._run_tk_loop, daemon=True, name="MoonHudOverlay")
            self._thread.start()
        return self.status()

    def stop(self):
        with self._lock:
            self._enabled = False
            self._stop_evt.set()
            t = self._thread
        if t is not None and t.is_alive() and threading.current_thread() is not t:
            t.join(timeout=1.5)
        return self.status()

    def toggle(self, version_name=None, pid=None):
        with self._lock:
            running = bool(self._enabled and self._thread and self._thread.is_alive())
        if running:
            return self.stop()
        return self.start(pid=pid, version_name=version_name, pin_visible=True)

    def status(self):
        with self._lock:
            return {
                "running": bool(self._enabled and self._thread and self._thread.is_alive()),
                "visible": not self._manual_hidden,
                "pin_visible": self._pin_visible,
                "version_name": self._version_name,
                "audio_preset": self._audio_preset,
                "coords": self._last_coords,
                "ping_ms": self._last_ping_ms,
                "hotkey": "F8",
            }

    def _collect_telemetry_text(self):
        now_clock = datetime.now().strftime("%H:%M")
        ram_txt = "-- MB"
        game_pid = _find_game_pid(self._target_pid)
        if game_pid and psutil:
            try:
                mem_mb = int(psutil.Process(game_pid).memory_info().rss / (1024 * 1024))
                ram_txt = f"{mem_mb} MB"
            except Exception:
                pass

        sess_sec = int(time.time() - (self._session_start or time.time()))
        pt = get_playtime_summary(self._version_name)
        total_sec = pt["instance_seconds"] + (sess_sec if game_pid else 0)

        # Check F3+C clipboard coords safely
        clip = _read_clipboard_unicode()
        if clip:
            m = PAT_F3C.search(clip)
            if m:
                dim = m.group(1).replace("minecraft:", "").replace("the_", "").title()
                x = int(float(m.group(2)))
                y = int(float(m.group(3)))
                z = int(float(m.group(4)))
                self._last_coords = f"{x} / {y} / {z} ({dim})"

        # Check live server ping every 6 seconds if server address known
        srv = self._server_addr
        if srv and (time.time() - self._last_ping_check > 6.0):
            self._last_ping_check = time.time()
            try:
                import network_hub
                host, port = (srv.split(":", 1)[0], int(srv.split(":", 1)[1])) if ":" in srv else (srv, 25565)
                res = network_hub.ping_minecraft_server(host, port, timeout=1.5)
                self._last_ping_ms = res.get("latency_ms") if res.get("online") else None
            except Exception:
                self._last_ping_ms = None

        lines = [
            f"MOON HUD  •  {now_clock}  •  [F8 Hide]",
            f"Profile : {self._version_name[:26]}",
            f"Memory  : {ram_txt}   |   Session: {format_duration(sess_sec)} (Total {format_duration(total_sec)})",
        ]
        if self._last_ping_ms is not None:
            lines.append(f"Server  : {srv} ({self._last_ping_ms} ms)")
        elif srv:
            lines.append(f"Server  : {srv}")
        if self._last_coords:
            lines.append(f"Coords  : {self._last_coords}  [F3+C]")
        lines.append(f"Audio   : {self._audio_preset.upper()}")
        return "\n".join(lines), game_pid

    def _run_tk_loop(self):
        try:
            import tkinter as tk
        except Exception:
            return

        TRANS_BG = "#010101"
        root = tk.Tk()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.configure(bg=TRANS_BG)
        if sys.platform == "win32":
            try:
                root.wm_attributes("-transparentcolor", TRANS_BG)
                root.wm_attributes("-alpha", 0.90)
            except Exception:
                pass
        root.geometry("+18+18")

        frame = tk.Frame(root, bg="#0f172a", highlightbackground="#6366f1", highlightthickness=2, padx=10, pady=7)
        frame.pack()
        lbl = tk.Label(
            frame,
            text="MOON HUD Initializing...",
            font=("Consolas", 9, "bold"),
            fg="#e2e8f0",
            bg="#0f172a",
            justify="left",
            anchor="w",
        )
        lbl.pack()

        if sys.platform == "win32":
            try:
                root.update_idletasks()
                hwnd = int(root.winfo_id())
                # Parent wrapper hwnd when overrideredirect is used
                GWL_EXSTYLE = -20
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                user32 = ctypes.windll.user32
                top_hwnd = user32.GetParent(hwnd) or hwnd
                ex = user32.GetWindowLongW(top_hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(top_hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            except Exception:
                pass

        f8_down_prev = False

        def _tick():
            nonlocal f8_down_prev
            if self._stop_evt.is_set() or not self._enabled:
                try:
                    root.destroy()
                except Exception:
                    pass
                return

            if sys.platform == "win32":
                state_f8 = ctypes.windll.user32.GetAsyncKeyState(0x77)  # VK_F8
                is_down = bool(state_f8 & 0x8000)
                if is_down and not f8_down_prev:
                    self._manual_hidden = not self._manual_hidden
                f8_down_prev = is_down

            txt, game_pid = self._collect_telemetry_text()
            should_show = not self._manual_hidden
            if should_show and not self._pin_visible and sys.platform == "win32" and game_pid:
                fg = ctypes.windll.user32.GetForegroundWindow()
                fg_pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(fg, ctypes.byref(fg_pid))
                if fg_pid.value != game_pid:
                    should_show = False

            if should_show:
                lbl.config(text=txt)
                root.deiconify()
            else:
                root.withdraw()

            root.after(250, _tick)

        root.after(80, _tick)
        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            try:
                lbl = None
                frame = None
                root.quit()
                root = None
            except Exception:
                pass


GLOBAL_HUD_OVERLAY = MoonHudOverlay()
