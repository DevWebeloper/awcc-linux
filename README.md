# 👽 AWCC for Linux (Alienware Command Center)

[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20SteamOS%20%7C%20CachyOS-orange.svg)](#)
[![Decky Loader: v3+](https://img.shields.io/badge/Decky%20Loader-v3%2B-purple.svg)](#)
[![Interface: GTK4 / Libadwaita](https://img.shields.io/badge/GUI-GTK4%20%2F%20Libadwaita-brightgreen.svg)](#)

A modern, native open-source alternative to **Alienware Command Center (AWCC)** built for Linux, SteamOS, and Gamescope. 

Provides granular power, thermal, acoustic, and CPU boost controls through both a **Decky Loader quick-access plugin** and a native **GTK4 / Libadwaita desktop application**.

---

## ✨ Features

* **⚡ Power Saver (Eco / Cool Mode)**:
  Instantly switches `power-saver` profiles and lowers AMD/Intel Energy Performance Preference (`EPP`) to tame high idling temperatures and keep laptop chassis cool to the touch.
* **🚀 CPU Turbo Boost Switch**:
  Toggle off CPU turbo boost with one click to lock cores at base frequency (e.g. 3.00 GHz on Ryzen 9 7845HX), eliminating aggressive temperature spikes and jet-engine fan noise.
* **🎮 Full ACPI Platform Profiles**:
  Quick selection across all Alienware firmware profiles:
  * `Performance (G-Mode)`: Maximum clocks and aggressive fan cooling tables
  * `Balanced Performance`: Gaming performance headroom with adaptive acoustic control
  * `Balanced`: Optimal daily balance
  * `Quiet`: Silent operation with acoustic throttling
  * `Cool`: Chassis surface cooling
  * `Power Saver`: Maximum battery and minimum heat
* **📊 Live Telemetry**:
  Real-time CPU and GPU sensor temperature monitoring alongside 4-zone fan RPM indicators (`alienware-wmi` / `dell_smm`).
* **🕹️ Decky Loader Integration**:
  Quick Access menu companion for Steam Deck / Gamescope gaming mode.

---

## 📂 Repository Structure

```
awcc-linux/
├── main.py                     # Decky Loader Python backend daemon
├── plugin.json                 # Decky Loader manifest
├── package.json                # Decky Loader package definition
├── dist/
│   └── index.js                # Decky Loader React / DFL frontend
├── gui/
│   ├── alienware_adwaita_app.py # GTK4 + Libadwaita Desktop Control Center
│   ├── run_gui.sh              # Application runner
│   ├── alienware-mode-control.desktop
│   └── alienware-mode-control.svg
├── system/
│   ├── aliencontrol-helper     # Sudoers helper for hardware & sysfs writes
│   ├── 99-cpu-boost.rules      # Udev rules for boost & platform profile permissions
│   └── alienware-gamescope-profile.service
├── install.sh                  # One-step automated installer
└── README.md
```

---

## 🚀 Installation

### Automated Install

```bash
git clone https://github.com/DevWebeloper/awcc-linux.git
cd awcc-linux
chmod +x install.sh
sudo ./install.sh
```

The installer will:
1. Install `/usr/local/bin/aliencontrol-helper` and configure passwordless sudo access.
2. Install udev permissions for hardware nodes.
3. Deploy the Decky Loader plugin into `~/homebrew/plugins/Alienware-Control/`.
4. Install the Desktop GUI application and `.desktop` launcher.

---

## 🛠️ Usage

### In Gamescope / Gaming Mode (Decky Loader)
1. Press the Quick Access menu button (`...` or `Guide + A`).
2. Navigate to the **Alienware Control** plugin icon.
3. Toggle **Power Saver**, **CPU Turbo Boost**, or **Ollama AI Service**, or choose a thermal preset.

### On Desktop (GNOME / KDE)
Launch **Alienware Mode & Turbo** from your application launcher or run:
```bash
alienware-control
```

---

## 📜 License

Licensed under the [GNU General Public License v3.0](LICENSE).
