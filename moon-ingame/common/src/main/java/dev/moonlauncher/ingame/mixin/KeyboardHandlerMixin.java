package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonConfigScreen;
import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.KeyboardHandler;
import net.minecraft.client.Minecraft;
import org.lwjgl.glfw.GLFW;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(KeyboardHandler.class)
public class KeyboardHandlerMixin {
    @Inject(method = "keyPress", at = @At("HEAD"), require = 0)
    private void moon$onKey(long window, int key, int scancode, int action, int mods, CallbackInfo ci) {
        Minecraft mc = Minecraft.getInstance();
        if (window != mc.getWindow().getWindow()) return;

        if (key == GLFW.GLFW_KEY_RIGHT_SHIFT && action == GLFW.GLFW_PRESS && mc.screen == null && mc.player != null) {
            mc.execute(() -> mc.setScreen(new MoonConfigScreen(null)));
        }
        if (key == GLFW.GLFW_KEY_C) {
            if (action == GLFW.GLFW_PRESS && mc.screen == null) {
                MoonIngameState.zoomHeld = true;
            } else if (action == GLFW.GLFW_RELEASE) {
                MoonIngameState.zoomHeld = false;
            }
        }
        if (key == GLFW.GLFW_KEY_V) {
            if (action == GLFW.GLFW_PRESS && mc.screen == null && mc.player != null) {
                mc.execute(() -> MoonIngameState.startFreelook(mc));
            } else if (action == GLFW.GLFW_RELEASE) {
                mc.execute(() -> MoonIngameState.stopFreelook(mc));
            }
        }
    }
}

