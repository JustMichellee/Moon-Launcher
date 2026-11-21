package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonFairPlay;
import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Applies camera-only rotation during third-person Freelook without touching server movement/aim packets.
 */
@Mixin(Camera.class)
public abstract class CameraMixin {
    @Shadow
    protected abstract void setRotation(float yRot, float xRot);

    @Inject(
        method = "setup",
        at = @At(value = "INVOKE", target = "Lnet/minecraft/client/Camera;setRotation(FF)V", shift = At.Shift.AFTER),
        require = 0
    )
    private void moon$applyFreelookRotation(
        BlockGetter level,
        Entity entity,
        boolean detached,
        boolean thirdPersonReverse,
        float partialTick,
        CallbackInfo ci
    ) {
        Minecraft mc = Minecraft.getInstance();
        if (detached && MoonIngameState.freelookActive && MoonFairPlay.isFreelookAllowed(mc)) {
            this.setRotation(MoonIngameState.freelookYaw, MoonIngameState.freelookPitch);
        }
    }
}

