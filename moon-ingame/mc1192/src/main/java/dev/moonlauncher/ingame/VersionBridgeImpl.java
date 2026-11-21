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
        if (mc == null || mc.fpsString == null) return 0;
        String s = mc.fpsString.trim();
        int sp = s.indexOf(' ');
        try {
            return Integer.parseInt(sp > 0 ? s.substring(0, sp) : s);
        } catch (Exception ignored) {
            return 0;
        }
    }

    public static void sendChat(Minecraft mc, String msg) {
        if (mc != null && mc.player != null) {
            mc.player.chatSigned(msg, null);
        }
    }

    public static String getEffectName(MobEffectInstance inst) {
        return inst.getEffect().getDisplayName().getString();
    }

    public static void connectToServer(String host, int port, String name) {
        Minecraft mc = Minecraft.getInstance();
        String addr = host + ":" + port;
        if (mc.level != null) {
            mc.level.disconnect();
            mc.clearLevel();
        }
        ServerData data = new ServerData(name, addr, false);
        ConnectScreen.startConnecting(new JoinMultiplayerScreen(new TitleScreen()), mc, new ServerAddress(host, port), data);
    }
}

