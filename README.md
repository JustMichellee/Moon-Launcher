<div align="center">

```ascii
  __  __                       _                             _               
 |  \/  | ___   ___  _ __     | |    __ _ _   _ _ __   ___| |__   ___ _ __ 
 | |\/| |/ _ \ / _ \| '_ \    | |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|
 | |  | | (_) | (_) | | | |   | |__| (_| | |_| | | | | (__| | | |  __/ |   
 |_|  |_|\___/ \___/|_| |_|   |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|   
```

# Moon Launcher & DeadZone Modpack
### *Official Collaborative Project Edition*

**An enterprise-grade, high-performance CLI Minecraft Launcher Studio paired with the curated DeadZone Zombie Apocalypse Modpack.**

[![Collaboration](https://img.shields.io/badge/Collaborators-Epithap%20x%20alfianzidan321--cmd-blueviolet?style=for-the-badge&logo=github)](https://github.com/alfianzidan321-cmd/Moon-Launcher)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Minecraft](https://img.shields.io/badge/Minecraft-1.20.1%20Forge-5B8C33?style=for-the-badge&logo=minecraft&logoColor=white)](https://minecraft.net)
[![Mods Count](https://img.shields.io/badge/Installed_Mods-175+-E04E39?style=for-the-badge&logo=curseforge&logoColor=white)](mods/)
[![Discord RPC](https://img.shields.io/badge/Discord-Rich_Presence_V2-5865F2?style=for-the-badge&logo=discord&logoColor=white)](Moon-Launcher/)
[![Network Tunnel](https://img.shields.io/badge/Multiplayer-Anycast_P2P_Tunnel-00C7B7?style=for-the-badge&logo=cloudflare)](Moon-Launcher/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/alfianzidan321-cmd">
        <img src="https://github.com/alfianzidan321-cmd.png?size=100" width="100px;" alt="alfianzidan321-cmd"/><br />
        <sub><b>alfianzidan321-cmd</b></sub>
      </a><br />
      <sub><b>Project Lead & Modpack Curator</b></sub>
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
- [Architecture & Key Highlights](#-architecture--key-highlights)
  - [Moon Launcher Engine](#1-moon-launcher-engine-cli-studio)
  - [DeadZone Modpack (175+ Mods)](#2-deadzone-modpack-hardcore-survival)
- [Repository Structure](#-repository-structure)
- [System Requirements](#-system-requirements)
- [Installation & Quick Start](#-installation--quick-start)
- [Command Matrix & CLI Reference](#-command-matrix--cli-reference)
- [Global Multiplayer & Anycast Tunneling](#-global-multiplayer--anycast-tunneling)
- [Universal Skin & Cape System](#-universal-skin--cape-system)
- [Diagnostics, Crash Watchdog & Self-Repair](#-diagnostics-crash-watchdog--self-repair)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Collaborators & Credits](#-collaborators--credits)
- [License](#-license)

---

## 📖 Overview

The **Moon Launcher & DeadZone Project** is a unified, collaborative gaming ecosystem engineered specifically for Minecraft enthusiasts who demand extreme performance, zero bloat, and a seamless survival experience.

This repository bundles two major components:

1. **Moon Launcher Studio (`Moon-Launcher/`)**: A terminal-based, keyboard-driven Minecraft launcher built with pure Python standard libraries. It eliminates third-party dependencies, intrusive advertisements, telemetry tracking, and memory-heavy web wrappers, featuring built-in Anycast P2P tunneling, native Discord IPC Rich Presence, pre-flight diagnostics, and CustomSkinLoader integration.
2. **DeadZone Modpack (`mods/`)**: A curated, meticulously balanced hardcore survival horror modpack for **Minecraft 1.20.1 Forge** featuring 175+ mods, modern modular firearm ballistics (Timeless and Classics Zero), realistic body thermoregulation, dynamic zombie AI swarms, procedural world generation, and an optimized modern rendering pipeline.

---

## 🌟 Architecture & Key Highlights

### 1. Moon Launcher Engine (CLI Studio)

- **Pure Python Standard Library Architecture**
  - Runs out of the box using vanilla Python 3.8+ without requiring `pip install` or compiling C-extensions.
  - Zero telemetry, zero telemetry bloat, and instantaneous startup times (< 50ms).
- **Zero-Config Global P2P Anycast Tunneling (`/host`)**
  - Built-in network tunneling daemon allowing you to host singleplayer worlds over the public Internet.
  - No router port-forwarding, CGNAT circumvention issues, Radmin VPN, or Hamachi required.
  - Automatically provisions a public Anycast DNS endpoint (e.g. `*.playit.gg:port`) that friends can paste directly into standard Minecraft multiplayer.
- **Native Discord Rich Presence V2 (Direct Named Pipe IPC)**
  - Direct communication with the Discord desktop client via `\\.\pipe\discord-ipc-0` without external wrappers.
  - Dynamic game state tracking:
    - **In Launcher**: Displays active profile, mod count, and configured memory.
    - **Singleplayer**: Dynamically reads world folder names and NBT level data in real time.
    - **Multiplayer**: Detects server addresses, LAN broadcasts, Radmin/Hamachi virtual subnets, and Anycast tunnels.
    - **3D Head Avatars**: Automatically extracts and displays player skin head avatars in the Discord presence.
    - **Modpack Logo & Fallback**: Automatically uploads local modpack logos to Discord; falls back to an animated grass icon when no logo is present.
- **Universal Offline & Online Skin Integration (CustomSkinLoader CSL)**
  - Fully configured CustomSkinLoader (CSL) deployed across all installed versions.
  - Multi-provider skin pipeline prioritizing local cache (`skins/<username>.png`) with 0ms latency, backed by Mojang, TLauncher, ElyBy, LittleSkin, BlessingSkin, and MCHeads.
  - Instant in-game skin switching via CLI (`/skin <url|file|player>`) and friend skin synchronization (`/skin friend <name> <url>`).
- **Interactive Terminal UI & Management Suite**
  - Unicode border-protected terminal studio with single-key shortcuts (`1` Play, `2` Settings, `3` Status, `4` Version, `5` Remove).
  - Built-in Modrinth `.mrpack` archive downloader and installer simulating Linux Ubuntu APT progress (`Get:1`, `Unpacking`, `Setting up`).
  - Automated pre-flight dry-run tests (`/test`), self-repair engine (`/fix`), and stack-trace crash analyzer (`/crash`).

### 2. DeadZone Modpack (Hardcore Survival)

- **Modern Firearm Ballistics & Arsenal**
  - **Timeless and Classics Zero (TaCZ)**: High-fidelity firearms with custom animations, attachment customization, recoil models, and projectile ballistics.
  - Weapon expansion addons providing tactical gear, military scopes, suppressors, and specialized ammunition.
- **Brutal Environmental Survival & AI**
  - **Cold Sweat**: Hyperthermia and hypothermia mechanics tied to biomes, weather, altitude, and nearby thermal blocks.
  - **Thirst Was Taken**: Hydration tracking requiring water purification, boiling, and hydration equipment.
  - **Enhanced Zombie AI & Zombie Awareness**: Zombies track scent trails, respond to gunshots and block breaking, sprint in darkness, and coordinate horde sieges.
- **Atmospheric Overhauls & Immersive Audio**
  - **Terralith & Tectonic**: Dramatic procedural world generation featuring mountains, ravines, and diverse geological strata.
  - **Biomes O' Plenty**: Vibrant biomes integrated with post-apocalyptic vegetation and ruined structures.
  - **AmbientSounds & Sound Physics Remastered**: Dynamic reverberation in caves, muffled acoustics through walls, and realistic directional audio.
- **Extreme High-FPS Performance Stack**
  - **ModernFix**: Reduces JVM heap allocation and fixes vanilla memory leaks.
  - **Embeddium**: High-performance Sodium-based rendering engine rewritten for Forge.
  - **Canary & FerriteCore**: Optimized entity math, AI pathfinding algorithms, and compressed memory structures.
  - **ImmediatelyFast & Entity Culling**: Rapid font/particle rendering and off-screen entity occlusion culling.

---

## 📁 Repository Structure

```text
Moon-Launcher/
│
├── Moon-Launcher/                     # Launcher engine source directory
│   ├── launcher.py                    # Core engine, IPC pipe, networking & CLI
│   ├── Moon Launcher.bat              # Launcher startup script (handles Python PATH)
│   └── launcher_config.json           # Default engine configuration template
│
├── mods/                              # 175+ Curated Minecraft 1.20.1 Forge mod JARs
│   ├── tacz-1.20.1-*.jar              # Timeless and Classics Zero firearm engine
│   ├── embeddium-*.jar                # High-performance Sodium rendering port
│   ├── modernfix-*.jar                # Memory leak and heap footprint optimizer
│   ├── coldsweat-*.jar                # Body temperature and thermoregulation
│   └── ...                            # Tracked seamlessly via Git LFS
│
├── skins/                             # Local skin storage for 0ms offline rendering
│   ├── Michelle.png                   # Player skin template
│   └── Alfian.png                     # Player skin template
│
├── versions/                          # Minecraft versions directory
│   └── DeadZone 1.20.1 Forge/         # Pre-configured DeadZone game profile
│       ├── icon.png                   # Custom modpack Discord RPC logo
│       ├── launch_args.txt            # Optimized JVM parameters
│       ├── options.txt                # Curated control bindings and visual settings
│       └── CustomSkinLoader/          # Universal offline skin configuration
│
├── Moon Launcher.bat                  # Root 1-Click Launch Script
├── launcher.py                        # Root launcher entrypoint
├── launcher_config.json               # Active user profile and settings
├── .gitattributes                     # Git LFS configuration for binary JAR files
├── .gitignore                         # Exclusions for runtime caches, saves, and logs
├── LICENSE                            # MIT Open-Source License
└── README.md                          # Official documentation
```

---

## 💻 System Requirements

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | Windows 10 (64-bit, 1809+) | Windows 10 / 11 (64-bit, Latest) |
| **Processor (CPU)** | Intel Core i5-4460 / AMD FX-8350 | Intel Core i5-11400 / AMD Ryzen 5 5600 or better |
| **System Memory (RAM)** | 8 GB DDR3 / DDR4 | 16 GB DDR4 / DDR5 (Allocated: 8 GB - 12 GB) |
| **Graphics Card (GPU)** | Intel UHD 630 / GeForce GT 1030 | NVIDIA GeForce GTX 1660 / AMD Radeon RX 580+ |
| **Java Runtime** | Java 17 (64-bit) | Microsoft OpenJDK 17 or Eclipse Temurin 17 |
| **Python** | Python 3.8 (64-bit) | Python 3.10+ (Checked *"Add python.exe to PATH"*) |
| **Storage** | 8 GB free storage (HDD) | 12 GB free storage (NVMe / SSD recommended) |

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
Ensure the following tools are installed on your Windows machine:
1. **Python 3.8+**: Download from [python.org](https://www.python.org/). **Important:** Ensure *"Add python.exe to PATH"* is checked during setup.
2. **Java 17 (64-bit)**: Download [Microsoft Build of OpenJDK 17](https://learn.microsoft.com/en-us/java/openjdk/download) or [Eclipse Temurin 17](https://adoptium.net/).
3. **Git & Git LFS**: Download from [git-scm.com](https://git-scm.com/) and verify LFS is initialized:
   ```bash
   git lfs install
   ```

### 2. Clone the Repository
Clone the repository and pull the 175+ mod files via Git LFS:
```bash
git clone https://github.com/alfianzidan321-cmd/Moon-Launcher.git
cd Moon-Launcher
git lfs pull
```

### 3. Launch the Studio
Launch the engine by double-clicking:
```cmd
Moon Launcher.bat
```
*Alternatively, run from PowerShell or Command Prompt:*
```powershell
python launcher.py
```

### 4. Initial Configuration
Configure your player identity and memory allocation inside the Moon Launcher CLI:
```text
/setting user YourPlayerName
/setting ram 8
/status
/play
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

### Modpack & Version Management
| Command | Arguments | Description |
|---|---|---|
| `/version` | `[name]` / `4` | List all detected local versions and switch active profile |
| `/install` | — | Open the interactive Modpack & Version Installer Studio |
| `/install` | `<modpack_name>` | Search and install modpacks directly from Modrinth |
| `/install` | `forge [version]` | Install clean Minecraft Forge (e.g. `1.20.1`, `1.12.2`) |
| `/install` | `fabric [version]`| Install clean Fabric Loader (e.g. `1.20.1`, `1.21.1`) |
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

Moon Launcher eliminates the traditional barriers of Minecraft multiplayer. You can host your singleplayer world for friends across the globe without paying for server hosting or configuring router NAT port-forwarding:

```
[ Your Minecraft World ] ──> [ Moon Launcher Anycast Daemon ] ──> [ Global Anycast Edge ] ──> [ Remote Players ]
```

### Hosting a World in 4 Simple Steps:
1. **Open World to LAN**: Inside Minecraft, pause the game and select **Open to LAN**. Note the 5-digit port (e.g. `52341`).
2. **Start the Tunnel**: In Moon Launcher CLI, enter:
   ```text
   /host start 52341
   ```
   *(If you omit the port, Moon Launcher will automatically scan and detect your open LAN world).*
3. **Copy the Public Address**: Moon Launcher provisions an encrypted Anycast endpoint:
   ```text
   Public Address: emerald-tiger.playit.gg:38921
   ```
4. **Share with Friends**: Friends launch Minecraft (using Moon Launcher or any client), go to **Multiplayer -> Direct Connection**, paste `emerald-tiger.playit.gg:38921`, and connect immediately.

---

## 🎭 Universal Skin & Cape System

Because offline/free Minecraft accounts are rejected by Mojang's official session server (returning HTTP 204), standard clients render default Steve or Alex skins. 

Moon Launcher resolves this using an integrated **CustomSkinLoader (CSL)** engine with an optimized local-first priority order:

1. **LocalSkin Engine (0ms Latency)**: Looks up `skins/<username>.png` directly in your launcher directory.
2. **Mojang API**: Fetches official skins if the username matches an official paid account.
3. **Third-Party Providers**: Queries fallback skin repositories including TLauncher, ElyBy, LittleSkin, BlessingSkin, and MCHeads.

### Changing Skins:
- **Apply Your Own Skin**:
  ```text
  /skin https://example.com/my_skin.png
  /skin C:\Users\Username\Downloads\custom_skin.png
  /skin Notch
  ```
- **Synchronize a Friend's Skin**:
  ```text
  /skin friend Michelle https://example.com/michelle.png
  ```

---

## 🛡️ Diagnostics, Crash Watchdog & Self-Repair

Moon Launcher includes active health-monitoring systems to prevent crashes before they happen:

```
                   ┌────────────────────────────────────────┐
                   │        Moon Launcher Diagnostics       │
                   └───────────────────┬────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
  Java Compatibility             JAR Integrity                Crash Log Parser
  (Java 8 vs 17 vs 21)         (Detects 0-byte mods)        (Identifies culprit mod)
```

### Diagnostics Tools:
- **Pre-Flight Test (`/test`)**: Verifies that your selected Java version matches the Minecraft loader requirements, verifies client libraries and LWJGL native binaries, and performs a simulated dry-run launch.
- **Automated Repair (`/fix`)**: Re-creates missing `launch_args.txt`, repairs native library links, purges corrupt zero-byte mod JARs, and synchronizes CustomSkinLoader configuration templates.
- **Crash Watchdog (`/crash`)**: Parses `crash-reports/` and `logs/latest.log` to extract the root exception and highlights the exact mod JAR responsible for a failure.

---

## ❓ Troubleshooting & FAQ

### Q1: The game crashes during launch with exit code 1 or -1
- Type `/crash` in the launcher to view the automated stack trace analysis.
- Run `/fix` to re-synchronize corrupted launch arguments and native libraries.
- Run `/test` to verify your Java runtime version and mod JAR integrity.

### Q2: Mods are missing or Minecraft launches in vanilla mode
- Verify that your active profile is set to `DeadZone 1.20.1 Forge` using `/version`.
- If you recently cloned the repository, ensure Git LFS pulled the actual mod JAR files:
  ```bash
  git lfs pull
  ```

### Q3: How much RAM should I allocate for DeadZone?
- DeadZone includes 175+ mods, high-resolution textures, and complex AI pathfinding.
- **Recommended**: 8 GB to 10 GB:
  ```text
  /setting ram 8
  ```
- Avoid allocating more than 14 GB, as excessive JVM heap sizes can cause garbage collection stutter.

### Q4: Windows Defender or Antivirus flags `Moon Launcher.bat`
- `Moon Launcher.bat` is a simple three-line batch script that checks if Python is installed and executes `launcher.py`. You can inspect its contents in Notepad. It contains zero obfuscated binaries or network downloaders.

---

## 👥 Collaborators & Credits

The **Moon Launcher & DeadZone Project** is maintained through active collaboration:

| Collaborator | GitHub Profile | Primary Responsibilities |
|---|---|---|
| **alfianzidan321-cmd** | [@alfianzidan321-cmd](https://github.com/alfianzidan321-cmd) | Project Founder, DeadZone Modpack Lead, Gameplay Balancing, Asset Curation |
| **Epithap** | [@Epithap](https://github.com/Epithap) | Core Systems Architect, Moon Launcher CLI Engine, Discord IPC Pipe, Anycast Tunnel Integration |

### Upstream Open-Source Acknowledgments:
- **[CustomSkinLoader](https://github.com/xfl03/MCCustomSkinLoader)** — Universal offline/online skin rendering engine.
- **[Timeless and Classics Zero (TaCZ)](https://github.com/Mayday-Memory/Timeless-and-Classics-Zero)** — Modern modular firearm combat framework.
- **[Embeddium](https://github.com/embeddedt/embeddium)** & **[ModernFix](https://github.com/embeddedt/modernfix)** — Core optimization and memory performance infrastructure.

---

## 📜 License

This project is licensed under the open-source **[MIT License](LICENSE)**. You are free to inspect, modify, fork, and distribute this software for personal and community use.
