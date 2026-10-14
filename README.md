# 👽 Alienware Control (Decky Plugin & Libadwaita GUI)

[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20SteamOS%20%7C%20CachyOS-orange.svg)](#)
[![Decky Loader: v3+](https://img.shields.io/badge/Decky%20Loader-v3%2B-purple.svg)](#)
[![Interface: GTK4 / Libadwaita](https://img.shields.io/badge/GUI-GTK4%20%2F%20Libadwaita-brightgreen.svg)](#)

Unified power, thermal, acoustic, and CPU boost management suite designed specifically for **Alienware gaming laptops and desktops running Linux / SteamOS / Gamescope**.

Includes both a **Decky Loader plugin** (for quick in-game access within Gamescope / Steam Big Picture) and a sleek **GTK4 / Libadwaita desktop application**.

---

## ✨ Key Features

* **⚡ Power Saver (Eco / Cool Mode) Toggle**:
  Instantly switches `power-saver` profiles and lowers AMD/Intel Energy Performance Preference (`EPP`) to tame high idling temperatures and keep laptop surfaces cool.
* **🚀 CPU Turbo Boost On/Off**:
  One-click toggle to cap CPUs at base clocks (e.g. 3.00 GHz on Ryzen 9 7845HX) eliminating thermal spikes and jet-engine fan noise during light gaming or browsing.
* **🎮 ACPI Platform Profiles**:
  Quick selection across all Alienware firmware modes:
  * `Performance (G-Mode)`: Maximum clocks and aggressive fan cooling tables
  * `Balanced Performance`: Balanced high clocks with adaptive acoustic fan curves
  * `Balanced`: Standard daily profile
  * `Quiet`: Silent operation with acoustic throttling
  * `Cool`: Chassis surface cooling
  * `Power Saver`: Maximum battery and lowest thermal footprint
* **🤖 Ollama / AI Service Switcher**:
  Convenient toggle to stop/start local AI services, instantly freeing up **7–8 GB of RAM** and stopping background CPU polling.
* **📊 Live Telemetry**:
  Real-time CPU and GPU sensor temperature monitoring alongside 4-zone fan RPM indicators (`alienware-wmi` / `dell_smm`).
* **🕹️ Seamless Decky Loader Integration**:
  Full controller-friendly quick menu inside Steam Deck / Gamescope gaming mode.

---

## 📂 Repository Structure

```
alienware-control/
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

Clone the repository and run the installer:

```bash
git clone https://github.com/DevWebeloper/alienware-control.git
cd alienware-control
chmod +x install.sh
sudo ./install.sh
```

The script will:
1. Install `/usr/local/bin/aliencontrol-helper` and configure passwordless sudo access.
2. Install udev permissions for hardware nodes.
3. Deploy the Decky Loader plugin into `~/homebrew/plugins/Alienware-Control/`.
4. Install the Desktop GUI application and `.desktop` launcher.

---

## 🛠️ Usage

### From Decky Loader (Gaming Mode)
1. Press the Quick Access menu button (`...` or `Guide + A`).
2. Navigate to the **Alienware Control** plugin icon.
3. Toggle **Power Saver**, **CPU Turbo Boost**, or **Ollama AI Service**, or pick a quick thermal preset.

### From Desktop (GNOME / KDE)
Launch **Alienware Mode & Turbo** from your applications menu or via terminal:
```bash
alienware-control
```

---

## 📜 License

Licensed under the [GNU General Public License v3.0](LICENSE).
