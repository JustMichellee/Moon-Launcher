package dev.moonlauncher.sync;

import java.awt.Color;
import java.awt.Desktop;
import java.awt.Graphics2D;
import java.awt.GraphicsEnvironment;
import java.awt.Image;
import java.awt.MenuItem;
import java.awt.PopupMenu;
import java.awt.SystemTray;
import java.awt.Toolkit;
import java.awt.TrayIcon;
import java.awt.datatransfer.StringSelection;
import java.awt.image.BufferedImage;
import java.net.URI;

/**
 * Headless-safe desktop tray companion for quick access to the Moon Client Hub
 * while Minecraft is running (Friends, Multiplayer Host/Join, Mod Sync, Waypoints).
 */
public class MoonCompanionUI {

    private static TrayIcon trayIcon = null;

    public static void attachTray(final MoonClientContext ctx, final MoonCloudClient cloud, final MoonCompanionServer server) {
        if (GraphicsEnvironment.isHeadless() || server == null || server.getPort() <= 0) {
            return;
        }
        try {
            if (!SystemTray.isSupported()) {
                return;
            }
            SystemTray tray = SystemTray.getSystemTray();
            if (trayIcon != null) {
                tray.remove(trayIcon);
            }

            PopupMenu menu = new PopupMenu();
            MenuItem openItem = new MenuItem("Open Moon Client Hub (" + ctx.moonId + ")");
            openItem.addActionListener(e -> openHubInBrowser(server.getUrl()));

            MenuItem copyItem = new MenuItem("Copy My Moon ID: " + ctx.moonId);
            copyItem.addActionListener(e -> copyToClipboard(ctx.moonId));

            MenuItem syncItem = new MenuItem("Sync Friends & Presence");
            syncItem.addActionListener(e -> new Thread(() -> {
                cloud.upsertPlayerAndPresence(false);
                cloud.syncFriendsAndPresence();
            }, "MoonTraySync").start());

            menu.add(openItem);
            menu.add(copyItem);
            menu.add(syncItem);

            trayIcon = new TrayIcon(createMoonBadgeImage(), "Moon Client Companion • " + ctx.moonId, menu);
            trayIcon.setImageAutoSize(true);
            trayIcon.addActionListener(e -> openHubInBrowser(server.getUrl()));
            tray.add(trayIcon);
        } catch (Throwable ignored) {
            // Safely ignore on restricted window managers / headless JREs
        }
    }

    public static void detachTray() {
        try {
            if (trayIcon != null && SystemTray.isSupported()) {
                SystemTray.getSystemTray().remove(trayIcon);
                trayIcon = null;
            }
        } catch (Throwable ignored) {}
    }

    public static void openHubInBrowser(String url) {
        if (url == null || url.isEmpty() || GraphicsEnvironment.isHeadless()) return;
        try {
            if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().browse(new URI(url));
            }
        } catch (Throwable ignored) {}
    }

    public static void copyToClipboard(String text) {
        if (text == null || GraphicsEnvironment.isHeadless()) return;
        try {
            Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(text), null);
        } catch (Throwable ignored) {}
    }

    private static Image createMoonBadgeImage() {
        BufferedImage img = new BufferedImage(16, 16, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = img.createGraphics();
        g.setColor(new Color(124, 58, 237));
        g.fillOval(1, 1, 14, 14);
        g.setColor(new Color(241, 245, 249));
        g.fillOval(4, 3, 8, 9);
        g.setColor(new Color(124, 58, 237));
        g.fillOval(7, 3, 7, 8);
        g.dispose();
        return img;
    }
}

