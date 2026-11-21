package dev.moonlauncher.sync;

import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.imageio.ImageIO;

/**
 * Connects MoonLauncher ID (MOON-XXXX) inside Minecraft directly to the Supabase Cloud
 * database schema (`players`, `presence`, `friendships`), tracks live game activity from
 * logs, and synchronizes bidirectional friend requests with local friends.json.
 */
public class MoonCloudClient {

    private static final Pattern PAT_LAN_PORT = Pattern.compile("(?:Local game hosted on port|Started serving on)\\s+(\\d+)");
    private static final Pattern PAT_SERVER_CONN = Pattern.compile("Connecting to\\s+([^,\\s]+),\\s*(\\d+)");
    private static final Pattern PAT_WORLD = Pattern.compile("Saving chunks for level 'ServerLevel\\[(.+?)\\]'");
    private static final Pattern PAT_LEAVE = Pattern.compile("Stopping server|Stopping singleplayer server|Leaving world|Lost connection|Disconnected|Connection closed");

    private final MoonClientContext ctx;

    public volatile boolean cloudReachable = false;
    public volatile String lastCloudError = "";
    public volatile String currentStatus = "online";
    public volatile String currentActivity = "In Main Menu";
    public volatile String detectedWorld = "";
    public volatile String currentServerAddr = "";
    public volatile int detectedLanPort = 0;
    public volatile boolean tunnelActive = false;
    public volatile String tunnelPublicAddr = "";
    public volatile boolean friendsOnlyHost = false;

    private long logLastOffset = 0L;
    private volatile List<Map<String, Object>> cachedFriends = new ArrayList<>();
    private volatile List<Map<String, Object>> cachedIncomingRequests = new ArrayList<>();
    private volatile List<Map<String, Object>> cachedOutgoingRequests = new ArrayList<>();
    private volatile Map<String, Object> cachedParty = null;
    private volatile List<Map<String, Object>> cachedPartyInvites = new ArrayList<>();
    private volatile List<Map<String, Object>> cachedMessages = new ArrayList<>();

    public MoonCloudClient(MoonClientContext ctx) {
        this.ctx = ctx;
        loadLocalFriendsIntoCache();
        File logFile = new File(new File(ctx.getGameDir(), "logs"), "latest.log");
        if (logFile.exists()) {
            logLastOffset = logFile.length();
        }
    }

    public List<Map<String, Object>> getCachedFriends() {
        return new ArrayList<>(cachedFriends);
    }

    public List<Map<String, Object>> getCachedIncomingRequests() {
        return new ArrayList<>(cachedIncomingRequests);
    }

    public List<Map<String, Object>> getCachedOutgoingRequests() {
        return new ArrayList<>(cachedOutgoingRequests);
    }

    public Map<String, Object> getCachedParty() {
        return cachedParty;
    }

    public List<Map<String, Object>> getCachedPartyInvites() {
        return new ArrayList<>(cachedPartyInvites);
    }

    public List<Map<String, Object>> getCachedMessages() {
        return new ArrayList<>(cachedMessages);
    }

    public void pollGameActivity() {
        File logFile = new File(new File(ctx.getGameDir(), "logs"), "latest.log");
        if (!logFile.exists()) return;
        try {
            long len = logFile.length();
            if (len < logLastOffset) {
                logLastOffset = 0L;
            }
            if (len > logLastOffset) {
                try (java.io.RandomAccessFile raf = new java.io.RandomAccessFile(logFile, "r")) {
                    raf.seek(logLastOffset);
                    byte[] bytes = new byte[(int) Math.min(len - logLastOffset, 262144)];
                    int read = raf.read(bytes);
                    logLastOffset = raf.getFilePointer();
                    if (read > 0) {
                        String chunk = new String(bytes, 0, read, StandardCharsets.UTF_8);
                        for (String line : chunk.split("\\r?\\n")) {
                            inspectLogLine(line);
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
    }

    private void inspectLogLine(String line) {
        Matcher mLan = PAT_LAN_PORT.matcher(line);
        if (mLan.find()) {
            try {
                detectedLanPort = Integer.parseInt(mLan.group(1));
                currentStatus = "hosting";
                if (detectedWorld.isEmpty()) detectedWorld = "LAN World";
                currentActivity = "LAN Open (Port " + detectedLanPort + ")";
            } catch (Exception ignored) {}
        }

        Matcher mSrv = PAT_SERVER_CONN.matcher(line);
        if (mSrv.find()) {
            String host = mSrv.group(1);
            String port = mSrv.group(2);
            currentServerAddr = "25565".equals(port) ? host : (host + ":" + port);
            currentStatus = "playing";
            detectedWorld = "";
            detectedLanPort = 0;
            currentActivity = "Multiplayer: " + currentServerAddr;
        }

        Matcher mWorld = PAT_WORLD.matcher(line);
        if (mWorld.find()) {
            detectedWorld = mWorld.group(1);
            if (!tunnelActive && detectedLanPort <= 0) {
                currentStatus = "playing";
                currentActivity = "Singleplayer: " + detectedWorld;
            }
        }

        if (PAT_LEAVE.matcher(line).find()) {
            detectedWorld = "";
            detectedLanPort = 0;
            currentServerAddr = "";
            if (!tunnelActive) {
                currentStatus = "online";
                currentActivity = "In Main Menu";
            }
        }
    }

    public boolean upsertPlayerAndPresence(boolean offline) {
        if (!ctx.hasSupabaseConfig()) {
            cloudReachable = false;
            return false;
        }
        try {
            String nowIso = isoNow();
            Map<String, Object> playerRow = new LinkedHashMap<>();
            playerRow.put("player_id", ctx.moonId);
            playerRow.put("username", ctx.username);
            String prefix = ctx.username.replaceAll("[^A-Za-z0-9]", "");
            if (prefix.length() > 3) prefix = prefix.substring(0, 3);
            if (prefix.isEmpty()) prefix = "PLR";
            playerRow.put("tag", prefix.toUpperCase() + "-" + ctx.moonId.replace("MOON-", ""));
            if (ctx.skinUrl != null && !ctx.skinUrl.isEmpty()) {
                playerRow.put("skin_url", ctx.skinUrl);
            }
            playerRow.put("last_seen", nowIso);

            String addr = tunnelActive && !tunnelPublicAddr.isEmpty() ? tunnelPublicAddr : currentServerAddr;
            String st = offline ? "offline" : (tunnelActive ? "hosting" : currentStatus);

            Map<String, Object> presRow = new LinkedHashMap<>();
            presRow.put("username", ctx.username);
            presRow.put("player_id", ctx.moonId);
            presRow.put("status", st);
            presRow.put("version_name", ctx.versionName);
            presRow.put("mc_version", ctx.mcVersion);
            presRow.put("loader", ctx.loader);
            presRow.put("mod_count", MoonSyncMod.getLocalManifest().size());
            presRow.put("server_addr", addr != null ? addr : "");
            presRow.put("tunnel_active", tunnelActive);
            presRow.put("updated_at", nowIso);

            if (ctx.hasCloudApiUrl()) {
                String pResp = requestCloudApi("/api/players/upsert", "POST", SimpleJson.stringify(playerRow));
                String prResp = requestCloudApi("/api/presence/upsert", "POST", SimpleJson.stringify(presRow));
                cloudReachable = (pResp != null && prResp != null);
                return cloudReachable;
            }

            String pResp = requestSupabase("players", "POST", SimpleJson.stringify(playerRow),
                "resolution=merge-duplicates,return=minimal");
            if (pResp == null) {
                cloudReachable = false;
                return false;
            }

            // Clear stale presence rows for this Moon ID under an older username
            requestSupabase(
                "presence?player_id=eq." + urlEnc(ctx.moonId) + "&username=neq." + urlEnc(ctx.username),
                "DELETE", null, null
            );

            String prResp = requestSupabase("presence", "POST", SimpleJson.stringify(presRow),
                "resolution=merge-duplicates,return=minimal");
            cloudReachable = (prResp != null);
            return cloudReachable;
        } catch (Exception e) {
            lastCloudError = e.getMessage() != null ? e.getMessage() : "Sync error";
            cloudReachable = false;
            return false;
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> lookupPlayer(String idOrName) {
        String raw = idOrName != null ? idOrName.trim() : "";
        if (raw.isEmpty()) return null;

        String normId = normalizeMoonId(raw);
        if (ctx.hasCloudApiUrl()) {
            try {
                String resJson = requestCloudApi("/api/players/lookup?q=" + urlEnc(normId != null ? normId : raw), "GET", null);
                Map<String, Object> obj = SimpleJson.parseObject(resJson);
                if (SimpleJson.asBoolean(obj, "found", false) && obj.get("player") instanceof Map) {
                    return (Map<String, Object>) obj.get("player");
                }
            } catch (Exception ignored) {}
        } else if (ctx.hasSupabaseConfig()) {
            try {
                if (normId != null) {
                    String prJson = requestSupabase("presence?player_id=eq." + urlEnc(normId), "GET", null, null);
                    List<Object> prList = SimpleJson.parseArray(prJson);
                    if (!prList.isEmpty() && prList.get(0) instanceof Map) {
                        return (Map<String, Object>) prList.get(0);
                    }
                    String plJson = requestSupabase("players?player_id=eq." + urlEnc(normId), "GET", null, null);
                    List<Object> plList = SimpleJson.parseArray(plJson);
                    if (!plList.isEmpty() && plList.get(0) instanceof Map) {
                        Map<String, Object> pl = new LinkedHashMap<>((Map<String, Object>) plList.get(0));
                        pl.put("status", "offline");
                        return pl;
                    }
                }
                String uPrJson = requestSupabase("presence?username=ilike." + urlEnc(raw), "GET", null, null);
                List<Object> uPrList = SimpleJson.parseArray(uPrJson);
                if (!uPrList.isEmpty() && uPrList.get(0) instanceof Map) {
                    return (Map<String, Object>) uPrList.get(0);
                }
                String uPlJson = requestSupabase("players?username=ilike." + urlEnc(raw), "GET", null, null);
                List<Object> uPlList = SimpleJson.parseArray(uPlJson);
                if (!uPlList.isEmpty() && uPlList.get(0) instanceof Map) {
                    Map<String, Object> pl = new LinkedHashMap<>((Map<String, Object>) uPlList.get(0));
                    pl.put("status", "offline");
                    return pl;
                }
            } catch (Exception ignored) {}
        }

        if (normId != null) {
            Map<String, Object> fallback = new LinkedHashMap<>();
            fallback.put("player_id", normId);
            fallback.put("username", normId);
            fallback.put("status", "offline");
            return fallback;
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> addFriend(String idOrName) {
        Map<String, Object> result = new LinkedHashMap<>();
        String clean = idOrName != null ? idOrName.trim() : "";
        if (clean.isEmpty()) {
            result.put("success", false);
            result.put("error", "Enter a Moon ID (MOON-XXXX) or username");
            return result;
        }

        Map<String, Object> resolved = lookupPlayer(clean);
        String targetId = resolved != null ? SimpleJson.asString(resolved, "player_id", "") : "";
        String targetUser = resolved != null ? SimpleJson.asString(resolved, "username", clean) : clean;
        if (targetId.isEmpty()) {
            String norm = normalizeMoonId(clean);
            targetId = norm != null ? norm : MoonClientContext.computeDeterministicMoonId(clean);
        }
        if (targetId.equalsIgnoreCase(ctx.moonId) || targetUser.equalsIgnoreCase(ctx.username)) {
            result.put("success", false);
            result.put("error", "Cannot add yourself as a friend");
            return result;
        }

        String relStatus = "pending";
        if (ctx.hasCloudApiUrl()) {
            Map<String, Object> reqBody = new LinkedHashMap<>();
            reqBody.put("user_a", ctx.moonId);
            reqBody.put("user_b", targetId);
            String postRes = requestCloudApi("/api/friends/request", "POST", SimpleJson.stringify(reqBody));
            if (postRes != null) {
                Map<String, Object> parsed = SimpleJson.parseObject(postRes);
                relStatus = SimpleJson.asString(parsed, "status", "pending");
            }
        } else if (ctx.hasSupabaseConfig()) {
            // Check if the other player already sent us a pending friend request
            String existingRev = requestSupabase(
                "friendships?user_a=eq." + urlEnc(targetId) + "&user_b=eq." + urlEnc(ctx.moonId),
                "GET", null, null
            );
            List<Object> revList = SimpleJson.parseArray(existingRev);
            if (!revList.isEmpty()) {
                Map<String, Object> patch = new LinkedHashMap<>();
                patch.put("status", "accepted");
                requestSupabase(
                    "friendships?user_a=eq." + urlEnc(targetId) + "&user_b=eq." + urlEnc(ctx.moonId),
                    "PATCH", SimpleJson.stringify(patch), "return=minimal"
                );
                relStatus = "accepted";
            } else {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("user_a", ctx.moonId);
                row.put("user_b", targetId);
                row.put("status", "pending");
                String postRes = requestSupabase(
                    "friendships?on_conflict=user_a,user_b", "POST", SimpleJson.stringify(row),
                    "resolution=merge-duplicates,return=minimal"
                );
                if (postRes != null) {
                    relStatus = "pending";
                }
            }
        } else {
            relStatus = "local";
        }

        saveLocalFriendContact(targetId, targetUser,
            resolved != null ? SimpleJson.asString(resolved, "status", "offline") : "offline",
            resolved != null ? SimpleJson.asString(resolved, "server_addr", "") : "",
            resolved != null ? SimpleJson.asString(resolved, "version_name", "") : "");

        syncFriendsAndPresence();
        result.put("success", true);
        result.put("player_id", targetId);
        result.put("username", targetUser);
        result.put("friendship_status", relStatus);
        return result;
    }

    public boolean acceptFriendRequest(String targetId) {
        String cleanId = normalizeMoonId(targetId);
        if (cleanId == null) cleanId = targetId != null ? targetId.trim().toUpperCase() : "";
        if (cleanId.isEmpty()) return false;

        boolean ok = true;
        if (ctx.hasCloudApiUrl()) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("user_a", cleanId);
            body.put("user_b", ctx.moonId);
            ok = requestCloudApi("/api/friends/accept", "POST", SimpleJson.stringify(body)) != null;
        } else if (ctx.hasSupabaseConfig()) {
            Map<String, Object> patch = new LinkedHashMap<>();
            patch.put("status", "accepted");
            String r1 = requestSupabase(
                "friendships?user_a=eq." + urlEnc(cleanId) + "&user_b=eq." + urlEnc(ctx.moonId),
                "PATCH", SimpleJson.stringify(patch), "return=minimal"
            );
            ok = (r1 != null);
        }
        Map<String, Object> resolved = lookupPlayer(cleanId);
        String uname = resolved != null ? SimpleJson.asString(resolved, "username", cleanId) : cleanId;
        saveLocalFriendContact(cleanId, uname,
            resolved != null ? SimpleJson.asString(resolved, "status", "offline") : "offline",
            resolved != null ? SimpleJson.asString(resolved, "server_addr", "") : "",
            resolved != null ? SimpleJson.asString(resolved, "version_name", "") : "");
        syncFriendsAndPresence();
        return ok;
    }

    public boolean removeOrDeclineFriend(String targetIdOrUser) {
        String raw = targetIdOrUser != null ? targetIdOrUser.trim() : "";
        if (raw.isEmpty()) return false;
        String normId = normalizeMoonId(raw);

        if (ctx.hasCloudApiUrl() && normId != null) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("user_a", ctx.moonId);
            body.put("user_b", normId);
            requestCloudApi("/api/friends/remove", "POST", SimpleJson.stringify(body));
        } else if (ctx.hasSupabaseConfig() && normId != null) {
            requestSupabase(
                "friendships?or=(and(user_a.eq." + urlEnc(ctx.moonId) + ",user_b.eq." + urlEnc(normId) + "),and(user_a.eq." + urlEnc(normId) + ",user_b.eq." + urlEnc(ctx.moonId) + "))",
                "DELETE", null, null
            );
        }

        // Remove from local friends.json
        File ff = ctx.getFriendsFile();
        if (ff.exists()) {
            try {
                Map<String, Object> data = SimpleJson.parseObject(MoonClientContext.readText(ff));
                Object rawArr = data.get("friends");
                if (rawArr instanceof List) {
                    List<Object> kept = new ArrayList<>();
                    for (Object o : (List<?>) rawArr) {
                        if (o instanceof Map) {
                            @SuppressWarnings("unchecked")
                            Map<String, Object> m = (Map<String, Object>) o;
                            String pid = SimpleJson.asString(m, "player_id", "");
                            String un = SimpleJson.asString(m, "username", "");
                            if (raw.equalsIgnoreCase(pid) || raw.equalsIgnoreCase(un)) continue;
                        } else if (o != null && raw.equalsIgnoreCase(String.valueOf(o))) {
                            continue;
                        }
                        kept.add(o);
                    }
                    data.put("friends", kept);
                    MoonClientContext.writeJson(ff, data);
                }
            } catch (Exception ignored) {}
        }
        syncFriendsAndPresence();
        return true;
    }

    @SuppressWarnings("unchecked")
    public synchronized void syncFriendsAndPresence() {
        loadLocalFriendsIntoCache();
        Map<String, Map<String, Object>> byKey = new LinkedHashMap<>();
        for (Map<String, Object> f : cachedFriends) {
            String pid = SimpleJson.asString(f, "player_id", "").toUpperCase();
            String un = SimpleJson.asString(f, "username", "");
            String k = !pid.isEmpty() ? pid : un.toLowerCase();
            if (!k.isEmpty()) byKey.put(k, new LinkedHashMap<>(f));
        }

        List<Map<String, Object>> incoming = new ArrayList<>();
        List<Map<String, Object>> outgoing = new ArrayList<>();

        if (ctx.hasCloudApiUrl()) {
            try {
                String listJson = requestCloudApi("/api/friends/list?moon_id=" + urlEnc(ctx.moonId), "GET", null);
                if (listJson != null) {
                    cloudReachable = true;
                    Map<String, Object> resp = SimpleJson.parseObject(listJson);
                    if (resp.get("friends") instanceof List) {
                        for (Object fo : (List<Object>) resp.get("friends")) {
                            if (fo instanceof Map) {
                                Map<String, Object> fm = new LinkedHashMap<>((Map<String, Object>) fo);
                                String pid = SimpleJson.asString(fm, "player_id", "").toUpperCase();
                                if (!pid.isEmpty()) byKey.put(pid, fm);
                            }
                        }
                    }
                    if (resp.get("incoming_requests") instanceof List) {
                        for (Object ro : (List<Object>) resp.get("incoming_requests")) {
                            if (ro instanceof Map) incoming.add(new LinkedHashMap<>((Map<String, Object>) ro));
                        }
                    }
                    if (resp.get("outgoing_requests") instanceof List) {
                        for (Object ro : (List<Object>) resp.get("outgoing_requests")) {
                            if (ro instanceof Map) outgoing.add(new LinkedHashMap<>((Map<String, Object>) ro));
                        }
                    }
                }
            } catch (Exception e) {
                lastCloudError = e.getMessage() != null ? e.getMessage() : "Cloud sync error";
            }
        } else if (ctx.hasSupabaseConfig()) {
            try {
                String fsJson = requestSupabase(
                    "friendships?or=(user_a.eq." + urlEnc(ctx.moonId) + ",user_b.eq." + urlEnc(ctx.moonId) + ")",
                    "GET", null, null
                );
                if (fsJson != null) {
                    cloudReachable = true;
                    List<Object> rows = SimpleJson.parseArray(fsJson);
                    for (Object rowObj : rows) {
                        if (!(rowObj instanceof Map)) continue;
                        Map<String, Object> row = (Map<String, Object>) rowObj;
                        String ua = SimpleJson.asString(row, "user_a", "").toUpperCase();
                        String ub = SimpleJson.asString(row, "user_b", "").toUpperCase();
                        String st = SimpleJson.asString(row, "status", "accepted").toLowerCase();
                        String peerId = ua.equals(ctx.moonId) ? ub : ua;
                        if (peerId.isEmpty() || peerId.equals(ctx.moonId)) continue;

                        if ("pending".equals(st)) {
                            Map<String, Object> reqItem = new LinkedHashMap<>();
                            reqItem.put("player_id", peerId);
                            reqItem.put("username", peerId);
                            reqItem.put("status", "pending");
                            if (ub.equals(ctx.moonId)) {
                                incoming.add(reqItem);
                            } else {
                                outgoing.add(reqItem);
                            }
                        } else {
                            if (!byKey.containsKey(peerId)) {
                                Map<String, Object> newF = new LinkedHashMap<>();
                                newF.put("player_id", peerId);
                                newF.put("username", peerId);
                                newF.put("status", "offline");
                                byKey.put(peerId, newF);
                            }
                        }
                    }
                }

                // Collect IDs and usernames to enrich with live presence + players
                List<String> ids = new ArrayList<>();
                for (Map<String, Object> f : byKey.values()) {
                    String pid = SimpleJson.asString(f, "player_id", "");
                    if (!pid.isEmpty()) ids.add(pid);
                }
                for (Map<String, Object> r : incoming) ids.add(SimpleJson.asString(r, "player_id", ""));
                for (Map<String, Object> r : outgoing) ids.add(SimpleJson.asString(r, "player_id", ""));

                if (!ids.isEmpty()) {
                    StringBuilder inList = new StringBuilder();
                    for (int i = 0; i < ids.size(); i++) {
                        if (i > 0) inList.append(',');
                        inList.append('"').append(ids.get(i)).append('"');
                    }
                    String qIn = urlEnc(inList.toString());
                    String plResp = requestSupabase("players?player_id=in.(" + qIn + ")", "GET", null, null);
                    Map<String, Map<String, Object>> playerMeta = new LinkedHashMap<>();
                    for (Object o : SimpleJson.parseArray(plResp)) {
                        if (o instanceof Map) {
                            Map<String, Object> pm = (Map<String, Object>) o;
                            playerMeta.put(SimpleJson.asString(pm, "player_id", "").toUpperCase(), pm);
                        }
                    }

                    String prResp = requestSupabase("presence?player_id=in.(" + qIn + ")", "GET", null, null);
                    Map<String, Map<String, Object>> presMeta = new LinkedHashMap<>();
                    for (Object o : SimpleJson.parseArray(prResp)) {
                        if (o instanceof Map) {
                            Map<String, Object> pm = (Map<String, Object>) o;
                            presMeta.put(SimpleJson.asString(pm, "player_id", "").toUpperCase(), pm);
                        }
                    }

                    for (Map<String, Object> f : byKey.values()) {
                        applyCloudMeta(f, playerMeta, presMeta);
                    }
                    for (Map<String, Object> r : incoming) {
                        applyCloudMeta(r, playerMeta, presMeta);
                    }
                    for (Map<String, Object> r : outgoing) {
                        applyCloudMeta(r, playerMeta, presMeta);
                    }
                }
            } catch (Exception e) {
                lastCloudError = e.getMessage() != null ? e.getMessage() : "Sync error";
            }
        }

        cachedFriends = new ArrayList<>(byKey.values());
        cachedIncomingRequests = incoming;
        cachedOutgoingRequests = outgoing;

        if (ctx.hasCloudApiUrl()) {
            syncPartyAndChat();
        }
    }

    @SuppressWarnings("unchecked")
    public void syncPartyAndChat() {
        if (!ctx.hasCloudApiUrl()) return;
        try {
            String pJson = requestCloudApi("/api/party/state?moon_id=" + urlEnc(ctx.moonId), "GET", null);
            if (pJson != null) {
                Map<String, Object> parsed = SimpleJson.parseObject(pJson);
                Object pObj = parsed.get("party");
                cachedParty = (pObj instanceof Map) ? new LinkedHashMap<>((Map<String, Object>) pObj) : null;
                List<Map<String, Object>> invs = new ArrayList<>();
                if (parsed.get("pending_invites") instanceof List) {
                    for (Object io : (List<Object>) parsed.get("pending_invites")) {
                        if (io instanceof Map) invs.add(new LinkedHashMap<>((Map<String, Object>) io));
                    }
                }
                cachedPartyInvites = invs;
            }

            String cJson = requestCloudApi("/api/chat/poll?moon_id=" + urlEnc(ctx.moonId) + "&limit=40", "GET", null);
            if (cJson != null) {
                Map<String, Object> parsed = SimpleJson.parseObject(cJson);
                List<Map<String, Object>> msgs = new ArrayList<>();
                if (parsed.get("messages") instanceof List) {
                    for (Object mo : (List<Object>) parsed.get("messages")) {
                        if (mo instanceof Map) msgs.add(new LinkedHashMap<>((Map<String, Object>) mo));
                    }
                }
                cachedMessages = msgs;
            }
        } catch (Exception ignored) {}
    }

    public Map<String, Object> sendChatMessage(String recipientId, String partyId, String text, String kind) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (!ctx.hasCloudApiUrl()) {
            out.put("success", false);
            out.put("error", "Cloudflare endpoint not configured");
            return out;
        }
        String cleanBody = text != null ? text.trim() : "";
        if (cleanBody.isEmpty()) {
            out.put("success", false);
            out.put("error", "Message cannot be empty");
            return out;
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("sender_id", ctx.moonId);
        payload.put("sender_name", ctx.username);
        if (recipientId != null && !recipientId.trim().isEmpty()) {
            payload.put("recipient_id", recipientId.trim().toUpperCase());
        }
        if (partyId != null && !partyId.trim().isEmpty()) {
            payload.put("party_id", partyId.trim().toUpperCase());
        }
        payload.put("kind", kind != null && !kind.isEmpty() ? kind : "text");
        payload.put("body", cleanBody);
        String res = requestCloudApi("/api/chat/send", "POST", SimpleJson.stringify(payload));
        if (res != null) {
            syncPartyAndChat();
            return SimpleJson.parseObject(res);
        }
        out.put("success", false);
        out.put("error", lastCloudError);
        return out;
    }

    public List<Map<String, Object>> pollChatMessages(String peerId, String partyId) {
        if (!ctx.hasCloudApiUrl()) return getCachedMessages();
        StringBuilder q = new StringBuilder("/api/chat/poll?moon_id=").append(urlEnc(ctx.moonId)).append("&limit=40");
        if (peerId != null && !peerId.trim().isEmpty()) q.append("&peer_id=").append(urlEnc(peerId.trim().toUpperCase()));
        if (partyId != null && !partyId.trim().isEmpty()) q.append("&party_id=").append(urlEnc(partyId.trim().toUpperCase()));
        String raw = requestCloudApi(q.toString(), "GET", null);
        if (raw == null) return getCachedMessages();
        Map<String, Object> parsed = SimpleJson.parseObject(raw);
        List<Map<String, Object>> msgs = new ArrayList<>();
        if (parsed.get("messages") instanceof List) {
            for (Object mo : (List<?>) parsed.get("messages")) {
                if (mo instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> mm = new LinkedHashMap<>((Map<String, Object>) mo);
                    msgs.add(mm);
                }
            }
        }
        cachedMessages = msgs;
        return msgs;
    }

    public Map<String, Object> createParty() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("moon_id", ctx.moonId);
        payload.put("username", ctx.username);
        String res = requestCloudApi("/api/party/create", "POST", SimpleJson.stringify(payload));
        if (res != null) {
            syncPartyAndChat();
            return SimpleJson.parseObject(res);
        }
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("success", false);
        err.put("error", lastCloudError);
        return err;
    }

    public Map<String, Object> inviteToParty(List<String> targets) {
        List<String> finalTargets = new ArrayList<>();
        if (targets != null && !targets.isEmpty()) {
            finalTargets.addAll(targets);
        } else {
            for (Map<String, Object> f : cachedFriends) {
                String pid = SimpleJson.asString(f, "player_id", "");
                if (!pid.isEmpty()) finalTargets.add(pid);
            }
        }
        if (finalTargets.isEmpty()) {
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("success", false);
            err.put("error", "No friends available to invite");
            return err;
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("leader_id", ctx.moonId);
        payload.put("username", ctx.username);
        if (cachedParty != null) {
            String pid = SimpleJson.asString(cachedParty, "party_id", "");
            if (!pid.isEmpty()) payload.put("party_id", pid);
        }
        payload.put("targets", finalTargets);
        String res = requestCloudApi("/api/party/invite", "POST", SimpleJson.stringify(payload));
        if (res != null) {
            syncPartyAndChat();
            return SimpleJson.parseObject(res);
        }
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("success", false);
        err.put("error", lastCloudError);
        return err;
    }

    public Map<String, Object> joinParty(String partyId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("party_id", partyId);
        payload.put("moon_id", ctx.moonId);
        payload.put("username", ctx.username);
        String res = requestCloudApi("/api/party/join", "POST", SimpleJson.stringify(payload));
        if (res != null) {
            syncPartyAndChat();
            return SimpleJson.parseObject(res);
        }
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("success", false);
        err.put("error", lastCloudError);
        return err;
    }

    public boolean leaveOrDeclineParty(String partyId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("moon_id", ctx.moonId);
        if (partyId != null && !partyId.trim().isEmpty()) {
            payload.put("party_id", partyId.trim().toUpperCase());
        }
        String res = requestCloudApi("/api/party/leave", "POST", SimpleJson.stringify(payload));
        syncPartyAndChat();
        return res != null;
    }

    public boolean broadcastPartyTarget(String serverAddr, String worldName) {
        if (cachedParty == null || !SimpleJson.asBoolean(cachedParty, "is_leader", false)) return false;
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("moon_id", ctx.moonId);
        payload.put("target_server", serverAddr != null ? serverAddr : "");
        payload.put("target_world", worldName != null ? worldName : ctx.versionName);
        String res = requestCloudApi("/api/party/target", "POST", SimpleJson.stringify(payload));
        if (res != null) {
            syncPartyAndChat();
            return true;
        }
        return false;
    }

    public Map<String, Object> syncFriendsWhitelist(boolean enableFriendsOnly) {
        friendsOnlyHost = enableFriendsOnly;
        Map<String, Object> out = new LinkedHashMap<>();
        List<Map<String, Object>> whitelist = new ArrayList<>();
        List<String> names = new ArrayList<>();

        if (ctx.username != null && !ctx.username.isEmpty()) {
            names.add(ctx.username);
        }
        for (Map<String, Object> f : cachedFriends) {
            String un = SimpleJson.asString(f, "username", "");
            if (!un.isEmpty() && !un.toUpperCase().startsWith("MOON-") && !names.contains(un)) {
                names.add(un);
            }
        }
        for (String name : names) {
            Map<String, Object> entry = new LinkedHashMap<>();
            UUID offUuid = UUID.nameUUIDFromBytes(("OfflinePlayer:" + name).getBytes(StandardCharsets.UTF_8));
            entry.put("uuid", offUuid.toString());
            entry.put("name", name);
            whitelist.add(entry);
        }
        try {
            File wlFile = new File(ctx.getGameDir(), "whitelist.json");
            MoonClientContext.writeJson(wlFile, whitelist);
            out.put("success", true);
            out.put("enabled", friendsOnlyHost);
            out.put("count", whitelist.size());
            out.put("path", wlFile.getAbsolutePath());
        } catch (Exception e) {
            out.put("success", false);
            out.put("error", e.getMessage());
        }
        return out;
    }

    public Map<String, Object> shareScreenshot(File shotFile) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (!ctx.hasCloudApiUrl()) {
            out.put("success", false);
            out.put("error", "Cloudflare API endpoint unavailable");
            return out;
        }
        if (shotFile == null || !shotFile.exists() || !shotFile.isFile()) {
            out.put("success", false);
            out.put("error", "Screenshot file not found");
            return out;
        }
        try {
            BufferedImage src = ImageIO.read(shotFile);
            if (src == null) {
                out.put("success", false);
                out.put("error", "Unsupported image file");
                return out;
            }
            int maxW = 1280;
            BufferedImage scaled = src;
            if (src.getWidth() > maxW) {
                int newH = Math.max(1, (int) Math.round((double) src.getHeight() * maxW / src.getWidth()));
                BufferedImage tmp = new BufferedImage(maxW, newH, BufferedImage.TYPE_INT_RGB);
                Graphics2D g = tmp.createGraphics();
                g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                g.drawImage(src, 0, 0, maxW, newH, null);
                g.dispose();
                scaled = tmp;
            }
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            String mime = "image/jpeg";
            if (!ImageIO.write(scaled, "jpg", baos)) {
                baos.reset();
                ImageIO.write(scaled, "png", baos);
                mime = "image/png";
            }
            byte[] bytes = baos.toByteArray();
            if (bytes.length > 420000 && "image/jpeg".equals(mime)) {
                int w2 = 960;
                int h2 = Math.max(1, (int) Math.round((double) scaled.getHeight() * w2 / scaled.getWidth()));
                BufferedImage small = new BufferedImage(w2, h2, BufferedImage.TYPE_INT_RGB);
                Graphics2D g2 = small.createGraphics();
                g2.drawImage(scaled, 0, 0, w2, h2, null);
                g2.dispose();
                baos.reset();
                ImageIO.write(small, "jpg", baos);
                bytes = baos.toByteArray();
            }
            String b64 = Base64.getEncoder().encodeToString(bytes);
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("owner_id", ctx.moonId);
            payload.put("owner_name", ctx.username);
            payload.put("version_name", ctx.versionName);
            payload.put("mime_type", mime);
            payload.put("image_b64", b64);
            String raw = requestCloudApi("/api/screenshots/upload", "POST", SimpleJson.stringify(payload));
            if (raw != null) {
                return SimpleJson.parseObject(raw);
            }
            out.put("success", false);
            out.put("error", lastCloudError);
        } catch (Exception e) {
            out.put("success", false);
            out.put("error", e.getMessage());
        }
        return out;
    }

    private void applyCloudMeta(Map<String, Object> target, Map<String, Map<String, Object>> playerMeta, Map<String, Map<String, Object>> presMeta) {
        String pid = SimpleJson.asString(target, "player_id", "").toUpperCase();
        Map<String, Object> pl = playerMeta.get(pid);
        if (pl != null) {
            String un = SimpleJson.asString(pl, "username", "");
            if (!un.isEmpty()) target.put("username", un);
            String sk = SimpleJson.asString(pl, "skin_url", "");
            if (!sk.isEmpty()) target.put("skin_url", sk);
        }
        Map<String, Object> pr = presMeta.get(pid);
        if (pr != null) {
            String un = SimpleJson.asString(pr, "username", "");
            if (!un.isEmpty()) target.put("username", un);
            target.put("status", SimpleJson.asString(pr, "status", "offline"));
            target.put("version_name", SimpleJson.asString(pr, "version_name", ""));
            target.put("mc_version", SimpleJson.asString(pr, "mc_version", ""));
            target.put("loader", SimpleJson.asString(pr, "loader", ""));
            target.put("mod_count", SimpleJson.asInt(pr, "mod_count", 0));
            target.put("server_addr", SimpleJson.asString(pr, "server_addr", ""));
            target.put("tunnel_active", SimpleJson.asBoolean(pr, "tunnel_active", false));
        }
    }

    @SuppressWarnings("unchecked")
    private void loadLocalFriendsIntoCache() {
        File ff = ctx.getFriendsFile();
        List<Map<String, Object>> loaded = new ArrayList<>();
        if (ff.exists()) {
            try {
                Map<String, Object> data = SimpleJson.parseObject(MoonClientContext.readText(ff));
                Object rawArr = data.get("friends");
                if (rawArr instanceof List) {
                    for (Object o : (List<?>) rawArr) {
                        if (o instanceof Map) {
                            loaded.add(new LinkedHashMap<>((Map<String, Object>) o));
                        } else if (o != null) {
                            String un = String.valueOf(o).trim();
                            if (!un.isEmpty()) {
                                Map<String, Object> m = new LinkedHashMap<>();
                                m.put("player_id", MoonClientContext.computeDeterministicMoonId(un));
                                m.put("username", un);
                                m.put("status", "offline");
                                loaded.add(m);
                            }
                        }
                    }
                }
            } catch (Exception ignored) {}
        }
        cachedFriends = loaded;
    }

    @SuppressWarnings("unchecked")
    private void saveLocalFriendContact(String pid, String uname, String status, String serverAddr, String versionName) {
        File ff = ctx.getFriendsFile();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("friends", new ArrayList<>());
        data.put("servers", new ArrayList<>());
        if (ff.exists()) {
            try {
                Map<String, Object> existing = SimpleJson.parseObject(MoonClientContext.readText(ff));
                if (!existing.isEmpty()) data = existing;
            } catch (Exception ignored) {}
        }
        Object rawArr = data.get("friends");
        List<Object> list = (rawArr instanceof List) ? (List<Object>) rawArr : new ArrayList<>();
        data.put("friends", list);

        for (Object itemObj : list) {
            if (itemObj instanceof Map) {
                Map<String, Object> item = (Map<String, Object>) itemObj;
                if (pid.equalsIgnoreCase(SimpleJson.asString(item, "player_id", ""))
                    || uname.equalsIgnoreCase(SimpleJson.asString(item, "username", ""))) {
                    item.put("player_id", pid);
                    item.put("username", uname);
                    item.put("status", status);
                    if (serverAddr != null && !serverAddr.isEmpty()) item.put("server_addr", serverAddr);
                    if (versionName != null && !versionName.isEmpty()) item.put("version_name", versionName);
                    try { MoonClientContext.writeJson(ff, data); } catch (Exception ignored) {}
                    return;
                }
            }
        }

        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("player_id", pid);
        entry.put("username", uname);
        entry.put("status", status);
        entry.put("server_addr", serverAddr != null ? serverAddr : "");
        entry.put("version_name", versionName != null ? versionName : "");
        list.add(entry);
        try { MoonClientContext.writeJson(ff, data); } catch (Exception ignored) {}
    }

    public String requestCloudApi(String endpointPath, String method, String jsonBody) {
        if (!ctx.hasCloudApiUrl()) return null;
        HttpURLConnection conn = null;
        try {
            URL url = new URL(ctx.cloudApiUrl + endpointPath);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(4500);
            conn.setReadTimeout(6000);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("User-Agent", "MoonSyncMod/2.0");
            if (jsonBody != null) {
                conn.setDoOutput(true);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = conn.getResponseCode();
            if (code >= 200 && code < 300) {
                try (InputStream is = conn.getInputStream()) {
                    return readAll(is);
                }
            }
            lastCloudError = "HTTP " + code;
            return null;
        } catch (Exception e) {
            lastCloudError = e.getMessage() != null ? e.getMessage() : "Connection failed";
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    public String requestSupabase(String endpoint, String method, String jsonBody, String preferHeader) {
        if (!ctx.hasSupabaseConfig()) return null;
        HttpURLConnection conn = null;
        try {
            URL url = new URL(ctx.supabaseUrl + "/rest/v1/" + endpoint);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(4500);
            conn.setReadTimeout(6000);
            conn.setRequestProperty("apikey", ctx.supabaseKey);
            conn.setRequestProperty("Authorization", "Bearer " + ctx.supabaseKey);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("User-Agent", "MoonSyncMod/2.0");
            if (preferHeader != null && !preferHeader.isEmpty()) {
                conn.setRequestProperty("Prefer", preferHeader);
            }
            if ("PATCH".equalsIgnoreCase(method)) {
                conn.setRequestProperty("X-HTTP-Method-Override", "PATCH");
            }
            if (jsonBody != null) {
                conn.setDoOutput(true);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = conn.getResponseCode();
            if (code >= 200 && code < 300) {
                try (InputStream is = conn.getInputStream()) {
                    return readAll(is);
                }
            }
            lastCloudError = "HTTP " + code;
            return null;
        } catch (Exception e) {
            lastCloudError = e.getMessage() != null ? e.getMessage() : "Connection failed";
            return null;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    public static String normalizeMoonId(String raw) {
        if (raw == null) return null;
        String clean = raw.trim().toUpperCase();
        if (clean.startsWith("MOON-")) return clean;
        if (clean.matches("[A-Z0-9]{4,6}") && clean.matches(".*\\d.*")) {
            return "MOON-" + clean;
        }
        return null;
    }

    private static String urlEnc(String s) {
        try {
            return URLEncoder.encode(s, "UTF-8").replace("+", "%20");
        } catch (Exception e) {
            return s;
        }
    }

    private static String isoNow() {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'");
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
        return sdf.format(new Date());
    }

    private static String readAll(InputStream is) throws Exception {
        if (is == null) return "";
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = is.read(buf)) != -1) {
            baos.write(buf, 0, n);
        }
        return new String(baos.toByteArray(), StandardCharsets.UTF_8);
    }
}

