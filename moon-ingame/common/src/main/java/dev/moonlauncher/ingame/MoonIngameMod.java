package dev.moonlauncher.ingame;

import net.fabricmc.api.ClientModInitializer;
import net.minecraft.client.Minecraft;

public class MoonIngameMod implements ClientModInitializer {

    @Override
    public void onInitializeClient() {
        Minecraft mc = Minecraft.getInstance();
        MoonIngameConfig.get().load(mc.gameDirectory);
        MoonIngameState.startLocalControlServer(mc.gameDirectory);
        System.out.println("[MoonInGame] Initialized True In-Game Mixin Addon (Press Right Shift for HUD Menu).");
    }
}

