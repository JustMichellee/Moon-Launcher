package dev.moonlauncher.sync;

import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Client-side multiplayer & utility toolkit:
 * - Minecraft TCP Server List Ping (SLP) with MOTD, player count, latency
 * - Launcher Bridge calls to host public tunnel or trigger 1-click friend join
 * - Screenshot gallery index & per-instance world coordinate notes
 * - Live JVM memory & performance metrics
 */
public class MultiplayerTools {

    public static Map<String, Object> pingServer(String rawAddress, int timeoutMs) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("online", false);
        out.put("address", rawAddress);

        String host = rawAddress != null ? rawAddress.trim() : "";
        int port = 25565;
        if (host.contains(":")) {
            int idx = host.lastIndexOf(':');
            try {
                port = Integer.parseInt(host.substring(idx + 1).trim());
                host = host.substring(0, idx).trim();
            } catch (Exception ignored) {}
        }
        if (host.isEmpty()) {
            out.put("error", "Empty address");
            return out;
        }

        long t0 = System.currentTimeMillis();
        try (Socket sock = new Socket()) {
            sock.connect(new InetSocketAddress(host, port), timeoutMs);
            sock.setSoTimeout(timeoutMs);

            DataOutputStream dos = new DataOutputStream(sock.getOutputStream());
            DataInputStream dis = new DataInputStream(sock.getInputStream());

            // Handshake packet (ID 0x00)
            ByteArrayOutputStream hs = new ByteArrayOutputStream();
            DataOutputStream hsOut = new DataOutputStream(hs);
            writeVarInt(hsOut, 0x00);
            writeVarInt(hsOut, 763); // 1.20.1 protocol baseline (accepted across versions for status)
            byte[] hostBytes = host.getBytes(StandardCharsets.UTF_8);
            writeVarInt(hsOut, hostBytes.length);
            hsOut.write(hostBytes);
            hsOut.writeShort(port);
            writeVarInt(hsOut, 1); // Next state: status

            byte[] hsBytes = hs.toByteArray();
            writeVarInt(dos, hsBytes.length);
            dos.write(hsBytes);

            // Status Request packet (ID 0x00, empty)
            writeVarInt(dos, 1);
            writeVarInt(dos, 0x00);
            dos.flush();

            long latency = System.currentTimeMillis() - t0;
            readVarInt(dis); // packet length
            int pktId = readVarInt(dis);
            if (pktId == 0x00) {
                int strLen = readVarInt(dis);
                byte[] jsonBytes = new byte[Math.min(strLen, 131072)];
                dis.readFully(jsonBytes);
                String rawJson = new String(jsonBytes, StandardCharsets.UTF_8);
                Map<String, Object> parsed = SimpleJson.parseObject(rawJson);

                out.put("online", true);
                out.put("latency_ms", latency);
                Object playersObj = parsed.get("players");
                if (playersObj instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> pm = (Map<String, Object>) playersObj;
                    out.put("players_online", SimpleJson.asInt(pm, "online", 0));
                    out.put("players_max", SimpleJson.asInt(pm, "max", 0));
                }
                Object verObj = parsed.get("version");
                if (verObj instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> vm = (Map<String, Object>) verObj;
                    out.put("version", SimpleJson.asString(vm, "name", ""));
                }
                out.put("motd", extractMotdText(parsed.get("description")));
            }
        } catch (Exception e) {
            out.put("error", e.getMessage() != null ? e.getMessage() : "Unreachable");
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static String extractMotdText(Object desc) {
        if (desc == null) return "Minecraft Server";
        if (desc instanceof String) return ((String) desc).replaceAll("§.", "");
        if (desc instanceof Map) {
            Map<String, Object> m = (Map<String, Object>) desc;
            String t = SimpleJson.asString(m, "text", "");
            if (t.isEmpty() && m.get("extra") instanceof List) {
                StringBuilder sb = new StringBuilder();
                for (Object ex : (List<Object>) m.get("extra")) {
                    if (ex instanceof Map) sb.append(SimpleJson.asString((Map<String, Object>) ex, "text", ""));
                    else if (ex != null) sb.append(ex.toString());
                }
                t = sb.toString();
            }
            return t.replaceAll("§.", "").trim();
        }
        return "Minecraft Server";
    }

    public static Map<String, Object> callLauncherBridge(MoonClientContext ctx, String path, String method, String jsonBody) {
        Map<String, Object> res = new LinkedHashMap<>();
        if (ctx == null || ctx.bridgeUrl == null || ctx.bridgeUrl.isEmpty()) {
            res.put("success", false);
            res.put("error", "Moon Launcher desktop bridge is not active");
            return res;
        }
        HttpURLConnection conn = null;
        try {
            URL u = new URL(ctx.bridgeUrl.replaceAll("/+$", "") + path);
            conn = (HttpURLConnection) u.openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(3000);
            conn.setReadTimeout(12000);
            conn.setRequestProperty("Content-Type", "application/json");
            if (jsonBody != null) {
                conn.setDoOutput(true);
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = conn.getResponseCode();
            InputStream is = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            StringBuilder sb = new StringBuilder();
            if (is != null) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = is.read(buf)) != -1) {
                    sb.append(new String(buf, 0, n, StandardCharsets.UTF_8));
                }
            }
            Map<String, Object> parsed = SimpleJson.parseObject(sb.toString());
            if (!parsed.containsKey("success")) {
                parsed.put("success", code >= 200 && code < 300);
            }
            return parsed;
        } catch (Exception e) {
            res.put("success", false);
            res.put("error", e.getMessage() != null ? e.getMessage() : "Bridge unreachable");
            return res;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    public static List<String> getLocalNetworkIps() {
        List<String> ips = new ArrayList<>();
        try {
            Enumeration<NetworkInterface> ifaces = NetworkInterface.getNetworkInterfaces();
            while (ifaces.hasMoreElements()) {
                NetworkInterface iface = ifaces.nextElement();
                if (!iface.isUp() || iface.isLoopback()) continue;
                Enumeration<InetAddress> addrs = iface.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress addr = addrs.nextElement();
                    if (addr instanceof Inet4Address) {
                        ips.add(addr.getHostAddress());
                    }
                }
            }
        } catch (Exception ignored) {}
        return ips;
    }

    public static List<Map<String, Object>> listScreenshots(File gameDir) {
        List<Map<String, Object>> items = new ArrayList<>();
        if (gameDir == null) return items;
        File dir = new File(gameDir, "screenshots");
        if (!dir.isDirectory()) return items;
        File[] files = dir.listFiles((d, name) -> name.toLowerCase().endsWith(".png"));
        if (files == null) return items;
        Arrays.sort(files, Comparator.comparingLong(File::lastModified).reversed());
        int limit = Math.min(files.length, 24);
        for (int i = 0; i < limit; i++) {
            File f = files[i];
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", f.getName());
            m.put("size_kb", Math.max(1, f.length() / 1024));
            m.put("modified", f.lastModified());
            items.add(m);
        }
        return items;
    }

    public static File getNotesFile(File gameDir) {
        File cfgDir = new File(gameDir, "config");
        if (!cfgDir.exists()) cfgDir.mkdirs();
        return new File(cfgDir, "moon-notes.json");
    }

    @SuppressWarnings("unchecked")
    public static List<Map<String, Object>> loadNotes(File gameDir) {
        List<Map<String, Object>> out = new ArrayList<>();
        File nf = getNotesFile(gameDir);
        if (!nf.exists()) return out;
        try {
            List<Object> arr = SimpleJson.parseArray(MoonClientContext.readText(nf));
            for (Object o : arr) {
                if (o instanceof Map) out.add((Map<String, Object>) o);
            }
        } catch (Exception ignored) {}
        return out;
    }

    public static List<Map<String, Object>> addNote(File gameDir, String title, String coords, String dimension) {
        List<Map<String, Object>> list = loadNotes(gameDir);
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", String.valueOf(System.currentTimeMillis()));
        item.put("title", title != null && !title.trim().isEmpty() ? title.trim() : "Waypoint");
        item.put("coords", coords != null ? coords.trim() : "");
        item.put("dimension", dimension != null && !dimension.trim().isEmpty() ? dimension.trim() : "Overworld");
        item.put("created_at", System.currentTimeMillis());
        list.add(0, item);
        try { MoonClientContext.writeJson(getNotesFile(gameDir), list); } catch (Exception ignored) {}
        return list;
    }

    public static List<Map<String, Object>> deleteNote(File gameDir, String noteId) {
        List<Map<String, Object>> list = loadNotes(gameDir);
        List<Map<String, Object>> kept = new ArrayList<>();
        for (Map<String, Object> m : list) {
            if (!SimpleJson.asString(m, "id", "").equals(noteId)) {
                kept.add(m);
            }
        }
        try { MoonClientContext.writeJson(getNotesFile(gameDir), kept); } catch (Exception ignored) {}
        return kept;
    }

    public static Map<String, Object> getJvmStats() {
        Runtime rt = Runtime.getRuntime();
        long maxMb = rt.maxMemory() / (1024 * 1024);
        long totalMb = rt.totalMemory() / (1024 * 1024);
        long freeMb = rt.freeMemory() / (1024 * 1024);
        long usedMb = Math.max(0, totalMb - freeMb);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("used_mb", usedMb);
        m.put("max_mb", maxMb);
        m.put("java_version", System.getProperty("java.version", "8"));
        return m;
    }

    private static void writeVarInt(DataOutputStream out, int value) throws Exception {
        while ((value & ~0x7F) != 0) {
            out.writeByte((value & 0x7F) | 0x80);
            value >>>= 7;
        }
        out.writeByte(value);
    }

    private static int readVarInt(DataInputStream in) throws Exception {
        int numRead = 0;
        int result = 0;
        byte read;
        do {
            read = in.readByte();
            int value = (read & 0x7F);
            result |= (value << (7 * numRead));
            numRead++;
            if (numRead > 5) throw new RuntimeException("VarInt too big");
        } while ((read & 0x80) != 0);
        return result;
    }
}

