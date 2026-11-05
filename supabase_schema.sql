-- ==============================================================================
-- Moon Launcher - Cloud Database Schema (Supabase PostgreSQL)
-- Copy and paste this script into Supabase SQL Editor and click "RUN"
-- ==============================================================================

-- 1. Table: players (Registered profiles, skins, and player IDs)
CREATE TABLE IF NOT EXISTS public.players (
    player_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    tag TEXT,
    skin_url TEXT,
    skin_cape_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Table: presence (Real-time live status, active modpack, and game server)
CREATE TABLE IF NOT EXISTS public.presence (
    username TEXT PRIMARY KEY,
    player_id TEXT,
    status TEXT DEFAULT 'online', -- 'online', 'playing', 'hosting', 'offline'
    version_name TEXT,
    mc_version TEXT,
    loader TEXT,
    mod_count INTEGER DEFAULT 0,
    server_addr TEXT,
    tunnel_active BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Table: friendships (Bidirectional mutual friendships)
CREATE TABLE IF NOT EXISTS public.friendships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_a TEXT NOT NULL,
    user_b TEXT NOT NULL,
    status TEXT DEFAULT 'accepted', -- 'pending', 'accepted'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_a, user_b)
);

-- 4. Enable Row Level Security (RLS) with Public Anon Access
ALTER TABLE public.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.presence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to players" ON public.players
    FOR SELECT USING (true);
CREATE POLICY "Allow public insert/update access to players" ON public.players
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read access to presence" ON public.presence
    FOR SELECT USING (true);
CREATE POLICY "Allow public insert/update access to presence" ON public.presence
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow public read access to friendships" ON public.friendships
    FOR SELECT USING (true);
CREATE POLICY "Allow public insert/update access to friendships" ON public.friendships
    FOR ALL USING (true) WITH CHECK (true);

-- 5. Enable Supabase Realtime for instant WebSockets events
ALTER PUBLICATION supabase_realtime ADD TABLE public.presence;
ALTER PUBLICATION supabase_realtime ADD TABLE public.friendships;

-- Create helper index for fast search
CREATE INDEX IF NOT EXISTS idx_presence_updated ON public.presence(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_friendships_users ON public.friendships(user_a, user_b);
