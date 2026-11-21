import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import worker from "./src/index.js";

function createD1Shim(sqliteDb) {
  return {
    prepare(sql) {
      let boundArgs = [];
      const stmtObj = {
        bind(...args) {
          boundArgs = args;
          return stmtObj;
        },
        async first() {
          const stmt = sqliteDb.prepare(sql);
          return stmt.get(...boundArgs) ?? null;
        },
        async all() {
          const stmt = sqliteDb.prepare(sql);
          const results = stmt.all(...boundArgs);
          return { success: true, results };
        },
        async run() {
          const stmt = sqliteDb.prepare(sql);
          const info = stmt.run(...boundArgs);
          return { success: true, meta: { changes: info.changes } };
        },
      };
      return stmtObj;
    },
  };
}

const sqlite = new DatabaseSync(":memory:");
const schema = fs.readFileSync(path.join(import.meta.dirname, "schema.sql"), "utf8");
sqlite.exec(schema);
const env = { DB: createD1Shim(sqlite) };

async function call(method, p, body = null) {
  const req = new Request(`https://worker.local${p}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const res = await worker.fetch(req, env);
  return { status: res.status, data: await res.json() };
}

// 1. Health
const h = await call("GET", "/health");
assert.equal(h.status, 200);
assert.equal(h.data.ok, true);
assert.equal(h.data.engine, "cloudflare-d1");

// 2. Players & Presence
await call("POST", "/api/players/upsert", {
  player_id: "MOON-1111",
  username: "AliceMC",
  tag: "ALI-1111",
  skin_url: "https://example.com/alice.png",
});
await call("POST", "/api/players/upsert", {
  player_id: "MOON-2222",
  username: "BobMC",
  tag: "BOB-2222",
});
await call("POST", "/api/presence/upsert", {
  player_id: "MOON-2222",
  username: "BobMC",
  status: "hosting",
  version_name: "Fabric 1.20.1",
  mc_version: "1.20.1",
  loader: "Fabric",
  mod_count: 15,
  server_addr: "bob.playit.gg:25565",
  tunnel_active: true,
});

// 3. Lookup
const lk = await call("GET", "/api/players/lookup?q=MOON-2222");
assert.equal(lk.data.found, true);
assert.equal(lk.data.player.username, "BobMC");
assert.equal(lk.data.player.status, "hosting");
assert.equal(lk.data.player.server_addr, "bob.playit.gg:25565");

// 4. Bidirectional Friends (request -> incoming -> accept -> remove)
const reqRes = await call("POST", "/api/friends/request", { user_a: "MOON-2222", user_b: "MOON-1111" });
assert.equal(reqRes.data.status, "pending");

const listAliceBefore = await call("GET", "/api/friends/list?moon_id=MOON-1111");
assert.equal(listAliceBefore.data.incoming_requests.length, 1);
assert.equal(listAliceBefore.data.incoming_requests[0].player_id, "MOON-2222");
assert.equal(listAliceBefore.data.incoming_requests[0].username, "BobMC");

await call("POST", "/api/friends/accept", { user_a: "MOON-2222", user_b: "MOON-1111" });
const listAliceAfter = await call("GET", "/api/friends/list?moon_id=MOON-1111");
assert.equal(listAliceAfter.data.incoming_requests.length, 0);
assert.equal(listAliceAfter.data.friends.length, 1);

// 5. Phase 1 Party + Cross-Server Chat + Screenshot Share
const ptyCreate = await call("POST", "/api/party/create", { moon_id: "MOON-2222", username: "BobMC" });
assert.equal(ptyCreate.data.success, true);
const partyId = ptyCreate.data.party_id;

const ptyInvite = await call("POST", "/api/party/invite", {
  party_id: partyId,
  leader_id: "MOON-2222",
  username: "BobMC",
  targets: ["MOON-1111"],
});
assert.equal(ptyInvite.data.invited.length, 1);

const alicePartyInv = await call("GET", "/api/party/state?moon_id=MOON-1111");
assert.equal(alicePartyInv.data.pending_invites.length, 1);
assert.equal(alicePartyInv.data.pending_invites[0].party_id, partyId);

await call("POST", "/api/party/join", { party_id: partyId, moon_id: "MOON-1111", username: "AliceMC" });
await call("POST", "/api/party/target", { moon_id: "MOON-2222", target_server: "bob.playit.gg:25565", target_world: "Survival" });

const alicePartyState = await call("GET", "/api/party/state?moon_id=MOON-1111");
assert.equal(alicePartyState.data.party.party_id, partyId);
assert.equal(alicePartyState.data.party.target_server, "bob.playit.gg:25565");
assert.equal(alicePartyState.data.party.members.length, 2);

const chatSend = await call("POST", "/api/chat/send", {
  sender_id: "MOON-1111",
  sender_name: "AliceMC",
  recipient_id: "MOON-2222",
  body: "On my way!",
});
assert.equal(chatSend.data.success, true);

const chatPoll = await call("GET", "/api/chat/poll?moon_id=MOON-2222&peer_id=MOON-1111");
assert.ok(chatPoll.data.messages.some((m) => m.body === "On my way!"));

const tinyPngB64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";
const shotUp = await call("POST", "/api/screenshots/upload", {
  owner_id: "MOON-1111",
  owner_name: "AliceMC",
  version_name: "Fabric 1.20.1",
  mime_type: "image/png",
  image_b64: tinyPngB64,
});
assert.equal(shotUp.data.success, true);
const shotView = await worker.fetch(new Request(`https://worker.local/api/screenshots/view?id=${shotUp.data.share_id}`), env);
assert.equal(shotView.status, 200);
assert.equal(shotView.headers.get("Content-Type"), "image/png");
const viewBuf = new Uint8Array(await shotView.arrayBuffer());
assert.ok(viewBuf.length > 20);

await call("POST", "/api/party/leave", { moon_id: "MOON-1111" });
await call("POST", "/api/party/leave", { moon_id: "MOON-2222" });

// 6. Phase 3 P2P NAT Traversal Signaling
const offerRes = await call("POST", "/api/p2p/offer", {
  host_id: "MOON-2222",
  host_name: "BobMC",
  local_port: 55123,
  stun_ip: "203.0.113.10",
  stun_port: 49200,
  lan_ip: "192.168.1.50",
  lan_port: 49200,
  friends_only: true,
  fallback_addr: "bob.playit.gg:25565",
  psk_hex: "00112233445566778899aabbccddeeff",
});
assert.equal(offerRes.data.success, true);
const roomCode = offerRes.data.room_code;

// Non-friend blocked when friends_only=true
const strgConn = await call("POST", "/api/p2p/connect", {
  peer_id: "MOON-9999",
  peer_name: "Stranger",
  room_code: roomCode,
  stun_ip: "198.51.100.5",
  stun_port: 41000,
});
assert.equal(strgConn.status, 403);

// Friend MOON-1111 allowed
const peerConn = await call("POST", "/api/p2p/connect", {
  peer_id: "MOON-1111",
  peer_name: "AliceMC",
  room_code: roomCode,
  stun_ip: "198.51.100.20",
  stun_port: 51000,
  lan_ip: "192.168.1.60",
  lan_port: 51000,
});
assert.equal(peerConn.status, 200);
assert.equal(peerConn.data.host_stun_ip, "203.0.113.10");
assert.equal(peerConn.data.fallback_addr, "bob.playit.gg:25565");

const cands = await call("GET", `/api/p2p/candidates?host_id=MOON-2222`);
assert.equal(cands.data.candidates.length, 1);
assert.equal(cands.data.candidates[0].peer_id, "MOON-1111");

await call("POST", "/api/p2p/close", { host_id: "MOON-2222" });

// 7. Phase 4 Cloud Profile Sync (options.txt + servers)
const pPush = await call("POST", "/api/profile/push", {
  player_id: "MOON-1111",
  options: { fov: "90.0", key_key_forward: "key.keyboard.w" },
  servers: [{ name: "Hypixel", ip: "mc.hypixel.net", acceptTextures: 1 }],
});
assert.equal(pPush.data.success, true);

const pPull = await call("GET", "/api/profile/pull?moon_id=MOON-1111");
assert.equal(pPull.data.found, true);
assert.equal(pPull.data.options.fov, "90.0");
assert.equal(pPull.data.servers[0].ip, "mc.hypixel.net");
assert.equal(listAliceAfter.data.friends[0].status, "hosting");
assert.equal(listAliceAfter.data.friends[0].server_addr, "bob.playit.gg:25565");

// 5. Pack share presence & delete
await call("POST", "/api/presence/upsert", {
  player_id: "MOON-PACK-9001",
  username: "BobMC",
  status: "sharing_pack",
  version_name: "SkyFactory",
  server_addr: "https://share.trycloudflare.com",
  tunnel_active: true,
});
const packLk = await call("GET", "/api/players/lookup?q=MOON-PACK-9001");
assert.equal(packLk.data.found, true);
assert.equal(packLk.data.player.version_name, "SkyFactory");
await call("DELETE", "/api/presence/delete?player_id=MOON-PACK-9001");
const packAfter = await call("GET", "/api/players/lookup?q=MOON-PACK-9001");
assert.equal(packAfter.data.found, false);

// 6. Remove friend
await call("POST", "/api/friends/remove", { user_a: "MOON-1111", user_b: "MOON-2222" });
const listAliceRemoved = await call("GET", "/api/friends/list?moon_id=MOON-1111");
assert.equal(listAliceRemoved.data.friends.length, 0);

console.log("CLOUDFLARE_WORKER_D1_TESTS_PASSED");

