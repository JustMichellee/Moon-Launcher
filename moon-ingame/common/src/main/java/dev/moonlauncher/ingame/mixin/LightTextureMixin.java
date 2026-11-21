package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonIngameConfig;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.world.level.dimension.DimensionType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(LightTexture.class)
public class LightTextureMixin {
    @Inject(method = "getBrightness", at = @At("HEAD"), cancellable = true, require = 0)
    private static void moon$fullbright(DimensionType type, int lightLevel, CallbackInfoReturnable<Float> cir) {
        if (MoonIngameConfig.get().fullbright) {
            cir.setReturnValue(1.0F);
        }
    }
}

