package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonFairPlay;
import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Intercepts player camera turn ONLY while Freelook ([V]) is active so the
 * third-person camera rotates smoothly without altering player/packet yaw or pitch.
 */
@Mixin(Entity.class)
public class EntityMixin {
    @Inject(method = "turn(DD)V", at = @At("HEAD"), cancellable = true, require = 0)
    private void moon$freelookTurn(double yRot, double xRot, CallbackInfo ci) {
        Minecraft mc = Minecraft.getInstance();
        if ((Object) this == mc.player && MoonIngameState.freelookActive && MoonFairPlay.isFreelookAllowed(mc)) {
            MoonIngameState.updateFreelookAngles((float) (yRot * 0.15D), (float) (xRot * 0.15D));
            ci.cancel();
        }
    }
}

