package dev.moonlauncher.ingame;

import com.sun.net.httpserver.HttpServer;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.server.IntegratedServer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.level.GameType;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.concurrent.ConcurrentLinkedDeque;

public class MoonIngameState {

    private static final ConcurrentLinkedDeque<Long> LMB_CLICKS = new ConcurrentLinkedDeque<>();
    private static final ConcurrentLinkedDeque<Long> RMB_CLICKS = new ConcurrentLinkedDeque<>();

    public static volatile boolean zoomHeld = false;
    public static volatile boolean sneakToggled = false;
    public static volatile boolean freelookActive = false;
    public static volatile float freelookYaw = 0.0F;
    public static volatile float freelookPitch = 0.0F;
    public static volatile long lastAutoGgMs = 0L;
    public static volatile String activeRoomCode = "";
    public static volatile boolean sharingWorld = false;

    private static CameraType savedCameraType = CameraType.FIRST_PERSON;
    private static boolean sprintHeldByMoon = false;
    private static HttpServer controlServer;

    public static void recordMouseClick(int button) {
        long now = System.currentTimeMillis();
        if (button == 0) LMB_CLICKS.addLast(now);
        else if (button == 1) RMB_CLICKS.addLast(now);
        pruneClicks(now);
    }

    public static int getLmbCps() {
        long now = System.currentTimeMillis();
        pruneClicks(now);
        return LMB_CLICKS.size();
    }

    public static int getRmbCps() {
        long now = System.currentTimeMillis();
        pruneClicks(now);
        return RMB_CLICKS.size();
    }

    private static void pruneClicks(long now) {
        long cutoff = now - 1000L;
        Iterator<Long> it1 = LMB_CLICKS.iterator();
        while (it1.hasNext() && it1.next() < cutoff) it1.remove();
        Iterator<Long> it2 = RMB_CLICKS.iterator();
        while (it2.hasNext() && it2.next() < cutoff) it2.remove();
    }

    public static void onClientTick(Minecraft mc) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        if (mc.player == null || mc.screen != null) {
            if (freelookActive) stopFreelook(mc);
            if (sprintHeldByMoon) {
                mc.options.keySprint.setDown(false);
                sprintHeldByMoon = false;
            }
            return;
        }

        // Server-safe ToggleSprint: presses vanilla sprint keybind ONLY under valid vanilla sprint conditions
        boolean canSprint = cfg.toggleSprint
            && mc.options.keyUp.isDown()
            && !mc.player.isShiftKeyDown()
            && !mc.player.isUsingItem()
            && !mc.player.horizontalCollision
            && (mc.player.getAbilities().mayfly || mc.player.getFoodData().getFoodLevel() > 6);
        if (canSprint) {
            mc.options.keySprint.setDown(true);
            sprintHeldByMoon = true;
        } else if (sprintHeldByMoon) {
            mc.options.keySprint.setDown(false);
            sprintHeldByMoon = false;
        }
    }

    public static void startFreelook(Minecraft mc) {
        if (mc == null || mc.player == null || freelookActive) return;
        if (!MoonIngameConfig.get().freelookEnabled) return;
        if (!MoonFairPlay.isFreelookAllowed(mc)) {
            MoonFairPlay.notifyIfFreelookBlocked(mc);
            return;
        }
        savedCameraType = mc.options.getCameraType();
        freelookYaw = mc.player.getYRot();
        freelookPitch = mc.player.getXRot();
        freelookActive = true;
        if (savedCameraType == CameraType.FIRST_PERSON) {
            mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
        }
    }

    public static void stopFreelook(Minecraft mc) {
        if (!freelookActive) return;
        freelookActive = false;
        if (mc != null && savedCameraType != null) {
            mc.options.setCameraType(savedCameraType);
        }
    }

    public static void updateFreelookAngles(float dy, float dx) {
        freelookYaw += dy;
        freelookPitch = Math.max(-90.0F, Math.min(90.0F, freelookPitch + dx));
    }

    private static int ensurePublishedLanPort(Minecraft mc, IntegratedServer srv) {
        if (srv == null) return -1;
        if (srv.isPublished()) return srv.getPort();
        final int port = findFreePort();
        final Object latch = new Object();
        final boolean[] okOut = new boolean[1];
        srv.execute(() -> {
            try {
                okOut[0] = srv.publishServer(GameType.SURVIVAL, true, port);
            } finally {
                synchronized (latch) { latch.notifyAll(); }
            }
        });
        try {
            synchronized (latch) { latch.wait(3000L); }
        } catch (InterruptedException ignored) {}
        if (!okOut[0] && !srv.isPublished()) return -1;
        return srv.isPublished() ? srv.getPort() : port;
    }

    public static void shareWorldOneClick(boolean friendsOnly) {
        Minecraft mc = Minecraft.getInstance();
        IntegratedServer srv = mc.getSingleplayerServer();
        if (srv == null) {
            chatNotice(mc, "\u00a7c[Moon P2P] Buka sebuah Singleplayer world terlebih dahulu untuk Share World.");
            return;
        }
        new Thread(() -> {
            try {
                int port = ensurePublishedLanPort(mc, srv);
                if (port <= 0) {
                    chatNotice(mc, "\u00a7c[Moon P2P] Gagal Auto-Publish LAN server.");
                    return;
                }

                MoonIngameConfig cfg = MoonIngameConfig.get();
                cfg.refreshBridgeContext();
                if (cfg.bridgeUrl == null || cfg.bridgeUrl.isEmpty()) {
                    chatNotice(mc, "\u00a7a[Moon P2P] Auto-LAN aktif di port " + port + " (jalankan lewat Moon Launcher untuk Room Code P2P).");
                    return;
                }

                String res = postJson(
                    cfg.bridgeUrl.replaceAll("/+$", "") + "/api/p2p/host",
                    "{\"port\":" + port + ",\"friends_only\":" + friendsOnly + "}"
                );
                String room = MoonIngameConfig.extractJsonString(res, "room_code");
                if (!room.isEmpty()) {
                    activeRoomCode = room;
                    sharingWorld = true;
                    mc.execute(() -> {
                        try { mc.keyboardHandler.setClipboard(room); } catch (Exception ignored) {}
                    });
                    chatNotice(mc, "\u00a7b[Moon P2P] \u00a7aWorld dibagikan! Room Code: \u00a7e" + room + " \u00a77(Auto-copied, tanpa klik LAN manual!)");
                } else {
                    String err = MoonIngameConfig.extractJsonString(res, "error");
                    chatNotice(mc, "\u00a7a[Moon P2P] Auto-LAN port " + port + " siap. " + (err.isEmpty() ? "" : err));
                }
            } catch (Exception e) {
                chatNotice(mc, "\u00a7c[Moon P2P] Error: " + e.getMessage());
            }
        }, "MoonAutoHost").start();
    }

    public static void chatNotice(Minecraft mc, String msg) {
        if (mc != null && msg != null) {
            mc.execute(() -> {
                try {
                    mc.gui.getChat().addMessage(Component.literal(msg));
                } catch (Exception ignored) {}
            });
        }
    }

    private static int findFreePort() {
        try (ServerSocket s = new ServerSocket(0)) {
            return s.getLocalPort();
        } catch (Exception e) {
            return 25565;
        }
    }

    public static void startLocalControlServer(File gameDir) {
        if (controlServer != null) return;
        try {
            controlServer = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0), 8);
            controlServer.createContext("/ingame/host", ex -> {
                Minecraft mc = Minecraft.getInstance();
                IntegratedServer srv = mc.getSingleplayerServer();
                int port = ensurePublishedLanPort(mc, srv);
                String respJson = port > 0
                    ? ("{\"success\":true,\"ok\":true,\"port\":" + port + "}")
                    : "{\"success\":false,\"error\":\"No singleplayer world open\"}";
                byte[] b = respJson.getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().set("Content-Type", "application/json");
                ex.sendResponseHeaders(port > 0 ? 200 : 400, b.length);
                try (OutputStream os = ex.getResponseBody()) { os.write(b); }
            });
            controlServer.createContext("/ingame/join", ex -> {
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                try (InputStream is = ex.getRequestBody()) {
                    byte[] buf = new byte[1024];
                    int n;
                    while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
                }
                String raw = new String(baos.toByteArray(), StandardCharsets.UTF_8);
                String host = MoonIngameConfig.extractJsonString(raw, "host").trim();
                int port = MoonIngameConfig.extractJsonInt(raw, "port", 25565);
                String addr = MoonIngameConfig.extractJsonString(raw, "address").trim();
                if (host.isEmpty() && !addr.isEmpty()) {
                    host = addr;
                    int colon = addr.lastIndexOf(':');
                    if (colon > 0) {
                        host = addr.substring(0, colon).trim();
                        try { port = Integer.parseInt(addr.substring(colon + 1).trim()); } catch (Exception ignored) {}
                    }
                }
                String name = MoonIngameConfig.extractJsonString(raw, "name");
                boolean ok = !host.isEmpty();
                if (ok) {
                    final String fHost = host;
                    final int fPort = port;
                    Minecraft.getInstance().execute(() -> VersionBridgeImpl.connectToServer(fHost, fPort, name.isEmpty() ? "Moon P2P" : name));
                }
                byte[] b = (ok ? "{\"success\":true,\"ok\":true}" : "{\"success\":false,\"error\":\"Missing address\"}").getBytes(StandardCharsets.UTF_8);
                ex.getResponseHeaders().set("Content-Type", "application/json");
                ex.sendResponseHeaders(ok ? 200 : 400, b.length);
                try (OutputStream os = ex.getResponseBody()) { os.write(b); }
            });
            controlServer.start();
            int port = controlServer.getAddress().getPort();
            File cfgDir = new File(gameDir != null ? gameDir : new File("."), "config");
            if (!cfgDir.exists()) cfgDir.mkdirs();
            File meta = new File(cfgDir, "moon-ingame.json");
            try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(meta), StandardCharsets.UTF_8)) {
                w.write("{\"port\":" + port + ",\"url\":\"http://127.0.0.1:" + port + "\"}");
            }
        } catch (Exception ignored) {}
    }

    private static String postJson(String target, String json) {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URL(target).openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(3000);
            conn.setReadTimeout(8000);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(json.getBytes(StandardCharsets.UTF_8));
            }
            InputStream is = conn.getResponseCode() >= 400 ? conn.getErrorStream() : conn.getInputStream();
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            if (is != null) {
                byte[] buf = new byte[2048];
                int n;
                while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
            }
            return new String(baos.toByteArray(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "";
        } finally {
            if (conn != null) conn.disconnect();
        }
    }
}

