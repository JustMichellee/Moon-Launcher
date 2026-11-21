package dev.moonlauncher.ingame;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;

import java.lang.reflect.Method;
import java.util.function.Consumer;

public final class UiBridgeImpl {
    private static Method addWidgetMethod;

    private UiBridgeImpl() {}

    public static Button addBtn(Screen screen, int x, int y, int w, int h, Component label, Consumer<Button> onPress) {
        Button btn = Button.builder(label, onPress::accept).bounds(x, y, w, h).build();
        if (screen instanceof MoonBaseScreen) {
            ((MoonBaseScreen) screen).addBridgeButton(btn);
            return btn;
        }
        try {
            if (addWidgetMethod == null) {
                try {
                    addWidgetMethod = ObfuscationReflectionHelper.findMethod(Screen.class, "m_142416_", GuiEventListener.class);
                } catch (Throwable ignored) {
                    addWidgetMethod = Screen.class.getDeclaredMethod("addRenderableWidget", GuiEventListener.class);
                }
                addWidgetMethod.setAccessible(true);
            }
            addWidgetMethod.invoke(screen, btn);
        } catch (Throwable ignored) {}
        return btn;
    }

    public static abstract class BridgeScreen extends Screen {
        protected BridgeScreen(Component title) {
            super(title);
        }

        void addBridgeButton(Button btn) {
            this.addRenderableWidget(btn);
        }
    }
}

