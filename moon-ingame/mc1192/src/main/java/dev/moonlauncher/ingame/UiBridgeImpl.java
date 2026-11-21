package dev.moonlauncher.ingame;

import dev.moonlauncher.ingame.mixin.ScreenAccessor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

import java.util.function.Consumer;

public final class UiBridgeImpl {
    private UiBridgeImpl() {}

    public static Button addBtn(Screen screen, int x, int y, int w, int h, Component label, Consumer<Button> onPress) {
        Button btn = new Button(x, y, w, h, label, onPress::accept);
        return ((ScreenAccessor) screen).moon$addRenderableWidget(btn);
    }
}

