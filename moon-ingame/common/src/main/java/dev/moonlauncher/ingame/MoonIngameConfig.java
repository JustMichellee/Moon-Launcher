package dev.moonlauncher.ingame;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.Properties;

public class MoonIngameConfig {

    private static final MoonIngameConfig INSTANCE = new MoonIngameConfig();

    public boolean hudEnabled = true;
    public boolean keystrokesEnabled = true;
    public boolean armorPotionsEnabled = true;
    public boolean toggleSprint = true;
    public boolean toggleSneak = false;
    public boolean fullbright = false;
    public boolean autoGg = true;
    public boolean freelookEnabled = true;
    public boolean strictFairPlay = true;
    public int telemetryX = -1;
    public int telemetryY = -1;
    public int keystrokesX = -1;
    public int keystrokesY = -1;
    public int armorX = -1;
    public int armorY = -1;
    public String bridgeUrl = "";
    public String moonId = "";

    private File gameDir = new File(".");

    public static MoonIngameConfig get() {
        return INSTANCE;
    }

    public void load(File runDir) {
        if (runDir != null) gameDir = runDir;
        File cfgDir = new File(gameDir, "config");
        if (!cfgDir.exists()) cfgDir.mkdirs();

        File propsFile = new File(cfgDir, "moon-ingame.properties");
        if (propsFile.exists()) {
            Properties p = new Properties();
            try (InputStreamReader r = new InputStreamReader(new FileInputStream(propsFile), StandardCharsets.UTF_8)) {
                p.load(r);
                hudEnabled = Boolean.parseBoolean(p.getProperty("hudEnabled", "true"));
                keystrokesEnabled = Boolean.parseBoolean(p.getProperty("keystrokesEnabled", "true"));
                armorPotionsEnabled = Boolean.parseBoolean(p.getProperty("armorPotionsEnabled", "true"));
                toggleSprint = Boolean.parseBoolean(p.getProperty("toggleSprint", "true"));
                toggleSneak = Boolean.parseBoolean(p.getProperty("toggleSneak", "false"));
                fullbright = Boolean.parseBoolean(p.getProperty("fullbright", "false"));
                autoGg = Boolean.parseBoolean(p.getProperty("autoGg", "true"));
                freelookEnabled = Boolean.parseBoolean(p.getProperty("freelookEnabled", "true"));
                strictFairPlay = Boolean.parseBoolean(p.getProperty("strictFairPlay", "true"));
                telemetryX = parseIntSafe(p.getProperty("telemetryX"), -1);
                telemetryY = parseIntSafe(p.getProperty("telemetryY"), -1);
                keystrokesX = parseIntSafe(p.getProperty("keystrokesX"), -1);
                keystrokesY = parseIntSafe(p.getProperty("keystrokesY"), -1);
                armorX = parseIntSafe(p.getProperty("armorX"), -1);
                armorY = parseIntSafe(p.getProperty("armorY"), -1);
            } catch (Exception ignored) {}
        } else {
            save();
        }
        refreshBridgeContext();
    }

    public void save() {
        File cfgDir = new File(gameDir, "config");
        if (!cfgDir.exists()) cfgDir.mkdirs();
        File propsFile = new File(cfgDir, "moon-ingame.properties");
        Properties p = new Properties();
        p.setProperty("hudEnabled", String.valueOf(hudEnabled));
        p.setProperty("keystrokesEnabled", String.valueOf(keystrokesEnabled));
        p.setProperty("armorPotionsEnabled", String.valueOf(armorPotionsEnabled));
        p.setProperty("toggleSprint", String.valueOf(toggleSprint));
        p.setProperty("toggleSneak", String.valueOf(toggleSneak));
        p.setProperty("fullbright", String.valueOf(fullbright));
        p.setProperty("autoGg", String.valueOf(autoGg));
        p.setProperty("freelookEnabled", String.valueOf(freelookEnabled));
        p.setProperty("strictFairPlay", String.valueOf(strictFairPlay));
        p.setProperty("telemetryX", String.valueOf(telemetryX));
        p.setProperty("telemetryY", String.valueOf(telemetryY));
        p.setProperty("keystrokesX", String.valueOf(keystrokesX));
        p.setProperty("keystrokesY", String.valueOf(keystrokesY));
        p.setProperty("armorX", String.valueOf(armorX));
        p.setProperty("armorY", String.valueOf(armorY));
        try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(propsFile), StandardCharsets.UTF_8)) {
            p.store(w, "Moon Client In-Game Mod Config");
        } catch (Exception ignored) {}
    }

    public void refreshBridgeContext() {
        File[] candidates = new File[] {
            new File(new File(gameDir, "config"), "moon-client-context.json"),
            new File(gameDir, "moon-client-context.json")
        };
        for (File f : candidates) {
            if (f.exists() && f.isFile()) {
                String txt = readAll(f);
                String br = extractJsonString(txt, "bridge_url");
                if (!br.isEmpty()) bridgeUrl = br;
                String mid = extractJsonString(txt, "moon_id");
                if (!mid.isEmpty()) moonId = mid;
                break;
            }
        }
    }

    public File getGameDir() {
        return gameDir;
    }

    public static String extractJsonString(String json, String key) {
        if (json == null || key == null) return "";
        String needle = "\"" + key + "\"";
        int idx = json.indexOf(needle);
        if (idx < 0) return "";
        int colon = json.indexOf(':', idx + needle.length());
        if (colon < 0) return "";
        int q1 = json.indexOf('"', colon + 1);
        if (q1 < 0) return "";
        int q2 = json.indexOf('"', q1 + 1);
        while (q2 > 0 && json.charAt(q2 - 1) == '\\') {
            q2 = json.indexOf('"', q2 + 1);
        }
        return (q2 > q1) ? json.substring(q1 + 1, q2) : "";
    }

    public static int extractJsonInt(String json, String key, int defVal) {
        if (json == null || key == null) return defVal;
        String needle = "\"" + key + "\"";
        int idx = json.indexOf(needle);
        if (idx < 0) return defVal;
        int colon = json.indexOf(':', idx + needle.length());
        if (colon < 0) return defVal;
        int i = colon + 1;
        while (i < json.length() && Character.isWhitespace(json.charAt(i))) i++;
        if (i < json.length() && json.charAt(i) == '"') i++;
        int start = i;
        while (i < json.length() && (Character.isDigit(json.charAt(i)) || json.charAt(i) == '-')) i++;
        if (i == start) return defVal;
        try {
            return Integer.parseInt(json.substring(start, i));
        } catch (Exception ignored) {
            return defVal;
        }
    }

    private static int parseIntSafe(String raw, int defVal) {
        if (raw == null) return defVal;
        try {
            return Integer.parseInt(raw.trim());
        } catch (Exception ignored) {
            return defVal;
        }
    }

    private static String readAll(File f) {
        StringBuilder sb = new StringBuilder();
        try (InputStreamReader r = new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)) {
            char[] buf = new char[2048];
            int n;
            while ((n = r.read(buf)) != -1) sb.append(buf, 0, n);
        } catch (Exception ignored) {}
        return sb.toString();
    }
}

