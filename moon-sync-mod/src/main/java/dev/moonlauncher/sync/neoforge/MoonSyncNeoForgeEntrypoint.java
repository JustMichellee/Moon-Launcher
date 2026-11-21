package dev.moonlauncher.sync.neoforge;

import dev.moonlauncher.sync.MoonSyncMod;
import java.io.File;
import net.neoforged.fml.common.Mod;

@Mod("moonsync")
public class MoonSyncNeoForgeEntrypoint {
    public MoonSyncNeoForgeEntrypoint() {
        MoonSyncMod.init(new File("."));
    }
}

