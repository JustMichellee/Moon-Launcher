package dev.moonlauncher.ingame;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public abstract class MoonBaseScreen extends Screen {

    protected MoonBaseScreen(Component title) {
        super(title);
    }

    protected abstract void renderMoon(MoonDraw g, int mouseX, int mouseY, float partialTick);

    @Override
    public void render(PoseStack pose, int mouseX, int mouseY, float partialTick) {
        renderMoon(MoonDrawImpl.of(pose), mouseX, mouseY, partialTick);
        super.render(pose, mouseX, mouseY, partialTick);
    }
}

