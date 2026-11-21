"""
Microsoft Account OAuth2 Authentication & Multi-Account Manager for Moon Launcher.
Implements:
  Live OAuth2 (00000000402b5328) -> Xbox Live -> XSTS -> Minecraft Services
  -> Entitlements check -> Mojang Profile (UUID, Username, Skin, Cape)
"""

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from paths import ACCOUNTS_PATH, BASE_DIR, CONFIG_PATH, SKINS_DIR

MS_CLIENT_ID = "00000000402b5328"
MS_REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"
MS_SCOPE = "XboxLive.signin offline_access"

USER_AGENT = "MoonLauncher/2.5.1"


def offline_minecraft_uuid(username):
    """
    Computes standard Minecraft OfflinePlayer UUID (version 3 MD5, 32-char hex without hyphens),
    matching Java UUID.nameUUIDFromBytes(("OfflinePlayer:" + username).getBytes(UTF_8)).
    """
    raw = f"OfflinePlayer:{username}".encode("utf-8")
    md5_bytes = bytearray(hashlib.md5(raw).digest())
    md5_bytes[6] = (md5_bytes[6] & 0x0F) | 0x30
    md5_bytes[8] = (md5_bytes[8] & 0x3F) | 0x80
    return bytes(md5_bytes).hex()


def validate_minecraft_username(raw_name):
    """Validates and normalizes a Minecraft username (3-16 chars, A-Z, a-z, 0-9, _)."""
    if raw_name is None:
        return False, "Username cannot be empty.", ""
    cleaned = str(raw_name).strip().replace(" ", "_")
    if not cleaned:
        return False, "Username cannot be empty.", ""
    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", cleaned):
        return (
            False,
            "Username must be 3-16 characters using only letters, numbers, and underscores (_).",
            cleaned,
        )
    return True, "", cleaned


def get_authorize_url():
    params = urllib.parse.urlencode(
        {
            "client_id": MS_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": MS_REDIRECT_URI,
            "scope": MS_SCOPE,
            "prompt": "select_account",
        }
    )
    return f"https://login.live.com/oauth20_authorize.srf?{params}"


def extract_code_from_input(raw_input):
    """Extracts the OAuth2 authorization code from either a full redirect URL or raw code string."""
    s = str(raw_input or "").strip().strip('"').strip("'")
    if not s:
        return None
    if s.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(parsed.query)
        codes = qs.get("code")
        if codes:
            return codes[0]
        return None
    if "code=" in s:
        qs = urllib.parse.parse_qs(s.lstrip("?"))
        codes = qs.get("code")
        if codes:
            return codes[0]
    return s


def _http_post_form(url, form_dict, timeout=15):
    data = urllib.parse.urlencode(form_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_body}")


def _http_post_json(url, payload, headers=None, timeout=15):
    body = json.dumps(payload).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_body}")


def _http_get_json(url, headers=None, timeout=15):
    req_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_body}")


def _complete_xbox_mc_chain(ms_access_token, ms_refresh_token, ms_expires_in):
    # 1. Xbox Live User Authenticate
    xbl_resp = _http_post_json(
        "https://user.auth.xboxlive.com/user/authenticate",
        {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={ms_access_token}",
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        },
    )
    xbl_token = xbl_resp.get("Token")
    uhs = xbl_resp.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs")
    if not xbl_token or not uhs:
        raise RuntimeError("Xbox Live authentication failed (missing XBL token or UHS).")

    # 2. XSTS Authorize
    try:
        xsts_resp = _http_post_json(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            {
                "Properties": {
                    "SandboxId": "RETAIL",
                    "UserTokens": [xbl_token],
                },
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT",
            },
        )
    except RuntimeError as e:
        msg = str(e)
        if "2148916233" in msg:
            raise RuntimeError("This Microsoft account has no Xbox profile yet. Sign in on xbox.com once first.")
        if "2148916238" in msg:
            raise RuntimeError("Child account requires family consent on xbox.com before signing in.")
        raise

    xsts_token = xsts_resp.get("Token")
    xuid = xsts_resp.get("DisplayClaims", {}).get("xui", [{}])[0].get("xid", "0")
    if not xsts_token:
        raise RuntimeError("XSTS authorization failed (missing token).")

    # 3. Minecraft Services Login
    mc_auth = _http_post_json(
        "https://api.minecraftservices.com/authentication/login_with_xbox",
        {"identityToken": f"XBL3.0 x={uhs};{xsts_token}"},
    )
    mc_access_token = mc_auth.get("access_token")
    mc_expires_in = int(mc_auth.get("expires_in", 86400))
    if not mc_access_token:
        raise RuntimeError("Minecraft Services login failed.")

    auth_header = {"Authorization": f"Bearer {mc_access_token}"}

    # 4. Verify Minecraft Java Edition Ownership
    ent = _http_get_json(
        "https://api.minecraftservices.com/entitlements/mcstore",
        headers=auth_header,
    )
    if not ent.get("items"):
        raise RuntimeError(
            "This Microsoft account does not own Minecraft: Java Edition."
        )

    # 5. Fetch Minecraft Profile (UUID, Username, Skins, Capes)
    profile = _http_get_json(
        "https://api.minecraftservices.com/minecraft/profile",
        headers=auth_header,
    )
    mc_uuid = profile.get("id")
    mc_name = profile.get("name")
    if not mc_uuid or not mc_name:
        raise RuntimeError("Could not retrieve Minecraft profile (has a Java username been created?).")

    active_skin = next(
        (s for s in profile.get("skins", []) if s.get("state") == "ACTIVE"),
        (profile.get("skins") or [{}])[0],
    )
    active_cape = next(
        (c for c in profile.get("capes", []) if c.get("state") == "ACTIVE"),
        None,
    )

    expires_at = int(time.time()) + min(mc_expires_in, int(ms_expires_in or 86400))
    return {
        "id": f"msa:{mc_uuid}",
        "type": "microsoft",
        "username": mc_name,
        "uuid": mc_uuid,
        "access_token": mc_access_token,
        "refresh_token": ms_refresh_token or "",
        "expires_at": expires_at,
        "xuid": xuid or "0",
        "skin_url": active_skin.get("url", ""),
        "skin_variant": str(active_skin.get("variant", "classic")).lower(),
        "cape_url": active_cape.get("url", "") if active_cape else "",
    }


def login_with_auth_code(code_or_url):
    """Completes Microsoft OAuth2 login from authorization code or redirect URL."""
    code = extract_code_from_input(code_or_url)
    if not code:
        raise RuntimeError("Authorization code not found in redirect URL.")

    token_resp = _http_post_form(
        "https://login.live.com/oauth20_token.srf",
        {
            "client_id": MS_CLIENT_ID,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": MS_REDIRECT_URI,
            "scope": MS_SCOPE,
        },
    )
    ms_access = token_resp.get("access_token")
    ms_refresh = token_resp.get("refresh_token")
    ms_expires = token_resp.get("expires_in", 86400)
    if not ms_access:
        raise RuntimeError("Failed to obtain Microsoft OAuth2 access token.")

    account = _complete_xbox_mc_chain(ms_access, ms_refresh, ms_expires)
    save_account(account, set_active=True)
    sync_account_to_config(account)
    return account


def refresh_microsoft_account(account):
    """Refreshes an existing Microsoft account using its stored refresh_token."""
    refresh_tok = account.get("refresh_token")
    if not refresh_tok:
        raise RuntimeError("No refresh token saved. Please sign in with Microsoft again.")

    token_resp = _http_post_form(
        "https://login.live.com/oauth20_token.srf",
        {
            "client_id": MS_CLIENT_ID,
            "refresh_token": refresh_tok,
            "grant_type": "refresh_token",
            "redirect_uri": MS_REDIRECT_URI,
            "scope": MS_SCOPE,
        },
    )
    ms_access = token_resp.get("access_token")
    ms_refresh = token_resp.get("refresh_token") or refresh_tok
    ms_expires = token_resp.get("expires_in", 86400)
    if not ms_access:
        raise RuntimeError("Failed to refresh Microsoft token.")

    updated = _complete_xbox_mc_chain(ms_access, ms_refresh, ms_expires)
    save_account(updated, set_active=True)
    sync_account_to_config(updated)
    return updated


def load_accounts_store():
    if os.path.exists(ACCOUNTS_PATH):
        try:
            with open(ACCOUNTS_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("accounts", [])
                    data.setdefault("active_account_id", "")
                    return data
        except Exception:
            pass
    return {"active_account_id": "", "accounts": []}


def save_accounts_store(store):
    os.makedirs(os.path.dirname(ACCOUNTS_PATH), exist_ok=True)
    with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def save_account(account, set_active=True):
    store = load_accounts_store()
    accounts = [a for a in store.get("accounts", []) if a.get("id") != account.get("id")]
    accounts.append(account)
    store["accounts"] = accounts
    if set_active:
        store["active_account_id"] = account["id"]
    save_accounts_store(store)


def get_active_account():
    store = load_accounts_store()
    active_id = store.get("active_account_id", "")
    for acc in store.get("accounts", []):
        if acc.get("id") == active_id:
            return acc
    return None


def list_accounts_public():
    """Returns sanitized account summaries safe to display in UI/CLI (no tokens exposed)."""
    store = load_accounts_store()
    active_id = store.get("active_account_id", "")
    out = []
    for acc in store.get("accounts", []):
        out.append(
            {
                "id": acc.get("id", ""),
                "type": acc.get("type", "offline"),
                "username": acc.get("username", "Player"),
                "uuid": acc.get("uuid", ""),
                "skin_url": acc.get("skin_url", ""),
                "skin_variant": acc.get("skin_variant", "classic"),
                "active": acc.get("id") == active_id,
            }
        )
    return out


def switch_account(account_id):
    """Switches to a stored Microsoft account or 'offline' mode."""
    store = load_accounts_store()
    if account_id == "offline" or not account_id:
        store["active_account_id"] = ""
        save_accounts_store(store)
        sync_offline_to_config()
        return {"type": "offline", "username": _read_root_username()}

    target = next((a for a in store.get("accounts", []) if a.get("id") == account_id), None)
    if not target:
        raise RuntimeError(f"Account '{account_id}' not found.")
    store["active_account_id"] = account_id
    save_accounts_store(store)
    sync_account_to_config(target)
    return target


def remove_account(account_id):
    store = load_accounts_store()
    store["accounts"] = [a for a in store.get("accounts", []) if a.get("id") != account_id]
    if store.get("active_account_id") == account_id:
        store["active_account_id"] = ""
        sync_offline_to_config()
    save_accounts_store(store)
    return True


def _read_root_username():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f).get("username") or "Player"
        except Exception:
            pass
    return "Player"


def sync_offline_to_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["auth_type"] = "offline"
    cfg.pop("active_account_id", None)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def sync_account_to_config(account):
    """Synchronizes Microsoft account profile (username, skin, cape) into launcher_config.json."""
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            pass

    username = account.get("username", "Player")
    cfg["username"] = username
    cfg["auth_type"] = account.get("type", "microsoft")
    cfg["active_account_id"] = account.get("id", "")

    skin_url = account.get("skin_url", "")
    if skin_url:
        try:
            os.makedirs(SKINS_DIR, exist_ok=True)
            req = urllib.request.Request(skin_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
            if raw.startswith(b"\x89PNG"):
                active_p = os.path.join(SKINS_DIR, "active_skin.png")
                user_p = os.path.join(SKINS_DIR, f"{username}.png")
                with open(active_p, "wb") as f1:
                    f1.write(raw)
                with open(user_p, "wb") as f2:
                    f2.write(raw)
                cfg["custom_skin"] = active_p
                cfg["custom_skin_url"] = skin_url
                cfg["skin_model"] = "slim" if account.get("skin_variant") == "slim" else "classic"
        except Exception:
            pass

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_launch_auth(cfg=None):
    """
    Returns launch auth credentials for Minecraft CLI arguments:
    {'username', 'uuid', 'access_token', 'user_type', 'xuid', 'auth_type'}
    Automatically refreshes Microsoft token if expired or nearing expiration.
    """
    acc = get_active_account()
    if acc and acc.get("type") == "microsoft":
        if time.time() >= float(acc.get("expires_at", 0)) - 300:
            try:
                acc = refresh_microsoft_account(acc)
            except Exception as e:
                print(f"[Moon Auth] Warning: Token refresh failed ({e}); using cached session.")
        return {
            "auth_type": "microsoft",
            "username": acc.get("username", "Player"),
            "uuid": acc.get("uuid", offline_minecraft_uuid(acc.get("username", "Player"))),
            "access_token": acc.get("access_token", "0"),
            "user_type": "msa",
            "xuid": acc.get("xuid", "0"),
        }

    uname = (cfg or {}).get("username") or _read_root_username() or "Player"
    return {
        "auth_type": "offline",
        "username": uname,
        "uuid": offline_minecraft_uuid(uname),
        "access_token": "0",
        "user_type": "legacy",
        "xuid": "0",
    }

