package dev.moonlauncher.sync;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;

/**
 * Manages the zero-click seamless reconnection lifecycle.
 * Writes moon-rejoin.json to instruct Moon Launcher to restart Minecraft with new mods
 * and reconnect straight to the host's server/world.
 */
public class RejoinHelper {

    public static final String REJOIN_FILE_NAME = "moon-rejoin.json";

    public static class RejoinSession {
        public String server;
        public int port;
        public String worldName;
        public long timestamp;

        public RejoinSession(String server, int port, String worldName) {
            this.server = server;
            this.port = port;
            this.worldName = worldName != null ? worldName : "Moon World";
            this.timestamp = System.currentTimeMillis();
        }
    }

    public static boolean writeRejoinFile(File gameDir, String server, int port, String worldName) {
        try {
            File target = new File(gameDir, REJOIN_FILE_NAME);
            String json = String.format(
                "{\n  \"server\": \"%s\",\n  \"port\": %d,\n  \"worldName\": \"%s\",\n  \"timestamp\": %d,\n  \"reason\": \"mod_sync_complete\"\n}",
                server.replace("\\", "\\\\").replace("\"", "\\\""),
                port,
                worldName.replace("\\", "\\\\").replace("\"", "\\\""),
                System.currentTimeMillis()
            );

            try (Writer writer = new OutputStreamWriter(new FileOutputStream(target), StandardCharsets.UTF_8)) {
                writer.write(json);
            }
            System.out.println("[MoonSync] Rejoin file written successfully to " + target.getAbsolutePath());
            return true;
        } catch (Exception e) {
            System.err.println("[MoonSync] Failed to write rejoin state: " + e.getMessage());
            return false;
        }
    }

    public static RejoinSession readAndClearRejoin(File gameDir) {
        File target = new File(gameDir, REJOIN_FILE_NAME);
        if (!target.exists()) return null;

        try {
            StringBuilder sb = new StringBuilder();
            try (Reader reader = new InputStreamReader(new FileInputStream(target), StandardCharsets.UTF_8)) {
                char[] buf = new char[1024];
                int n;
                while ((n = reader.read(buf)) != -1) {
                    sb.append(buf, 0, n);
                }
            }
            // Delete file immediately to prevent infinite reconnect loops
            target.delete();

            String content = sb.toString();
            String server = extractJsonField(content, "server");
            String portStr = extractJsonField(content, "port");
            String worldName = extractJsonField(content, "worldName");
            int port = portStr != null ? Integer.parseInt(portStr) : 25565;

            if (server != null && !server.isEmpty()) {
                return new RejoinSession(server, port, worldName);
            }
        } catch (Exception e) {
            System.err.println("[MoonSync] Failed to parse rejoin file: " + e.getMessage());
        }
        return null;
    }

    private static String extractJsonField(String json, String field) {
        String key = "\"" + field + "\":";
        int idx = json.indexOf(key);
        if (idx == -1) return null;
        int start = idx + key.length();
        while (start < json.length() && (json.charAt(start) == ' ' || json.charAt(start) == '\"')) {
            start++;
        }
        int end = start;
        while (end < json.length() && json.charAt(end) != '\"' && json.charAt(end) != ',' && json.charAt(end) != '\n' && json.charAt(end) != '}') {
            end++;
        }
        return json.substring(start, end).trim();
    }
}

