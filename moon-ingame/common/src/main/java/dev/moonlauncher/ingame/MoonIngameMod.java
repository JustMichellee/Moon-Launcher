package dev.moonlauncher.ingame;

import net.minecraft.client.Minecraft;

public class MoonIngameMod {

    private static volatile boolean initialized = false;

    public static void initClient() {
        if (initialized) return;
        initialized = true;
        Minecraft mc = Minecraft.getInstance();
        if (mc == null) return;
        MoonIngameConfig.get().load(mc.gameDirectory);
        MoonIngameState.startLocalControlServer(mc.gameDirectory);
        System.out.println("[MoonInGame] Initialized Fair-Play In-Game Mixin Addon (Press Right Shift for HUD Menu).");
    }
}
