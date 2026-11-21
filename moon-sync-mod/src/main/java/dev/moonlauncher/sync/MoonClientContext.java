package dev.moonlauncher.sync;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Resolves and persists Moon Launcher identity (MOON-XXXX ID), username, Supabase DB
 * credentials, and local Launcher IPC bridge endpoints inside the running game instance.
 */
public class MoonClientContext {

    public static final String CONTEXT_FILE_NAME = "moon-client-context.json";
    public static final String COMPANION_META_NAME = "moon-companion.json";
    public static final String DEFAULT_CLOUD_API_URL = "https://moon-launcher-cloud.moonlauncher.workers.dev";

    public String moonId = "";
    public String username = "Player";
    public String uuid = "";
    public String accountType = "offline";
    public String versionName = "Minecraft";
    public String mcVersion = "";
    public String loader = "Vanilla";
    public String supabaseUrl = "";
    public String supabaseKey = "";
    public String cloudApiUrl = "";
    public String bridgeUrl = "";
    public String skinUrl = "";
    public String launcherHome = "";
    public int companionPort = 0;

    private final File gameDir;

    public MoonClientContext(File gameDir) {
        this.gameDir = gameDir != null ? gameDir : new File(".");
        load();
    }

    public File getGameDir() {
        return gameDir;
    }

    public File getContextFile() {
        File cfgDir = new File(gameDir, "config");
        if (cfgDir.isDirectory()) {
            File f = new File(cfgDir, CONTEXT_FILE_NAME);
            if (f.exists()) return f;
        }
        File rootFile = new File(gameDir, CONTEXT_FILE_NAME);
        if (rootFile.exists()) return rootFile;
        return cfgDir.isDirectory() ? new File(cfgDir, CONTEXT_FILE_NAME) : rootFile;
    }

    public File getFriendsFile() {
        if (launcherHome != null && !launcherHome.trim().isEmpty()) {
            File lf = new File(launcherHome, "friends.json");
            if (lf.getParentFile().isDirectory()) return lf;
        }
        File parent = gameDir.getParentFile();
        if (parent != null && parent.getParentFile() != null) {
            File maybeHome = parent.getParentFile();
            if (new File(maybeHome, "launcher_config.json").exists()) {
                return new File(maybeHome, "friends.json");
            }
        }
        File cfgDir = new File(gameDir, "config");
        if (!cfgDir.exists()) cfgDir.mkdirs();
        return new File(cfgDir, "moon-friends.json");
    }

    public void load() {
        // 1. Check version folder & launcher config candidates
        File[] candidates = new File[] {
            new File(new File(gameDir, "config"), CONTEXT_FILE_NAME),
            new File(gameDir, CONTEXT_FILE_NAME),
            new File(gameDir, "launcher_config.json")
        };
        for (File cand : candidates) {
            mergeFromFile(cand);
        }

        // 2. Check launcher root config if parent/grandparent is Moon Launcher home
        File p = gameDir.getParentFile();
        if (p != null && p.getParentFile() != null) {
            File rootCfg = new File(p.getParentFile(), "launcher_config.json");
            if (rootCfg.exists()) {
                if (launcherHome.isEmpty()) {
                    launcherHome = p.getParentFile().getAbsolutePath();
                }
                mergeFromFile(rootCfg);
            }
        }

        // 3. Environment & JVM properties take precedence when provided
        applyOverride(System.getenv("MOON_LAUNCHER_HOME"), "launcherHome");
        applyOverride(System.getenv("MOON_CLOUD_URL"), "cloudApiUrl");
        applyOverride(System.getenv("MOON_SUPABASE_URL"), "supabaseUrl");
        applyOverride(System.getenv("MOON_SUPABASE_KEY"), "supabaseKey");
        applyOverride(System.getProperty("moon.id"), "moonId");
        applyOverride(System.getProperty("moon.username"), "username");
        applyOverride(System.getProperty("moon.cloud.url"), "cloudApiUrl");
        applyOverride(System.getProperty("moon.supabase.url"), "supabaseUrl");
        applyOverride(System.getProperty("moon.supabase.key"), "supabaseKey");
        applyOverride(System.getProperty("moon.bridge.url"), "bridgeUrl");

        if (versionName == null || versionName.trim().isEmpty() || "Minecraft".equals(versionName)) {
            String dirName = gameDir.getAbsoluteFile().getName();
            if (dirName != null && !dirName.isEmpty() && !".".equals(dirName)) {
                versionName = dirName;
            }
        }

        if (moonId == null || !moonId.toUpperCase().startsWith("MOON-")) {
            moonId = computeDeterministicMoonId(username);
        } else {
            moonId = moonId.trim().toUpperCase();
        }
        if (cloudApiUrl == null || cloudApiUrl.trim().isEmpty()) {
            cloudApiUrl = DEFAULT_CLOUD_API_URL;
        }
        if (cloudApiUrl != null) {
            cloudApiUrl = cloudApiUrl.trim().replaceAll("/+$", "");
        }
        if (supabaseUrl != null) {
            supabaseUrl = supabaseUrl.trim().replaceAll("/+$", "");
        }
        if (supabaseKey != null) {
            supabaseKey = supabaseKey.trim();
        }
    }

    public void saveContext() {
        try {
            File target = getContextFile();
            if (target.getParentFile() != null) {
                target.getParentFile().mkdirs();
            }
            writeJson(target, toMap());
        } catch (Exception ignored) {}
    }

    public void writeCompanionMeta(int port) {
        this.companionPort = port;
        try {
            Map<String, Object> meta = new LinkedHashMap<>();
            meta.put("port", port);
            meta.put("url", "http://127.0.0.1:" + port + "/");
            meta.put("moon_id", moonId);
            meta.put("username", username);
            meta.put("version_name", versionName);
            meta.put("pid", getCurrentPid());
            meta.put("updated_at", System.currentTimeMillis());

            File rootMeta = new File(gameDir, COMPANION_META_NAME);
            writeJson(rootMeta, meta);
            File cfgDir = new File(gameDir, "config");
            if (!cfgDir.exists()) cfgDir.mkdirs();
            writeJson(new File(cfgDir, COMPANION_META_NAME), meta);
        } catch (Exception ignored) {}
    }

    public void clearCompanionMeta() {
        try { new File(gameDir, COMPANION_META_NAME).delete(); } catch (Exception ignored) {}
        try { new File(new File(gameDir, "config"), COMPANION_META_NAME).delete(); } catch (Exception ignored) {}
    }

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("moon_id", moonId);
        m.put("username", username);
        m.put("uuid", uuid);
        m.put("account_type", accountType);
        m.put("version_name", versionName);
        m.put("mc_version", mcVersion);
        m.put("loader", loader);
        m.put("cloud_api_url", cloudApiUrl);
        m.put("supabase_url", supabaseUrl);
        m.put("supabase_key", supabaseKey);
        m.put("bridge_url", bridgeUrl);
        m.put("skin_url", skinUrl);
        m.put("launcher_home", launcherHome);
        return m;
    }

    private void mergeFromFile(File f) {
        if (f == null || !f.exists() || !f.isFile()) return;
        try {
            String raw = readText(f);
            Map<String, Object> data = SimpleJson.parseObject(raw);
            if (data.isEmpty()) return;

            String mid = SimpleJson.asString(data, "moon_id", "");
            if (mid.isEmpty()) mid = SimpleJson.asString(data, "player_id", "");
            if (!mid.isEmpty() && moonId.isEmpty()) moonId = mid;

            String u = SimpleJson.asString(data, "username", "");
            if (!u.isEmpty() && ("Player".equals(username) || username.isEmpty())) username = u;

            String idUuid = SimpleJson.asString(data, "uuid", "");
            if (!idUuid.isEmpty() && uuid.isEmpty()) uuid = idUuid;

            String aType = SimpleJson.asString(data, "account_type", "");
            if (!aType.isEmpty()) accountType = aType;

            String vName = SimpleJson.asString(data, "version_name", "");
            if (!vName.isEmpty()) versionName = vName;

            String mcV = SimpleJson.asString(data, "mc_version", "");
            if (!mcV.isEmpty()) mcVersion = mcV;

            String ld = SimpleJson.asString(data, "loader", "");
            if (!ld.isEmpty()) loader = ld;

            String caUrl = SimpleJson.asString(data, "cloud_api_url", "");
            if (!caUrl.isEmpty() && cloudApiUrl.isEmpty()) cloudApiUrl = caUrl;

            String sbUrl = SimpleJson.asString(data, "supabase_url", "");
            if (!sbUrl.isEmpty() && supabaseUrl.isEmpty()) supabaseUrl = sbUrl;

            String sbKey = SimpleJson.asString(data, "supabase_key", "");
            if (!sbKey.isEmpty() && supabaseKey.isEmpty()) supabaseKey = sbKey;

            String br = SimpleJson.asString(data, "bridge_url", "");
            if (!br.isEmpty()) bridgeUrl = br;

            String sk = SimpleJson.asString(data, "skin_url", "");
            if (sk.isEmpty()) sk = SimpleJson.asString(data, "discord_small_image", "");
            if (!sk.isEmpty() && skinUrl.isEmpty()) skinUrl = sk;

            String lh = SimpleJson.asString(data, "launcher_home", "");
            if (!lh.isEmpty() && launcherHome.isEmpty()) launcherHome = lh;
        } catch (Exception ignored) {}
    }

    private void applyOverride(String val, String field) {
        if (val == null || val.trim().isEmpty()) return;
        String clean = val.trim();
        if ("moonId".equals(field)) moonId = clean;
        else if ("username".equals(field)) username = clean;
        else if ("cloudApiUrl".equals(field)) cloudApiUrl = clean;
        else if ("supabaseUrl".equals(field)) supabaseUrl = clean;
        else if ("supabaseKey".equals(field)) supabaseKey = clean;
        else if ("bridgeUrl".equals(field)) bridgeUrl = clean;
        else if ("launcherHome".equals(field)) launcherHome = clean;
    }

    public static String computeDeterministicMoonId(String uname) {
        try {
            String clean = (uname != null && !uname.trim().isEmpty()) ? uname.trim().toLowerCase() : "player";
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(("MoonLauncher:" + clean).getBytes(StandardCharsets.UTF_8));
            int num = ((hash[0] & 0xFF) << 8) | (hash[1] & 0xFF);
            return "MOON-" + (1000 + (num % 9000));
        } catch (Exception e) {
            return "MOON-4821";
        }
    }

    public boolean hasCloudApiUrl() {
        return cloudApiUrl != null && !cloudApiUrl.isEmpty();
    }

    public boolean hasSupabaseConfig() {
        return hasCloudApiUrl() || (supabaseUrl != null && !supabaseUrl.isEmpty()
            && supabaseKey != null && !supabaseKey.isEmpty());
    }

    public static String readText(File f) throws Exception {
        StringBuilder sb = new StringBuilder();
        try (Reader r = new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)) {
            char[] buf = new char[4096];
            int n;
            while ((n = r.read(buf)) != -1) {
                sb.append(buf, 0, n);
            }
        }
        return sb.toString();
    }

    public static void writeJson(File f, Object obj) throws Exception {
        try (Writer w = new OutputStreamWriter(new FileOutputStream(f), StandardCharsets.UTF_8)) {
            w.write(SimpleJson.stringify(obj));
        }
    }

    private static String getCurrentPid() {
        try {
            String name = java.lang.management.ManagementFactory.getRuntimeMXBean().getName();
            int at = name.indexOf('@');
            return at > 0 ? name.substring(0, at) : "";
        } catch (Exception e) {
            return "";
        }
    }
}

