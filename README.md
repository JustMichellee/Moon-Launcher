# 🌙 Moon Launcher
### *High-Performance CLI Minecraft Launcher Studio*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Architecture: Pure Python](https://img.shields.io/badge/Dependencies-0%20External%20Pip-success.svg)](#-key-architectural-highlights)
[![Multiplayer: Anycast + LAN](https://img.shields.io/badge/Multiplayer-Global%20Anycast%20%26%20LAN%20P2P-purple.svg)](#-global-multiplayer--anycast-tunneling)
[![Skins: CustomSkinLoader + P2P](https://img.shields.io/badge/Skins-Universal%20CSL%20%26%20LAN%20Auto--Sync-green.svg)](#-universal-skin--cape-system)

---

```ascii
  __  __                       _                             _               
 |  \/  | ___   ___  _ __     | |    __ _ _   _ _ __   ___| |__   ___ _ __ 
 | |\/| |/ _ \ / _ \| '_ \ ___| |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|
 | |  | | (_) | (_) | | | |___| |__| (_| | |_| | | | | (__| | | |  __/ |   
 |_|  |_|\___/ \___/|_| |_|   |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|   
                                                                            
  High-Performance Command Line Interface Minecraft Launcher Studio
  Copyright (c) 2026 JustMichellee & Epithap • Licensed under MIT
```

---

## Table of Contents
- [📖 Overview](#-overview)
- [🌟 Key Architectural Highlights](#-key-architectural-highlights)
- [📁 Directory Structure & Architecture](#-directory-structure--architecture)
  - [📂 Directory Reference Guide](#-directory-reference-guide)
- [💻 System Requirements](#-system-requirements)
- [🚀 Installation & Quick Start](#-installation--quick-start)
- [⌨️ Command Matrix & CLI Reference](#-command-matrix--cli-reference)
  - [Gameplay & Runtime](#gameplay--runtime)
  - [Multiplayer & Networking](#multiplayer--networking)
  - [Modpack & Version Management](#modpack--version-management)
  - [Configuration & Customization](#configuration--customization)
  - [File System & Utility](#file-system--utility)
- [🌐 Global Multiplayer & Anycast Tunneling](#-global-multiplayer--anycast-tunneling)
  - [1. Global Internet Tunneling (/host)](#1-global-internet-tunneling-host)
  - [2. Virtual LAN & Radmin VPN Integration](#2-virtual-lan--radmin-vpn-integration)
  - [3. Friend & Server Management Studio](#3-friend--server-management-studio)
- [🎭 Universal Skin & Cape System](#-universal-skin--cape-system)
  - [The Offline Minecraft Skin Dilemma](#the-offline-minecraft-skin-dilemma)
  - [Native Zero-Config LAN & Radmin P2P Skin Auto-Sync](#native-zero-config-lan--radmin-p2p-skin-auto-sync)
  - [11-Tier Multi-Provider Fallback Hierarchy](#11-tier-multi-provider-fallback-hierarchy)
  - [Custom Capes & Elytras Support](#custom-capes--elytras-support)
  - [CLI Skin Commands](#cli-skin-commands)
- [📦 Modpack & Version Management Studio](#-modpack--version-management-studio)
  - [Modrinth Search & Live APT Installer](#modrinth-search--live-apt-installer)
  - [Standalone Mod Loader Installation](#standalone-mod-loader-installation)
  - [Profile Isolation Architecture](#profile-isolation-architecture)
  - [Interactive Mod Manager (/mods)](#interactive-mod-manager-mods)
- [🛡️ Diagnostics, Crash Watchdog & Self-Repair](#-diagnostics-crash-watchdog--self-repair)
  - [Pre-Flight Diagnostic Suite (/test)](#pre-flight-diagnostic-suite-test)
  - [One-Click Self-Repair Engine (/fix)](#one-click-self-repair-engine-fix)
  - [Automated Crash Watchdog (/crash)](#automated-crash-watchdog-crash)
- [⚙️ Configuration & Settings Studio](#-configuration--settings-studio)
- [❓ Troubleshooting & Comprehensive FAQ](#-troubleshooting--comprehensive-faq)
- [👥 Collaborators & Credits](#-collaborators--credits)
- [📜 License](#-license)

---

## 📖 Overview

**Moon Launcher** is an ultra-fast, keyboard-driven Command Line Interface (CLI) Minecraft Launcher Studio engineered from the ground up for players, server hosts, and modders who prioritize raw performance, zero bloat, and total configuration autonomy.

Traditional modern launchers suffer from sluggish web wrappers (Electron/Chromium), intrusive advertisements, opaque telemetry background services, and complex login hurdles. Moon Launcher redefines the experience by running on **pure Python standard library** with zero external pip dependencies—delivering lightning-fast sub-50ms boot times, seamless zero-config internet hosting, rich Discord Rich Presence, and automated client health diagnostics.

Whether launching vanilla releases, heavily modded Forge/Fabric/NeoForge/Quilt modpacks, or hosting LAN worlds for friends across the globe, Moon Launcher delivers an unmatched, streamlined desktop experience.

---

## 🌟 Key Architectural Highlights

### 1. Pure Python Standard Library Architecture
- **Zero Third-Party Dependencies**: No `pip install`, no wheel compiling, no external Python package maintenance. Runs directly out of the box on Python 3.8+.
- **Zero Bloat & Telemetry**: No background telemetry daemons, no tracking, and no CPU/RAM overhead while Minecraft is running.
- **Instantaneous Startup**: Cold-boots to the interactive CLI in under 50 milliseconds.

### 2. Zero-Config Global P2P Anycast Tunneling (`/host`)
- **Play Singleplayer Worlds with Remote Friends**: Seamlessly host singleplayer / LAN worlds over the public Internet.
- **No Port Forwarding Required**: Fully circumvents carrier-grade NAT (CGNAT), router firewall restrictions, and ISP blocks without router admin access.
- **Zero Third-Party VPN Software**: Eliminates the need for Radmin VPN, Hamachi, or third-party virtual network adapters.
- **Instant Public Anycast Endpoints**: Generates a public DNS domain (e.g. `*.playit.gg:port`) that remote players can paste directly into the standard Minecraft Multiplayer menu.

### 3. Native Zero-Config LAN & Radmin P2P Skin Auto-Sync Engine
- **Instant Background Skin Exchange**: Background peer service running on UDP and TCP port `25564` automatically discovers and exchanges custom player skins with other Moon Launcher users on local Wi-Fi or Radmin VPN (`26.x.x.x`).
- **Zero Manual Setup**: No need to upload skins to third-party websites or share files manually. Simply open the launcher and your skins are automatically shared and rendered in-game.
- **100% Offline Capable**: Operates seamlessly over isolated local area networks with zero internet connection required.

### 4. Native Discord Rich Presence V2 (Direct IPC Pipe)
- **Direct IPC Named Pipe Engine**: Interacts directly with the local Discord client via Windows named pipe (`\\.\pipe\discord-ipc-0`) without requiring `pypresence` or third-party wrappers.
- **Dynamic In-Game Detection**:
  - 🏠 **Launcher Status**: Shows active profile, installed mod counts, and memory configuration.
  - 🕹️ **Singleplayer Gameplay**: Dynamically inspects world folders and parses live NBT level data to display current world names.
  - 🌐 **Multiplayer & Co-op**: Detects connected server IP addresses, LAN broadcasts, virtual networks, and active Anycast tunnels.
  - 👤 **Player Head Avatars**: Automatically extracts and displays the player's 2D skin head avatar directly in Discord.
  - 🖼️ **Dynamic Modpack Logos**: Automatically uploads local profile icons (`icon.png`); defaults to the official Minecraft grass block icon if no custom logo is found.

### 5. Universal Offline & Online Skin Integration (CustomSkinLoader CSL)
- **Universal Multi-Loader Deployment**: Automatically configures and deploys CustomSkinLoader across Forge, Fabric, NeoForge, and Quilt profiles.
- **Local-First Zero-Latency Pipeline**: Resolves skins locally from `skins/<username>.png` with 0ms delay.
- **Multi-Provider Fallback**: Seamlessly falls back to Mojang, TLauncher, ElyBy, LittleSkin, BlessingSkin, and MCHeads.
- **Friend Skin Synchronization**: Set custom skins for yourself (`/skin <url|file|player>`), assign friend skins (`/skin friend <name> <url>`), or inspect active peer sync status (`/lan`).

### 6. Intelligent Diagnostics & Self-Repair Engine
- **Pre-Flight Diagnostics (`/test`)**: Audits Java runtime compatibility (Java 8 vs 17 vs 21), verifies client JAR checksums, checks LWJGL native DLLs, and performs simulated dry-run boots.
- **One-Click Auto-Repair (`/fix`)**: Automatically regenerates corrupted launch argument files, re-links missing native libraries, purges 0-byte corrupted mod JARs, and synchronizes CustomSkinLoader configurations.
- **Crash Watchdog (`/crash`)**: Real-time process monitor that detects abnormal terminations, parses `crash-reports/` and `logs/latest.log`, and pinpoints the exact culprit mod JAR causing the failure.

### 7. Interactive Terminal Studio & APT-Style Installer
- **Border-Protected Unicode Dashboard**: Clean, responsive terminal UI with single-character quick access keys (`1` Play, `2` Settings, `3` Status, `4` Version, `5` Remove).
- **Ubuntu APT-Styled Modpack Installer (`/install`)**: Search and download modpacks from Modrinth, install raw `.mrpack` files, or set up clean Forge, Fabric, NeoForge, or Vanilla runtimes with live terminal progress bars.

---

## 📁 Directory Structure & Architecture

Moon Launcher organizes both its lightweight launcher engine and local Minecraft runtime data within an intuitive, fully documented modular structure:

```text
Moon-Launcher/
│
├── launcher.py                    # Core launcher engine, Discord IPC & CLI studio
├── network_hub.py                 # P2P Anycast multiplayer tunneling, LAN skin sync & friends
├── Moon Launcher.bat              # 1-Click Windows launch script (auto-detects Python)
├── launcher_config.json           # User configuration (RAM, player nickname, resolution)
├── friends.json                   # Multiplayer contacts, saved friend hosts & bookmarks
│
├── assets/                        # Minecraft assets (sounds, textures, fonts, title logos)
├── config/                        # Global mod configuration files & client settings
├── libraries/                     # Java runtime dependencies, LWJGL natives & loaders
├── logs/                          # Game output logs (latest.log) & debug information
├── mods/                          # Active mod JARs for the primary game profile
├── resourcepacks/                 # Custom texture packs, audio packs, and UI themes
├── runtime/                       # Bundled Java runtimes and networking binaries
├── saves/                         # Singleplayer worlds, LAN saves & dimension data
├── shaderpacks/                   # Graphical shader packs (Embeddium / Oculus / Iris)
├── skins/                         # Local skin storage (0ms offline CustomSkinLoader cache)
├── templates/                     # CustomSkinLoader templates & engine libraries
├── versions/                      # Installed Minecraft version profiles (Forge, Fabric, NeoForge)
│
├── .gitattributes                 # Git LFS tracking configuration
├── .gitignore                     # Git filter for temporary caches, saves, and logs
├── LICENSE                        # MIT Open-Source License
└── README.md                      # Official documentation
```

### 📂 Directory Reference Guide

| Directory | Purpose & Function |
|---|---|
| **`assets/`** | Stores Minecraft game sound effects, music, language files, and launcher icons. |
| **`config/`** | Contains `.json`, `.toml`, and `.cfg` configuration files for installed mods and loaders. |
| **`libraries/`** | Java class libraries, Forge/Fabric dependencies, and LWJGL native binaries (`.dll`). |
| **`logs/`** | Minecraft runtime logs (`latest.log`) and launcher activity records parsed by `/crash`. |
| **`mods/`** | Storage for active `.jar` mod files. Managed dynamically via `/mods` (enable, disable, filter). |
| **`resourcepacks/`** | Texture packs, custom models, and visual overhauls placed by the player. |
| **`runtime/`** | Isolated 64-bit Java runtimes (JRE 8 for legacy versions, OpenJDK 17/21 for modern). |
| **`saves/`** | Singleplayer world saves, player inventories, and NBT level data tracked by `/host`. |
| **`shaderpacks/`** | High-performance GLSL shader packs utilized by Oculus/Embeddium or Iris. |
| **`skins/`** | High-speed local cache for player and friend skins rendered via CustomSkinLoader. |
| **`templates/`** | Pre-configured `CustomSkinLoader.json` templates and universal skin loader JARs. |
| **`versions/`** | Individual Minecraft profiles and version JARs (e.g. `1.20.1-Forge`, `Fabric-1.21`). |

> [!NOTE]
> When cloning or downloading Moon Launcher from GitHub, only the core engine files, templates, and assets are downloaded. Runtime directories such as `saves/`, `skins/`, `mods/`, and `versions/` are automatically created on-demand as soon as you install a version or boot up Minecraft.

---

## 💻 System Requirements

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | Windows 10 (64-bit) / Windows 11 | Windows 10/11 (64-bit) |
| **Python** | Python 3.8+ (64-bit) | Python 3.11+ (64-bit) |
| **Java Runtime** | OpenJDK 8 / 17 / 21 | Eclipse Temurin / Azul Zulu OpenJDK |
| **System Memory (RAM)** | 4 GB | 16 GB+ (Allocate 6–10 GB for modpacks) |
| **Storage** | 500 MB free storage | Solid State Drive (SSD) with 10 GB+ free space |
| **Network** | Offline or Broadband | High-speed Internet for modpack downloads & hosting |

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
- **Python 3.8 or Newer**: Download and install from [python.org](https://www.python.org/downloads/). Ensure you check **"Add Python to PATH"** during installation.
- **Java Runtime Environment (JRE/JDK)**:
  - **Minecraft 1.18 to 1.21+**: Java 17 or Java 21 (64-bit)
  - **Minecraft 1.12.2 and older**: Java 8 (64-bit)

### 2. Download / Clone the Repository
Clone the repository to your preferred local directory:
```bash
git clone https://github.com/JustMichellee/Moon-Launcher.git C:\Moon-Launcher
```

### 3. Launch Moon Launcher Studio
Double-click **`Moon Launcher.bat`** or execute via terminal:
```powershell
cd C:\Moon-Launcher
python launcher.py
```

### 4. Configure Your Profile & Launch
Upon launching Moon Launcher for the first time:
1. **Set Player Username**: Type `/setting user <YourNickname>` (or `/user <YourNickname>`).
2. **Install a Minecraft Version**: Type `/install` to open the installer, or install directly:
   ```text
   /install fabric 1.20.1
   ```
3. **Launch the Game**: Type `/play` or press `1`.

---

## ⌨️ Command Matrix & CLI Reference

Moon Launcher features a comprehensive command-line interface. Commands can be issued at any interactive prompt:

### Gameplay & Runtime
| Command | Shortcut | Description |
|---|---|---|
| `/play` | `1` | Launch the active Minecraft profile with optimized JVM arguments |
| `/test` | `t` | Run pre-flight diagnostics, verify JAR checksums, and simulate boot |
| `/fix` | `f` | Automatically repair missing native DLLs, launch arguments, or config errors |
| `/status` | `3` | Display active profile details, Java runtime version, RAM, and mod counts |
| `/crash` | `diag` | Inspect the latest crash report with automated root-cause stack trace analysis |

### Multiplayer & Networking
| Command | Arguments | Description |
|---|---|---|
| `/host` | `start [port]` | Start a zero-config Anycast P2P internet tunnel for your LAN world |
| `/host` | `stop` | Terminate the active multiplayer internet tunnel |
| `/host` | `scan` | Scan and discover open LAN worlds on your local Wi-Fi or virtual network |
| `/lan` | `[sync]` | View native LAN & Radmin P2P skin auto-sync status and probe network |
| `/invite` | — | Generate and auto-copy a 1-click multiplayer join link with your public IP |
| `/friend` | `[list]` | Display your contacts table with live server latency (ms) and online status |
| `/friend` | `add <link|name>` | Add a friend via their invite link or `username [ip:port]` |
| `/friend` | `ping <name>` | Query real-time latency and player count for a friend's hosted world |
| `/friend` | `remove <name>` | Delete a friend from your saved contacts |
| `/server` | `add <name> <ip>` | Bookmark a multiplayer server to your favorites list |
| `/server` | `ping <ip>` | Query server latency, player count, MOTD, and Minecraft version |

### Modpack & Version Management
| Command | Arguments | Description |
|---|---|---|
| `/version` | `[name]` / `4` | List all detected local versions and switch active profile |
| `/install` | — | Open the interactive Modpack & Version Installer Studio |
| `/install` | `<modpack_name>` | Search and install modpacks directly from Modrinth |
| `/install` | `forge [version]` | Install clean Minecraft Forge (e.g. `1.20.1`, `1.12.2`) |
| `/install` | `fabric [version]`| Install clean Fabric Loader (e.g. `1.20.1`, `1.21.1`) |
| `/install` | `neoforge [v]`    | Install clean NeoForge Loader (e.g. `1.20.4`, `1.21.1`) |
| `/install` | `quilt [version]` | Install clean Quilt Loader (e.g. `1.20.1`) |
| `/install` | `vanilla [version]`| Install official vanilla Minecraft release |
| `/install url`| `<mrpack_url>` | Download and install `.mrpack` directly from web URL |
| `/remove` | `<name>` / `5` | Safely uninstall a modpack profile and reclaim disk storage space |

### Configuration & Customization
| Command | Arguments | Description |
|---|---|---|
| `/setting` | `2` | Open the interactive Terminal Settings Studio (TUI) |
| `/setting ram` | `<gb>` | Configure maximum JVM heap memory (e.g. `/setting ram 10`) |
| `/setting minram`| `<gb>` | Configure initial JVM heap memory (e.g. `/setting minram 4`) |
| `/setting user` | `<username>` | Update active player username |
| `/setting res` | `<width> <height>`| Set client window resolution (e.g. `/setting res 1920 1080`) |
| `/setting java` | `<path>` | Set explicit path to custom `javaw.exe` runtime binary |
| `/skin` | `<url|file|player>` | Apply custom player skin PNG directly |
| `/skin friend` | `<name> <url|file>` | Map a custom skin to a friend for in-game multiplayer rendering |
| `/skin lan` | `[sync]` | View LAN & Radmin peer skin auto-sync hub |

### File System & Utility
| Command | Arguments | Description |
|---|---|---|
| `/mods` | `[query]` | Display active mods table with file sizes; filter by search term |
| `/mods disable`| `<name|index>` | Disable a mod safely by appending `.disabled` |
| `/mods enable` | `<name|index>` | Re-enable a previously disabled mod |
| `/open` | `[folder]` | Open folder in Windows Explorer (`mods`, `saves`, `logs`, `crash`, `skins`) |
| `/clear` | `/cls` | Clear terminal screen and redraw Moon Launcher banner |
| `/help` | `[topic]` | Display topic-specific documentation (e.g. `/help host`, `/help install`) |
| `/exit` | `/quit` | Terminate the launcher process safely |

---

## 🌐 Global Multiplayer & Anycast Tunneling

Moon Launcher revolutionizes Minecraft multiplayer. It offers three distinct, friction-free multiplayer topologies designed to fit every scenario:

```
                               ┌───────────────────────────┐
                               │   Moon Launcher Network   │
                               └─────────────┬─────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
    1. Global Internet               2. Virtual LAN                  3. Local Wi-Fi
   Anycast Tunnel (/host)         (Radmin VPN / ZeroTier)           (Physical Subnet)
   • Bypasses CGNAT & firewalls   • Subnet discovery (26.x.x.x)     • 0ms local ping
   • Zero port forwarding         • P2P skin auto-sync              • Instant LAN detection
   • Public domain endpoint       • Low-latency direct mesh         • 100% offline-ready
```

### 1. Global Internet Tunneling (`/host`)
Host your local singleplayer world to friends across the globe without purchasing expensive servers, port-forwarding home routers, or asking friends to download VPN clients:

1. **Open World to LAN**: Inside Minecraft, pause the game and select **Open to LAN**. Note the 5-digit port (e.g. `52341`).
2. **Start the Tunnel**: In Moon Launcher CLI, execute:
   ```text
   /host start 52341
   ```
   *(If you omit the port, Moon Launcher automatically listens on UDP 4445 and detects the active LAN port).*
3. **Obtain Public Endpoint**: Moon Launcher automatically provisions an encrypted Playit.gg Anycast tunnel:
   ```text
   Public Address: emerald-tiger.playit.gg:38921
   ```
4. **Share with Friends**: Remote players paste `emerald-tiger.playit.gg:38921` directly into Minecraft's **Multiplayer -> Direct Connection** and join immediately.

### 2. Virtual LAN & Radmin VPN Integration
If you and your friends prefer using **Radmin VPN** (`26.x.x.x`) or local network meshes:
- Moon Launcher automatically detects the active Radmin network adapter.
- The built-in **P2P Skin Auto-Sync Daemon** immediately discovers other players on the Radmin network, transferring custom skins in milliseconds without any web upload.
- Players simply connect using the host's Radmin IP and Minecraft LAN port (e.g. `26.79.166.10:52341`).

### 3. Friend & Server Management Studio
- **Generate 1-Click Invite Link**: Type `/invite` or `/friend invite`. Copies both a universal web link and custom protocol link:
  ```text
  moon://invite/eyJ1c2VyIjoiSnVzdE1pY2hlbGxlZSIsImFkZHIiOiIyNi43OS4xNjYuMTA6NTIzNDEifQ==
  ```
- **Add Friend via Link**: Type `/friend add <link>` to automatically parse the friend's nickname, bookmark their server, and query live latency.
- **Query Live Server Status**: Type `/server ping <ip:port>`. Displays real-time ping latency (ms), player counts, MOTD, and server version.

---

## 🎭 Universal Skin & Cape System

### The Offline Minecraft Skin Dilemma
In offline / non-premium Minecraft environments, Mojang's authentication server rejects session queries (HTTP 204 No Content). As a result, vanilla Minecraft clients fail to resolve custom textures, defaulting every player to the generic Steve or Alex skins.

Moon Launcher permanently solves this dilemma through a multi-layered architecture combining **CustomSkinLoader (CSL)** with an automated **LAN & Radmin P2P Skin Auto-Sync Engine**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Moon Launcher Skin Resolution Pipeline                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
     ┌─────────────────────────────────┴─────────────────────────────────┐
     ▼                                                                   ▼
[ONLINE PROVIDERS]                                              [P2P & LOCAL CACHE]
• Mojang API (Original skins)                                   • skins/<user>.png (0ms)
• TLauncher (auth.tlauncher.org)                                • LocalSkin/skins/<user>.png
• ElyBy (skinsystem.ely.by)                                     • LAN & Radmin P2P Auto-Sync
• LittleSkin / BlessingSkin                                       (UDP/TCP Port 25564)
• MCHeads & OptiFine Capes
```

### Native Zero-Config LAN & Radmin P2P Skin Auto-Sync
When playing via local Wi-Fi or virtual LAN (such as Radmin VPN), Moon Launcher eliminates the need to upload skins to the web or manually copy PNG files:

1. **Auto-Discovery Beacon (UDP 25564)**:
   - Moon Launcher listens on UDP port `25564` across all active network adapters (including Radmin VPN's `26.255.255.255` and local `/24` broadcast targets).
   - Every few seconds, it broadcasts an encrypted beacon: `{"magic": "MOON_SKIN_V1", "user": "YourName", "hash": "md5_hash", "port": 25564}`.
2. **Direct TCP Skin Handshake (TCP 25564-25575)**:
   - When Peer B detects Peer A's beacon on the network, Peer B checks its local cache.
   - If Peer A's skin is missing or has an updated hash, Peer B sends an HTTP request (`GET /skin/raw`) directly to Peer A's background daemon.
   - The skin PNG (typically 2 KB – 8 KB) is transmitted and validated in under 10 milliseconds.
3. **Automated Multi-Target Distribution**:
   - The received skin is saved into `skins/<PeerA>.png` and instantly synchronized to:
     - Active profile's `CustomSkinLoader/LocalSkin/skins/<PeerA>.png`
     - Global `%APPDATA%\.minecraft\CustomSkinLoader\LocalSkin\skins/<PeerA>.png`
4. **Immediate Unicast Response**:
   - Peer B immediately responds to Peer A with its own skin beacon, ensuring both players receive each other's skins before entering the world.

> [!TIP]
> You can monitor your active LAN peers and skin synchronization anytime by typing **`/lan`** or **`/skin lan`** in the Moon Launcher console.

### 11-Tier Multi-Provider Fallback Hierarchy
In [CustomSkinLoader.json](templates/CustomSkinLoader.json), Moon Launcher orchestrates an 11-tier fallback order:

| Priority | Provider Name | Type | Target / API Endpoint |
|---|---|---|---|
| **1** | `LocalSkin` | Legacy | `CustomSkinLoader/LocalSkin/skins/{USERNAME}.png` |
| **2** | `LocalSkinRoot`| Legacy | `LocalSkin/skins/{USERNAME}.png` |
| **3** | `LauncherSkins`| Legacy | `skins/{USERNAME}.png` |
| **4** | `Mojang` | MojangAPI | `https://sessionserver.mojang.com/` |
| **5** | `TLauncher` | ElyByAPI | `https://auth.tlauncher.org/skin/profile/texture/login/` |
| **6** | `ElyBy` | ElyByAPI | `https://skinsystem.ely.by/textures/` |
| **7** | `LittleSkin` | CustomSkinAPI | `https://littleskin.cn/csl/` |
| **8** | `BlessingSkin`| CustomSkinAPI | `https://skin.prinzeugen.net/` |
| **9** | `MCHeadsSkin` | Legacy | `https://mc-heads.net/skin/{USERNAME}.png` |
| **10** | `MinecraftCapes`| MinecraftCapesAPI| `https://api.minecraftcapes.net/profile/` |
| **11** | `OptiFine` | Legacy | `https://optifine.net/capes/{USERNAME}.png` |

### Custom Capes & Elytras Support
Moon Launcher fully supports custom capes and elytra textures:
- **Player Capes**: Place a 64x32 PNG at `skins/<username>_cape.png` or `CustomSkinLoader/LocalSkin/capes/<username>.png`.
- **Elytra Textures**: Place a texture at `CustomSkinLoader/LocalSkin/elytras/<username>.png`.
- **OptiFine Capes**: If a player has an official OptiFine cape associated with their nickname, it is loaded automatically in-game.

### CLI Skin Commands
- **Apply Own Skin via URL, Local File, or Player Nickname**:
  ```text
  /skin https://i.imgur.com/example.png
  /skin C:\Users\User\Pictures\MySkin.png
  /skin Notch
  ```
- **Assign a Friend's Skin Manually**:
  ```text
  /skin friend Alex https://i.imgur.com/alex_skin.png
  /skin friend Steve C:\Skins\steve.png
  ```
- **Inspect LAN & Radmin Peer Sync Status**:
  ```text
  /lan
  /lan sync
  ```

---

## 📦 Modpack & Version Management Studio

Managing Minecraft versions, mod loaders, and third-party modpacks in Moon Launcher is fast, transparent, and completely automated.

```
                      ┌────────────────────────────────────────┐
                      │    Moon Launcher Installer Studio      │
                      └───────────────────┬────────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          ▼                               ▼                               ▼
  Modrinth Search Engine          Mod Loader Generator            Local Profile Isolation
  • APT-style progress bar        • Forge / Fabric / NeoForge     • Isolated saves & configs
  • Dependency resolution         • Vanilla official releases     • Zero profile cross-talk
```

### Modrinth Search & Live APT Installer
Moon Launcher features an Ubuntu APT-styled installer. You can search, fetch metadata, and download complete modpacks with live terminal progress indicators:

```text
moon ❯ /install Cobblemon

Reading package lists... Done
Building dependency tree... Done
Reading state information... Done

The following NEW packages will be installed:
  cobblemon-fabric-1.20.1  fabric-loader  client-libraries  asset-index

0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.
Need to get ~42.8 MB of archives.
Get:1 https://cdn.modrinth.com/data/cobblemon.mrpack [42.8 MB]
[########################################] 100.0% (14.2 MB/s)
Extracting modpack index and installing client JARs...
[OK] Installation completed successfully! Profile set to 'Cobblemon'.
```

### Standalone Mod Loader Installation
Install clean mod loaders for any Minecraft version:
```text
/install fabric 1.20.1
/install forge 1.20.1
/install neoforge 1.21.1
/install quilt 1.20.1
/install vanilla 1.20.1
```

### Profile Isolation Architecture
Unlike traditional launchers that dump all mods into a shared `.minecraft/mods` folder, Moon Launcher maintains strict profile isolation:
- Each profile under `versions/<Profile_Name>/` maintains its own dedicated `mods/`, `config/`, `saves/`, `resourcepacks/`, `shaderpacks/`, and `options.txt`.
- Worlds created in a 1.12.2 Forge modpack will never be accidentally corrupted by a 1.20.1 Fabric client.
- Switching between modpacks with `/version <name>` takes less than 1 second.

### Interactive Mod Manager (`/mods`)
Audit, filter, and toggle mods without opening File Explorer:
- **List and Filter Active Mods**:
  ```text
  /mods
  /mods opti
  ```
- **Disable Conflicting Mods Safely**:
  ```text
  /mods disable Sodium
  ```
  *(Appends `.disabled` to the filename, preventing the loader from reading it while preserving the file).*
- **Re-enable Mods**:
  ```text
  /mods enable Sodium
  ```

---

## 🛡️ Diagnostics, Crash Watchdog & Self-Repair

Moon Launcher incorporates enterprise-grade health diagnostics and automated self-repair mechanisms to eliminate crash guesswork.

```
                      ┌────────────────────────────────────────┐
                      │        Moon Launcher Diagnostics       │
                      └───────────────────┬────────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          ▼                               ▼                               ▼
    Java Check                     Asset Integrity                 Crash Log Parser
  (Java 8 / 17 / 21)             (Detects 0-byte JARs)           (Identifies culprit mod)
```

### Pre-Flight Diagnostic Suite (`/test`)
Run simulated pre-flight checks before booting the game:
```text
moon ❯ /test

── Pre-Flight Launch Verification ──
  • Java Runtime Compatibility  : [PASS] OpenJDK 64-Bit Server VM (Java 17.0.10)
  • Client JAR Checksum         : [PASS] 1.20.1-Forge.jar verified
  • LWJGL Native Libraries      : [PASS] 32 native binaries present in natives/
  • Memory Configuration        : [PASS] Max RAM: 8 GB, Min RAM: 2 GB
  • CustomSkinLoader Setup      : [PASS] Universal CSL JAR & config synchronized
  • Log4j Security Status       : [PASS] Patched against CVE-2021-44228
Result: All pre-flight checks passed! Safe to launch.
```

### One-Click Self-Repair Engine (`/fix`)
If your client fails to start or encounters missing libraries, `/fix` executes an automated repair routine:
1. Re-generates `launch_args.txt` parameter files from version JSON metadata.
2. Re-extracts missing LWJGL native binaries (`.dll`).
3. Scans for and purges corrupted 0-byte `.jar` mod files.
4. Re-links and synchronizes `CustomSkinLoader.json` templates.
5. Deploys Log4j vulnerability mitigation XML arguments.

### Automated Crash Watchdog (`/crash`)
When a Minecraft process terminates abnormally (non-zero exit code), Moon Launcher immediately captures the error:
- Parses `crash-reports/*.txt` and `logs/latest.log`.
- Filters out noise and extracts the root cause exception (e.g. `java.lang.NoClassDefFoundError`, `MixinApplyError`).
- Pinpoints the exact mod filename causing the crash and recommends actionable troubleshooting steps.

---

## ⚙️ Configuration & Settings Studio

Moon Launcher provides both an interactive Terminal User Interface (TUI) and direct quick-commands for instant configuration:

```text
moon ❯ /setting

╭─ Settings Studio ───────────────────────────────────────────────╮
│  1. Player Nickname         : JustMichellee                     │
│  2. Maximum Memory (RAM)    : 8 GB (-Xmx8G)                     │
│  3. Minimum Memory (RAM)    : 2 GB (-Xms2G)                     │
│  4. Screen Resolution       : 1920 x 1080 (Windowed)            │
│  5. Java Runtime Path       : Auto-Detect (C:\\Program Files\\...)│
│  6. Discord Rich Presence   : Enabled                           │
│  7. LAN P2P Skin Sync       : Active (Port 25564)               │
│  ──────────────────────────────────────────────────────────────│
│  Enter option number [1-7] to edit, or type /setting <key> <val> │
╰─────────────────────────────────────────────────────────────────╯
```

### `launcher_config.json` Reference

| Key | Type | Default | Description |
|---|---|---|---|
| `username` | String | `"Player"` | Active player nickname displayed in-game and on LAN |
| `ram_max_gb` | Integer | `8` | Maximum heap memory allocated to JVM (`-Xmx`) |
| `ram_min_gb` | Integer | `2` | Initial heap memory allocated to JVM (`-Xms`) |
| `window_width` | Integer | `1920` | Minecraft launch window width in pixels |
| `window_height` | Integer | `1080` | Minecraft launch window height in pixels |
| `java_path` | String | `""` | Explicit path to `javaw.exe` (empty string for auto-detection) |
| `discord_rpc` | Boolean | `true` | Enable or disable native Discord Rich Presence IPC pipe |
| `version_name` | String | `""` | Currently selected Minecraft profile directory |

---

## ❓ Troubleshooting & Comprehensive FAQ

### Q1: The game crashes immediately upon launch with exit code 1 or -1
- **Step 1**: Type `/crash` to inspect the automated stack trace root cause.
- **Step 2**: Run `/fix` to re-synchronize launch arguments and native libraries.
- **Step 3**: Run `/test` to verify Java runtime compatibility and mod file integrity.

### Q2: What Java version should I use?
- **Minecraft 1.18 to 1.21+**: Requires **Java 17 (64-bit)** or **Java 21 (64-bit)**.
- **Minecraft 1.16.5 to 1.17**: Requires **Java 16** or **Java 17**.
- **Minecraft 1.12.2 and older**: Requires **Java 8 (64-bit)**.
- Type `/status` to inspect your currently detected Java runtime.

### Q3: My custom skin is not visible in-game or appears as Steve/Alex
- Verify that your skin is a valid **64x64 PNG** file.
- Type `/skin <path_or_url>` to reload your skin.
- For multiplayer over LAN/Radmin, type `/lan` to ensure the LAN P2P Skin Sync daemon is active.
- Run `/fix` to guarantee that CustomSkinLoader is deployed into your version's `mods/` directory.

### Q4: How does LAN skin auto-sync work over Radmin VPN?
- Moon Launcher automatically detects Radmin VPN's `26.x.x.x` network adapter.
- As long as you and your friends have Moon Launcher open and are in the same Radmin VPN room, skins are automatically exchanged in the background over UDP/TCP port `25564`.
- Type `/lan` in the console to view detected peers and sync status.

### Q5: How much RAM should I allocate?
- **Vanilla Minecraft**: 2 GB to 4 GB (`/setting ram 4`).
- **Light to Medium Modpacks (50 - 120 mods)**: 4 GB to 6 GB (`/setting ram 6`).
- **Heavy Modpacks (150+ mods / Shaders)**: 8 GB to 10 GB (`/setting ram 8`).
- *Tip: Avoid allocating more than 14 GB unless strictly necessary to avoid Java Garbage Collection micro-stutters.*

### Q6: Windows Defender or Antivirus flags `Moon Launcher.bat`
- `Moon Launcher.bat` is an open-source, 3-line batch script that verifies Python is installed in your PATH and launches `launcher.py`. You can inspect its source code in any text editor. It contains zero compiled executables or hidden downloaders.

### Q7: Can I import my worlds and resource packs from another launcher?
- **Yes!** Type `/open saves` to open your active profile's world saves folder, or `/open resourcepacks` for texture packs. Simply copy your existing folders over.

---

## 👥 Collaborators & Credits

**Moon Launcher** is an actively maintained open-source collaborative project:

| Collaborator | GitHub Profile | Primary Responsibilities |
|---|---|---|
| **JustMichellee** | [@JustMichellee](https://github.com/JustMichellee) | Project Lead, Repository Maintainer, UI/UX Design, Testing |
| **Epithap** | [@Epithap](https://github.com/Epithap) | Core Systems Architect, Launcher Engine, Discord IPC Pipe, Anycast Tunnel Integration |

### Upstream Open-Source Acknowledgments:
- **[CustomSkinLoader](https://github.com/xfl03/MCCustomSkinLoader)** — Universal offline & multi-provider skin rendering engine.
- **[Playit.gg](https://playit.gg/)** — Zero-configuration Anycast TCP/UDP tunnel network infrastructure.
- **[Modrinth API](https://docs.modrinth.com/)** — Open-source modpack and version discovery platform.

---

## 📜 License

This project is licensed under the open-source **[MIT License](LICENSE)**:

```text
MIT License

Copyright (c) 2026 JustMichellee & Epithap

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
