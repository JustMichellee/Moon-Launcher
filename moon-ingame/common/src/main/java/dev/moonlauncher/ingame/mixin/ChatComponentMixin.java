package dev.moonlauncher.ingame.mixin;

import dev.moonlauncher.ingame.MoonIngameConfig;
import dev.moonlauncher.ingame.MoonIngameState;
import dev.moonlauncher.ingame.VersionBridgeImpl;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.ChatComponent;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ChatComponent.class)
public class ChatComponentMixin {
    @Inject(method = "addMessage(Lnet/minecraft/network/chat/Component;)V", at = @At("HEAD"), require = 0)
    private void moon$autoGg(Component msg, CallbackInfo ci) {
        if (!MoonIngameConfig.get().autoGg || msg == null) return;
        String raw = msg.getString();
        String text = raw.toLowerCase().trim();
        // Ignore player-typed chat messages to prevent Auto-GG chat baiting / spam mutes
        if (text.startsWith("<") || text.contains(": victory!") || text.contains(": game over!")) return;
        if (text.contains("victory!") || text.contains("game over!") || text.contains("1st killer") || text.contains("you won the game")) {
            long now = System.currentTimeMillis();
            if (now - MoonIngameState.lastAutoGgMs > 15000L) {
                MoonIngameState.lastAutoGgMs = now;
                Minecraft mc = Minecraft.getInstance();
                mc.execute(() -> {
                    VersionBridgeImpl.sendChat(mc, "gg");
                });
            }
        }
    }
}

