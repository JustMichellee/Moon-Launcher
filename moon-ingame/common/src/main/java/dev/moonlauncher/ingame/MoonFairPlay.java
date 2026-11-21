package dev.moonlauncher.ingame;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;

import java.util.Arrays;
import java.util.List;

/**
 * Enforces server-safe Fair-Play compliance so Moon Client behaves strictly as
 * an allowed QoL/HUD client and avoids accidental kicks or bans on competitive servers.
 */
public final class MoonFairPlay {

    private static final List<String> RESTRICTED_DOMAINS = Arrays.asList(
        "hypixel.net",
        "hypixel.io",
        "minemen.club",
        "pvplegacy.net",
        "cubecraft.net",
        "mccisland.net",
        "hoplite.gg",
        "gommehd.net",
        "mineplex.com",
        "stray.gg",
        "mcpvp.club"
    );

    private static String lastNoticedServer = "";

    private MoonFairPlay() {}

    public static boolean isLocalOrSingleplayer(Minecraft mc) {
        if (mc == null) return true;
        if (mc.hasSingleplayerServer()) return true;
        ServerData srv = mc.getCurrentServer();
        if (srv == null || srv.ip == null) return true;
        String ip = srv.ip.trim().toLowerCase();
        int colon = ip.lastIndexOf(':');
        if (colon > 0) ip = ip.substring(0, colon);
        return ip.isEmpty()
            || ip.equals("localhost")
            || ip.equals("127.0.0.1")
            || ip.startsWith("192.168.")
            || ip.startsWith("10.")
            || ip.startsWith("26.");
    }

    public static String getCurrentServerHost(Minecraft mc) {
        if (mc == null || mc.hasSingleplayerServer()) return "";
        ServerData srv = mc.getCurrentServer();
        if (srv == null || srv.ip == null) return "";
        String host = srv.ip.trim().toLowerCase();
        int colon = host.lastIndexOf(':');
        if (colon > 0) host = host.substring(0, colon);
        return host;
    }

    public static boolean isCompetitiveRestrictedServer(Minecraft mc) {
        String host = getCurrentServerHost(mc);
        if (host.isEmpty()) return false;
        for (String domain : RESTRICTED_DOMAINS) {
            if (host.equals(domain) || host.endsWith("." + domain)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Freelook is automatically blocked on known competitive servers (e.g. Hypixel/Minemen)
     * whenever Fair-Play Guard is enabled, preventing accidental Watchdog/anti-cheat bans.
     */
    public static boolean isFreelookAllowed(Minecraft mc) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        if (!cfg.freelookEnabled) return false;
        if (isLocalOrSingleplayer(mc)) return true;
        return !(cfg.strictFairPlay && isCompetitiveRestrictedServer(mc));
    }

    public static void notifyIfFreelookBlocked(Minecraft mc) {
        if (mc == null) return;
        String host = getCurrentServerHost(mc);
        if (!host.isEmpty() && !host.equals(lastNoticedServer)) {
            lastNoticedServer = host;
            MoonIngameState.chatNotice(
                mc,
                "\u00a7e[Moon Fair-Play] \u00a77Freelook dinonaktifkan otomatis di \u00a7f" + host + " \u00a77agar aman dari aturan/anti-cheat server."
            );
        }
    }

    public static String getServerSafetyLabel(Minecraft mc) {
        if (isLocalOrSingleplayer(mc)) return "\u00a7aSafe (Local/P2P)";
        if (MoonIngameConfig.get().strictFairPlay && isCompetitiveRestrictedServer(mc)) {
            return "\u00a7bFair-Play Locked";
        }
        return "\u00a7aFair-Play ON";
    }
}

