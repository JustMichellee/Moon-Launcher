package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonIngameConfig;
import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public class MinecraftMixin {
    @Inject(method = "tick", at = @At("HEAD"), require = 0)
    private void moon$onTick(CallbackInfo ci) {
        Minecraft mc = (Minecraft) (Object) this;
        MoonIngameState.onClientTick(mc);
    }
}

