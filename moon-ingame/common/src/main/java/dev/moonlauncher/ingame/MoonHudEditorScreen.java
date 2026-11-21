package dev.moonlauncher.ingame;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class MoonHudEditorScreen extends MoonBaseScreen {

    private final Screen parent;
    private int dragging = 0; // 1=telemetry, 2=keystrokes, 3=armor
    private int dragOffsetX = 0;
    private int dragOffsetY = 0;

    public MoonHudEditorScreen(Screen parent) {
        super(Component.literal("Moon HUD Position Editor (Drag Boxes)"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int cx = this.width / 2;
        int by = this.height - 32;
        UiBridgeImpl.addBtn(this, cx - 155, by, 150, 20, Component.literal("Reset Default Layout"), btn -> {
            MoonIngameConfig cfg = MoonIngameConfig.get();
            cfg.telemetryX = -1;
            cfg.telemetryY = -1;
            cfg.keystrokesX = -1;
            cfg.keystrokesY = -1;
            cfg.armorX = -1;
            cfg.armorY = -1;
            cfg.save();
        });

        UiBridgeImpl.addBtn(this, cx + 5, by, 150, 20, Component.literal("Save & Back"), btn -> {
            MoonIngameConfig.get().save();
            this.minecraft.setScreen(parent);
        });
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (button == 0) {
            int sw = this.width;
            int sh = this.height;
            int[] tPos = MoonHudRenderer.getTelemetryPos(sw, sh);
            int[] kPos = MoonHudRenderer.getKeystrokesPos(sw, sh);
            int[] aPos = MoonHudRenderer.getArmorPos(sw, sh);

            if (inside(mouseX, mouseY, tPos[0] - 4, tPos[1] - 4, 155, 36)) {
                dragging = 1;
                dragOffsetX = (int) mouseX - tPos[0];
                dragOffsetY = (int) mouseY - tPos[1];
                return true;
            }
            if (inside(mouseX, mouseY, kPos[0], kPos[1], 72, 76)) {
                dragging = 2;
                dragOffsetX = (int) mouseX - kPos[0];
                dragOffsetY = (int) mouseY - kPos[1];
                return true;
            }
            if (inside(mouseX, mouseY, aPos[0], aPos[1] - 64, 144, 78)) {
                dragging = 3;
                dragOffsetX = (int) mouseX - aPos[0];
                dragOffsetY = (int) mouseY - aPos[1];
                return true;
            }
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }

    @Override
    public boolean mouseDragged(double mouseX, double mouseY, int button, double dragX, double dragY) {
        if (button == 0 && dragging != 0) {
            MoonIngameConfig cfg = MoonIngameConfig.get();
            int nx = clamp((int) mouseX - dragOffsetX, 6, Math.max(12, this.width - 80));
            int ny = clamp((int) mouseY - dragOffsetY, 6, Math.max(12, this.height - 20));
            if (dragging == 1) {
                cfg.telemetryX = nx;
                cfg.telemetryY = ny;
            } else if (dragging == 2) {
                cfg.keystrokesX = nx;
                cfg.keystrokesY = ny;
            } else if (dragging == 3) {
                cfg.armorX = nx;
                cfg.armorY = clamp(ny, 68, Math.max(70, this.height - 16));
            }
            return true;
        }
        return super.mouseDragged(mouseX, mouseY, button, dragX, dragY);
    }

    @Override
    public boolean mouseReleased(double mouseX, double mouseY, int button) {
        if (button == 0 && dragging != 0) {
            dragging = 0;
            MoonIngameConfig.get().save();
            return true;
        }
        return super.mouseReleased(mouseX, mouseY, button);
    }

    @Override
    protected void renderMoon(MoonDraw g, int mouseX, int mouseY, float partialTick) {
        g.fill(0, 0, this.width, this.height, 0x66090D16);
        g.drawCentered(this.font, "\u00a7bDrag HUD Boxes to Reposition • Click Save & Back", this.width / 2, 12, 0xFFFFFF);

        int[] tPos = MoonHudRenderer.getTelemetryPos(this.width, this.height);
        int[] kPos = MoonHudRenderer.getKeystrokesPos(this.width, this.height);
        int[] aPos = MoonHudRenderer.getArmorPos(this.width, this.height);

        drawHandle(g, tPos[0] - 4, tPos[1] - 4, 155, 36, "Telemetry HUD", dragging == 1);
        drawHandle(g, kPos[0] - 2, kPos[1] - 2, 74, 78, "Keystrokes + CPS", dragging == 2);
        drawHandle(g, aPos[0] - 2, aPos[1] - 64, 146, 80, "Armor / Potions / Totems", dragging == 3);

        Minecraft mc = Minecraft.getInstance();
        if (mc.player != null) {
            MoonHudRenderer.renderPreview(g, this.width, this.height);
        }
    }

    private void drawHandle(MoonDraw g, int x, int y, int w, int h, String label, boolean active) {
        g.fill(x, y, x + w, y + h, active ? 0x447C3AED : 0x331E293B);
        g.outline(x, y, w, h, active ? 0xFFA78BFA : 0xFF38BDF8);
        g.drawString(this.font, "\u00a7b" + label, x + 3, Math.max(2, y - 10), 0xE2E8F0);
    }

    private static boolean inside(double mx, double my, int x, int y, int w, int h) {
        return mx >= x && mx <= x + w && my >= y && my <= y + h;
    }

    private static int clamp(int v, int lo, int hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}
