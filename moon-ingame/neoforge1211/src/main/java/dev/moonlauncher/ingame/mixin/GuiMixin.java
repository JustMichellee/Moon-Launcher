package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonDrawImpl;
import dev.moonlauncher.ingame.MoonHudRenderer;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public class GuiMixin {
    @Inject(method = "render", at = @At("TAIL"), require = 0)
    private void moon$renderHud(GuiGraphics guiGraphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        MoonHudRenderer.render(MoonDrawImpl.of(guiGraphics));
    }
}

