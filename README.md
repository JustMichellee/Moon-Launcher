<div align="center">

```ascii
  __  __                       _                             _               
 |  \/  | ___   ___  _ __     | |    __ _ _   _ _ __   ___| |__   ___ _ __ 
 | |\/| |/ _ \ / _ \| '_ \    | |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|
 | |  | | (_) | (_) | | | |   | |__| (_| | |_| | | | | (__| | | |  __/ |   
 |_|  |_|\___/ \___/|_| |_|   |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|   
```

# 🌙 Moon Launcher
### *High-Performance CLI Minecraft Launcher Studio*

**A lightweight, privacy-focused, keyboard-driven Minecraft launcher built with pure Python standard libraries, native Discord Rich Presence, zero-config Anycast P2P multiplayer tunneling, universal skin synchronization, and intelligent diagnostics.**

[![Collaboration](https://img.shields.io/badge/Collaborators-Epithap%20x%20JustMichellee-blueviolet?style=for-the-badge&logo=github)](https://github.com/JustMichellee/Moon-Launcher)
[![Python](https://img.shields.io/badge/Python-3.8+_(Zero_Deps)-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows_(x64)-0078D6?style=for-the-badge&logo=windows&logoColor=white)](Moon-Launcher/)
[![Minecraft](https://img.shields.io/badge/Minecraft-Vanilla%20%7C%20Forge%20%7C%20Fabric%20%7C%20NeoForge%20%7C%20Quilt-5B8C33?style=for-the-badge&logo=minecraft&logoColor=white)](https://minecraft.net)
[![Discord RPC](https://img.shields.io/badge/Discord-Rich_Presence_V2-5865F2?style=for-the-badge&logo=discord&logoColor=white)](Moon-Launcher/)
[![Network Tunnel](https://img.shields.io/badge/Multiplayer-Anycast_P2P_Tunnel-00C7B7?style=for-the-badge&logo=cloudflare)](Moon-Launcher/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/JustMichellee">
        <img src="https://github.com/JustMichellee.png?size=100" width="100px;" alt="JustMichellee"/><br />
        <sub><b>JustMichellee</b></sub>
      </a><br />
      <sub><b>Project Lead & Repository Maintainer</b></sub>
    </td>
    <td align="center">
      <a href="https://github.com/Epithap">
        <img src="https://github.com/Epithap.png?size=100" width="100px;" alt="Epithap"/><br />
        <sub><b>Epithap</b></sub>
      </a><br />
      <sub><b>Core Systems Architect & Engine Developer</b></sub>
    </td>
  </tr>
</table>

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Key Architectural Highlights](#-key-architectural-highlights)
- [Directory Structure & Architecture](#-directory-structure--architecture)
- [System Requirements](#-system-requirements)
- [Installation & Quick Start](#-installation--quick-start)
- [Command Matrix & CLI Reference](#-command-matrix--cli-reference)
- [Global Multiplayer & Anycast Tunneling](#-global-multiplayer--anycast-tunneling)
- [Universal Skin & Cape System](#-universal-skin--cape-system)
- [Modpack & Version Management Studio](#-modpack--version-management-studio)
- [Diagnostics, Crash Watchdog & Self-Repair](#-diagnostics-crash-watchdog--self-repair)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Collaborators & Credits](#-collaborators--credits)
- [License](#-license)

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

### 3. Native Discord Rich Presence V2 (Direct IPC Pipe)
- **Direct IPC Named Pipe Engine**: Interacts directly with the local Discord client via Windows named pipe (`\\.\pipe\discord-ipc-0`) without requiring `pypresence` or third-party wrappers.
- **Dynamic In-Game Detection**:
  - 🏠 **Launcher Status**: Shows active profile, installed mod counts, and memory configuration.
  - 🕹️ **Singleplayer Gameplay**: Dynamically inspects world folders and parses live NBT level data to display current world names.
  - 🌐 **Multiplayer & Co-op**: Detects connected server IP addresses, LAN broadcasts, virtual networks, and active Anycast tunnels.
  - 👤 **Player Head Avatars**: Automatically extracts and displays the player's 2D skin head avatar directly in Discord.
  - 🖼️ **Dynamic Modpack Logos**: Automatically uploads local profile icons (`icon.png`); defaults to the official Minecraft grass block icon if no custom logo is found.

### 4. Universal Offline & Online Skin Integration (CustomSkinLoader CSL)
- **Universal Multi-Loader Deployment**: Automatically configures and deploys CustomSkinLoader across Forge, Fabric, NeoForge, and Quilt profiles.
- **Native Zero-Config LAN & Radmin P2P Skin Auto-Sync**: Built-in background daemon (UDP/TCP port `25564`) automatically discovers and exchanges custom player skins with other Moon Launcher users across local Wi-Fi or Radmin VPN (`26.x.x.x`) with zero setup and zero internet dependency.
- **Local-First Zero-Latency Pipeline**: Resolves skins locally from `skins/<username>.png` with 0ms delay.
- **Multi-Provider Fallback**: Seamlessly falls back to Mojang, TLauncher, ElyBy, LittleSkin, BlessingSkin, and MCHeads.
- **Friend Skin Synchronization**: Set custom skins for yourself (`/skin <url|file|player>`), assign friend skins (`/skin friend <name> <url>`), or inspect active peer sync status (`/lan`).

### 5. Intelligent Diagnostics & Self-Repair Engine
- **Pre-Flight Diagnostics (`/test`)**: Audits Java runtime compatibility (Java 8 vs 17 vs 21), verifies client JAR checksums, checks LWJGL native DLLs, and performs simulated dry-run boots.
- **One-Click Auto-Repair (`/fix`)**: Automatically regenerates corrupted launch argument files, re-links missing native libraries, purges 0-byte corrupted mod JARs, and synchronizes CustomSkinLoader configurations.
- **Crash Watchdog (`/crash`)**: Real-time process monitor that detects abnormal terminations, parses `crash-reports/` and `logs/latest.log`, and pinpoints the exact culprit mod JAR causing the failure.

### 6. Interactive Terminal Studio & APT-Style Installer
- **Border-Protected Unicode Dashboard**: Clean, responsive terminal UI with single-character quick access keys (`1` Play, `2` Settings, `3` Status, `4` Version, `5` Remove).
- **Ubuntu APT-Styled Modpack Installer (`/install`)**: Search and download modpacks from Modrinth, install raw `.mrpack` files, or set up clean Forge, Fabric, NeoForge, or Vanilla runtimes with live terminal progress bars.

---

## 📁 Directory Structure & Architecture

Moon Launcher organizes both its lightweight launcher engine and local Minecraft runtime data within an intuitive, fully documented modular structure:

```text
Moon-Launcher/
│
├── launcher.py                    # Core launcher engine, Discord IPC & CLI studio
├── network_hub.py                 # P2P Anycast multiplayer tunneling & friends system
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
├── runtime/                       # Bundled Java runtimes (Java 8, Java 17, Java 21)
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

---

## 💻 System Requirements

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | Windows 10 (64-bit, 1809+) | Windows 10 / 11 (64-bit, Latest Build) |
| **Processor (CPU)** | Intel Core i3 / AMD Ryzen 3 | Intel Core i5 / AMD Ryzen 5 or higher |
| **System Memory (RAM)** | 4 GB RAM (Vanilla) / 8 GB (Modded) | 16 GB+ RAM (Configured: 6 GB - 10 GB) |
| **Graphics Card (GPU)** | Intel HD Graphics 4000 / AMD Radeon | NVIDIA GeForce GTX 1050+ / AMD RX 560+ |
| **Java Runtime** | Java 8 (for 1.12.2 and older) / Java 17+ (for 1.18+) | Microsoft OpenJDK 17/21 or Eclipse Temurin |
| **Python** | Python 3.8 (64-bit) | Python 3.10+ (Checked *"Add python.exe to PATH"*) |
| **Disk Storage** | 200 MB for Launcher core | 5 GB+ for Minecraft profiles, assets & mods |

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
Ensure you have the following installed on Windows:
1. **Python 3.8+**: Download from [python.org](https://www.python.org/). **Crucial:** Check *"Add python.exe to PATH"* during installation.
2. **Java Runtime (64-bit)**: 
   - Minecraft 1.18+: [Microsoft Build of OpenJDK 17](https://learn.microsoft.com/en-us/java/openjdk/download) or [OpenJDK 21](https://adoptium.net/).
   - Minecraft 1.16.5 and older: Java 8 (64-bit).
3. **Git**: Download from [git-scm.com](https://git-scm.com/) (Optional, for cloning).

### 2. Download / Clone the Repository
```bash
git clone https://github.com/JustMichellee/Moon-Launcher.git
cd Moon-Launcher
```

### 3. Launch Moon Launcher Studio
Simply double-click the one-click runner script:
```cmd
Moon Launcher.bat
```
*Or start directly from PowerShell / Command Prompt:*
```powershell
python launcher.py
```

### 4. Configure Your Profile & Launch
Inside the interactive Moon Launcher terminal prompt, run:
```text
/setting user YourPlayerName     -> Sets your in-game player name
/setting ram 8                   -> Allocates 8 GB maximum JVM RAM
/status                          -> Verifies Java runtime & profile status
/play                            -> Launches Minecraft!
```

---

## ⌨️ Command Matrix & CLI Reference

Moon Launcher features a comprehensive command-line interface. Commands can be issued at any prompt:

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
| `/invite` | — | Generate and auto-copy a 1-click multiplayer join link with your public IP |
| `/friend` | `[list]` | Display your contacts table with live server latency (ms) and online status |
| `/friend` | `add <link|name>` | Add a friend via their invite link or `username [ip:port]` |
| `/friend` | `ping <name>` | Query real-time latency and player count for a friend's hosted world |
| `/server` | `add <name> <ip>` | Bookmark a multiplayer server to your favorites list |
| `/lan` | `[sync]` | Inspect native LAN & Radmin P2P skin auto-sync daemon and force a discovery probe |

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

Moon Launcher revolutionizes Minecraft multiplayer. You can host your singleplayer world for friends anywhere on earth without purchasing a server, port-forwarding your home router, or dealing with third-party VPN clients:

```
┌──────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
│ Your Local PC        │          │ Moon Launcher Tunnel      │          │ Global Anycast Edge    │
│ Minecraft LAN World  ├─────────►│ P2P Anycast Daemon        ├─────────►│ Endpoints Worldwide    │
└──────────────────────┘          └───────────────────────────┘          └───────────┬────────────┘
                                                                                     │
                                                                                     ▼
                                                                         ┌────────────────────────┐
                                                                         │ Remote Players Connect │
                                                                         │ (Direct Connection IP) │
                                                                         └────────────────────────┘
```

### Hosting a World in 4 Simple Steps:
1. **Open World to LAN**: Inside Minecraft, pause the game and select **Open to LAN**. Note the 5-digit port (e.g. `52341`).
2. **Start the Tunnel**: In Moon Launcher CLI, run:
   ```text
   /host start 52341
   ```
   *(If you omit the port, Moon Launcher will automatically scan and detect your open LAN world).* 
3. **Obtain the Public Address**: Moon Launcher instantly allocates an encrypted Anycast endpoint:
   ```text
   Public Address: emerald-tiger.playit.gg:38921
   ```
4. **Share with Friends**: Friends launch Minecraft (using Moon Launcher or any client), go to **Multiplayer -> Direct Connection**, paste `emerald-tiger.playit.gg:38921`, and connect immediately.

---

## 🎭 Universal Skin & Cape System

In offline / non-premium Minecraft environments, Mojang's session server rejects authentication requests (HTTP 204), causing the game client to display default Steve or Alex skins.

Moon Launcher permanently resolves this with a unified **CustomSkinLoader (CSL)** pipeline configured for high efficiency:

1. **LocalSkin Priority (0ms Latency)**: Prioritizes local textures located at `skins/<username>.png`.
2. **Mojang Official API**: Automatically downloads skins for players using official premium usernames.
3. **Multi-Provider Fallback**: Dynamically queries TLauncher, ElyBy, LittleSkin, BlessingSkin, and MCHeads repositories.

### Setting Skins via CLI:
- **Apply Skin from URL or Local PNG**:
  ```text
  /skin https://example.com/skin.png
  /skin C:\Users\User\Pictures\skin.png
  /skin Notch
  ```
- **Synchronize a Friend's Skin**:
  ```text
  /skin friend Alex https://example.com/alex_skin.png
  ```

---

## 📦 Modpack & Version Management Studio

Managing versions and modpacks in Moon Launcher is fast and intuitive:

- **Install from Modrinth**:
  ```text
  /install Fabulously Optimized
  /install Cobblemon
  ```
- **Install Clean Loaders**:
  ```text
  /install fabric 1.20.1
  /install forge 1.20.1
  /install neoforge 1.21.1
  /install vanilla 1.20.1
  ```
- **Switch Active Version**:
  Type `/version` to view an interactive menu of all installed profiles, or switch directly by name:
  ```text
  /version 1.20.1-Forge
  ```
- **Safely Uninstall a Version**:
  ```text
  /remove OldModpackName
  ```

---

## 🛡️ Diagnostics, Crash Watchdog & Self-Repair

Moon Launcher incorporates automated health and debugging tools to eliminate crash guesswork:

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

### Diagnostic Tools:
- **Pre-Flight Test (`/test`)**: Validates that your installed Java version matches your Minecraft release (e.g. Java 17+ for 1.18+, Java 8 for 1.12.2), checks native LWJGL libraries, and verifies memory syntax.
- **Automated Self-Repair (`/fix`)**: Re-creates missing `launch_args.txt` parameter files, re-links native DLLs, deletes 0-byte corrupt JAR files, and synchronizes CustomSkinLoader configurations.
- **Crash Watchdog (`/crash`)**: Parses `crash-reports/` and `logs/latest.log` to extract the exact stack trace and root cause, highlighting the specific mod file responsible.

---

## ❓ Troubleshooting & FAQ

### Q1: The game crashes immediately upon launch with exit code 1 or -1
- Type `/crash` to inspect the automated stack trace root cause.
- Run `/fix` to re-synchronize launch arguments and native libraries.
- Run `/test` to verify Java runtime compatibility and mod file integrity.

### Q2: What Java runtime should I use?
- **Minecraft 1.18 to 1.21+**: Requires **Java 17 (64-bit)** or **Java 21 (64-bit)**.
- **Minecraft 1.12.2 and older**: Requires **Java 8 (64-bit)**.
- You can check your active Java status anytime via `/status`.

### Q3: How much RAM should I allocate?
- **Vanilla Minecraft**: 2 GB to 4 GB (`/setting ram 4`).
- **Light to Medium Modpacks (50 - 120 mods)**: 4 GB to 6 GB (`/setting ram 6`).
- **Heavy Modpacks (150+ mods / Shaders)**: 8 GB to 10 GB (`/setting ram 8`).
- *Tip: Avoid allocating more than 14 GB unless strictly necessary to prevent JVM garbage collector pauses.*

### Q4: Windows Defender or Antivirus flags `Moon Launcher.bat`
- `Moon Launcher.bat` is a simple three-line batch script that verifies Python is in your PATH and starts `launcher.py`. You can inspect its source code in any text editor. It contains zero obfuscated binaries or downloaders.

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

This project is licensed under the open-source **[MIT License](LICENSE)**. You are free to inspect, modify, fork, and distribute this software for personal and community use.
