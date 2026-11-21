package dev.moonlauncher.sync;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URL;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;

/**
 * Embedded local Companion Web UI and REST API running inside Minecraft.
 * Provides Essential/Lunar-style Social Friends, Friend Requests, Multiplayer Host/Join,
 * Server Ping, Mod Sync/Inspector, Screenshots Gallery, and Coordinate Waypoints across
 * every loader and Minecraft version.
 */
public class MoonCompanionServer {

    private final MoonClientContext ctx;
    private final MoonCloudClient cloud;
    private HttpServer server;
    private int port = 0;

    public MoonCompanionServer(MoonClientContext ctx, MoonCloudClient cloud) {
        this.ctx = ctx;
        this.cloud = cloud;
    }

    public int start() {
        try {
            server = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0), 16);
            server.setExecutor(Executors.newFixedThreadPool(4, new ThreadFactory() {
                @Override
                public Thread newThread(Runnable r) {
                    Thread t = new Thread(r, "MoonCompanionHTTP");
                    t.setDaemon(true);
                    return t;
                }
            }));

            server.createContext("/", ex -> handleDashboard(ex));
            server.createContext("/api/state", ex -> handleState(ex));
            server.createContext("/api/friends/add", ex -> handleFriendAdd(ex));
            server.createContext("/api/friends/accept", ex -> handleFriendAccept(ex));
            server.createContext("/api/friends/remove", ex -> handleFriendRemove(ex));
            server.createContext("/api/friends/sync", ex -> handleFriendSync(ex));
            server.createContext("/api/chat/send", ex -> handleChatSend(ex));
            server.createContext("/api/chat/poll", ex -> handleChatPoll(ex));
            server.createContext("/api/party/create", ex -> handlePartyCreate(ex));
            server.createContext("/api/party/invite", ex -> handlePartyInvite(ex));
            server.createContext("/api/party/join", ex -> handlePartyJoin(ex));
            server.createContext("/api/party/leave", ex -> handlePartyLeave(ex));
            server.createContext("/api/party/target", ex -> handlePartyTarget(ex));
            server.createContext("/api/host/start", ex -> handleHostStart(ex));
            server.createContext("/api/host/stop", ex -> handleHostStop(ex));
            server.createContext("/api/host/whitelist", ex -> handleHostWhitelist(ex));
            server.createContext("/api/join", ex -> handleJoin(ex));
            server.createContext("/api/ping", ex -> handlePing(ex));
            server.createContext("/api/mods", ex -> handleMods(ex));
            server.createContext("/api/mods/toggle", ex -> handleModToggle(ex));
            server.createContext("/api/notes/add", ex -> handleNoteAdd(ex));
            server.createContext("/api/notes/delete", ex -> handleNoteDelete(ex));
            server.createContext("/api/screenshots/file", ex -> handleScreenshotFile(ex));
            server.createContext("/api/screenshots/share", ex -> handleScreenshotShare(ex));
            server.createContext("/api/qol/status", ex -> handleQolStatus(ex));
            server.createContext("/api/qol/action", ex -> handleQolAction(ex));
            server.createContext("/api/p2p/action", ex -> handleP2pAction(ex));

            server.start();
            port = server.getAddress().getPort();
            ctx.writeCompanionMeta(port);
            return port;
        } catch (Exception e) {
            System.err.println("[MoonSync] Companion server failed to start: " + e.getMessage());
            return 0;
        }
    }

    public int getPort() {
        return port;
    }

    public String getUrl() {
        return port > 0 ? ("http://127.0.0.1:" + port + "/") : "";
    }

    public void stop() {
        if (server != null) {
            try {
                server.stop(0);
            } catch (Exception ignored) {}
            server = null;
        }
        ctx.clearCompanionMeta();
    }

    private void handleState(HttpExchange ex) throws IOException {
        cloud.pollGameActivity();
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("moon_id", ctx.moonId);
        state.put("username", ctx.username);
        state.put("version_name", ctx.versionName);
        state.put("mc_version", ctx.mcVersion);
        state.put("loader", ctx.loader);
        state.put("cloud_configured", ctx.hasSupabaseConfig());
        state.put("cloud_reachable", cloud.cloudReachable);
        state.put("last_cloud_error", cloud.lastCloudError);
        state.put("bridge_connected", ctx.bridgeUrl != null && !ctx.bridgeUrl.isEmpty());
        state.put("activity", cloud.currentActivity);
        state.put("status", cloud.tunnelActive ? "hosting" : cloud.currentStatus);
        state.put("lan_port", cloud.detectedLanPort);
        state.put("local_ips", MultiplayerTools.getLocalNetworkIps());
        state.put("tunnel_active", cloud.tunnelActive);
        state.put("tunnel_addr", cloud.tunnelPublicAddr);
        state.put("friends_only_host", cloud.friendsOnlyHost);
        state.put("friends", cloud.getCachedFriends());
        state.put("incoming_requests", cloud.getCachedIncomingRequests());
        state.put("outgoing_requests", cloud.getCachedOutgoingRequests());
        state.put("party", cloud.getCachedParty());
        state.put("party_invites", cloud.getCachedPartyInvites());
        state.put("messages", cloud.getCachedMessages());
        state.put("mods", scanAllMods());
        state.put("screenshots", MultiplayerTools.listScreenshots(ctx.getGameDir()));
        state.put("notes", MultiplayerTools.loadNotes(ctx.getGameDir()));
        state.put("jvm", MultiplayerTools.getJvmStats());
        sendJson(ex, 200, state);
    }

    private void handleFriendAdd(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String target = SimpleJson.asString(body, "target", "");
        Map<String, Object> res = cloud.addFriend(target);
        sendJson(ex, 200, res);
    }

    private void handleFriendAccept(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String target = SimpleJson.asString(body, "player_id", "");
        boolean ok = cloud.acceptFriendRequest(target);
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", ok);
        sendJson(ex, 200, res);
    }

    private void handleFriendRemove(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String target = SimpleJson.asString(body, "target", "");
        boolean ok = cloud.removeOrDeclineFriend(target);
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", ok);
        sendJson(ex, 200, res);
    }

    private void handleFriendSync(HttpExchange ex) throws IOException {
        cloud.upsertPlayerAndPresence(false);
        cloud.syncFriendsAndPresence();
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", true);
        res.put("cloud_reachable", cloud.cloudReachable);
        res.put("friends", cloud.getCachedFriends());
        res.put("incoming_requests", cloud.getCachedIncomingRequests());
        res.put("party", cloud.getCachedParty());
        res.put("party_invites", cloud.getCachedPartyInvites());
        res.put("messages", cloud.getCachedMessages());
        sendJson(ex, 200, res);
    }

    private void handleChatSend(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String recipientId = SimpleJson.asString(body, "recipient_id", "");
        String partyId = SimpleJson.asString(body, "party_id", "");
        String text = SimpleJson.asString(body, "body", "");
        String kind = SimpleJson.asString(body, "kind", "text");
        sendJson(ex, 200, cloud.sendChatMessage(recipientId, partyId, text, kind));
    }

    private void handleChatPoll(HttpExchange ex) throws IOException {
        Map<String, String> q = parseQuery(ex.getRequestURI().getRawQuery());
        List<Map<String, Object>> msgs = cloud.pollChatMessages(q.get("peer_id"), q.get("party_id"));
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("messages", msgs);
        sendJson(ex, 200, res);
    }

    private void handlePartyCreate(HttpExchange ex) throws IOException {
        sendJson(ex, 200, cloud.createParty());
    }

    @SuppressWarnings("unchecked")
    private void handlePartyInvite(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        List<String> targets = new ArrayList<>();
        Object rawT = body.get("targets");
        if (rawT instanceof List) {
            for (Object o : (List<Object>) rawT) {
                if (o != null && !String.valueOf(o).trim().isEmpty()) targets.add(String.valueOf(o).trim());
            }
        } else {
            String single = SimpleJson.asString(body, "target", "");
            if (!single.isEmpty()) targets.add(single);
        }
        sendJson(ex, 200, cloud.inviteToParty(targets));
    }

    private void handlePartyJoin(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        sendJson(ex, 200, cloud.joinParty(SimpleJson.asString(body, "party_id", "")));
    }

    private void handlePartyLeave(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        boolean ok = cloud.leaveOrDeclineParty(SimpleJson.asString(body, "party_id", ""));
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", ok);
        sendJson(ex, 200, res);
    }

    private void handlePartyTarget(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String srv = SimpleJson.asString(body, "target_server", "");
        String world = SimpleJson.asString(body, "target_world", ctx.versionName);
        boolean ok = cloud.broadcastPartyTarget(srv, world);
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", ok);
        sendJson(ex, 200, res);
    }

    private void handleHostWhitelist(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        boolean enabled = SimpleJson.asBoolean(body, "enabled", true);
        sendJson(ex, 200, cloud.syncFriendsWhitelist(enabled));
    }

    private void handleHostStart(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        int reqPort = SimpleJson.asInt(body, "port", cloud.detectedLanPort > 0 ? cloud.detectedLanPort : 0);
        if (reqPort <= 0) {
            Map<String, Object> ingameHost = callIngameAddon("/ingame/host", new LinkedHashMap<>());
            int igPort = SimpleJson.asInt(ingameHost, "port", 0);
            if (igPort > 0) {
                reqPort = igPort;
                cloud.detectedLanPort = igPort;
            }
        }
        if (reqPort <= 0) reqPort = 25565;
        boolean friendsOnly = SimpleJson.asBoolean(body, "friends_only", cloud.friendsOnlyHost);
        if (friendsOnly) {
            cloud.syncFriendsWhitelist(true);
        } else {
            cloud.friendsOnlyHost = false;
        }

        Map<String, Object> bridgeRes = MultiplayerTools.callLauncherBridge(
            ctx, "/api/host/start", "POST", "{\"port\":" + reqPort + "}"
        );
        if (SimpleJson.asBoolean(bridgeRes, "success", false)) {
            String pubAddr = SimpleJson.asString(bridgeRes, "public_address", "");
            cloud.tunnelActive = true;
            cloud.tunnelPublicAddr = pubAddr;
            cloud.currentStatus = "hosting";
            cloud.currentActivity = !pubAddr.isEmpty() ? ("Hosting: " + pubAddr) : ("Tunnel Starting (Port " + reqPort + ")");
            cloud.upsertPlayerAndPresence(false);
            if (!pubAddr.isEmpty()) cloud.broadcastPartyTarget(pubAddr, ctx.versionName);
            sendJson(ex, 200, bridgeRes);
            return;
        }

        // Local LAN / Radmin fallback if Playit tunnel bridge is offline
        List<String> ips = MultiplayerTools.getLocalNetworkIps();
        String fallbackAddr = ips.isEmpty() ? ("127.0.0.1:" + reqPort) : (ips.get(0) + ":" + reqPort);
        cloud.tunnelActive = false;
        cloud.detectedLanPort = reqPort;
        cloud.currentServerAddr = fallbackAddr;
        cloud.currentStatus = "hosting";
        cloud.currentActivity = "LAN/VPN Host: " + fallbackAddr;
        cloud.upsertPlayerAndPresence(false);
        cloud.broadcastPartyTarget(fallbackAddr, ctx.versionName);

        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", true);
        res.put("mode", "local_lan");
        res.put("public_address", fallbackAddr);
        res.put("friends_only", friendsOnly);
        res.put("note", SimpleJson.asString(bridgeRes, "error", "Sharing LAN/Radmin IP directly"));
        sendJson(ex, 200, res);
    }

    private void handleHostStop(HttpExchange ex) throws IOException {
        Map<String, Object> bridgeRes = MultiplayerTools.callLauncherBridge(ctx, "/api/host/stop", "POST", "{}");
        cloud.tunnelActive = false;
        cloud.tunnelPublicAddr = "";
        cloud.currentStatus = "online";
        cloud.currentActivity = "In Main Menu";
        cloud.upsertPlayerAndPresence(false);
        Map<String, Object> res = new LinkedHashMap<>(bridgeRes);
        res.put("success", true);
        sendJson(ex, 200, res);
    }

    private void handleJoin(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String addr = SimpleJson.asString(body, "address", "").trim();
        String worldName = SimpleJson.asString(body, "name", "Friend World");
        if (addr.isEmpty()) {
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("success", false);
            err.put("error", "Missing server address");
            sendJson(ex, 400, err);
            return;
        }
        String host = addr;
        int srvPort = 25565;
        if (addr.contains(":")) {
            int idx = addr.lastIndexOf(':');
            try {
                srvPort = Integer.parseInt(addr.substring(idx + 1).trim());
                host = addr.substring(0, idx).trim();
            } catch (Exception ignored) {}
        }
        RejoinHelper.writeRejoinFile(ctx.getGameDir(), host, srvPort, worldName);
        Map<String, Object> ingamePayload = new LinkedHashMap<>();
        ingamePayload.put("address", addr);
        ingamePayload.put("name", worldName);
        Map<String, Object> ingameRes = callIngameAddon("/ingame/join", ingamePayload);
        Map<String, Object> bridgePayload = new LinkedHashMap<>();
        bridgePayload.put("address", addr);
        bridgePayload.put("version_name", ctx.versionName);
        Map<String, Object> bridgeRes = MultiplayerTools.callLauncherBridge(
            ctx, "/api/join", "POST", SimpleJson.stringify(bridgePayload)
        );
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", true);
        res.put("address", addr);
        res.put("rejoin_written", true);
        res.put("ingame_triggered", SimpleJson.asBoolean(ingameRes, "success", false));
        res.put("launcher_triggered", SimpleJson.asBoolean(bridgeRes, "success", false));
        sendJson(ex, 200, res);
    }

    private void handlePing(HttpExchange ex) throws IOException {
        Map<String, String> q = parseQuery(ex.getRequestURI().getRawQuery());
        String host = q.get("host");
        Map<String, Object> pingRes = MultiplayerTools.pingServer(host, 2500);
        sendJson(ex, 200, pingRes);
    }

    private void handleMods(HttpExchange ex) throws IOException {
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("mods", scanAllMods());
        sendJson(ex, 200, res);
    }

    private void handleModToggle(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String fname = SimpleJson.asString(body, "file_name", "");
        Map<String, Object> res = new LinkedHashMap<>();
        if (fname.isEmpty() || fname.contains("/") || fname.contains("\\") || fname.toLowerCase().startsWith("moon-sync")) {
            res.put("success", false);
            res.put("error", "Protected or invalid mod filename");
            sendJson(ex, 400, res);
            return;
        }
        File target = new File(MoonSyncMod.getModsDirectory(), fname);
        if (!target.exists()) {
            res.put("success", false);
            res.put("error", "Mod file not found");
            sendJson(ex, 404, res);
            return;
        }
        String newName = fname.toLowerCase().endsWith(".disabled")
            ? fname.substring(0, fname.length() - ".disabled".length())
            : (fname + ".disabled");
        boolean ok = target.renameTo(new File(MoonSyncMod.getModsDirectory(), newName));
        res.put("success", ok);
        res.put("new_file_name", newName);
        sendJson(ex, 200, res);
    }

    private void handleNoteAdd(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        List<Map<String, Object>> notes = MultiplayerTools.addNote(
            ctx.getGameDir(),
            SimpleJson.asString(body, "title", "Waypoint"),
            SimpleJson.asString(body, "coords", ""),
            SimpleJson.asString(body, "dimension", "Overworld")
        );
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", true);
        res.put("notes", notes);
        sendJson(ex, 200, res);
    }

    private void handleNoteDelete(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        List<Map<String, Object>> notes = MultiplayerTools.deleteNote(
            ctx.getGameDir(),
            SimpleJson.asString(body, "id", "")
        );
        Map<String, Object> res = new LinkedHashMap<>();
        res.put("success", true);
        res.put("notes", notes);
        sendJson(ex, 200, res);
    }

    private void handleScreenshotFile(HttpExchange ex) throws IOException {
        Map<String, String> q = parseQuery(ex.getRequestURI().getRawQuery());
        String name = q.get("name");
        if (name == null || name.contains("/") || name.contains("\\") || name.contains("..")) {
            sendText(ex, 400, "Invalid filename", "text/plain");
            return;
        }
        File shot = new File(new File(ctx.getGameDir(), "screenshots"), name);
        if (!shot.exists() || !shot.isFile()) {
            sendText(ex, 404, "Not found", "text/plain");
            return;
        }
        ex.getResponseHeaders().set("Content-Type", "image/png");
        ex.sendResponseHeaders(200, shot.length());
        try (FileInputStream fis = new FileInputStream(shot); OutputStream os = ex.getResponseBody()) {
            byte[] buf = new byte[16384];
            int n;
            while ((n = fis.read(buf)) != -1) {
                os.write(buf, 0, n);
            }
        }
    }

    private void handleScreenshotShare(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String name = SimpleJson.asString(body, "name", "");
        if (name.isEmpty() || name.contains("/") || name.contains("\\") || name.contains("..")) {
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("success", false);
            err.put("error", "Invalid screenshot name");
            sendJson(ex, 400, err);
            return;
        }
        File shot = new File(new File(ctx.getGameDir(), "screenshots"), name);
        Map<String, Object> res = cloud.shareScreenshot(shot);
        String shareUrl = SimpleJson.asString(res, "url", "");
        boolean sendToParty = SimpleJson.asBoolean(body, "send_to_party", false);
        String recipientId = SimpleJson.asString(body, "recipient_id", "");
        if (SimpleJson.asBoolean(res, "success", false) && !shareUrl.isEmpty()) {
            if (sendToParty && cloud.getCachedParty() != null) {
                String pid = SimpleJson.asString(cloud.getCachedParty(), "party_id", "");
                if (!pid.isEmpty()) cloud.sendChatMessage("", pid, "Screenshot (" + name + "): " + shareUrl, "screenshot");
            } else if (!recipientId.isEmpty()) {
                cloud.sendChatMessage(recipientId, "", "Screenshot (" + name + "): " + shareUrl, "screenshot");
            }
        }
        sendJson(ex, 200, res);
    }

    private void handleQolStatus(HttpExchange ex) throws IOException {
        Map<String, Object> br = MultiplayerTools.callLauncherBridge(ctx, "/api/qol/status", "GET", null);
        sendJson(ex, 200, br);
    }

    private void handleQolAction(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String action = SimpleJson.asString(body, "action", "");
        if (!action.matches("overlay|audio|borderless|gamma|backup")) {
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("success", false);
            err.put("error", "Invalid QoL action");
            sendJson(ex, 400, err);
            return;
        }
        Map<String, Object> br = MultiplayerTools.callLauncherBridge(ctx, "/api/qol/" + action, "POST", SimpleJson.stringify(body));
        sendJson(ex, 200, br);
    }

    private void handleP2pAction(HttpExchange ex) throws IOException {
        Map<String, Object> body = readJsonBody(ex);
        String action = SimpleJson.asString(body, "action", "");
        if ("status".equals(action)) {
            sendJson(ex, 200, MultiplayerTools.callLauncherBridge(ctx, "/api/p2p/status", "GET", null));
            return;
        }
        if (!action.matches("host|connect|stop")) {
            Map<String, Object> err = new LinkedHashMap<>();
            err.put("success", false);
            err.put("error", "Invalid P2P action");
            sendJson(ex, 400, err);
            return;
        }
        if ("host".equals(action) && !body.containsKey("port")) {
            int hostPort = cloud.detectedLanPort;
            if (hostPort <= 0) {
                Map<String, Object> ingameHost = callIngameAddon("/ingame/host", new LinkedHashMap<>());
                int igPort = SimpleJson.asInt(ingameHost, "port", 0);
                if (igPort > 0) {
                    hostPort = igPort;
                    cloud.detectedLanPort = igPort;
                }
            }
            if (hostPort > 0) {
                body.put("port", hostPort);
            }
        }
        Map<String, Object> br = MultiplayerTools.callLauncherBridge(ctx, "/api/p2p/" + action, "POST", SimpleJson.stringify(body));
        sendJson(ex, 200, br);
    }

    private Map<String, Object> callIngameAddon(String endpoint, Map<String, Object> payload) {
        Map<String, Object> empty = new LinkedHashMap<>();
        try {
            File cfg = new File(new File(ctx.getGameDir(), "config"), "moon-ingame.json");
            if (!cfg.exists() || !cfg.isFile()) return empty;
            byte[] bytes = java.nio.file.Files.readAllBytes(cfg.toPath());
            Map<String, Object> parsed = SimpleJson.parseObject(new String(bytes, StandardCharsets.UTF_8));
            int port = SimpleJson.asInt(parsed, "port", 0);
            if (port <= 0 || port > 65535) return empty;
            String ep = endpoint.startsWith("/") ? endpoint : ("/" + endpoint);
            HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:" + port + ep).openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(1500);
            conn.setReadTimeout(2500);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] body = SimpleJson.stringify(payload != null ? payload : new LinkedHashMap<>()).getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(body);
            }
            int code = conn.getResponseCode();
            InputStream is = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            if (is == null) return empty;
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[2048];
            int n;
            while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
            return SimpleJson.parseObject(new String(baos.toByteArray(), StandardCharsets.UTF_8));
        } catch (Exception ignored) {
            return empty;
        }
    }

    private List<Map<String, Object>> scanAllMods() {
        List<Map<String, Object>> list = new ArrayList<>();
        File modsDir = MoonSyncMod.getModsDirectory();
        if (modsDir == null || !modsDir.isDirectory()) return list;
        File[] files = modsDir.listFiles((d, n) -> {
            String low = n.toLowerCase();
            return low.endsWith(".jar") || low.endsWith(".jar.disabled");
        });
        if (files == null) return list;
        for (File f : files) {
            Map<String, Object> m = new LinkedHashMap<>();
            String fn = f.getName();
            boolean enabled = !fn.toLowerCase().endsWith(".disabled");
            m.put("file_name", fn);
            m.put("enabled", enabled);
            m.put("client_only", ModManifest.isClientOnlyMod(fn));
            m.put("size_kb", Math.max(1, f.length() / 1024));
            list.add(m);
        }
        return list;
    }

    private void handleDashboard(HttpExchange ex) throws IOException {
        sendText(ex, 200, DASHBOARD_HTML, "text/html; charset=utf-8");
    }

    private static Map<String, Object> readJsonBody(HttpExchange ex) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (InputStream is = ex.getRequestBody()) {
            byte[] buf = new byte[4096];
            int n;
            while ((n = is.read(buf)) != -1) {
                baos.write(buf, 0, n);
            }
        }
        return SimpleJson.parseObject(new String(baos.toByteArray(), StandardCharsets.UTF_8));
    }

    private static Map<String, String> parseQuery(String raw) {
        Map<String, String> map = new LinkedHashMap<>();
        if (raw == null || raw.isEmpty()) return map;
        for (String pair : raw.split("&")) {
            int eq = pair.indexOf('=');
            if (eq > 0) {
                try {
                    String k = URLDecoder.decode(pair.substring(0, eq), "UTF-8");
                    String v = URLDecoder.decode(pair.substring(eq + 1), "UTF-8");
                    map.put(k, v);
                } catch (Exception ignored) {}
            }
        }
        return map;
    }

    private static void sendJson(HttpExchange ex, int status, Object obj) throws IOException {
        sendText(ex, status, SimpleJson.stringify(obj), "application/json; charset=utf-8");
    }

    private static void sendText(HttpExchange ex, int status, String text, String contentType) throws IOException {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", contentType);
        ex.getResponseHeaders().set("Cache-Control", "no-store");
        ex.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static final String DASHBOARD_HTML =
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        + "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        + "<title>Moon Client Companion Hub</title>"
        + "<style>"
        + ":root{--bg:#0b0f19;--card:#131a2a;--line:#25314d;--text:#f1f5f9;--muted:#94a3b8;--accent:#7c3aed;--mint:#34d399;--sky:#38bdf8;--amber:#fbbf24;--rose:#fb7185;}"
        + "*{box-sizing:border-box;font-family:Inter,Segoe UI,system-ui,sans-serif;}"
        + "body{margin:0;background:radial-gradient(circle at top right,#1d1740,var(--bg) 55%);color:var(--text);padding:20px;}"
        + ".wrap{max-width:1100px;margin:0 auto;}"
        + ".top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin-bottom:16px;}"
        + ".id-pill{background:#1e1b4b;border:1px solid #6366f1;color:#c7d2fe;padding:6px 12px;border-radius:999px;font-weight:800;font-family:monospace;cursor:pointer;}"
        + ".badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:800;text-transform:uppercase;}"
        + ".b-ok{background:rgba(52,211,153,.16);color:var(--mint);border:1px solid rgba(52,211,153,.4);}"
        + ".b-warn{background:rgba(251,191,36,.16);color:var(--amber);border:1px solid rgba(251,191,36,.4);}"
        + ".tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;}"
        + ".tab{background:var(--card);border:1px solid var(--line);color:var(--muted);padding:9px 15px;border-radius:10px;font-weight:700;cursor:pointer;}"
        + ".tab.active{background:var(--accent);border-color:#a78bfa;color:#fff;}"
        + ".panel{display:none;}.panel.active{display:block;}"
        + ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;}"
        + ".card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;}"
        + "h3{margin:0 0 10px 0;font-size:15px;}label{font-size:12px;color:var(--muted);display:block;margin-bottom:4px;}"
        + "input,select{width:100%;background:#0a0e17;border:1px solid var(--line);color:var(--text);padding:9px 11px;border-radius:8px;margin-bottom:8px;}"
        + ".row{display:flex;gap:8px;align-items:center;}.btn{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:9px 13px;font-weight:700;cursor:pointer;white-space:nowrap;}"
        + ".btn.sec{background:#1e293b;border:1px solid var(--line);}.btn.mint{background:#059669;}.btn.rose{background:#e11d48;}"
        + ".item{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#0d1321;border:1px solid var(--line);padding:10px 12px;border-radius:10px;margin-bottom:8px;}"
        + ".muted{color:var(--muted);font-size:12px;}.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;}"
        + ".shot img{width:100%;height:105px;object-fit:cover;border-radius:8px;border:1px solid var(--line);}"
        + "</style></head><body><div class='wrap'>"
        + "<div class='top'><div><div style='font-size:18px;font-weight:900'>Moon Client Companion</div>"
        + "<div class='muted' id='hdr-sub'>Loading instance...</div></div>"
        + "<div class='row'><span id='hdr-cloud' class='badge b-warn'>Cloud Check</span>"
        + "<span id='hdr-id' class='id-pill' onclick='copyId()' title='Click to copy Moon ID'>MOON-0000</span>"
        + "<button class='btn sec' onclick='syncNow()'>Sync Cloud</button></div></div>"
        + "<div class='tabs'>"
        + "<button class='tab active' onclick=\"tab('social',this)\">Friends & Cloud</button>"
        + "<button class='tab' onclick=\"tab('multi',this)\">Multiplayer & Host</button>"
        + "<button class='tab' onclick=\"tab('mods',this)\">Mod Sync & Mods</button>"
        + "<button class='tab' onclick=\"tab('extras',this)\">Screenshots & Waypoints</button>"
        + "</div>"
        + "<div id='social' class='panel active'><div class='grid'>"
        + "<div class='card'><h3>Add Friend by Moon ID / Username</h3>"
        + "<div class='row'><input id='f-input' placeholder='MOON-4821 or PlayerName' style='margin:0'>"
        + "<button class='btn' onclick='addFriend()'>Add Friend</button></div>"
        + "<div id='f-msg' class='muted' style='margin-top:8px'></div>"
        + "<h3 style='margin-top:16px'>Incoming Friend Requests</h3><div id='req-list'></div>"
        + "<h3 style='margin-top:16px'>Party / Squad</h3><div id='party-box'></div></div>"
        + "<div class='card'><h3>Friends Online & Activity</h3><div id='friends-list'></div>"
        + "<h3 style='margin-top:16px'>Cross-Server Chat</h3>"
        + "<div class='row' style='margin-bottom:8px'><select id='chat-target' style='margin:0'></select>"
        + "<button class='btn sec' onclick='pollChatNow()'>Refresh</button></div>"
        + "<div id='chat-feed' style='max-height:210px;overflow-y:auto;background:#0a0e17;border:1px solid var(--line);border-radius:8px;padding:8px;margin-bottom:8px'></div>"
        + "<div class='row'><input id='chat-input' placeholder='Whisper friend or message party...' style='margin:0' onkeydown=\"if(event.key==='Enter')sendChat()\">"
        + "<button class='btn mint' onclick='sendChat()'>Send</button></div></div>"
        + "</div></div>"
        + "<div id='multi' class='panel'><div class='grid'>"
        + "<div class='card'><h3>Host World Online</h3>"
        + "<div id='host-info' class='muted' style='margin-bottom:10px'>Detecting LAN / Tunnel...</div>"
        + "<label style='display:flex;align-items:center;gap:8px;margin-bottom:10px;cursor:pointer'><input type='checkbox' id='wl-toggle' style='width:auto;margin:0' onchange='toggleWhitelist(this.checked)'> <span>Friends-Only Whitelist (auto-sync whitelist.json)</span></label>"
        + "<div class='row'><input id='host-port' type='number' value='25565' style='max-width:120px;margin:0'>"
        + "<button class='btn mint' onclick='startHost()'>Host Tunnel</button>"
        + "<button class='btn rose' onclick='stopHost()'>Stop</button></div>"
        + "<div style='margin-top:12px;padding-top:10px;border-top:1px solid var(--line)'>"
        + "<div class='muted' style='margin-bottom:6px'>Direct P2P Hole Punch (Zero-Setup Room + servers.dat auto-add)</div>"
        + "<div class='row' style='margin-bottom:6px'><button class='btn' onclick='p2pHost()'>Host P2P Room</button><button class='btn sec' onclick='p2pStop()'>Stop P2P</button></div>"
        + "<div class='row'><input id='p2p-join-id' placeholder='MOON-P2P-XXXX or Friend Moon ID' style='margin:0'><button class='btn mint' onclick='p2pJoin()'>Join P2P</button></div>"
        + "<div id='p2p-msg' class='muted' style='margin-top:6px'></div></div></div>"
        + "<div class='card'><h3>Live Server Pinger</h3>"
        + "<div class='row'><input id='ping-addr' placeholder='mc.hypixel.net or IP:port' style='margin:0'>"
        + "<button class='btn' onclick='pingSrv()'>Ping</button></div>"
        + "<div id='ping-out' class='muted' style='margin-top:10px'>Enter a server IP to check MOTD & latency.</div>"
        + "<h3 style='margin-top:16px'>HUD Overlay, Audio & Backup QoL</h3>"
        + "<div class='row' style='flex-wrap:wrap;gap:6px;margin-bottom:8px'>"
        + "<button class='btn sec' onclick=\"qolAct('overlay')\">HUD Overlay [F8]</button>"
        + "<button class='btn sec' onclick=\"qolAct('borderless')\">Borderless</button>"
        + "<button class='btn sec' onclick=\"qolAct('gamma')\">Fullbright</button>"
        + "<button class='btn mint' onclick=\"qolAct('backup')\">Backup Saves</button></div>"
        + "<div class='row'><select id='qol-aud' style='margin:0'><option value='normal'>Audio: Normal</option><option value='pvp_focus'>Audio: PvP Focus</option><option value='chill'>Audio: Chill</option><option value='mute_game'>Audio: Mute MC</option></select>"
        + "<button class='btn' onclick=\"qolAct('audio',{preset:document.getElementById('qol-aud').value})\">Apply</button></div>"
        + "<div id='qol-msg' class='muted' style='margin-top:6px'></div></div>"
        + "</div></div>"
        + "<div id='mods' class='panel'><div class='card'>"
        + "<div class='row' style='justify-content:space-between;margin-bottom:10px'><h3>Installed Instance Mods</h3>"
        + "<span class='muted' id='mods-count'>0 mods</span></div><div id='mods-list'></div></div></div>"
        + "<div id='extras' class='panel'><div class='grid'>"
        + "<div class='card'><h3>Quick Waypoints & World Notes</h3>"
        + "<input id='n-title' placeholder='Base / Nether Portal / Stronghold'>"
        + "<div class='row'><input id='n-coords' placeholder='X: 120, Y: 64, Z: -340' style='margin:0'>"
        + "<select id='n-dim' style='max-width:130px;margin:0'><option>Overworld</option><option>Nether</option><option>The End</option></select>"
        + "<button class='btn' onclick='addNote()'>Save</button></div><div id='notes-list' style='margin-top:10px'></div></div>"
        + "<div class='card'><h3>Recent Screenshots (Instant Share)</h3><div id='shot-msg' class='muted' style='margin-bottom:8px'></div><div id='shots-list' class='shots'></div></div>"
        + "</div></div></div>"
        + "<script>"
        + "let S={};"
        + "function tab(id,btn){document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));"
        + "document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));"
        + "document.getElementById(id).classList.add('active');btn.classList.add('active');}"
        + "async function api(u,b){const r=await fetch(u,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});return r.json();}"
        + "function copyId(){navigator.clipboard.writeText(S.moon_id||'');document.getElementById('f-msg').textContent='Copied '+S.moon_id;}"
        + "async function refresh(){S=await api('/api/state');"
        + "document.getElementById('hdr-id').textContent=S.moon_id||'MOON-0000';"
        + "document.getElementById('hdr-sub').textContent=`${S.username} • ${S.version_name} (${S.loader} ${S.mc_version||''}) • ${S.activity} • RAM ${S.jvm.used_mb}/${S.jvm.max_mb}MB`;"
        + "const cb=document.getElementById('hdr-cloud');cb.textContent=S.cloud_reachable?'Cloudflare D1 Synced':(S.cloud_configured?'Cloud Unreachable':'Local Cache Mode');"
        + "cb.className='badge '+(S.cloud_reachable?'b-ok':'b-warn');"
        + "const wl=document.getElementById('wl-toggle');if(wl)wl.checked=!!S.friends_only_host;"
        + "renderRequests(S.incoming_requests||[]);renderParty(S.party,S.party_invites||[]);renderFriends(S.friends||[]);renderChatTargets();renderChatFeed(S.messages||[]);renderHost();renderMods(S.mods||[]);renderNotes(S.notes||[]);renderShots(S.screenshots||[]);}"
        + "function renderRequests(reqs){const el=document.getElementById('req-list');"
        + "el.innerHTML=reqs.length?reqs.map(r=>`<div class='item'><div><b>${r.username}</b> <span class='muted'>${r.player_id}</span></div><div class='row'><button class='btn mint' onclick=\"acceptReq('${r.player_id}')\">Accept</button><button class='btn sec' onclick=\"rmFriend('${r.player_id}')\">Decline</button></div></div>`).join(''):\"<div class='muted'>No pending requests.</div>\";}"
        + "function renderParty(p,invs){const el=document.getElementById('party-box');let h='';"
        + "if(invs&&invs.length){h+=invs.map(i=>`<div class='item'><div><b>Invite from ${i.leader_name}</b><div class='muted'>${i.party_id} ${i.target_server?'• '+i.target_server:''}</div></div><div class='row'><button class='btn mint' onclick=\"joinParty('${i.party_id}')\">Join</button><button class='btn sec' onclick=\"leaveParty('${i.party_id}')\">Decline</button></div></div>`).join('');}"
        + "if(!p){h+=`<div class='row'><button class='btn' onclick='createParty()'>Create Party</button><button class='btn mint' onclick='massInviteParty()'>1-Click Invite All Friends</button></div>`;el.innerHTML=h;return;}"
        + "h+=`<div class='item'><div><b>${p.party_id}</b> ${p.is_leader?'<span class=\"badge b-ok\">LEADER</span>':''}<div class='muted'>Target: ${p.target_server||'Not hosting yet'} ${p.target_world?'('+p.target_world+')':''}</div></div><div class='row'>${p.target_server?`<button class='btn mint' onclick=\"joinAddr('${p.target_server}','Party')\">Join Target</button>`:''}<button class='btn rose' onclick=\"leaveParty('')\">Leave</button></div></div>`;"
        + "h+=`<div class='row' style='margin-bottom:8px'>${p.is_leader?`<button class='btn mint' onclick='massInviteParty()'>Mass Invite Friends</button><button class='btn sec' onclick='syncPartyTarget()'>Broadcast My Server</button>`:''}</div>`;"
        + "h+=(p.members||[]).map(m=>`<div class='item'><div><b>${m.username}</b> <span class='muted'>${m.role} • ${m.invite_status}</span></div><span class='badge ${m.online_status==='hosting'||m.online_status==='playing'||m.online_status==='online'?'b-ok':'b-warn'}'>${m.online_status||'offline'}</span></div>`).join('');"
        + "el.innerHTML=h;}"
        + "function renderFriends(fs){const el=document.getElementById('friends-list');"
        + "el.innerHTML=fs.length?fs.map(f=>`<div class='item'><div><div><b>${f.username||f.player_id}</b> <span class='badge ${f.status==='hosting'||f.status==='playing'||f.status==='online'?'b-ok':'b-warn'}'>${f.status||'offline'}</span></div>"
        + "<div class='muted'>${f.player_id||''} ${f.version_name?'• '+f.version_name:''} ${f.server_addr?'• '+f.server_addr:''}</div></div>"
        + "<div class='row'>${f.server_addr?`<button class='btn mint' onclick=\"joinAddr('${f.server_addr}','${f.username}')\">Join</button>`:''}<button class='btn sec' onclick=\"selectChat('dm:${f.player_id||''}')\">Chat</button><button class='btn sec' onclick=\"rmFriend('${f.player_id||f.username}')\">Remove</button></div></div>`).join(''):\"<div class='muted'>No friends added yet.</div>\";}"
        + "function renderChatTargets(){const sel=document.getElementById('chat-target');if(!sel)return;const prev=sel.value;const opts=[];"
        + "if(S.party&&S.party.party_id)opts.push(`<option value='party:${S.party.party_id}'>Party (${S.party.party_id})</option>`);"
        + "(S.friends||[]).forEach(f=>{if(f.player_id)opts.push(`<option value='dm:${f.player_id}'>Whisper: ${f.username||f.player_id}</option>`);});"
        + "if(!opts.length)opts.push(`<option value=''>Add a friend or party first</option>`);sel.innerHTML=opts.join('');if(prev&&[...sel.options].some(o=>o.value===prev))sel.value=prev;}"
        + "function selectChat(v){const sel=document.getElementById('chat-target');if(sel&&v){sel.value=v;pollChatNow();document.getElementById('chat-input').focus();}}"
        + "function renderChatFeed(ms){const el=document.getElementById('chat-feed');if(!el)return;"
        + "el.innerHTML=ms.length?ms.map(m=>`<div style='margin-bottom:6px;font-size:12px'><b>${m.sender_name||m.sender_id}</b> ${m.party_id?`<span class='badge b-ok'>${m.party_id}</span>`:`<span class='muted'>→ ${m.recipient_id}</span>`}: <span>${String(m.body||'').replace(/</g,'&lt;')}</span></div>`).join(''):\"<div class='muted'>No messages yet.</div>\";el.scrollTop=el.scrollHeight;}"
        + "function renderHost(){const hi=document.getElementById('host-info');"
        + "if(S.lan_port>0&&!document.getElementById('host-port').dataset.ed)document.getElementById('host-port').value=S.lan_port;"
        + "hi.innerHTML=S.tunnel_active?`<b style='color:var(--mint)'>Hosting Live: ${S.tunnel_addr||'Tunnel Starting...'}</b>`:`LAN Port Detected: ${S.lan_port||'None (Open to LAN in Pause menu)'} • Local IPs: ${(S.local_ips||[]).join(', ')}`;}"
        + "function renderMods(ms){document.getElementById('mods-count').textContent=ms.length+' mods';"
        + "document.getElementById('mods-list').innerHTML=ms.map(m=>`<div class='item'><div><b>${m.file_name}</b> <span class='muted'>${m.size_kb} KB ${m.client_only?'• Client-Only':''}</span></div>"
        + "${m.file_name.toLowerCase().startsWith('moon-sync')?'<span class=\"badge b-ok\">CORE</span>':`<button class='btn sec' onclick=\"toggleMod('${m.file_name}')\">${m.enabled?'Disable':'Enable'}</button>`}</div>`).join('');}"
        + "function renderNotes(ns){document.getElementById('notes-list').innerHTML=ns.length?ns.map(n=>`<div class='item'><div><b>${n.title}</b> <span class='badge b-ok'>${n.dimension}</span><div class='muted'>${n.coords}</div></div><button class='btn sec' onclick=\"delNote('${n.id}')\">Del</button></div>`).join(''):\"<div class='muted'>No waypoints saved yet.</div>\";}"
        + "function renderShots(ss){document.getElementById('shots-list').innerHTML=ss.length?ss.map(s=>`<div class='shot'><a href='/api/screenshots/file?name=${encodeURIComponent(s.name)}' target='_blank'><img src='/api/screenshots/file?name=${encodeURIComponent(s.name)}'></a><div class='muted' style='margin:4px 0'>${s.name}</div><div class='row'><button class='btn sec' style='padding:4px 8px;font-size:11px' onclick=\"shareShot('${s.name}',false)\">Copy Link</button>${S.party?`<button class='btn mint' style='padding:4px 8px;font-size:11px' onclick=\"shareShot('${s.name}',true)\">To Party</button>`:''}</div></div>`).join(''):\"<div class='muted'>No screenshots in instance yet.</div>\";}"
        + "async function addFriend(){const v=document.getElementById('f-input').value.trim();if(!v)return;const r=await api('/api/friends/add',{target:v});document.getElementById('f-msg').textContent=r.success?`Sent/Added: ${r.username} (${r.player_id})`:r.error;document.getElementById('f-input').value='';refresh();}"
        + "async function acceptReq(id){await api('/api/friends/accept',{player_id:id});refresh();}"
        + "async function rmFriend(t){await api('/api/friends/remove',{target:t});refresh();}"
        + "async function syncNow(){await api('/api/friends/sync',{});refresh();}"
        + "async function createParty(){await api('/api/party/create',{});refresh();}"
        + "async function massInviteParty(){const r=await api('/api/party/invite',{targets:[]});document.getElementById('f-msg').textContent=r.success?`Invited ${(r.invited||[]).length} friend(s) to ${r.party_id}`:(r.error||'Invite failed');refresh();}"
        + "async function joinParty(id){await api('/api/party/join',{party_id:id});refresh();}"
        + "async function leaveParty(id){await api('/api/party/leave',{party_id:id});refresh();}"
        + "async function syncPartyTarget(){const addr=S.tunnel_addr||(S.lan_port>0?(S.local_ips&&S.local_ips[0]?S.local_ips[0]+':'+S.lan_port:'127.0.0.1:'+S.lan_port):'');await api('/api/party/target',{target_server:addr,target_world:S.version_name});refresh();}"
        + "async function pollChatNow(){const v=(document.getElementById('chat-target')||{}).value||'';let q='';if(v.startsWith('party:'))q='?party_id='+encodeURIComponent(v.slice(6));else if(v.startsWith('dm:'))q='?peer_id='+encodeURIComponent(v.slice(3));const r=await api('/api/chat/poll'+q);renderChatFeed(r.messages||[]);}"
        + "async function sendChat(){const v=(document.getElementById('chat-target')||{}).value||'';const inp=document.getElementById('chat-input');const txt=inp.value.trim();if(!v||!txt)return;const b={body:txt};if(v.startsWith('party:'))b.party_id=v.slice(6);else if(v.startsWith('dm:'))b.recipient_id=v.slice(3);inp.value='';await api('/api/chat/send',b);pollChatNow();}"
        + "async function toggleWhitelist(en){await api('/api/host/whitelist',{enabled:en});}"
        + "async function qolAct(action,extra){const r=await api('/api/qol/action',Object.assign({action},extra||{}));const el=document.getElementById('qol-msg');if(el)el.textContent=r.success?(r.label||(r.file?'Backup: '+r.file:(r.skipped?r.reason:('Done: '+action)))):(r.error||'Bridge offline');}"
        + "async function p2pHost(){const fo=!!(document.getElementById('wl-toggle')||{}).checked;const r=await api('/api/p2p/action',{action:'host',friends_only:fo});const el=document.getElementById('p2p-msg');el.textContent=r.success?`P2P Room: ${r.room_code} (Port ${r.local_port})`:(r.error||'Bridge offline');}"
        + "async function p2pJoin(){const t=(document.getElementById('p2p-join-id')||{}).value.trim();if(!t)return;const r=await api('/api/p2p/action',{action:'connect',target:t});const el=document.getElementById('p2p-msg');if(r.success&&r.local_address){navigator.clipboard.writeText(r.local_address).catch(()=>{});el.textContent=`Connected (${r.mode}): ${r.local_address} — Added to Multiplayer list!`;}else{el.textContent=r.error||'Connect failed';}}"
        + "async function p2pStop(){await api('/api/p2p/action',{action:'stop'});const el=document.getElementById('p2p-msg');if(el)el.textContent='P2P stopped';}"
        + "async function shareShot(name,toParty){const r=await api('/api/screenshots/share',{name,send_to_party:!!toParty});const el=document.getElementById('shot-msg');if(r.success&&r.url){navigator.clipboard.writeText(r.url).catch(()=>{});el.innerHTML=`Shared (48h): <a href='${r.url}' target='_blank' style='color:var(--mint)'>${r.url}</a> (copied)`;if(toParty)refresh();}else{el.textContent=r.error||'Upload failed';}}"
        + "async function startHost(){const p=parseInt(document.getElementById('host-port').value)||25565;const fo=!!(document.getElementById('wl-toggle')||{}).checked;const r=await api('/api/host/start',{port:p,friends_only:fo});if(r.claim_url&&!r.public_address){document.getElementById('host-info').innerHTML=`Open 1x Playit claim link: <a href='${r.claim_url}' target='_blank' style='color:var(--sky)'>${r.claim_url}</a>`;return;}refresh();}"
        + "async function stopHost(){await api('/api/host/stop',{});refresh();}"
        + "async function joinAddr(a,u){navigator.clipboard.writeText(a).catch(()=>{});const r=await api('/api/join',{address:a,name:u});document.getElementById('f-msg').textContent=`Address copied & rejoin queued: ${r.address}`;}"
        + "async function pingSrv(){const h=document.getElementById('ping-addr').value.trim();if(!h)return;const r=await api('/api/ping?host='+encodeURIComponent(h));document.getElementById('ping-out').textContent=r.online?`ONLINE • ${r.latency_ms}ms • ${r.players_online||0}/${r.players_max||0} • ${r.motd}`:`OFFLINE • ${r.error}`;}"
        + "async function toggleMod(fn){await api('/api/mods/toggle',{file_name:fn});refresh();}"
        + "async function addNote(){await api('/api/notes/add',{title:document.getElementById('n-title').value,coords:document.getElementById('n-coords').value,dimension:document.getElementById('n-dim').value});document.getElementById('n-title').value='';document.getElementById('n-coords').value='';refresh();}"
        + "async function delNote(id){await api('/api/notes/delete',{id});refresh();}"
        + "refresh();setInterval(refresh,4000);"
        + "</script></body></html>";
}

