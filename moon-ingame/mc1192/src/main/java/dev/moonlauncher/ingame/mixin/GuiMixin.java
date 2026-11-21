package dev.moonlauncher.ingame.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import dev.moonlauncher.ingame.MoonDrawImpl;
import dev.moonlauncher.ingame.MoonHudRenderer;
import net.minecraft.client.gui.Gui;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public class GuiMixin {
    @Inject(method = "render", at = @At("TAIL"), require = 0)
    private void moon$renderHud(PoseStack poseStack, float partialTick, CallbackInfo ci) {
        MoonHudRenderer.render(MoonDrawImpl.of(poseStack));
    }
}

