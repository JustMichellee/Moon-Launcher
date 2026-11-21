package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonConfigScreen;
import dev.moonlauncher.ingame.MoonIngameState;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
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
            ((ScreenAccessor) self).moon$addRenderableWidget(
                Button.builder(Component.literal("Share World (P2P)"), btn -> {
                    mc.setScreen(null);
                    MoonIngameState.shareWorldOneClick(true);
                }).bounds(x, y, btnW, 20).build()
            );
            y += 24;
        }
        ((ScreenAccessor) self).moon$addRenderableWidget(
            Button.builder(Component.literal("Moon Client Menu"), btn -> {
                mc.setScreen(new MoonConfigScreen(self));
            }).bounds(x, y, btnW, 20).build()
        );
    }
}

