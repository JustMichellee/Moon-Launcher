package dev.moonlauncher.ingame;

import dev.moonlauncher.ingame.mixin.ScreenAccessor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

import java.util.function.Consumer;

public final class UiBridgeImpl {
    private UiBridgeImpl() {}

    public static Button addBtn(Screen screen, int x, int y, int w, int h, Component label, Consumer<Button> onPress) {
        Button btn = Button.builder(label, onPress::accept).bounds(x, y, w, h).build();
        return ((ScreenAccessor) screen).moon$addRenderableWidget(btn);
    }
}

