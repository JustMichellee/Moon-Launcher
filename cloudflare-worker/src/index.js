/**
 * Moon Launcher Cloud API (Cloudflare Workers + D1)
 * Endpoints for Moon ID players, live presence, bidirectional friendships,
 * and MOON-PACK-XXXX modpack share registry.
 */

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Cache-Control": "no-store",
    },
  });
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function futureIso(hoursFromNow) {
  return new Date(Date.now() + hoursFromNow * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function pastIso(hoursAgo) {
  return new Date(Date.now() - hoursAgo * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function randomCode(prefix, len = 4) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = prefix;
  for (let i = 0; i < len; i++) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

function base64ToBytes(b64) {
  const clean = String(b64 || "").replace(/^data:image\/[a-zA-Z0-9+.-]+;base64,/, "").replace(/\s+/g, "");
  const bin = atob(clean);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    bytes[i] = bin.charCodeAt(i);
  }
  return bytes;
}

async function resolvePlayerIdOrName(db, rawTarget) {
  const q = cleanStr(rawTarget, 64);
  if (!q) return null;
  const qUpper = q.toUpperCase();
  const row = await db.prepare(
    "SELECT player_id, username FROM players WHERE upper(player_id) = ? OR lower(username) = lower(?) LIMIT 1"
  )
    .bind(qUpper, q)
    .first();
  if (row) return { player_id: String(row.player_id).toUpperCase(), username: row.username || q };
  if (qUpper.startsWith("MOON-")) return { player_id: qUpper, username: qUpper };
  return null;
}

async function leaveAllJoinedParties(db, moonId) {
  const ts = nowIso();
  const joined = await db.prepare(
    "SELECT party_id FROM party_members WHERE player_id = ? AND status = 'joined'"
  )
    .bind(moonId)
    .all();
  await db.prepare("DELETE FROM party_members WHERE player_id = ? AND status = 'joined'").bind(moonId).run();
  for (const r of joined.results || []) {
    const pid = r.party_id;
    const party = await db.prepare("SELECT leader_id FROM parties WHERE party_id = ? LIMIT 1").bind(pid).first();
    const nextMember = await db.prepare(
      "SELECT player_id FROM party_members WHERE party_id = ? AND status = 'joined' ORDER BY updated_at ASC LIMIT 1"
    )
      .bind(pid)
      .first();
    if (!nextMember) {
      await db.prepare("DELETE FROM party_members WHERE party_id = ?").bind(pid).run();
      await db.prepare("DELETE FROM parties WHERE party_id = ?").bind(pid).run();
    } else if (party && String(party.leader_id).toUpperCase() === moonId) {
      await db.prepare("UPDATE parties SET leader_id = ?, updated_at = ? WHERE party_id = ?")
        .bind(nextMember.player_id, ts, pid)
        .run();
    }
  }
}

function cleanStr(v, maxLen = 256) {
  return String(v ?? "").trim().slice(0, maxLen);
}

function formatPresenceRow(row) {
  if (!row) return null;
  return {
    username: row.username || "",
    player_id: row.player_id || "",
    status: row.status || "offline",
    version_name: row.version_name || "",
    mc_version: row.mc_version || "",
    loader: row.loader || "",
    mod_count: Number(row.mod_count || 0),
    server_addr: row.server_addr || "",
    tunnel_active: Boolean(row.tunnel_active),
    updated_at: row.updated_at || "",
    skin_url: row.skin_url || "",
  };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return jsonResponse({ ok: true }, 204);
    }

    const db = env?.DB;
    if (!db) {
      return jsonResponse({ error: "D1 database binding 'DB' is not configured" }, 500);
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (path === "/" || path === "/health") {
        await db.prepare("SELECT 1").first();
        return jsonResponse({ ok: true, service: "moon-launcher-cloud", engine: "cloudflare-d1" });
      }

      const body =
        request.method === "POST" || request.method === "PUT" || request.method === "PATCH"
          ? await request.json().catch(() => ({}))
          : {};

      // 1. Upsert player profile
      if (path === "/api/players/upsert" && request.method === "POST") {
        const playerId = cleanStr(body.player_id, 32).toUpperCase();
        const username = cleanStr(body.username, 32);
        if (!playerId || !username) {
          return jsonResponse({ error: "player_id and username are required" }, 400);
        }
        const tag = cleanStr(body.tag, 32);
        const skinUrl = cleanStr(body.skin_url, 512);
        const capeUrl = cleanStr(body.skin_cape_url, 512);
        const ts = nowIso();

        // Ensure username uniqueness if an older test record held the same username
        await db.prepare("DELETE FROM players WHERE lower(username) = lower(?) AND player_id != ?")
          .bind(username, playerId)
          .run();

        await db.prepare(
          `INSERT INTO players (player_id, username, tag, skin_url, skin_cape_url, created_at, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(player_id) DO UPDATE SET
             username = excluded.username,
             tag = CASE WHEN excluded.tag != '' THEN excluded.tag ELSE players.tag END,
             skin_url = CASE WHEN excluded.skin_url != '' THEN excluded.skin_url ELSE players.skin_url END,
             skin_cape_url = CASE WHEN excluded.skin_cape_url != '' THEN excluded.skin_cape_url ELSE players.skin_cape_url END,
             last_seen = excluded.last_seen`
        )
          .bind(playerId, username, tag, skinUrl, capeUrl, ts, ts)
          .run();

        return jsonResponse({ success: true, player_id: playerId, username });
      }

      // 2. Upsert presence or dedicated pack_shares (MOON-PACK-XXXX)
      if (path === "/api/presence/upsert" && request.method === "POST") {
        const username = cleanStr(body.username, 64);
        const playerId = cleanStr(body.player_id, 64).toUpperCase();
        if (!username || !playerId) {
          return jsonResponse({ error: "username and player_id are required" }, 400);
        }
        const status = cleanStr(body.status || "online", 32);
        const versionName = cleanStr(body.version_name, 128);
        const mcVersion = cleanStr(body.mc_version, 32);
        const loader = cleanStr(body.loader, 32);
        const modCount = Number(body.mod_count || 0);
        const serverAddr = cleanStr(body.server_addr, 256);
        const tunnelActive = body.tunnel_active ? 1 : 0;
        const ts = nowIso();

        if (playerId.startsWith("MOON-PACK-")) {
          await db.prepare(
            `INSERT INTO pack_shares (code, username, version_name, mc_version, loader, mod_count, server_addr, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
             ON CONFLICT(code) DO UPDATE SET
               username = excluded.username,
               version_name = excluded.version_name,
               mc_version = excluded.mc_version,
               loader = excluded.loader,
               mod_count = excluded.mod_count,
               server_addr = excluded.server_addr,
               updated_at = excluded.updated_at`
          )
            .bind(playerId, username, versionName, mcVersion, loader, modCount, serverAddr, ts)
            .run();
          return jsonResponse({ success: true });
        }

        await db.prepare(
          `INSERT INTO presence (player_id, username, status, version_name, mc_version, loader, mod_count, server_addr, tunnel_active, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(player_id) DO UPDATE SET
             username = excluded.username,
             status = excluded.status,
             version_name = excluded.version_name,
             mc_version = excluded.mc_version,
             loader = excluded.loader,
             mod_count = excluded.mod_count,
             server_addr = excluded.server_addr,
             tunnel_active = excluded.tunnel_active,
             updated_at = excluded.updated_at`
        )
          .bind(playerId, username, status, versionName, mcVersion, loader, modCount, serverAddr, tunnelActive, ts)
          .run();

        return jsonResponse({ success: true });
      }

      // 3. Delete presence or pack share (used when stopping MOON-PACK-XXXX share)
      if (path === "/api/presence/delete" && (request.method === "DELETE" || request.method === "POST")) {
        const pid = cleanStr(url.searchParams.get("player_id") || body.player_id, 64).toUpperCase();
        if (!pid) return jsonResponse({ error: "player_id required" }, 400);
        if (pid.startsWith("MOON-PACK-")) {
          await db.prepare("DELETE FROM pack_shares WHERE code = ?").bind(pid).run();
        } else {
          await db.prepare("DELETE FROM presence WHERE player_id = ?").bind(pid).run();
        }
        return jsonResponse({ success: true });
      }

      // 4. Lookup player or share code by Moon ID / username
      if (path === "/api/players/lookup" && request.method === "GET") {
        const q = cleanStr(url.searchParams.get("q"), 64);
        if (!q) return jsonResponse({ found: false }, 400);
        const qUpper = q.toUpperCase();

        if (qUpper.startsWith("MOON-PACK-")) {
          const ps = await db.prepare("SELECT * FROM pack_shares WHERE upper(code) = ? LIMIT 1").bind(qUpper).first();
          if (ps) {
            return jsonResponse({
              found: true,
              player: {
                player_id: ps.code,
                username: ps.username,
                status: "sharing_pack",
                version_name: ps.version_name || "",
                mc_version: ps.mc_version || "",
                loader: ps.loader || "",
                mod_count: Number(ps.mod_count || 0),
                server_addr: ps.server_addr || "",
                tunnel_active: true,
                updated_at: ps.updated_at || "",
              },
            });
          }
          return jsonResponse({ found: false, player: null });
        }

        const pr = await db.prepare(
          `SELECT pr.*, pl.skin_url
           FROM presence pr
           LEFT JOIN players pl ON pr.player_id = pl.player_id
           WHERE upper(pr.player_id) = ? OR lower(pr.username) = lower(?)
           ORDER BY pr.updated_at DESC LIMIT 1`
        )
          .bind(qUpper, q)
          .first();

        if (pr) {
          return jsonResponse({ found: true, player: formatPresenceRow(pr) });
        }

        const pl = await db.prepare(
          `SELECT * FROM players WHERE upper(player_id) = ? OR lower(username) = lower(?) LIMIT 1`
        )
          .bind(qUpper, q)
          .first();

        if (pl) {
          return jsonResponse({
            found: true,
            player: {
              player_id: pl.player_id,
              username: pl.username,
              skin_url: pl.skin_url || "",
              status: "offline",
              version_name: "",
              mc_version: "",
              loader: "",
              mod_count: 0,
              server_addr: "",
              tunnel_active: false,
            },
          });
        }

        return jsonResponse({ found: false, player: null });
      }

      // 5. Batch presence query
      if (path === "/api/presence/batch" && (request.method === "POST" || request.method === "GET")) {
        let keys = [];
        if (request.method === "POST" && Array.isArray(body.keys)) {
          keys = body.keys.map((k) => cleanStr(k, 64)).filter(Boolean);
        } else {
          const raw = cleanStr(url.searchParams.get("keys"), 1024);
          if (raw) keys = raw.split(",").map((s) => s.trim()).filter(Boolean);
        }
        if (!keys.length) return jsonResponse({ peers: [] });

        const upperKeys = [...new Set(keys.map((k) => k.toUpperCase()))].slice(0, 100);
        const lowerKeys = [...new Set(keys.map((k) => k.toLowerCase()))].slice(0, 100);
        const p1 = upperKeys.map(() => "?").join(",");
        const p2 = lowerKeys.map(() => "?").join(",");

        const stmt = db.prepare(
          `SELECT pr.*, pl.skin_url
           FROM presence pr
           LEFT JOIN players pl ON pr.player_id = pl.player_id
           WHERE upper(pr.player_id) IN (${p1}) OR lower(pr.username) IN (${p2})`
        );
        const res = await stmt.bind(...upperKeys, ...lowerKeys).all();
        return jsonResponse({ peers: (res.results || []).map(formatPresenceRow) });
      }

      // 6. Send friend request (auto-accepts if reverse pending request exists)
      if (path === "/api/friends/request" && request.method === "POST") {
        const userA = cleanStr(body.user_a, 32).toUpperCase();
        const userB = cleanStr(body.user_b, 32).toUpperCase();
        if (!userA || !userB || userA === userB) {
          return jsonResponse({ success: false, error: "Invalid user_a/user_b" }, 400);
        }

        const rev = await db.prepare(
          "SELECT status FROM friendships WHERE user_a = ? AND user_b = ? LIMIT 1"
        )
          .bind(userB, userA)
          .first();

        if (rev) {
          await db.prepare("UPDATE friendships SET status = 'accepted' WHERE user_a = ? AND user_b = ?")
            .bind(userB, userA)
            .run();
          return jsonResponse({ success: true, status: "accepted" });
        }

        const ts = nowIso();
        await db.prepare(
          `INSERT INTO friendships (user_a, user_b, status, created_at)
           VALUES (?, ?, 'pending', ?)
           ON CONFLICT(user_a, user_b) DO NOTHING`
        )
          .bind(userA, userB, ts)
          .run();

        const current = await db.prepare(
          "SELECT status FROM friendships WHERE user_a = ? AND user_b = ? LIMIT 1"
        )
          .bind(userA, userB)
          .first();

        return jsonResponse({ success: true, status: current?.status || "pending" });
      }

      // 7. Accept pending friend request
      if (path === "/api/friends/accept" && request.method === "POST") {
        const requesterId = cleanStr(body.user_a, 32).toUpperCase();
        const accepterId = cleanStr(body.user_b, 32).toUpperCase();
        if (!requesterId || !accepterId) {
          return jsonResponse({ success: false, error: "user_a and user_b required" }, 400);
        }
        await db.prepare("UPDATE friendships SET status = 'accepted' WHERE user_a = ? AND user_b = ?")
          .bind(requesterId, accepterId)
          .run();
        return jsonResponse({ success: true, status: "accepted" });
      }

      // 8. Remove / decline friendship
      if (path === "/api/friends/remove" && request.method === "POST") {
        const userA = cleanStr(body.user_a, 32).toUpperCase();
        const userB = cleanStr(body.user_b, 32).toUpperCase();
        if (!userA || !userB) {
          return jsonResponse({ success: false, error: "user_a and user_b required" }, 400);
        }
        await db.prepare(
          "DELETE FROM friendships WHERE (user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)"
        )
          .bind(userA, userB, userB, userA)
          .run();
        return jsonResponse({ success: true });
      }

      // 9. List friends & pending requests enriched with players + presence
      if (path === "/api/friends/list" && request.method === "GET") {
        const moonId = cleanStr(url.searchParams.get("moon_id"), 32).toUpperCase();
        if (!moonId) return jsonResponse({ error: "moon_id required" }, 400);

        const fsRes = await db.prepare(
          "SELECT user_a, user_b, status FROM friendships WHERE user_a = ? OR user_b = ?"
        )
          .bind(moonId, moonId)
          .all();

        const rows = fsRes.results || [];
        const peerIds = new Set();
        const friends = [];
        const incoming = [];
        const outgoing = [];

        for (const r of rows) {
          const ua = String(r.user_a || "").toUpperCase();
          const ub = String(r.user_b || "").toUpperCase();
          const peerId = ua === moonId ? ub : ua;
          if (!peerId || peerId === moonId) continue;
          peerIds.add(peerId);
          const item = { player_id: peerId, username: peerId, status: "offline" };
          if (r.status === "pending") {
            if (ub === moonId) incoming.push({ ...item, status: "pending" });
            else outgoing.push({ ...item, status: "pending" });
          } else {
            friends.push(item);
          }
        }

        if (peerIds.size > 0) {
          const idList = Array.from(peerIds);
          const placeholders = idList.map(() => "?").join(",");

          const plRes = await db.prepare(
            `SELECT player_id, username, skin_url FROM players WHERE player_id IN (${placeholders})`
          )
            .bind(...idList)
            .all();
          const plMap = new Map();
          for (const p of plRes.results || []) {
            plMap.set(String(p.player_id).toUpperCase(), p);
          }

          const prRes = await db.prepare(
            `SELECT * FROM presence WHERE player_id IN (${placeholders})`
          )
            .bind(...idList)
            .all();
          const prMap = new Map();
          for (const pr of prRes.results || []) {
            prMap.set(String(pr.player_id).toUpperCase(), pr);
          }

          for (const bucket of [...friends, ...incoming, ...outgoing]) {
            const pl = plMap.get(bucket.player_id);
            if (pl) {
              if (pl.username) bucket.username = pl.username;
              if (pl.skin_url) bucket.skin_url = pl.skin_url;
            }
            const pr = prMap.get(bucket.player_id);
            if (pr && bucket.status !== "pending") {
              if (pr.username) bucket.username = pr.username;
              bucket.status = pr.status || "offline";
              bucket.version_name = pr.version_name || "";
              bucket.mc_version = pr.mc_version || "";
              bucket.loader = pr.loader || "";
              bucket.mod_count = Number(pr.mod_count || 0);
              bucket.server_addr = pr.server_addr || "";
              bucket.tunnel_active = Boolean(pr.tunnel_active);
            } else if (pl && pl.username) {
              bucket.username = pl.username;
            }
          }
        }

        return jsonResponse({
          my_moon_id: moonId,
          friends,
          incoming_requests: incoming,
          outgoing_requests: outgoing,
        });
      }

      // 10. Cross-Server Chat / Quick Whisper
      if (path === "/api/chat/send" && request.method === "POST") {
        const senderId = cleanStr(body.sender_id, 32).toUpperCase();
        const senderName = cleanStr(body.sender_name, 32) || senderId;
        const recipientId = cleanStr(body.recipient_id, 32).toUpperCase();
        const partyId = cleanStr(body.party_id, 32).toUpperCase();
        const kind = cleanStr(body.kind || "text", 24) || "text";
        const msgBody = cleanStr(body.body, 500);
        if (!senderId || !msgBody || (!recipientId && !partyId)) {
          return jsonResponse({ success: false, error: "sender_id, body, and recipient_id or party_id are required" }, 400);
        }
        const ts = nowIso();
        await db.prepare("DELETE FROM messages WHERE created_at < ?").bind(pastIso(24 * 7)).run();
        const ins = await db.prepare(
          `INSERT INTO messages (sender_id, sender_name, recipient_id, party_id, kind, body, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)`
        )
          .bind(senderId, senderName, recipientId, partyId, kind, msgBody, ts)
          .run();
        return jsonResponse({
          success: true,
          id: ins?.meta?.last_row_id || 0,
          created_at: ts,
        });
      }

      if (path === "/api/chat/poll" && request.method === "GET") {
        const moonId = cleanStr(url.searchParams.get("moon_id"), 32).toUpperCase();
        const peerId = cleanStr(url.searchParams.get("peer_id"), 32).toUpperCase();
        const partyId = cleanStr(url.searchParams.get("party_id"), 32).toUpperCase();
        const limit = Math.max(1, Math.min(80, Number(url.searchParams.get("limit") || 40)));
        if (!moonId) return jsonResponse({ error: "moon_id required" }, 400);

        let rows = [];
        if (partyId) {
          const res = await db.prepare(
            `SELECT * FROM messages WHERE party_id = ? ORDER BY id DESC LIMIT ?`
          )
            .bind(partyId, limit)
            .all();
          rows = res.results || [];
        } else if (peerId) {
          const res = await db.prepare(
            `SELECT * FROM messages
             WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?)
             ORDER BY id DESC LIMIT ?`
          )
            .bind(moonId, peerId, peerId, moonId, limit)
            .all();
          rows = res.results || [];
        } else {
          const mem = await db.prepare(
            "SELECT party_id FROM party_members WHERE player_id = ? AND status = 'joined' LIMIT 1"
          )
            .bind(moonId)
            .first();
          const activeParty = mem ? String(mem.party_id || "").toUpperCase() : "";
          const res = activeParty
            ? await db.prepare(
                `SELECT * FROM messages
                 WHERE sender_id = ? OR recipient_id = ? OR party_id = ?
                 ORDER BY id DESC LIMIT ?`
              )
                .bind(moonId, moonId, activeParty, limit)
                .all()
            : await db.prepare(
                `SELECT * FROM messages
                 WHERE sender_id = ? OR recipient_id = ?
                 ORDER BY id DESC LIMIT ?`
              )
                .bind(moonId, moonId, limit)
                .all();
          rows = res.results || [];
        }

        return jsonResponse({ messages: rows.reverse() });
      }

      // 11. Party / Squad & 1-Click Mass Invite
      if (path === "/api/party/create" && request.method === "POST") {
        const moonId = cleanStr(body.moon_id, 32).toUpperCase();
        const username = cleanStr(body.username, 32) || moonId;
        if (!moonId) return jsonResponse({ success: false, error: "moon_id required" }, 400);

        await leaveAllJoinedParties(db, moonId);
        const partyId = randomCode("MOON-PTY-", 4);
        const ts = nowIso();
        await db.prepare(
          "INSERT INTO parties (party_id, leader_id, target_server, target_world, updated_at) VALUES (?, ?, '', '', ?)"
        )
          .bind(partyId, moonId, ts)
          .run();
        await db.prepare(
          "INSERT INTO party_members (party_id, player_id, username, status, updated_at) VALUES (?, ?, ?, 'joined', ?)"
        )
          .bind(partyId, moonId, username, ts)
          .run();

        return jsonResponse({ success: true, party_id: partyId, leader_id: moonId });
      }

      if (path === "/api/party/invite" && request.method === "POST") {
        const leaderId = cleanStr(body.leader_id || body.moon_id, 32).toUpperCase();
        let partyId = cleanStr(body.party_id, 32).toUpperCase();
        const rawTargets = Array.isArray(body.targets)
          ? body.targets
          : (body.target ? [body.target] : []);

        if (!leaderId || !rawTargets.length) {
          return jsonResponse({ success: false, error: "leader_id and targets required" }, 400);
        }

        const ts = nowIso();
        if (!partyId) {
          const own = await db.prepare(
            "SELECT party_id FROM party_members WHERE player_id = ? AND status = 'joined' LIMIT 1"
          )
            .bind(leaderId)
            .first();
          if (own) {
            partyId = String(own.party_id).toUpperCase();
          } else {
            await leaveAllJoinedParties(db, leaderId);
            partyId = randomCode("MOON-PTY-", 4);
            const leaderRow = await resolvePlayerIdOrName(db, leaderId);
            await db.prepare(
              "INSERT INTO parties (party_id, leader_id, target_server, target_world, updated_at) VALUES (?, ?, '', '', ?)"
            )
              .bind(partyId, leaderId, ts)
              .run();
            await db.prepare(
              "INSERT INTO party_members (party_id, player_id, username, status, updated_at) VALUES (?, ?, ?, 'joined', ?)"
            )
              .bind(partyId, leaderId, leaderRow?.username || leaderId, ts)
              .run();
          }
        }

        const leaderInfo = await resolvePlayerIdOrName(db, leaderId);
        const leaderName = cleanStr(body.username, 32) || leaderInfo?.username || leaderId;
        const invited = [];

        for (const rt of rawTargets.slice(0, 20)) {
          const resolved = await resolvePlayerIdOrName(db, rt);
          if (!resolved || resolved.player_id === leaderId) continue;
          const existing = await db.prepare(
            "SELECT status FROM party_members WHERE party_id = ? AND player_id = ? LIMIT 1"
          )
            .bind(partyId, resolved.player_id)
            .first();
          if (existing && existing.status === "joined") continue;

          await db.prepare(
            `INSERT INTO party_members (party_id, player_id, username, status, updated_at)
             VALUES (?, ?, ?, 'invited', ?)
             ON CONFLICT(party_id, player_id) DO UPDATE SET
               username = excluded.username,
               updated_at = excluded.updated_at`
          )
            .bind(partyId, resolved.player_id, resolved.username, ts)
            .run();

          await db.prepare(
            `INSERT INTO messages (sender_id, sender_name, recipient_id, party_id, kind, body, created_at)
             VALUES (?, ?, ?, ?, 'party_invite', ?, ?)`
          )
            .bind(leaderId, leaderName, resolved.player_id, partyId, `${leaderName} invited you to Party ${partyId}`, ts)
            .run();

          invited.push(resolved);
        }

        return jsonResponse({ success: true, party_id: partyId, invited });
      }

      if (path === "/api/party/join" && request.method === "POST") {
        const partyId = cleanStr(body.party_id, 32).toUpperCase();
        const moonId = cleanStr(body.moon_id, 32).toUpperCase();
        const username = cleanStr(body.username, 32) || moonId;
        if (!partyId || !moonId) return jsonResponse({ success: false, error: "party_id and moon_id required" }, 400);

        const party = await db.prepare("SELECT * FROM parties WHERE party_id = ? LIMIT 1").bind(partyId).first();
        if (!party) return jsonResponse({ success: false, error: "Party not found" }, 404);

        await leaveAllJoinedParties(db, moonId);
        const ts = nowIso();
        await db.prepare(
          `INSERT INTO party_members (party_id, player_id, username, status, updated_at)
           VALUES (?, ?, ?, 'joined', ?)
           ON CONFLICT(party_id, player_id) DO UPDATE SET
             username = excluded.username,
             status = 'joined',
             updated_at = excluded.updated_at`
        )
          .bind(partyId, moonId, username, ts)
          .run();

        await db.prepare(
          `INSERT INTO messages (sender_id, sender_name, recipient_id, party_id, kind, body, created_at)
           VALUES (?, ?, '', ?, 'system', ?, ?)`
        )
          .bind(moonId, username, partyId, `${username} joined the party`, ts)
          .run();

        return jsonResponse({ success: true, party_id: partyId });
      }

      if (path === "/api/party/leave" && request.method === "POST") {
        const moonId = cleanStr(body.moon_id, 32).toUpperCase();
        const partyId = cleanStr(body.party_id, 32).toUpperCase();
        if (!moonId) return jsonResponse({ success: false, error: "moon_id required" }, 400);
        if (partyId) {
          // Allow declining a specific pending invite without leaving current party
          const row = await db.prepare("SELECT status FROM party_members WHERE party_id = ? AND player_id = ? LIMIT 1")
            .bind(partyId, moonId)
            .first();
          if (row && row.status === "invited") {
            await db.prepare("DELETE FROM party_members WHERE party_id = ? AND player_id = ?").bind(partyId, moonId).run();
            return jsonResponse({ success: true });
          }
        }
        await leaveAllJoinedParties(db, moonId);
        return jsonResponse({ success: true });
      }

      if (path === "/api/party/target" && request.method === "POST") {
        const moonId = cleanStr(body.moon_id, 32).toUpperCase();
        const targetServer = cleanStr(body.target_server, 256);
        const targetWorld = cleanStr(body.target_world, 128);
        if (!moonId) return jsonResponse({ success: false, error: "moon_id required" }, 400);

        const mem = await db.prepare(
          "SELECT party_id FROM party_members WHERE player_id = ? AND status = 'joined' LIMIT 1"
        )
          .bind(moonId)
          .first();
        if (!mem) return jsonResponse({ success: false, error: "Not in a party" }, 404);

        const party = await db.prepare("SELECT * FROM parties WHERE party_id = ? LIMIT 1").bind(mem.party_id).first();
        if (!party || String(party.leader_id).toUpperCase() !== moonId) {
          return jsonResponse({ success: false, error: "Only the party leader can set party destination" }, 403);
        }

        const ts = nowIso();
        await db.prepare("UPDATE parties SET target_server = ?, target_world = ?, updated_at = ? WHERE party_id = ?")
          .bind(targetServer, targetWorld, ts, mem.party_id)
          .run();

        if (targetServer) {
          const leaderInfo = await resolvePlayerIdOrName(db, moonId);
          const lname = leaderInfo?.username || moonId;
          await db.prepare(
            `INSERT INTO messages (sender_id, sender_name, recipient_id, party_id, kind, body, created_at)
             VALUES (?, ?, '', ?, 'party_target', ?, ?)`
          )
            .bind(moonId, lname, mem.party_id, `${lname} is ready at ${targetServer}${targetWorld ? " (" + targetWorld + ")" : ""}`, ts)
            .run();
        }
        return jsonResponse({ success: true, party_id: mem.party_id, target_server: targetServer, target_world: targetWorld });
      }

      if (path === "/api/party/state" && request.method === "GET") {
        const moonId = cleanStr(url.searchParams.get("moon_id"), 32).toUpperCase();
        if (!moonId) return jsonResponse({ error: "moon_id required" }, 400);

        const myJoined = await db.prepare(
          "SELECT party_id FROM party_members WHERE player_id = ? AND status = 'joined' LIMIT 1"
        )
          .bind(moonId)
          .first();

        let partyObj = null;
        if (myJoined) {
          const party = await db.prepare("SELECT * FROM parties WHERE party_id = ? LIMIT 1")
            .bind(myJoined.party_id)
            .first();
          if (party) {
            const mRes = await db.prepare(
              `SELECT pm.player_id, pm.username, pm.status, pr.status AS online_status, pr.server_addr, pr.version_name
               FROM party_members pm
               LEFT JOIN presence pr ON pm.player_id = pr.player_id
               WHERE pm.party_id = ?
               ORDER BY pm.updated_at ASC`
            )
              .bind(party.party_id)
              .all();
            partyObj = {
              party_id: party.party_id,
              leader_id: party.leader_id,
              is_leader: String(party.leader_id).toUpperCase() === moonId,
              target_server: party.target_server || "",
              target_world: party.target_world || "",
              updated_at: party.updated_at || "",
              members: (mRes.results || []).map((m) => ({
                player_id: m.player_id,
                username: m.username || m.player_id,
                role: String(m.player_id).toUpperCase() === String(party.leader_id).toUpperCase() ? "leader" : "member",
                invite_status: m.status,
                online_status: m.online_status || "offline",
                server_addr: m.server_addr || "",
                version_name: m.version_name || "",
              })),
            };
          }
        }

        const invRes = await db.prepare(
          `SELECT pm.party_id, p.leader_id, p.target_server, p.target_world, pl.username AS leader_name, pm.updated_at
           FROM party_members pm
           JOIN parties p ON pm.party_id = p.party_id
           LEFT JOIN players pl ON p.leader_id = pl.player_id
           WHERE pm.player_id = ? AND pm.status = 'invited'
           ORDER BY pm.updated_at DESC LIMIT 10`
        )
          .bind(moonId)
          .all();

        return jsonResponse({
          my_moon_id: moonId,
          party: partyObj,
          pending_invites: (invRes.results || []).map((inv) => ({
            party_id: inv.party_id,
            leader_id: inv.leader_id,
            leader_name: inv.leader_name || inv.leader_id,
            target_server: inv.target_server || "",
            target_world: inv.target_world || "",
            updated_at: inv.updated_at || "",
          })),
        });
      }

      // 12. Screenshot Instant Share (D1 Blob + HTTP Viewer URL)
      if (path === "/api/screenshots/upload" && request.method === "POST") {
        const ownerId = cleanStr(body.owner_id, 32).toUpperCase();
        const ownerName = cleanStr(body.owner_name, 32) || ownerId;
        const versionName = cleanStr(body.version_name, 128);
        const mimeType = cleanStr(body.mime_type || "image/png", 48);
        const rawB64 = String(body.image_b64 || "").replace(/^data:image\/[a-zA-Z0-9+.-]+;base64,/, "").replace(/\s+/g, "");
        if (!ownerId || !rawB64) {
          return jsonResponse({ success: false, error: "owner_id and image_b64 are required" }, 400);
        }
        if (rawB64.length > 650000) {
          return jsonResponse({ success: false, error: "Screenshot too large (>480KB compressed limit)" }, 413);
        }
        const ts = nowIso();
        const expiresAt = futureIso(48);
        await db.prepare("DELETE FROM shared_screenshots WHERE expires_at < ?").bind(ts).run();

        const shareId = randomCode("SCR-", 8);
        await db.prepare(
          `INSERT INTO shared_screenshots (share_id, owner_id, owner_name, version_name, mime_type, image_b64, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
        )
          .bind(shareId, ownerId, ownerName, versionName, mimeType.startsWith("image/") ? mimeType : "image/png", rawB64, ts, expiresAt)
          .run();

        return jsonResponse({
          success: true,
          share_id: shareId,
          url: `${url.origin}/api/screenshots/view?id=${shareId}`,
          expires_at: expiresAt,
        });
      }

      if (path === "/api/screenshots/view" && request.method === "GET") {
        const shareId = cleanStr(url.searchParams.get("id"), 32).toUpperCase();
        if (!shareId) return jsonResponse({ error: "id required" }, 400);
        const row = await db.prepare(
          "SELECT mime_type, image_b64, expires_at FROM shared_screenshots WHERE share_id = ? LIMIT 1"
        )
          .bind(shareId)
          .first();
        if (!row) return jsonResponse({ error: "Screenshot not found or expired" }, 404);

        const bytes = base64ToBytes(row.image_b64);
        return new Response(bytes, {
          status: 200,
          headers: {
            "Content-Type": row.mime_type || "image/png",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
          },
        });
      }

      // 13. P2P NAT Traversal Signaling (Offer / Connect / Candidates / Close)
      if (path === "/api/p2p/offer" && request.method === "POST") {
        const hostId = cleanStr(body.host_id, 32).toUpperCase();
        const hostName = cleanStr(body.host_name, 32) || hostId;
        const localPort = Number(body.local_port || 25565);
        const stunIp = cleanStr(body.stun_ip, 64);
        const stunPort = Number(body.stun_port || 0);
        const lanIp = cleanStr(body.lan_ip, 64);
        const lanPort = Number(body.lan_port || stunPort || localPort);
        const friendsOnly = body.friends_only === false ? 0 : 1;
        const fallbackAddr = cleanStr(body.fallback_addr, 256);
        const pskHex = cleanStr(body.psk_hex, 64);
        if (!hostId) return jsonResponse({ success: false, error: "host_id required" }, 400);

        const ts = nowIso();
        await db.prepare("DELETE FROM p2p_sessions WHERE updated_at < ?").bind(pastIso(6)).run();

        const existing = await db.prepare("SELECT room_code FROM p2p_sessions WHERE host_id = ? LIMIT 1")
          .bind(hostId)
          .first();
        const roomCode = cleanStr(body.room_code, 32).toUpperCase() || existing?.room_code || randomCode("MOON-P2P-", 4);

        await db.prepare(
          `INSERT INTO p2p_sessions (room_code, host_id, host_name, local_port, stun_ip, stun_port, lan_ip, lan_port, friends_only, fallback_addr, psk_hex, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(room_code) DO UPDATE SET
             host_name = excluded.host_name,
             local_port = excluded.local_port,
             stun_ip = excluded.stun_ip,
             stun_port = excluded.stun_port,
             lan_ip = excluded.lan_ip,
             lan_port = excluded.lan_port,
             friends_only = excluded.friends_only,
             fallback_addr = excluded.fallback_addr,
             psk_hex = CASE WHEN excluded.psk_hex != '' THEN excluded.psk_hex ELSE p2p_sessions.psk_hex END,
             updated_at = excluded.updated_at`
        )
          .bind(roomCode, hostId, hostName, localPort, stunIp, stunPort, lanIp, lanPort, friendsOnly, fallbackAddr, pskHex, ts)
          .run();

        return jsonResponse({ success: true, room_code: roomCode, host_id: hostId });
      }

      if (path === "/api/p2p/connect" && request.method === "POST") {
        const peerId = cleanStr(body.peer_id, 32).toUpperCase();
        const peerName = cleanStr(body.peer_name, 32) || peerId;
        const rawTarget = cleanStr(body.room_code || body.host_id || body.target, 64).toUpperCase();
        const stunIp = cleanStr(body.stun_ip, 64);
        const stunPort = Number(body.stun_port || 0);
        const lanIp = cleanStr(body.lan_ip, 64);
        const lanPort = Number(body.lan_port || stunPort || 0);
        if (!peerId || !rawTarget) {
          return jsonResponse({ success: false, error: "peer_id and room_code or host_id required" }, 400);
        }

        const session = await db.prepare(
          "SELECT * FROM p2p_sessions WHERE upper(room_code) = ? OR upper(host_id) = ? OR lower(host_name) = lower(?) ORDER BY updated_at DESC LIMIT 1"
        )
          .bind(rawTarget, rawTarget, rawTarget)
          .first();
        if (!session) {
          return jsonResponse({ success: false, error: "Host P2P room not found or offline" }, 404);
        }

        if (Number(session.friends_only) === 1 && String(session.host_id).toUpperCase() !== peerId) {
          const fs = await db.prepare(
            "SELECT status FROM friendships WHERE ((user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)) AND status = 'accepted' LIMIT 1"
          )
            .bind(session.host_id, peerId, peerId, session.host_id)
            .first();
          if (!fs) {
            return jsonResponse({ success: false, error: "Host enabled Friends-Only P2P access" }, 403);
          }
        }

        const ts = nowIso();
        await db.prepare(
          `INSERT INTO p2p_candidates (room_code, peer_id, peer_name, stun_ip, stun_port, lan_ip, lan_port, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(room_code, peer_id) DO UPDATE SET
             peer_name = excluded.peer_name,
             stun_ip = excluded.stun_ip,
             stun_port = excluded.stun_port,
             lan_ip = excluded.lan_ip,
             lan_port = excluded.lan_port,
             updated_at = excluded.updated_at`
        )
          .bind(session.room_code, peerId, peerName, stunIp, stunPort, lanIp, lanPort, ts)
          .run();

        return jsonResponse({
          success: true,
          room_code: session.room_code,
          host_id: session.host_id,
          host_name: session.host_name,
          host_stun_ip: session.stun_ip || "",
          host_stun_port: Number(session.stun_port || 0),
          host_lan_ip: session.lan_ip || "",
          host_lan_port: Number(session.lan_port || 0),
          fallback_addr: session.fallback_addr || "",
          psk_hex: session.psk_hex || "",
        });
      }

      if (path === "/api/p2p/candidates" && request.method === "GET") {
        const hostId = cleanStr(url.searchParams.get("host_id") || url.searchParams.get("moon_id"), 32).toUpperCase();
        const roomCode = cleanStr(url.searchParams.get("room_code"), 32).toUpperCase();
        if (!hostId && !roomCode) return jsonResponse({ error: "host_id or room_code required" }, 400);

        const session = roomCode
          ? await db.prepare("SELECT room_code FROM p2p_sessions WHERE room_code = ? LIMIT 1").bind(roomCode).first()
          : await db.prepare("SELECT room_code FROM p2p_sessions WHERE host_id = ? LIMIT 1").bind(hostId).first();
        if (!session) return jsonResponse({ room_code: "", candidates: [] });

        const res = await db.prepare(
          "SELECT peer_id, peer_name, stun_ip, stun_port, lan_ip, lan_port, updated_at FROM p2p_candidates WHERE room_code = ? AND updated_at >= ?"
        )
          .bind(session.room_code, pastIso(0.1))
          .all();

        return jsonResponse({ room_code: session.room_code, candidates: res.results || [] });
      }

      if (path === "/api/p2p/close" && request.method === "POST") {
        const hostId = cleanStr(body.host_id || body.moon_id, 32).toUpperCase();
        const roomCode = cleanStr(body.room_code, 32).toUpperCase();
        if (roomCode) {
          await db.prepare("DELETE FROM p2p_candidates WHERE room_code = ?").bind(roomCode).run();
          await db.prepare("DELETE FROM p2p_sessions WHERE room_code = ?").bind(roomCode).run();
        } else if (hostId) {
          const s = await db.prepare("SELECT room_code FROM p2p_sessions WHERE host_id = ?").bind(hostId).all();
          for (const row of s.results || []) {
            await db.prepare("DELETE FROM p2p_candidates WHERE room_code = ?").bind(row.room_code).run();
          }
          await db.prepare("DELETE FROM p2p_sessions WHERE host_id = ?").bind(hostId).run();
        }
        return jsonResponse({ success: true });
      }

      // 14. Cloud Profile Sync (options.txt / Keybinds + servers.dat)
      if (path === "/api/profile/push" && request.method === "POST") {
        const playerId = cleanStr(body.player_id || body.moon_id, 32).toUpperCase();
        if (!playerId) return jsonResponse({ success: false, error: "player_id required" }, 400);

        const existing = await db.prepare("SELECT options_json, servers_json FROM user_profiles WHERE player_id = ? LIMIT 1")
          .bind(playerId)
          .first();

        let optsStr = existing?.options_json || "{}";
        if (body.options && typeof body.options === "object") {
          const serialized = JSON.stringify(body.options);
          if (serialized.length > 130000) {
            return jsonResponse({ success: false, error: "options payload too large" }, 413);
          }
          optsStr = serialized;
        }

        let srvsStr = existing?.servers_json || "[]";
        if (Array.isArray(body.servers)) {
          const serialized = JSON.stringify(body.servers.slice(0, 100));
          if (serialized.length > 130000) {
            return jsonResponse({ success: false, error: "servers payload too large" }, 413);
          }
          srvsStr = serialized;
        }

        const ts = nowIso();
        await db.prepare(
          `INSERT INTO user_profiles (player_id, options_json, servers_json, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(player_id) DO UPDATE SET
             options_json = excluded.options_json,
             servers_json = excluded.servers_json,
             updated_at = excluded.updated_at`
        )
          .bind(playerId, optsStr, srvsStr, ts)
          .run();

        return jsonResponse({ success: true, player_id: playerId, updated_at: ts });
      }

      if (path === "/api/profile/pull" && request.method === "GET") {
        const playerId = cleanStr(url.searchParams.get("moon_id") || url.searchParams.get("player_id"), 32).toUpperCase();
        if (!playerId) return jsonResponse({ error: "moon_id required" }, 400);
        const row = await db.prepare("SELECT * FROM user_profiles WHERE player_id = ? LIMIT 1").bind(playerId).first();
        if (!row) {
          return jsonResponse({ found: false, player_id: playerId, options: {}, servers: [] });
        }
        let options = {};
        let servers = [];
        try { options = JSON.parse(row.options_json || "{}"); } catch {}
        try { servers = JSON.parse(row.servers_json || "[]"); } catch {}
        return jsonResponse({
          found: true,
          player_id: playerId,
          options,
          servers,
          updated_at: row.updated_at || "",
        });
      }

      return jsonResponse({ error: "Not found" }, 404);
    } catch (err) {
      return jsonResponse({ error: err?.message || "Internal error" }, 500);
    }
  },
};
