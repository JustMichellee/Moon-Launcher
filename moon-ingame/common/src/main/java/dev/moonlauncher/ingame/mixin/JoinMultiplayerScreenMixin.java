package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonConfigScreen;
import dev.moonlauncher.ingame.UiBridgeImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.multiplayer.JoinMultiplayerScreen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(JoinMultiplayerScreen.class)
public class JoinMultiplayerScreenMixin {
    @Inject(method = "init", at = @At("TAIL"), require = 0)
    private void moon$addMultiplayerButton(CallbackInfo ci) {
        Screen self = (Screen) (Object) this;
        UiBridgeImpl.addBtn(self, 8, 8, 76, 20, Component.literal("Moon HUD"), btn -> {
            Minecraft.getInstance().setScreen(new MoonConfigScreen(self));
        });
    }
}

