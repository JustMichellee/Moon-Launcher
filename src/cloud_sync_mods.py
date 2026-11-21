"""
Moon Launcher Phase 4 Engine:
- Cloud Settings & Keybinds (options.txt) + Server List (servers.dat) Sync via Cloudflare D1
- Local Modpack Compatibility Checker (Loader mismatch, Duplicate Mod IDs, Missing Dependencies)
- Modrinth Batch Hash Updater (/v2/version_files/update) with Safe Backup Rollback
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile

SAFE_OPTION_EXACT = {
    "fov",
    "mouseSensitivity",
    "gamma",
    "autoJump",
    "toggleCrouch",
    "toggleSprint",
    "discrete_mouse_scroll",
    "mouseWheelSensitivity",
    "rawMouseInput",
    "renderDistance",
    "simulationDistance",
    "entityDistanceScaling",
    "maxFps",
    "enableVsync",
    "bobView",
    "guiScale",
    "particles",
    "lang",
    "darkMojangStudiosBackground",
    "skipMultiplayerWarning",
    "joinedFirstServer",
}

CLIENT_ONLY_HINTS = {
    "sodium", "iris", "oculus", "embeddium", "rubidium", "optifine", "ferritecore",
    "immediatelyfast", "entityculling", "modmenu", "appleskin", "rei", "roughlyenoughitems",
    "jei", "emi", "xaerominimap", "xaeroworldmap", "journeymap", "shulkerboxtooltip",
    "lambdynamiclights", "soundphysics", "moonsync", "customskinloader", "continuity",
    "indium", "dynamicfps", "krypton", "starlight", "lithium",
}


def extract_safe_options(version_dir):
    """Extracts portable keybinds, gameplay controls, audio sliders, and safe UI prefs from options.txt."""
    opt_path = os.path.join(version_dir, "options.txt")
    if not os.path.exists(opt_path):
        return {}
    out = {}
    with open(opt_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            raw = line.strip()
            if not raw or ":" not in raw:
                continue
            k, v = raw.split(":", 1)
            k = k.strip()
            if (
                k.startswith("key_")
                or k.startswith("soundCategory_")
                or k in SAFE_OPTION_EXACT
            ):
                out[k] = v.strip()
    return out


def apply_safe_options(version_dir, cloud_options):
    """Applies cloud keybinds & safe options into <version_dir>/options.txt without wiping unrelated lines."""
    if not version_dir or not os.path.isdir(version_dir) or not isinstance(cloud_options, dict) or not cloud_options:
        return {"success": False, "error": "Invalid options or instance directory"}
    opt_path = os.path.join(version_dir, "options.txt")
    ordered_keys = []
    existing = {}
    if os.path.exists(opt_path):
        with open(opt_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                raw = line.rstrip("\r\n")
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    if k not in existing:
                        ordered_keys.append(k)
                    existing[k] = v

    updated_count = 0
    for k, v in cloud_options.items():
        if k.startswith("key_") or k.startswith("soundCategory_") or k in SAFE_OPTION_EXACT:
            if k not in existing:
                ordered_keys.append(k)
            existing[k] = str(v)
            updated_count += 1

    with open(opt_path, "w", encoding="utf-8") as f:
        for k in ordered_keys:
            f.write(f"{k}:{existing[k]}\n")
    return {"success": True, "updated_keys": updated_count, "path": opt_path}


def merge_servers_dat(version_dir, cloud_servers):
    """Merges cloud server list into <version_dir>/servers.dat cleanly without removing local/P2P servers."""
    if not version_dir or not os.path.isdir(version_dir) or not isinstance(cloud_servers, list):
        return {"success": False, "error": "Invalid target"}
    import p2p_tunnel
    local = []
    try:
        local = p2p_tunnel.read_servers_dat(version_dir)
    except Exception:
        local = []

    seen_ips = {str(s.get("ip") or "").strip().lower(): s for s in local if s.get("ip")}
    added = 0
    merged = list(local)
    for cs in cloud_servers:
        if not isinstance(cs, dict):
            continue
        ip = str(cs.get("ip") or "").strip()
        if not ip or ip.startswith("127.0.0.1:") or str(cs.get("name") or "").startswith("Moon P2P:"):
            continue
        if ip.lower() not in seen_ips:
            merged.append({
                "name": str(cs.get("name") or "Synced Server"),
                "ip": ip,
                "icon": str(cs.get("icon") or ""),
                "acceptTextures": int(cs.get("acceptTextures", 1)),
            })
            seen_ips[ip.lower()] = cs
            added += 1

    # Serialize using p2p_tunnel NBT serializer
    comp_items = []
    for s in merged:
        c = {
            "name": (8, str(s.get("name") or "Minecraft Server")),
            "ip": (8, str(s.get("ip") or "")),
            "acceptTextures": (1, int(s.get("acceptTextures", 1))),
        }
        if s.get("icon"):
            c["icon"] = (8, str(s["icon"]))
        comp_items.append(c)

    root = {"servers": (9, (10, comp_items))}
    blob = b"\x0a" + p2p_tunnel._nbt_write_str("") + p2p_tunnel._nbt_write_payload(10, root)
    with open(os.path.join(version_dir, "servers.dat"), "wb") as f:
        f.write(blob)
    return {"success": True, "added": added, "total": len(merged)}


def push_cloud_profile(moon_id, version_dir):
    import network_hub
    import p2p_tunnel
    if not moon_id:
        moon_id = network_hub.get_or_create_moon_id()
    opts = extract_safe_options(version_dir) if (version_dir and os.path.isdir(version_dir)) else {}
    raw_servers = p2p_tunnel.read_servers_dat(version_dir) if (version_dir and os.path.isdir(version_dir)) else []
    clean_servers = [
        {
            "name": s.get("name", ""),
            "ip": s.get("ip", ""),
            "acceptTextures": int(s.get("acceptTextures", 1)),
        }
        for s in raw_servers
        if s.get("ip") and not str(s.get("name") or "").startswith("Moon P2P:")
    ]
    res = network_hub.cloud_api_request("/api/profile/push", "POST", {
        "player_id": str(moon_id).strip().upper(),
        "options": opts,
        "servers": clean_servers,
    })
    if res and res.get("success"):
        return {
            "success": True,
            "options_count": len(opts),
            "servers_count": len(clean_servers),
            "updated_at": res.get("updated_at", ""),
        }
    return {"success": False, "error": (res or {}).get("error", "Cloudflare profile push failed")}


def pull_cloud_profile(moon_id, version_dir):
    import network_hub
    if not moon_id:
        moon_id = network_hub.get_or_create_moon_id()
    res = network_hub.cloud_api_request(f"/api/profile/pull?moon_id={moon_id}", "GET")
    if not res:
        return {"success": False, "error": "Cloudflare profile pull failed"}
    if not res.get("found"):
        return {"success": False, "error": "No saved cloud profile found yet. Push from an instance first!"}
    opt_res = apply_safe_options(version_dir, res.get("options") or {}) if (res.get("options") and version_dir) else {"updated_keys": 0}
    srv_res = merge_servers_dat(version_dir, res.get("servers") or []) if (res.get("servers") and version_dir) else {"added": 0}
    return {
        "success": True,
        "updated_keys": opt_res.get("updated_keys", 0),
        "added_servers": srv_res.get("added", 0),
        "updated_at": res.get("updated_at", ""),
    }


def _inspect_jar_metadata(jar_path):
    """Reads mod ID, name, version, declared loader, and depends directly from JAR metadata."""
    meta = {
        "file_name": os.path.basename(jar_path),
        "mod_id": "",
        "name": os.path.basename(jar_path),
        "version": "",
        "loaders": [],
        "depends": [],
        "environment": "*",
        "sha512": "",
    }
    h512 = hashlib.sha512()
    with open(jar_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h512.update(chunk)
    meta["sha512"] = h512.hexdigest()

    try:
        with zipfile.ZipFile(jar_path, "r") as zf:
            names = set(zf.namelist())
            if "fabric.mod.json" in names:
                meta["loaders"].append("Fabric")
                try:
                    fj = json.loads(zf.read("fabric.mod.json").decode("utf-8", errors="replace"))
                    meta["mod_id"] = str(fj.get("id") or "")
                    meta["name"] = str(fj.get("name") or meta["mod_id"] or meta["name"])
                    meta["version"] = str(fj.get("version") or "")
                    meta["environment"] = str(fj.get("environment") or "*")
                    deps = fj.get("depends") or {}
                    if isinstance(deps, dict):
                        meta["depends"] = [str(k) for k in deps.keys() if k not in ("fabricloader", "minecraft", "java")]
                except Exception:
                    pass
            if "quilt.mod.json" in names:
                meta["loaders"].append("Quilt")
                try:
                    qj = json.loads(zf.read("quilt.mod.json").decode("utf-8", errors="replace"))
                    ql = qj.get("quilt_loader") or {}
                    if not meta["mod_id"]:
                        meta["mod_id"] = str(ql.get("id") or "")
                        meta["version"] = str(ql.get("version") or "")
                    md = ql.get("metadata") or {}
                    if md.get("name"):
                        meta["name"] = str(md["name"])
                except Exception:
                    pass
            if "META-INF/neoforge.mods.toml" in names:
                meta["loaders"].append("NeoForge")
                txt = zf.read("META-INF/neoforge.mods.toml").decode("utf-8", errors="replace")
                m_id = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', txt)
                m_nm = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', txt)
                m_vr = re.search(r'version\s*=\s*["\']([^"\']+)["\']', txt)
                if m_id and not meta["mod_id"]:
                    meta["mod_id"] = m_id.group(1)
                if m_nm:
                    meta["name"] = m_nm.group(1)
                if m_vr and "${" not in m_vr.group(1):
                    meta["version"] = m_vr.group(1)
            if "META-INF/mods.toml" in names:
                if "Forge" not in meta["loaders"]:
                    meta["loaders"].append("Forge")
                txt = zf.read("META-INF/mods.toml").decode("utf-8", errors="replace")
                if "neoforge" in txt.lower() and "NeoForge" not in meta["loaders"]:
                    meta["loaders"].append("NeoForge")
                m_id = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', txt)
                m_nm = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', txt)
                if m_id and not meta["mod_id"]:
                    meta["mod_id"] = m_id.group(1)
                if m_nm and meta["name"] == meta["file_name"]:
                    meta["name"] = m_nm.group(1)
            if "mcmod.info" in names and not meta["mod_id"]:
                meta["loaders"].append("Forge")
                try:
                    arr = json.loads(zf.read("mcmod.info").decode("utf-8", errors="replace"))
                    if isinstance(arr, dict) and isinstance(arr.get("modList"), list):
                        arr = arr["modList"]
                    if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                        meta["mod_id"] = str(arr[0].get("modid") or "")
                        meta["name"] = str(arr[0].get("name") or meta["name"])
                        meta["version"] = str(arr[0].get("version") or "")
                except Exception:
                    pass
    except Exception:
        pass

    norm_id = re.sub(r"[^a-z0-9]", "", (meta["mod_id"] or meta["file_name"]).lower())
    meta["client_only"] = (meta["environment"] == "client") or any(h in norm_id for h in CLIENT_ONLY_HINTS)
    return meta


def check_modpack_compatibility(version_dir, mc_version=None, loader=None):
    """Checks installed mods for loader mismatches, duplicates, and missing Fabric/Mod dependencies."""
    if not version_dir or not os.path.isdir(version_dir):
        return {"success": False, "error": "Instance directory not found", "issues": [], "mods": []}

    if not mc_version or not loader:
        try:
            import launcher
            mc_version, loader = launcher.detect_version_and_loader(version_dir)
        except Exception:
            mc_version = mc_version or "1.20.1"
            loader = loader or "Fabric"

    mods_dir = os.path.join(version_dir, "mods")
    if not os.path.isdir(mods_dir):
        return {"success": True, "mc_version": mc_version, "loader": loader, "issues": [], "mods": []}

    jars = sorted(
        f for f in os.listdir(mods_dir)
        if os.path.isfile(os.path.join(mods_dir, f)) and f.lower().endswith(".jar")
    )

    scanned = [_inspect_jar_metadata(os.path.join(mods_dir, fn)) for fn in jars]
    issues = []
    seen_ids = {}
    present_ids = {m["mod_id"].lower() for m in scanned if m["mod_id"]}
    inst_loader = str(loader or "Vanilla").lower()

    for m in scanned:
        mid = m["mod_id"].lower()
        if mid:
            if mid in seen_ids:
                issues.append({
                    "severity": "error",
                    "type": "duplicate_mod",
                    "mod": m["file_name"],
                    "detail": f"Duplicate mod ID '{m['mod_id']}' conflicts with {seen_ids[mid]}",
                })
            else:
                seen_ids[mid] = m["file_name"]

        # Loader compatibility check
        if m["loaders"] and inst_loader != "vanilla":
            low_loaders = {l.lower() for l in m["loaders"]}
            # Quilt can run Fabric mods; NeoForge 1.20.1 may accept some Forge mods, otherwise warn cleanly
            compatible = (inst_loader in low_loaders) or (inst_loader == "quilt" and "fabric" in low_loaders)
            if not compatible:
                issues.append({
                    "severity": "error",
                    "type": "loader_mismatch",
                    "mod": m["file_name"],
                    "detail": f"Built for {', '.join(m['loaders'])}, instance runs {loader}",
                })

        # Missing dependency check
        for dep in m["depends"]:
            d_low = dep.lower()
            if d_low in ("fabric", "fabric-api"):
                if "fabric-api" not in present_ids and "fabric" not in present_ids:
                    issues.append({
                        "severity": "warning",
                        "type": "missing_dependency",
                        "mod": m["file_name"],
                        "detail": "Requires Fabric API (not found in mods/)",
                    })
            elif d_low not in present_ids and d_low != m["mod_id"].lower():
                issues.append({
                    "severity": "warning",
                    "type": "missing_dependency",
                    "mod": m["file_name"],
                    "detail": f"Declares dependency '{dep}' (not found by mod_id in mods/)",
                })

    return {
        "success": True,
        "mc_version": mc_version,
        "loader": loader,
        "mods": scanned,
        "issues": issues,
    }


def check_modrinth_updates(version_dir, mc_version=None, loader=None):
    """Audits instance compatibility and batch-checks Modrinth /v2/version_files/update by SHA-512."""
    audit = check_modpack_compatibility(version_dir, mc_version=mc_version, loader=loader)
    if not audit.get("success"):
        return audit

    scanned = audit["mods"]
    loader_norm = str(audit.get("loader") or "fabric").lower()
    mc_ver = str(audit.get("mc_version") or "1.20.1").strip()
    if loader_norm == "vanilla" or not scanned:
        audit["updates"] = []
        return audit

    by_hash = {m["sha512"]: m for m in scanned if m.get("sha512")}
    if not by_hash:
        audit["updates"] = []
        return audit

    loaders_param = ["fabric", "quilt"] if loader_norm == "quilt" else [loader_norm]
    payload = json.dumps({
        "hashes": list(by_hash.keys()),
        "algorithm": "sha512",
        "loaders": loaders_param,
        "game_versions": [mc_ver],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.modrinth.com/v2/version_files/update",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "JustMichellee/Moon-Launcher/2.5.1",
        },
        method="POST",
    )
    updates = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for old_hash, ver_obj in (data or {}).items():
            local_mod = by_hash.get(old_hash)
            if not local_mod or not isinstance(ver_obj, dict):
                continue
            files = ver_obj.get("files") or []
            primary = next((f for f in files if f.get("primary")), files[0] if files else None)
            if not primary:
                continue
            new_sha512 = str((primary.get("hashes") or {}).get("sha512") or "")
            if new_sha512 and new_sha512 != old_hash:
                updates.append({
                    "file_name": local_mod["file_name"],
                    "mod_name": local_mod["name"],
                    "current_version": local_mod.get("version", ""),
                    "new_version": str(ver_obj.get("version_number") or ""),
                    "project_id": str(ver_obj.get("project_id") or ""),
                    "new_filename": str(primary.get("filename") or ""),
                    "download_url": str(primary.get("url") or ""),
                    "sha512": new_sha512,
                    "size_bytes": int(primary.get("size") or 0),
                })
        audit["modrinth_checked"] = len(by_hash)
    except Exception as e:
        audit["modrinth_error"] = str(e)

    audit["updates"] = updates
    return audit


def apply_modrinth_update(version_dir, old_file_name, download_url, new_filename, expected_sha512=None):
    """Downloads verified Modrinth update JAR and moves replaced JAR to mods/.backup_updates."""
    if not version_dir or not old_file_name or not download_url or not new_filename:
        return {"success": False, "error": "Missing update parameters"}
    mods_dir = os.path.join(version_dir, "mods")
    old_path = os.path.join(mods_dir, os.path.basename(old_file_name))
    safe_new = os.path.basename(new_filename)
    new_path = os.path.join(mods_dir, safe_new)
    backup_dir = os.path.join(mods_dir, ".backup_updates")
    os.makedirs(backup_dir, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=mods_dir, suffix=".tmp")
    os.close(tmp_fd)
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "JustMichellee/Moon-Launcher/2.5.1"})
        h512 = hashlib.sha512()
        with urllib.request.urlopen(req, timeout=25) as resp, open(tmp_path, "wb") as out_f:
            for chunk in iter(lambda: resp.read(32768), b""):
                h512.update(chunk)
                out_f.write(chunk)
        if expected_sha512 and h512.hexdigest().lower() != expected_sha512.lower():
            os.remove(tmp_path)
            return {"success": False, "error": "Downloaded JAR failed SHA-512 verification"}

        if os.path.exists(old_path):
            shutil.move(old_path, os.path.join(backup_dir, os.path.basename(old_file_name)))
        shutil.move(tmp_path, new_path)
        return {"success": True, "old_file": old_file_name, "new_file": safe_new}
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return {"success": False, "error": str(e)}

