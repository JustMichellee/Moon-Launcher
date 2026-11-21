package dev.moonlauncher.sync.forge;

import dev.moonlauncher.sync.MoonSyncMod;
import java.io.File;
import net.minecraftforge.fml.common.Mod;

@Mod("moonsync")
public class MoonSyncForgeEntrypoint {
    public MoonSyncForgeEntrypoint() {
        MoonSyncMod.init(new File("."));
    }
}

