package dev.moonlauncher.sync.fabric;

import dev.moonlauncher.sync.MoonSyncMod;
import java.io.File;
import net.fabricmc.api.ClientModInitializer;

public class MoonSyncFabricEntrypoint implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        MoonSyncMod.init(new File("."));
    }
}

