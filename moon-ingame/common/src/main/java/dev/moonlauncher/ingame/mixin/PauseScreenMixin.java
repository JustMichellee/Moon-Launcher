package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonConfigScreen;
import dev.moonlauncher.ingame.MoonIngameState;
import dev.moonlauncher.ingame.UiBridgeImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(PauseScreen.class)
public abstract class PauseScreenMixin {
    @Inject(method = "init", at = @At("TAIL"), require = 0)
    private void moon$addPauseButtons(CallbackInfo ci) {
        Screen self = (Screen) (Object) this;
        Minecraft mc = Minecraft.getInstance();
        int btnW = 112;
        int x = 8;
        int y = self.height - 54;

        if (mc.hasSingleplayerServer()) {
            UiBridgeImpl.addBtn(self, x, y, btnW, 20, Component.literal("Share World (P2P)"), btn -> {
                mc.setScreen(null);
                MoonIngameState.shareWorldOneClick(true);
            });
            y += 24;
        }
        UiBridgeImpl.addBtn(self, x, y, btnW, 20, Component.literal("Moon Client Menu"), btn -> {
            mc.setScreen(new MoonConfigScreen(self));
        });
    }
}

