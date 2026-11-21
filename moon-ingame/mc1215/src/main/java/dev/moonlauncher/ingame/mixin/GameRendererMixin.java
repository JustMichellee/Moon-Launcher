package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.Camera;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(GameRenderer.class)
public class GameRendererMixin {
    @Inject(method = "getFov", at = @At("RETURN"), cancellable = true, require = 0)
    private void moon$applyZoomFov(Camera camera, float partialTicks, boolean useFOVSetting, CallbackInfoReturnable<Float> cir) {
        if (MoonIngameState.zoomHeld) {
            cir.setReturnValue(cir.getReturnValue() * 0.28F);
        }
    }
}

