<div align="center">

```ascii
  __  __                       _                             _               
 |  \/  | ___   ___  _ __     | |    __ _ _   _ _ __   ___| |__   ___ _ __ 
 | |\/| |/ _ \ / _ \| '_ \    | |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|
 | |  | | (_) | (_) | | | |   | |__| (_| | |_| | | | | (__| | | |  __/ |   
 |_|  |_|\___/ \___/|_| |_|   |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|   
```

# 🌙 Moon Launcher & DeadZone Modpack
### *Official Collaborative Project Edition*

**A high-performance CLI Minecraft Launcher Studio paired with the curated DeadZone Zombie Apocalypse Modpack.**

[![Collaboration](https://img.shields.io/badge/Collaborators-Epithap%20x%20alfianzidan321--cmd-blueviolet?style=for-the-badge&logo=github)](https://github.com/alfianzidan321-cmd/Moon-Launcher)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Minecraft](https://img.shields.io/badge/Minecraft-1.20.1%20Forge-5B8C33?style=for-the-badge&logo=minecraft&logoColor=white)](https://minecraft.net)
[![Mods Count](https://img.shields.io/badge/Installed_Mods-175+-E04E39?style=for-the-badge&logo=curseforge&logoColor=white)](mods/)
[![Discord RPC](https://img.shields.io/badge/Discord-Rich_Presence_V2-5865F2?style=for-the-badge&logo=discord&logoColor=white)](Moon-Launcher/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/alfianzidan321-cmd">
        <img src="https://github.com/alfianzidan321-cmd.png?size=100" width="100px;" alt="alfianzidan321-cmd"/><br />
        <sub><b>alfianzidan321-cmd</b></sub>
      </a><br />
      <sub>👑 Repo Owner & Modpack Lead</sub>
    </td>
    <td align="center">
      <a href="https://github.com/Epithap">
        <img src="https://github.com/Epithap.png?size=100" width="100px;" alt="Epithap"/><br />
        <sub><b>Epithap</b></sub>
      </a><br />
      <sub>💻 Core Developer & Launcher Architecture</sub>
    </td>
  </tr>
</table>

</div>

---

## 📖 Tentang Proyek

Repositori ini menggabungkan dua hal utama dalam satu paket instalasi yang praktis dan langsung siap dimainkan:

1. **`Moon-Launcher/`** — Launcher Minecraft berbasis CLI yang super ringan, tanpa bloatware/iklan, dengan fitur diagnosa memori cerdas dan integrasi Discord Rich Presence native.
2. **`mods/`** — Koleksi 175+ mod curated untuk **Minecraft 1.20.1 Forge (DeadZone)** yang mencakup senjata modern (TaCZ), zombie apocalypse AI, cuaca ekstrem, ambient sound imersif, serta optimasi performa tinggi (Embeddium, Canary, ModernFix).

---

## 🌟 Fitur Utama

### 🎮 Moon Launcher Engine
- **Zero Third-Party Python Libraries**: Berjalan mulus di Python murni tanpa perlu ribet `pip install`.
- **Dynamic Discord Rich Presence (RPC)**:
  - 🏠 **In Launcher**: Menampilkan status sedang di studio dan profil modpack aktif.
  - 🕹️ **In-Game Singleplayer**: Membaca nama dunia (`World: New World`) secara otomatis via NBT level data.
  - 🌐 **Mabar / Multiplayer**: Deteksi otomatis koneksi server, LAN, maupun jaringan VPN:
    - `Mabar (Radmin): 26.79.166.199:6767`
    - `Mabar (LAN): 192.168.x.x:port`
    - `Mabar (Hamachi): 25.x.x.x:port`
  - 👤 **Custom Skin & Head Avatar**: Avatar 3D kepala pemain langsung tampil di status Discord.
- **Interactive Terminal UI**: Dashboard CLI dengan border anti-pecah, pemilih RAM instan, dan diagnostik Java 17 runtime.

### 🧟 DeadZone Modpack (175+ Mods)
- **Combat & Arsenal**: Timeless and Classics Zero (TaCZ), Expanded Arsenal, Modern Kinetic Guns, Pehkui.
- **Atmosphere & Survival**: Cold Sweat (suhu tubuh), Thirst Was Taken (kehausan), Zombie Awareness, Enhanced AI.
- **World Generation**: Biomes O' Plenty, Terralith, Tectonic, Dynamic Trees, Better Villages, Towns and Towers.
- **Performance Beast**: ModernFix, Embeddium (Sodium port), Canary (Lithium port), FerriteCore, ImmediatelyFast, Entity Culling.

---

## 📁 Struktur Repositori

```text
Moon-Launcher/
│
├── Moon-Launcher/            # Core source code launcher
│   ├── launcher.py           # Engine Moon Launcher & Discord IPC
│   ├── Moon Launcher.bat     # Runner internal launcher
│   └── launcher_config.json  # File konfigurasi default (RAM, User, Resolusi)
│
├── mods/                     # 175+ Mod jar Minecraft 1.20.1 Forge
│   ├── tacz-1.20.1-*.jar
│   ├── embeddium-*.jar
│   ├── modernfix-*.jar
│   └── ... (170+ mods lainnya via Git LFS)
│
├── Moon Launcher.bat         # 1-Click Runner utama (Deteksi otomatis Python)
├── launcher.py               # Entrypoint script
├── launcher_config.json      # Konfigurasi aktif
├── .gitattributes            # Konfigurasi Git LFS untuk mod jar
├── .gitignore                # Filter saves, logs, dan cache lokal
├── LICENSE                   # MIT Open-Source License
└── README.md                 # Dokumentasi proyek kolaborasi
```

---

## 🚀 Cara Pemasangan & Bermain

### Prasyarat
- Sistem Operasi: **Windows 10 / 11**
- **Python 3.8+** (Centang *"Add python.exe to PATH"* saat instalasi).
- **Java 17 (64-bit)** (Rekomendasi: Microsoft OpenJDK 17 atau Eclipse Temurin).
- **Git** dengan dukungan **Git LFS** terpasang.

### Langkah Cepat
1. **Clone repositori beserta file mod:**
   ```bash
   git clone https://github.com/alfianzidan321-cmd/Moon-Launcher.git
   cd Moon-Launcher
   git lfs pull
   ```

2. **Jalankan Launcher:**
   Cukup klik 2x pada file:
   ```cmd
   Moon Launcher.bat
   ```

3. **Perintah Cepat di Terminal:**
   ```text
   /setting user <NamaKamu>    -> Ganti nama player
   /setting ram 8              -> Atur alokasi RAM (misal 8 GB)
   /status                     -> Cek kelengkapan Java & Mod
   /play                       -> Mulai game!
   ```

---

## ⌨️ Daftar Perintah Interaktif

| Perintah | Deskripsi |
|---|---|
| `/play` | Meluncurkan Minecraft dengan modpack DeadZone |
| `/status` | Cek diagnosa sistem (Java, RAM, Mod terpasang, Discord RPC) |
| `/mods` | Menampilkan seluruh daftar 175 mod yang terpasang |
| `/version` | Beralih profil versi Minecraft / Modpack |
| `/setting` | Masuk ke menu pengaturan interaktif |
| `/setting ram <gb>` | Shortcut ganti RAM (contoh: `/setting ram 10`) |
| `/setting user <nama>` | Shortcut ganti nickname pemain |
| `/help` | Menampilkan bantuan perintah |
| `/exit` | Menutup launcher |

---

## 👥 Tim Kolaborasi & Kredit

Proyek ini terwujud berkat kolaborasi erat antara:
- **[alfianzidan321-cmd](https://github.com/alfianzidan321-cmd)** — Penggagas proyek, kurasi & balancing modpack DeadZone, arsitektur gameplay.
- **[Epithap](https://github.com/Epithap)** — Arsitektur core Moon Launcher, sistem Discord Rich Presence, automasi CLI, dan integrasi skin.

---

## 📜 Lisensi

Proyek ini berada di bawah lisensi terbuka **[MIT License](LICENSE)**. Bebas digunakan, dikembangkan, dan dimainkan bersama teman-teman!
