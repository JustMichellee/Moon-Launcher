package dev.moonlauncher.ingame;

import net.minecraft.network.chat.Component;

public class MoonConfigScreen extends MoonBaseScreen {

    private final net.minecraft.client.gui.screens.Screen parent;

    public MoonConfigScreen(net.minecraft.client.gui.screens.Screen parent) {
        super(Component.literal("Moon Client In-Game Studio (Right Shift)"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        MoonIngameConfig cfg = MoonIngameConfig.get();
        int cx = this.width / 2;
        int y = 46;

        UiBridgeImpl.addBtn(this, cx - 155, y, 150, 22, toggleLabel("HUD Overlay", cfg.hudEnabled), btn -> {
            cfg.hudEnabled = !cfg.hudEnabled;
            cfg.save();
            btn.setMessage(toggleLabel("HUD Overlay", cfg.hudEnabled));
        });

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, toggleLabel("Keystrokes & CPS", cfg.keystrokesEnabled), btn -> {
            cfg.keystrokesEnabled = !cfg.keystrokesEnabled;
            cfg.save();
            btn.setMessage(toggleLabel("Keystrokes & CPS", cfg.keystrokesEnabled));
        });

        y += 26;
        UiBridgeImpl.addBtn(this, cx - 155, y, 150, 22, toggleLabel("Armor/Potion HUD", cfg.armorPotionsEnabled), btn -> {
            cfg.armorPotionsEnabled = !cfg.armorPotionsEnabled;
            cfg.save();
            btn.setMessage(toggleLabel("Armor/Potion HUD", cfg.armorPotionsEnabled));
        });

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, toggleLabel("Toggle Sprint", cfg.toggleSprint), btn -> {
            cfg.toggleSprint = !cfg.toggleSprint;
            cfg.save();
            btn.setMessage(toggleLabel("Toggle Sprint", cfg.toggleSprint));
        });

        y += 26;
        UiBridgeImpl.addBtn(this, cx - 155, y, 150, 22, toggleLabel("Toggle Sneak", cfg.toggleSneak), btn -> {
            cfg.toggleSneak = !cfg.toggleSneak;
            this.minecraft.options.toggleCrouch().set(cfg.toggleSneak);
            cfg.save();
            btn.setMessage(toggleLabel("Toggle Sneak", cfg.toggleSneak));
        });

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, toggleLabel("Fullbright", cfg.fullbright), btn -> {
            cfg.fullbright = !cfg.fullbright;
            cfg.save();
            btn.setMessage(toggleLabel("Fullbright", cfg.fullbright));
        });

        y += 26;
        boolean flLocked = !MoonFairPlay.isLocalOrSingleplayer(this.minecraft) && cfg.strictFairPlay && MoonFairPlay.isCompetitiveRestrictedServer(this.minecraft);
        UiBridgeImpl.addBtn(
            this,
            cx - 155,
            y,
            150,
            22,
            flLocked ? Component.literal("Freelook [V]: \u00a7eLOCKED") : toggleLabel("Freelook [V]", cfg.freelookEnabled),
            btn -> {
                if (flLocked) {
                    MoonIngameState.chatNotice(this.minecraft, "\u00a7e[Moon Fair-Play] Freelook dikunci otomatis di server kompetitif ini agar aman dari ban.");
                    return;
                }
                cfg.freelookEnabled = !cfg.freelookEnabled;
                cfg.save();
                btn.setMessage(toggleLabel("Freelook [V]", cfg.freelookEnabled));
            }
        );

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, toggleLabel("Fair-Play Guard", cfg.strictFairPlay), btn -> {
            cfg.strictFairPlay = !cfg.strictFairPlay;
            cfg.save();
            btn.setMessage(toggleLabel("Fair-Play Guard", cfg.strictFairPlay));
        });

        y += 26;
        UiBridgeImpl.addBtn(this, cx - 155, y, 150, 22, toggleLabel("Auto-GG", cfg.autoGg), btn -> {
            cfg.autoGg = !cfg.autoGg;
            cfg.save();
            btn.setMessage(toggleLabel("Auto-GG", cfg.autoGg));
        });

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, Component.literal("Edit HUD Layout"), btn -> {
            this.minecraft.setScreen(new MoonHudEditorScreen(this));
        });

        y += 26;
        UiBridgeImpl.addBtn(this, cx - 155, y, 150, 22, Component.literal("1-Click Share World (P2P)"), btn -> {
            this.minecraft.setScreen(null);
            MoonIngameState.shareWorldOneClick(true);
        });

        UiBridgeImpl.addBtn(this, cx + 5, y, 150, 22, Component.literal("Done"), btn -> {
            this.minecraft.setScreen(parent);
        });
    }

    private static Component toggleLabel(String name, boolean state) {
        return Component.literal(name + ": " + (state ? "\u00a7aON" : "\u00a7cOFF"));
    }

    @Override
    protected void renderMoon(MoonDraw g, int mouseX, int mouseY, float partialTick) {
        g.fill(0, 0, this.width, this.height, 0x88090D16);
        g.drawCentered(this.font, this.title, this.width / 2, 16, 0xFFFFFF);
        String subtitle = "\u00a77Zoom [C] • Freelook [V] • Menu [Right Shift] • " + MoonFairPlay.getServerSafetyLabel(this.minecraft);
        g.drawCentered(this.font, subtitle, this.width / 2, 30, 0x94A3B8);
    }
}
