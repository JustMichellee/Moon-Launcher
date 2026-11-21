package dev.moonlauncher.ingame;

import net.fabricmc.api.ClientModInitializer;

public class MoonFabricEntrypoint implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        MoonIngameMod.initClient();
    }
}

