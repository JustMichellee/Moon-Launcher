package dev.moonlauncher.sync;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Clean-room implementation of Mod Manifest Scanner for Moon Launcher.
 * Scans local mods folder, computes SHA-256 checksums, and filters out client-only performance mods.
 */
public class ModManifest {

    // Performance and visual client-only mods that do NOT need strict server synchronization
    private static final Set<String> MANAGED_CLIENT_MODS = new HashSet<>(Arrays.asList(
        "sodium", "iris", "lithium", "ferritecore", "immediatelyfast",
        "entityculling", "lazydfu", "krypton", "modernfix", "rubidium",
        "oculus", "embeddium", "mouse_tweaks", "mousetweaks", "freecam",
        "appleskin", "dynamiclights", "continuity", "indium", "cloth-config"
    ));

    public static class ModEntry {
        public String fileName;
        public String sha256;
        public long sizeBytes;
        public boolean clientOnly;

        public ModEntry(String fileName, String sha256, long sizeBytes, boolean clientOnly) {
            this.fileName = fileName;
            this.sha256 = sha256;
            this.sizeBytes = sizeBytes;
            this.clientOnly = clientOnly;
        }
    }

    public static List<ModEntry> scanDirectory(File modsDir) {
        List<ModEntry> entries = new ArrayList<>();
        if (modsDir == null || !modsDir.exists() || !modsDir.isDirectory()) {
            return entries;
        }

        File[] files = modsDir.listFiles((dir, name) -> name.toLowerCase().endsWith(".jar") && !name.toLowerCase().endsWith(".disabled"));
        if (files == null) return entries;

        for (File file : files) {
            try {
                String sha256 = computeSHA256(file);
                boolean clientOnly = isClientOnlyMod(file.getName());
                entries.add(new ModEntry(file.getName(), sha256, file.length(), clientOnly));
            } catch (Exception e) {
                System.err.println("[MoonSync] Warning: Failed to hash " + file.getName() + ": " + e.getMessage());
            }
        }
        return entries;
    }

    public static String computeSHA256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream fis = new FileInputStream(file)) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = fis.read(buffer)) != -1) {
                digest.update(buffer, 0, n);
            }
        }
        byte[] hash = digest.digest();
        StringBuilder sb = new StringBuilder();
        for (byte b : hash) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    public static boolean isClientOnlyMod(String fileName) {
        String lower = fileName.toLowerCase();
        for (String clientMod : MANAGED_CLIENT_MODS) {
            if (lower.contains(clientMod)) {
                return true;
            }
        }
        return false;
    }
}

