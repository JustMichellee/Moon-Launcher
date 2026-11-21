package dev.moonlauncher.sync.forgelegacy;

import dev.moonlauncher.sync.MoonSyncMod;
import java.io.File;
import net.minecraftforge.fml.common.Mod;

@Mod(
    modid = "moonsync",
    name = "Moon Sync",
    version = "1.0.0",
    clientSideOnly = true,
    acceptableRemoteVersions = "*"
)
public class MoonSyncLegacyForgeMod {
    public MoonSyncLegacyForgeMod() {
        MoonSyncMod.init(new File("."));
    }
}

