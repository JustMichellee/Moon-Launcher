package dev.moonlauncher.sync;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Handles mod comparison and selective file transfer between Host and Guest.
 */
public class SyncEngine {

    public static class SyncDiff {
        public List<ModManifest.ModEntry> missingMods = new ArrayList<>();
        public List<ModManifest.ModEntry> mismatchedMods = new ArrayList<>();
        public int totalMissingBytes = 0;

        public boolean hasDifferences() {
            return !missingMods.isEmpty() || !mismatchedMods.isEmpty();
        }
    }

    public static SyncDiff calculateDiff(List<ModManifest.ModEntry> hostManifest, List<ModManifest.ModEntry> guestManifest) {
        SyncDiff diff = new SyncDiff();
        Map<String, ModManifest.ModEntry> guestMap = new HashMap<>();
        for (ModManifest.ModEntry entry : guestManifest) {
            guestMap.put(entry.fileName.toLowerCase(), entry);
        }

        for (ModManifest.ModEntry hostEntry : hostManifest) {
            // Ignore client-only mods (Sodium, Iris, etc.)
            if (hostEntry.clientOnly) {
                continue;
            }

            ModManifest.ModEntry guestEntry = guestMap.get(hostEntry.fileName.toLowerCase());
            if (guestEntry == null) {
                diff.missingMods.add(hostEntry);
                diff.totalMissingBytes += hostEntry.sizeBytes;
            } else if (!guestEntry.sha256.equalsIgnoreCase(hostEntry.sha256)) {
                diff.mismatchedMods.add(hostEntry);
                diff.totalMissingBytes += hostEntry.sizeBytes;
            }
        }
        return diff;
    }

    /**
     * Downloads a missing mod file directly from the Host's Moon Launcher HTTP endpoint.
     */
    public static boolean downloadModFromHost(String hostBaseUrl, String fileName, File destFolder) {
        try {
            String encodedName = fileName.replace(" ", "%20");
            URL url = new URL(hostBaseUrl + "/mods/" + encodedName);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestProperty("User-Agent", "Moon-Launcher-Sync/1.0");
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(15000);

            if (conn.getResponseCode() != 200) {
                System.err.println("[MoonSync] Host returned status: " + conn.getResponseCode() + " for " + fileName);
                return false;
            }

            File targetFile = new File(destFolder, fileName);
            File tempFile = new File(destFolder, fileName + ".moon_tmp");

            try (InputStream in = conn.getInputStream(); FileOutputStream out = new FileOutputStream(tempFile)) {
                byte[] buf = new byte[16384];
                int read;
                while ((read = in.read(buf)) != -1) {
                    out.write(buf, 0, read);
                }
            }

            if (targetFile.exists()) {
                targetFile.delete();
            }
            tempFile.renameTo(targetFile);
            System.out.println("[MoonSync] Successfully downloaded and installed: " + fileName);
            return true;
        } catch (Exception e) {
            System.err.println("[MoonSync] Download error for " + fileName + ": " + e.getMessage());
            return false;
        }
    }
}

