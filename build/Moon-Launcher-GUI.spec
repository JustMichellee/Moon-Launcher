# -*- mode: python ; coding: utf-8 -*-

import os

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
ROOT_DIR = os.path.dirname(SPEC_DIR)

a = Analysis(
    [os.path.join(ROOT_DIR, 'src', 'gui_app.py')],
    pathex=[os.path.join(ROOT_DIR, 'src')],
    binaries=[],
    datas=[
        (os.path.join(ROOT_DIR, 'gui'), 'gui'),
        (os.path.join(ROOT_DIR, 'assets', 'default_icon.png'), 'assets'),
        (os.path.join(ROOT_DIR, 'assets', 'minecraft_default_icon.png'), 'assets'),
        (os.path.join(ROOT_DIR, 'assets', 'minecraft_title_logo.png'), 'assets'),
        (os.path.join(ROOT_DIR, 'assets', 'moon-icon.ico'), 'assets'),
        (os.path.join(ROOT_DIR, 'assets', 'icon.ico'), 'assets'),
        (os.path.join(ROOT_DIR, 'templates'), 'templates'),
        (os.path.join(ROOT_DIR, 'skins', 'Player.png'), 'skins'),
        (os.path.join(ROOT_DIR, 'moon-sync-mod', 'moon-sync-1.0.0.jar'), 'moon-sync-mod'),
        (os.path.join(ROOT_DIR, 'moon-sync-mod', 'moon-sync-forge-legacy-1.0.0.jar'), 'moon-sync-mod'),
        (os.path.join(ROOT_DIR, 'moon-sync-mod', 'moon-ingame-fabric-1.20.1-1.0.0.jar'), 'moon-sync-mod'),
        (os.path.join(ROOT_DIR, 'moon-sync-mod', 'moon-ingame-fabric-1.21.1-1.0.0.jar'), 'moon-sync-mod'),
        (os.path.join(ROOT_DIR, 'version.json'), '.'),
    ],
    hiddenimports=['paths', 'auth_ms', 'launcher', 'pack_share', 'network_hub', 'updater', 'client_qol', 'p2p_tunnel', 'cloud_sync_mods'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Moon-Launcher-GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=os.path.join(ROOT_DIR, 'assets', 'moon-icon.ico'),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

