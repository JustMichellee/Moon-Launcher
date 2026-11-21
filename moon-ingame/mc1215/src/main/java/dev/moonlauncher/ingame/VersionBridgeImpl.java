package dev.moonlauncher.ingame;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.multiplayer.JoinMultiplayerScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.minecraft.world.effect.MobEffectInstance;

public class VersionBridgeImpl {
    public static int getFps(Minecraft mc) {
        return mc != null ? mc.getFps() : 0;
    }

    public static void sendChat(Minecraft mc, String msg) {
        if (mc != null && mc.player != null && mc.player.connection != null) {
            mc.player.connection.sendChat(msg);
        }
    }

    public static String getEffectName(MobEffectInstance inst) {
        return inst.getEffect().value().getDisplayName().getString();
    }

    public static void connectToServer(String host, int port, String name) {
        Minecraft mc = Minecraft.getInstance();
        String addr = host + ":" + port;
        if (mc.level != null) {
            mc.disconnect();
        }
        ServerData data = new ServerData(name, addr, ServerData.Type.OTHER);
        ConnectScreen.startConnecting(new JoinMultiplayerScreen(new TitleScreen()), mc, new ServerAddress(host, port), data, false, null);
    }
}

