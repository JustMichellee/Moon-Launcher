package dev.moonlauncher.ingame;

import net.minecraft.client.gui.Font;
import net.minecraft.network.chat.Component;

/**
 * Lightweight version-agnostic drawing surface abstracting PoseStack (1.19.2)
 * and GuiGraphics (1.20+).
 */
public interface MoonDraw {
    void fill(int x1, int y1, int x2, int y2, int color);

    default void outline(int x, int y, int w, int h, int color) {
        if (w <= 0 || h <= 0) return;
        fill(x, y, x + w, y + 1, color);
        fill(x, y + h - 1, x + w, y + h, color);
        fill(x, y, x + 1, y + h, color);
        fill(x + w - 1, y, x + w, y + h, color);
    }

    void drawString(Font font, String text, int x, int y, int color);

    void drawCentered(Font font, String text, int cx, int y, int color);

    void drawCentered(Font font, Component text, int cx, int y, int color);
}

