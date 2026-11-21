package dev.moonlauncher.ingame;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiComponent;
import net.minecraft.network.chat.Component;

public class MoonDrawImpl implements MoonDraw {

    private final PoseStack pose;

    private MoonDrawImpl(PoseStack pose) {
        this.pose = pose;
    }

    public static MoonDraw of(PoseStack pose) {
        return new MoonDrawImpl(pose);
    }

    @Override
    public void fill(int x1, int y1, int x2, int y2, int color) {
        GuiComponent.fill(pose, x1, y1, x2, y2, color);
    }

    @Override
    public void drawString(Font font, String text, int x, int y, int color) {
        font.drawShadow(pose, text, x, y, color);
    }

    @Override
    public void drawCentered(Font font, String text, int cx, int y, int color) {
        GuiComponent.drawCenteredString(pose, font, text, cx, y, color);
    }

    @Override
    public void drawCentered(Font font, Component text, int cx, int y, int color) {
        GuiComponent.drawCenteredString(pose, font, text, cx, y, color);
    }
}

