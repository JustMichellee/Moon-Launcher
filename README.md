# Moon Launcher v2.5.1

**Desktop GUI & Interactive CLI Minecraft Launcher Studio for Windows**

[![Version](https://img.shields.io/badge/Release-v2.5.1-6366f1.svg)](https://github.com/JustMichellee/Moon-Launcher/releases/tag/v2.5.1)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-0078D6.svg)](https://github.com/JustMichellee/Moon-Launcher/releases/latest)
[![Python](https://img.shields.io/badge/Runtime-Python%203.11-3776AB.svg)](https://www.python.org/)
[![Companion Mod](https://img.shields.io/badge/Companion%20Mod-Java%208%20Multi--Loader-10B981.svg)](https://github.com/JustMichellee/Moon-Launcher/releases/tag/v2.5.1)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

Moon Launcher is a dual-interface (**Desktop Studio GUI** and **Interactive CLI**) Minecraft launcher for Windows engineered around clean profile isolation, unified identity management, native multiplayer tunneling, Discord Rich Presence, and an in-game multi-loader companion mod.

Every public release is distributed exclusively through a single Windows Setup Installer (`Moon-Launcher-Setup-v2.5.1.exe`). Running the installer deploys both **Moon Launcher (GUI)** and **Moon Launcher (CLI)** together, registers Windows system integrations, and initializes a clean user workspace on first launch with zero external `.minecraft` pollution.

---

## Key Capabilities

### 1. Guided Windows Setup & Clean First-Run Workspace
- **Unified Setup Installer (`Moon-Launcher-Setup-v2.5.1.exe`)**: Installs both `Moon-Launcher-GUI.exe` and `Moon-Launcher-CLI.exe` alongside bundled assets, templates, default skin, and `moon-sync` companion mod JARs.
- **Native Windows Integration**: Automatically registers Start Menu shortcuts (`Moon Launcher`, `Moon Launcher (CLI)`, `Uninstall`), Windows Search (`App Paths`), optional Desktop shortcut, Windows Installed Apps entry, the `moon://` URI protocol handler, and optional user `PATH` registration for terminal usage.
- **Isolated User Storage**: Automatically resolves writable user data to `%LOCALAPPDATA%\MoonLauncher` when installed in protected directories (or custom `MOON_LAUNCHER_HOME`). Fresh installations initialize cleanly with zero preloaded instances.

### 2. Dual Interface: Desktop GUI & Interactive CLI
- **Desktop GUI (`Moon-Launcher-GUI.exe`)**: PyWebView desktop application with dashboard instance switching, Create Instance wizard, Modrinth catalog browser, interactive modpack/resource/shader pack managers, account switcher, skin studio, server browser, crash analyzer, and hardware/settings studio.
- **Interactive CLI (`Moon-Launcher-CLI.exe`)**: Terminal console supporting direct automation flags (`/status`, `/play`, `/install`, `/account`, `/java`, `/friend`, `/host`, `/skin`, `/mods`, `/fix`, `/crash`, `/update`) as well as interactive command-line studio navigation.

### 3. Moon Client Companion Mod (`moon-sync`) & In-Game Fabric Addon (`moon-ingame`)
Automatically deployed and kept synchronized inside every modded profile (`Fabric`, `Quilt`, `Forge 1.8–1.12.2`, `Forge 1.13–1.21+`, and `NeoForge`):
- **In-Game Social & Multiplayer Hub**: Runs an embedded localhost web hub (`http://127.0.0.1:<port>/`) and headless-safe Windows System Tray companion (`Moon Client Hub`) without depending on version-fragile obfuscated Minecraft GUI classes.
- **Native In-Game Fabric Mixin Addon (`moon-ingame`, MC 1.20.1 & 1.21.1)**: Automatically installed alongside `moon-sync` for Fabric profiles — adds Pause Screen `Share World (P2P)` (1-click auto-publish LAN + P2P without manual Open-to-LAN steps) and `Moon Client Menu` buttons, Multiplayer Screen quick room-code/friend-code P2P Direct Join, **Right-Shift HUD Menu + Drag-and-Drop HUD Position Editor**, customizable FPS/Ping/Coords/Keystrokes+CPS/Armor/Totem/Potion HUD, Smooth Zoom (`[C]`), Server-Safe Camera-Only Freelook (`[V]`), Fullbright, vanilla-compliant ToggleSprint/ToggleSneak, Auto-GG (anti-bait protected), and **Fair-Play Guard** (zero macros/packet-cheats; automatically locks Freelook on Hypixel, Minemen, CubeCraft, PvP Legacy, MCC Island, and other competitive servers).
- **Direct P2P UDP Hole-Punching & Relayed Fallback**: Includes custom STUN + Cloudflare D1 signaling (`p2p_tunnel.py`) for direct room-code multiplayer (`MOON-XXXX`) with automatic TCP relay / Playit fallback.
- **Moon ID & Cloudflare D1 Cloud Sync**: Connects persistent **Moon ID (`MOON-XXXX`)** directly to an always-on **Cloudflare Workers + D1** backend (`players`, `presence`, `friendships`, `parties`, `messages`, `shared_screenshots`, `pack_shares`, `p2p_sessions`, `user_profiles`), supporting zero-setup friend lookup, bidirectional friend requests, party invites + Follow Leader, cross-game whisper & party chat, screenshot sharing, `MOON-PACK-XXXX` pack share codes, and cloud profile/keybind/server sync.
- **Client QoL, Overlay & Auto-Backup (`client_qol.py`)**: Always-on-top Windows telemetry overlay (`Alt+Shift+M`), Windows per-app Audio Mixer & Borderless Fullscreen toggle, quick Gamma boost, automatic compressed world backups (`saves/`), and Modrinth mod updater / compatibility checker.
- **Multiplayer Host & 1-Click Join**: Bridges directly with P2P / Playit hosting (`/host`) for world sharing, provides in-game Direct Connect (`ConnectScreen`) or `moon-rejoin.json` friend joining, and includes a TCP Minecraft Server List Pinger (MOTD, latency, player counts).
- **Client Utility Tools**: Mod manifest scanner & SHA-256 sync engine (`SyncEngine` with automatic exclusion of client-only optimization mods such as Sodium, Iris, Embeddium, Oculus, and FerriteCore), per-instance mod toggle, screenshot gallery, world coordinate waypoints (`moon-notes.json`), and live JVM memory telemetry.

### 4. Authentication, Skins & Identity Decoupling
- **Microsoft OAuth2 & Offline Accounts**: Sign in with Microsoft / Xbox Live / Minecraft Java Edition (`src/auth_ms.py`) with multi-account switching and removal, alongside full offline profile support.
- **Standard Offline UUID & Username Validation**: Enforces Mojang-standard `[A-Za-z0-9_]{3,16}` username rules and RFC/Mojang-compliant `OfflinePlayer` UUIDv3 hashes, synchronized into `launch_args.txt`.
- **Decoupled Skin & Cape System**: Validates 64x64 / 64x32 PNG textures, supports classic/slim (`auto`, `classic`, `slim`) arm models and custom capes, keeps skin assets decoupled from username renames via `skins/active_skin.png`, and auto-syncs skins across LAN / Radmin VPN peers and CustomSkinLoader profiles.

### 5. Discord Rich Presence (RPC)
- **Full GUI & CLI Synchronization**: Native Windows Discord IPC pipe client (`\\.\pipe\discord-ipc-*`) initialized across both GUI and CLI with live enable/disable control from Settings.
- **Rich Activity Tracking**: Displays launcher idle state (`In Moon Launcher Studio` / `Idle in Launcher`), active profile, modpack artwork or default Minecraft icon, player avatar bust, and real-time in-game world, dimension (`Overworld`, `The Nether`, `The End`), or multiplayer server monitoring.

### 6. Instance, Runtime & Diagnostics Tooling
- **1-Click Adoptium Temurin Java Installer**: Automatically checks required Java versions (Java 8, 17, or 21) and downloads/extracts portable Temurin runtimes when missing.
- **Modrinth & Archive Installer**: Supports Modrinth search & `.mrpack` / `.zip` modpack imports as well as clean Vanilla, Fabric, Quilt, Forge, and NeoForge instance creation.
- **Diagnostics & Self-Repair**: Automated launch-argument sanitizer (`ensure_launch_args`), crash log root-cause analyzer (`/crash`), preflight check (`/test`), and profile repair (`/fix`).

---

## Installation

1. Download **`Moon-Launcher-Setup-v2.5.1.exe`** from the [Releases](https://github.com/JustMichellee/Moon-Launcher/releases/tag/v2.5.1) page.
2. Run the setup wizard and choose your preferred installation directory and integration tasks (Desktop shortcut, `moon://` URI handler, CLI `PATH`).
3. Launch **Moon Launcher** or **Moon Launcher (CLI)** directly from the **Windows Start Menu**, **Windows Search**, or Desktop shortcut.
4. *(Optional Self-Hosted Cloud DB)*: Global Moon ID friends sync and `MOON-PACK-XXXX` sharing work out of the box via Cloudflare Workers + D1. To override with your own Cloudflare Worker endpoint (`cloudflare-worker/`) or Supabase project, configure it in **Settings -> Cloud Database** or via `/cloud setup`.

---

## CLI Command Reference

| Command | Category | Description |
| :--- | :--- | :--- |
| `/play` | Runtime | Launch the active Minecraft instance |
| `/status` | Runtime | Display profile, Java runtime, memory, RPC, and LAN diagnostics |
| `/test` | Runtime | Run preflight validation before launching |
| `/fix` | Runtime | Repair launch arguments, natives, CustomSkinLoader, and `moon-sync` |
| `/crash` | Runtime | Analyze the latest crash report or exit failure |
| `/install [target]` | Instances | Install Vanilla, Fabric, Quilt, Forge, NeoForge, or Modrinth packs |
| `/version [name]` | Instances | List or switch the active installed instance |
| `/remove <name>` | Instances | Uninstall an installed instance |
| `/account [login\|list]` | Identity | Microsoft OAuth2 login and account switcher |
| `/skin <url\|file\|reset>` | Identity | Apply or reset player skin (`classic`/`slim`) or friend skin |
| `/java install <8\|17\|21>` | Runtime | Download and configure portable Adoptium Temurin Java |
| `/friend [list\|add\|accept\|join]` | Social | Manage Moon ID (`MOON-XXXX`) friends and requests |
| `/host [start\|stop\|scan]` | Multiplayer | Start/stop Playit internet world tunnel or scan LAN |
| `/server [list\|add]` | Multiplayer | Manage and ping saved Minecraft servers |
| `/cloud [status\|setup]` | Cloud | Inspect or override Cloudflare Worker / Supabase cloud endpoint |
| `/mods [filter]` | Mods | List, enable, or disable `.jar` mods in active instance |
| `/setting` | Config | Open interactive terminal Settings Studio |

---

## Repository Structure

```text
Moon-Launcher/
├── assets/                   # Icons, brand assets, default Minecraft artwork
├── build/                    # PyInstaller .spec files & Inno Setup script (Moon-Launcher-Setup.iss)
├── cloudflare-worker/        # Cloudflare Workers + D1 backend (`src/index.js`, `schema.sql`, `wrangler.toml`)
├── gui/                      # Desktop Studio HTML/CSS/JS frontend assets
├── moon-sync-mod/            # Universal Java 8 companion mod sources & build_mod.ps1
├── scripts/                  # Development runners and unified build script (build.ps1)
├── skins/                    # Default Player.png skin template
├── src/                      # Modular Python backend (paths, auth_ms, launcher, network_hub, gui_app, cli, ...)
├── templates/                # Sanitized launch_args.txt, CustomSkinLoader & Log4j templates
├── launcher_config.json      # Clean default configuration template
├── friends.json              # Clean default friends & servers template
├── supabase_schema.sql       # Legacy optional PostgreSQL schema for Supabase self-hosting
├── version.json              # Release metadata (v2.5.1)
└── requirements.txt          # Python build/runtime dependencies
```

---

## Building from Source

### Prerequisites
- Windows 10 / 11 (x64)
- Python 3.11+ (`pip install -r requirements.txt`)
- JDK 8+ (for `javac --release 8` compilation of `moon-sync-mod`)
- Inno Setup 6 (`ISCC.exe`, required to compile the Windows Setup Installer)

### Development & Packaging Commands

```powershell
# Install Python dependencies
pip install -r requirements.txt

# Run Desktop GUI or CLI directly from source
python src\gui_app.py
python src\cli.py

# Build multi-loader mod JARs, GUI/CLI executables, and Windows Setup Installer
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1
```

Compiled release output: `dist\releases\Moon-Launcher-Setup-v2.5.1.exe`.

---

## Credits & License

Maintained by [@JustMichellee](https://github.com/JustMichellee) and [@Epithap](https://github.com/Epithap).

Licensed under the [MIT License](LICENSE).
