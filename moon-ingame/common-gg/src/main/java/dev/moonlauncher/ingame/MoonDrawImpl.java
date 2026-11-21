package dev.moonlauncher.ingame;

import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;

public class MoonDrawImpl implements MoonDraw {

    private final GuiGraphics g;

    private MoonDrawImpl(GuiGraphics g) {
        this.g = g;
    }

    public static MoonDraw of(GuiGraphics g) {
        return new MoonDrawImpl(g);
    }

    @Override
    public void fill(int x1, int y1, int x2, int y2, int color) {
        g.fill(x1, y1, x2, y2, color);
    }

    @Override
    public void drawString(Font font, String text, int x, int y, int color) {
        g.drawString(font, text, x, y, color);
    }

    @Override
    public void drawCentered(Font font, String text, int cx, int y, int color) {
        g.drawCenteredString(font, text, cx, y, color);
    }

    @Override
    public void drawCentered(Font font, Component text, int cx, int y, int color) {
        g.drawCenteredString(font, text, cx, y, color);
    }
}

