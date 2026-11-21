package dev.moonlauncher.ingame;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;

public abstract class MoonBaseScreen extends UiBridgeImpl.BridgeScreen {

    protected MoonBaseScreen(Component title) {
        super(title);
    }

    protected abstract void renderMoon(MoonDraw g, int mouseX, int mouseY, float partialTick);

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partialTick) {
        renderMoon(MoonDrawImpl.of(g), mouseX, mouseY, partialTick);
        super.render(g, mouseX, mouseY, partialTick);
    }
}

