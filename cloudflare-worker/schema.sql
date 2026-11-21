-- ==============================================================================
-- Moon Launcher - Cloudflare D1 Schema (SQLite)
-- Zero auto-pause, 100% Free Tier compatible.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    tag TEXT DEFAULT '',
    skin_url TEXT DEFAULT '',
    skin_cape_url TEXT DEFAULT '',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_seen TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS presence (
    player_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    status TEXT DEFAULT 'online',
    version_name TEXT DEFAULT '',
    mc_version TEXT DEFAULT '',
    loader TEXT DEFAULT '',
    mod_count INTEGER DEFAULT 0,
    server_addr TEXT DEFAULT '',
    tunnel_active INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS pack_shares (
    code TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    version_name TEXT DEFAULT '',
    mc_version TEXT DEFAULT '',
    loader TEXT DEFAULT '',
    mod_count INTEGER DEFAULT 0,
    server_addr TEXT DEFAULT '',
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_a TEXT NOT NULL,
    user_b TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(user_a, user_b)
);

CREATE INDEX IF NOT EXISTS idx_presence_username ON presence(username);
CREATE INDEX IF NOT EXISTS idx_presence_updated ON presence(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_friendships_a ON friendships(user_a);
CREATE INDEX IF NOT EXISTS idx_friendships_b ON friendships(user_b);

-- ==============================================================================
-- Phase 1 Social Extension: Party / Squad, Cross-Server Chat & Screenshot Share
-- ==============================================================================

CREATE TABLE IF NOT EXISTS parties (
    party_id TEXT PRIMARY KEY,
    leader_id TEXT NOT NULL,
    target_server TEXT DEFAULT '',
    target_world TEXT DEFAULT '',
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS party_members (
    party_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    status TEXT DEFAULT 'joined',
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (party_id, player_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id TEXT NOT NULL,
    sender_name TEXT DEFAULT '',
    recipient_id TEXT DEFAULT '',
    party_id TEXT DEFAULT '',
    kind TEXT DEFAULT 'text',
    body TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS shared_screenshots (
    share_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    owner_name TEXT DEFAULT '',
    version_name TEXT DEFAULT '',
    mime_type TEXT DEFAULT 'image/png',
    image_b64 TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_party_members_player ON party_members(player_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_party ON messages(party_id, created_at);
CREATE INDEX IF NOT EXISTS idx_screenshots_expires ON shared_screenshots(expires_at);

-- ==============================================================================
-- Phase 3 P2P NAT Traversal Signaling (STUN / UDP Hole Punching + Relay Fallback)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS p2p_sessions (
    room_code TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    host_name TEXT DEFAULT '',
    local_port INTEGER DEFAULT 25565,
    stun_ip TEXT DEFAULT '',
    stun_port INTEGER DEFAULT 0,
    lan_ip TEXT DEFAULT '',
    lan_port INTEGER DEFAULT 0,
    friends_only INTEGER DEFAULT 1,
    fallback_addr TEXT DEFAULT '',
    psk_hex TEXT DEFAULT '',
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS p2p_candidates (
    room_code TEXT NOT NULL,
    peer_id TEXT NOT NULL,
    peer_name TEXT DEFAULT '',
    stun_ip TEXT DEFAULT '',
    stun_port INTEGER DEFAULT 0,
    lan_ip TEXT DEFAULT '',
    lan_port INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (room_code, peer_id)
);

CREATE INDEX IF NOT EXISTS idx_p2p_sessions_host ON p2p_sessions(host_id);
CREATE INDEX IF NOT EXISTS idx_p2p_candidates_room ON p2p_candidates(room_code, updated_at);

-- ==============================================================================
-- Phase 4 Cloud Profile Sync (Keybinds / options.txt & Saved Server List)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    player_id TEXT PRIMARY KEY,
    options_json TEXT DEFAULT '{}',
    servers_json TEXT DEFAULT '[]',
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
