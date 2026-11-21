package dev.moonlauncher.sync;

import java.io.File;
import java.util.List;

/**
 * Main Entrypoint for Moon Sync & Client Companion in-game mod.
 * Compatible with Fabric, Quilt, Forge (1.13-1.21+), NeoForge, and Legacy Forge (1.8-1.12.2).
 */
public class MoonSyncMod {

    public static final String MOD_ID = "moonsync";
    public static final String CHANNEL_SYNC_V1 = "moon:sync_v1";
    public static final String VERSION = "2.0.0";

    private static volatile boolean initialized = false;
    private static volatile boolean running = false;
    private static File gameDirectory = new File(".");
    private static File modsDirectory = new File("mods");

    private static MoonClientContext context;
    private static MoonCloudClient cloudClient;
    private static MoonCompanionServer companionServer;
    private static Thread heartbeatThread;

    public static synchronized void init(File runDir) {
        if (runDir != null) {
            gameDirectory = runDir;
            modsDirectory = new File(runDir, "mods");
        }
        if (initialized) {
            return;
        }
        initialized = true;
        running = true;

        context = new MoonClientContext(gameDirectory);
        cloudClient = new MoonCloudClient(context);
        companionServer = new MoonCompanionServer(context, cloudClient);
        int port = companionServer.start();
        MoonCompanionUI.attachTray(context, cloudClient, companionServer);

        System.out.println("==================================================");
        System.out.println("  Moon Client Companion v" + VERSION + " Initialized");
        System.out.println("  Player : " + context.username + " (" + context.moonId + ")");
        if (port > 0) {
            System.out.println("  Social & Multiplayer Hub : http://127.0.0.1:" + port + "/");
        }
        System.out.println("  Cloud DB Sync : " + (context.hasSupabaseConfig() ? "Configured" : "Local Cache"));
        System.out.println("==================================================");

        // Check if game was just relaunched after a mod sync
        RejoinHelper.RejoinSession session = RejoinHelper.readAndClearRejoin(gameDirectory);
        if (session != null) {
            System.out.println("[MoonSync] Restored rejoin target from previous session: "
                + session.server + ":" + session.port + " (" + session.worldName + ")");
        }

        heartbeatThread = new Thread(() -> {
            // Immediate initial cloud registration & friends sync
            try {
                cloudClient.pollGameActivity();
                cloudClient.upsertPlayerAndPresence(false);
                cloudClient.syncFriendsAndPresence();
            } catch (Exception ignored) {}

            while (running) {
                try {
                    Thread.sleep(10000L);
                    if (!running) break;
                    cloudClient.pollGameActivity();
                    cloudClient.upsertPlayerAndPresence(false);
                    cloudClient.syncFriendsAndPresence();
                } catch (InterruptedException ie) {
                    break;
                } catch (Exception ignored) {}
            }
        }, "MoonCloudHeartbeat");
        heartbeatThread.setDaemon(true);
        heartbeatThread.start();

        Runtime.getRuntime().addShutdownHook(new Thread(MoonSyncMod::shutdown, "MoonSyncShutdown"));
    }

    public static synchronized void shutdown() {
        running = false;
        if (heartbeatThread != null) {
            heartbeatThread.interrupt();
        }
        if (cloudClient != null) {
            try {
                cloudClient.upsertPlayerAndPresence(true);
            } catch (Exception ignored) {}
        }
        MoonCompanionUI.detachTray();
        if (companionServer != null) {
            companionServer.stop();
        }
    }

    public static MoonClientContext getContext() {
        return context;
    }

    public static MoonCloudClient getCloudClient() {
        return cloudClient;
    }

    public static MoonCompanionServer getCompanionServer() {
        return companionServer;
    }

    public static List<ModManifest.ModEntry> getLocalManifest() {
        return ModManifest.scanDirectory(modsDirectory);
    }

    public static File getGameDirectory() {
        return gameDirectory;
    }

    public static File getModsDirectory() {
        return modsDirectory;
    }
}
