# Moon Launcher - Development & Runtime Directory Guide

This clean development workspace separates source code, UI assets, build definitions, and user runtime data so Moon Launcher (both **GUI** and **CLI**) is ready to develop, build, and distribute to other users without leaking personal configs, saves, or hardcoded machine paths.

## Project Structure

```text
Moon-Launcher-Dev/
├── src/                        # Python application modules
│   ├── __init__.py
│   ├── paths.py                # Dynamic path resolution (dev / portable .exe / installed)
│   ├── cli.py                  # CLI entrypoint
│   ├── gui_app.py              # Desktop GUI (pywebview) + CLI passthrough
│   ├── launcher.py             # Core Minecraft launcher, installer, RPC, diagnostics
│   ├── network_hub.py          # Multiplayer tunneling, LAN skin sync, friends/servers
│   ├── pack_share.py           # P2P / cloud modpack sharing (MOON-PACK-XXXX)
│   └── updater.py              # GitHub auto-updater
│
├── gui/                        # Desktop GUI HTML/CSS/JS & brand icons
├── assets/                     # Default launcher icons & asset placeholders
├── templates/                  # CustomSkinLoader & Log4j templates
├── moon-sync-mod/              # Companion Java mod source & JAR
├── scripts/                    # Developer run & build scripts
│   ├── run_cli.bat             # Launch CLI from source
│   ├── run_gui.bat             # Launch GUI from source
│   ├── build.ps1               # Build CLI & GUI executables + optional setup installer
│   └── build.bat               # Windows wrapper for build.ps1
├── build/                      # PyInstaller specs & Inno Setup installer script
│   ├── Moon-Launcher-CLI.spec
│   ├── Moon-Launcher-GUI.spec
│   └── Moon-Launcher-Setup.iss
│
├── skins/                      # Default Player.png (active_skin.png created on first run)
├── launcher_config.json        # Clean default user configuration
├── friends.json                # Clean default friends/servers list
├── requirements.txt            # Python dependencies for GUI & building
├── version.json                # Release version metadata
└── supabase_schema.sql         # Cloud social/presence database schema
```

## Path Resolution (`src/paths.py`)

- **Development Mode** (`python src/cli.py` or `python src/gui_app.py`):
  `BASE_DIR` and `RESOURCE_DIR` both resolve to the project root.
- **Portable Executable Mode** (`Moon-Launcher-GUI.exe` / `Moon-Launcher-CLI.exe`):
  `RESOURCE_DIR` resolves to PyInstaller's `_MEIPASS` bundle; `BASE_DIR` resolves to the folder next to the `.exe` if writable.
- **Read-Only Install Mode** (e.g. `Program Files`):
  `BASE_DIR` automatically falls back to `%LOCALAPPDATA%\MoonLauncher` so users never hit permission errors.
- **Custom Data Location**:
  Set environment variable `MOON_LAUNCHER_HOME` to override `BASE_DIR`.

