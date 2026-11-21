package dev.moonlauncher.ingame;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.Collection;

public class MoonHudRenderer {

    public static int[] getTelemetryPos(int sw, int sh) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        int x = cfg.telemetryX >= 0 ? Math.min(cfg.telemetryX, Math.max(8, sw - 120)) : 8;
        int y = cfg.telemetryY >= 0 ? Math.min(cfg.telemetryY, Math.max(8, sh - 30)) : 8;
        return new int[] { x, y };
    }

    public static int[] getKeystrokesPos(int sw, int sh) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        int x = cfg.keystrokesX >= 0 ? Math.min(cfg.keystrokesX, Math.max(8, sw - 76)) : Math.max(8, sw - 78);
        int y = cfg.keystrokesY >= 0 ? Math.min(cfg.keystrokesY, Math.max(8, sh - 78)) : 8;
        return new int[] { x, y };
    }

    public static int[] getArmorPos(int sw, int sh) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        int x = cfg.armorX >= 0 ? Math.min(cfg.armorX, Math.max(8, sw - 140)) : 8;
        int y = cfg.armorY >= 0 ? Math.min(cfg.armorY, Math.max(68, sh - 16)) : Math.max(68, sh - 22);
        return new int[] { x, y };
    }

    public static void render(GuiGraphics g) {
        Minecraft mc = Minecraft.getInstance();
        MoonIngameConfig cfg = MoonIngameConfig.get();
        if (!cfg.hudEnabled || mc.player == null || mc.options.hideGui) return;
        if (mc.screen != null && !(mc.screen instanceof MoonConfigScreen)) return;
        renderModules(g, mc, mc.getWindow().getGuiScaledWidth(), mc.getWindow().getGuiScaledHeight());
    }

    public static void renderPreview(GuiGraphics g, int sw, int sh) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;
        renderModules(g, mc, sw, sh);
    }

    private static void renderModules(GuiGraphics g, Minecraft mc, int sw, int sh) {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        Font font = mc.font;
        Player player = mc.player;

        // 1. Core Telemetry Strip (FPS, Ping, Coords, Fair-Play / Freelook status, P2P Room)
        int[] tPos = getTelemetryPos(sw, sh);
        int x = tPos[0];
        int y = tPos[1];
        int fps = mc.getFps();
        int ping = -1;
        if (mc.getConnection() != null) {
            PlayerInfo info = mc.getConnection().getPlayerInfo(player.getUUID());
            if (info != null) ping = info.getLatency();
        }
        String xyz = String.format("%d / %d / %d", player.getBlockX(), player.getBlockY(), player.getBlockZ());
        String line1 = "\u00a7bMOON\u00a7r  FPS: \u00a7a" + fps + (ping >= 0 ? "  \u00a7rPing: \u00a7e" + ping + "ms" : "");
        String line2 = "XYZ: \u00a7f" + xyz
            + (cfg.toggleSprint ? "  \u00a7a[Sprint]" : "")
            + (MoonIngameState.freelookActive ? "  \u00a7b[Freelook]" : "");

        drawBoxedText(g, font, x, y, line1, line2, MoonIngameState.sharingWorld && !MoonIngameState.activeRoomCode.isEmpty()
            ? "\u00a7dP2P Room: " + MoonIngameState.activeRoomCode : null);

        // 2. Keystrokes + CPS Counter
        if (cfg.keystrokesEnabled) {
            int[] kPos = getKeystrokesPos(sw, sh);
            int kx = kPos[0];
            int ky = kPos[1];
            drawKey(g, font, kx + 24, ky, 22, 18, "W", mc.options.keyUp.isDown());
            drawKey(g, font, kx, ky + 20, 22, 18, "A", mc.options.keyLeft.isDown());
            drawKey(g, font, kx + 24, ky + 20, 22, 18, "S", mc.options.keyDown.isDown());
            drawKey(g, font, kx + 48, ky + 20, 22, 18, "D", mc.options.keyRight.isDown());
            drawKey(g, font, kx, ky + 40, 34, 18, "L:" + MoonIngameState.getLmbCps(), mc.options.keyAttack.isDown());
            drawKey(g, font, kx + 36, ky + 40, 34, 18, "R:" + MoonIngameState.getRmbCps(), mc.options.keyUse.isDown());
            drawKey(g, font, kx, ky + 60, 70, 14, "SPACE", mc.options.keyJump.isDown());
        }

        // 3. Armor Durability + Totem Counter + Potion Timers
        if (cfg.armorPotionsEnabled) {
            int[] aPos = getArmorPos(sw, sh);
            int ax = aPos[0];
            int ay = aPos[1];

            int totems = 0;
            for (ItemStack st : player.getInventory().items) {
                if (st.is(Items.TOTEM_OF_UNDYING)) totems += st.getCount();
            }
            for (ItemStack st : player.getInventory().offhand) {
                if (st.is(Items.TOTEM_OF_UNDYING)) totems += st.getCount();
            }
            if (totems > 0) {
                g.fill(ax, ay - 2, ax + 68, ay + 12, 0x880B1020);
                g.drawString(font, "\u00a76Totems: \u00a7f" + totems, ax + 4, ay + 1, 0xFFFFFF);
                ay -= 16;
            }

            for (ItemStack armor : player.getInventory().armor) {
                if (armor.isEmpty() || !armor.isDamageableItem()) continue;
                int rem = armor.getMaxDamage() - armor.getDamageValue();
                int pct = Math.max(0, (rem * 100) / Math.max(1, armor.getMaxDamage()));
                String color = pct > 50 ? "\u00a7a" : (pct > 20 ? "\u00a7e" : "\u00a7c");
                String label = armor.getHoverName().getString();
                if (label.length() > 12) label = label.substring(0, 12);
                g.fill(ax, ay - 2, ax + 126, ay + 12, 0x880B1020);
                g.drawString(font, label + " " + color + rem, ax + 4, ay + 1, 0xFFFFFF);
                ay -= 15;
            }

            Collection<MobEffectInstance> effects = player.getActiveEffects();
            int count = 0;
            for (MobEffectInstance eff : effects) {
                if (count++ >= 4) break;
                String ename = VersionBridgeImpl.getEffectName(eff);
                if (ename.length() > 14) ename = ename.substring(0, 14);
                int sec = Math.max(0, eff.getDuration() / 20);
                String tStr = String.format("%d:%02d", sec / 60, sec % 60);
                g.fill(ax, ay - 2, ax + 140, ay + 12, 0x88131A2E);
                g.drawString(font, "\u00a7d" + ename + " \u00a7f" + tStr, ax + 4, ay + 1, 0xFFFFFF);
                ay -= 15;
            }
        }
    }

    private static void drawBoxedText(GuiGraphics g, Font font, int x, int y, String l1, String l2, String l3) {
        int w = Math.max(font.width(l1), font.width(l2));
        if (l3 != null) w = Math.max(w, font.width(l3));
        int rows = l3 != null ? 3 : 2;
        g.fill(x - 3, y - 3, x + w + 6, y + rows * 11 + 3, 0x880B1020);
        g.drawString(font, l1, x + 1, y, 0xFFFFFF);
        g.drawString(font, l2, x + 1, y + 11, 0xE2E8F0);
        if (l3 != null) g.drawString(font, l3, x + 1, y + 22, 0xC4B5FD);
    }

    private static void drawKey(GuiGraphics g, Font font, int x, int y, int w, int h, String label, boolean pressed) {
        int bg = pressed ? 0xCC7C3AED : 0x880F172A;
        int fg = pressed ? 0xFFFFFF : 0xCBD5E1;
        g.fill(x, y, x + w, y + h, bg);
        g.renderOutline(x, y, w, h, pressed ? 0xFFA78BFA : 0x66475569);
        int tw = font.width(label);
        g.drawString(font, label, x + (w - tw) / 2, y + (h - 8) / 2, fg);
    }
}

