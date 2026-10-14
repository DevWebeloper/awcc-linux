#!/usr/bin/env python3
"""
Alienware / Linux Mode & Turbo Controller (GTK4 + Libadwaita)

Features:
- Simple 1-click power profile mode switcher (Performance, Balanced, Quiet, Cool, Power-Saver).
- Dedicated toggle to turn CPU Turbo Boost off/on (limiting clocks to tame heat and fan noise).
- Live state checker loop (polling sysfs and D-Bus every 1s) to immediately reflect external changes.
- Live hardware telemetry (CPU/GPU temperatures and 4-zone fan speeds from alienware-wmi).
- Modern GNOME HIG styling using Libadwaita cards, action rows, switch rows, and toast notifications.
"""

import os
import subprocess
import sys
import time
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio, GLib, Gtk


class HardwareManager:
    """Handles communication with Linux sysfs, power-profiles-daemon, and hwmon."""

    PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"
    PLATFORM_CHOICES_PATH = "/sys/firmware/acpi/platform_profile_choices"
    AMD_BOOST_PATH = "/sys/devices/system/cpu/cpufreq/boost"
    INTEL_NO_TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"

    def __init__(self):
        self.hwmon_path = self._detect_alienware_hwmon()
        self.supported_profiles = self._read_supported_profiles()

    def _detect_alienware_hwmon(self):
        """Finds hwmon directory corresponding to alienware_wmi or dell_smm."""
        hwmon_dir = "/sys/class/hwmon"
        if not os.path.exists(hwmon_dir):
            return None
        for name in ("alienware_wmi", "dell_smm", "k10temp", "coretemp"):
            for entry in os.listdir(hwmon_dir):
                target = os.path.join(hwmon_dir, entry)
                name_file = os.path.join(target, "name")
                if os.path.isfile(name_file):
                    try:
                        with open(name_file, "r") as f:
                            if f.read().strip() == name:
                                return target
                    except Exception:
                        pass
        return None

    def _read_supported_profiles(self):
        """Reads supported platform profile choices."""
        if os.path.isfile(self.PLATFORM_CHOICES_PATH):
            try:
                with open(self.PLATFORM_CHOICES_PATH, "r") as f:
                    return f.read().strip().split()
            except Exception:
                pass
        # Fallback to standard power-profiles-daemon list
        return ["performance", "balanced", "quiet", "cool", "power-saver"]

    def get_current_profile(self):
        """Gets currently active power profile."""
        if os.path.isfile(self.PLATFORM_PROFILE_PATH):
            try:
                with open(self.PLATFORM_PROFILE_PATH, "r") as f:
                    val = f.read().strip()
                    if val:
                        return val
            except Exception:
                pass
        # Fallback to powerprofilesctl
        try:
            res = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def _sync_aliencontrol_cfg(self, profile):
        """Keep ~/.config/aliencontrol.json current_profile synchronized."""
        cfg_path = os.path.expanduser("~/.config/aliencontrol.json")
        if not os.path.isfile(cfg_path):
            return
        try:
            import json
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            name_map = {
                "quiet": "Quiet",
                "performance": "Performance",
                "balanced-performance": "Balanced Performance",
                "balanced": "Balanced Power",
                "cool": "Cool Surface",
                "low-power": "Power Saver",
            }
            prof_name = name_map.get(profile, profile.title())
            if cfg.get("current_profile") != prof_name:
                cfg["current_profile"] = prof_name
                with open(cfg_path, "w") as f:
                    json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def set_profile(self, profile):
        """Sets power profile via passwordless helper, powerprofilesctl, or sysfs."""
        # 1. Try passwordless aliencontrol-helper first (instant, zero sudo prompt)
        try:
            res = subprocess.run(
                ["sudo", "-n", "/usr/local/bin/aliencontrol-helper", "profile", profile],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                self._sync_aliencontrol_cfg(profile)
                return True, f"Profile set to {profile}"
        except Exception:
            pass

        # 2. Try powerprofilesctl (no root prompt needed via polkit)
        mapped = profile
        if profile == "power-saver":
            mapped = "power-saver"
        try:
            res = subprocess.run(
                ["powerprofilesctl", "set", mapped],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                self._sync_aliencontrol_cfg(profile)
                return True, f"Profile set to {profile}"
        except Exception:
            pass

        # 3. Try direct sysfs write
        if os.path.isfile(self.PLATFORM_PROFILE_PATH):
            try:
                with open(self.PLATFORM_PROFILE_PATH, "w") as f:
                    f.write(profile)
                self._sync_aliencontrol_cfg(profile)
                return True, f"Profile set to {profile}"
            except PermissionError:
                # 4. Fallback to pkexec
                cmd = ["pkexec", "sh", "-c", f"echo {profile} > {self.PLATFORM_PROFILE_PATH}"]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        self._sync_aliencontrol_cfg(profile)
                        return True, f"Profile set to {profile} via pkexec"
                    return False, f"pkexec failed: {res.stderr.strip()}"
                except Exception as e:
                    return False, f"Error: {e}"
            except Exception as e:
                return False, f"Error setting profile: {e}"

        return False, "Platform profile interface unavailable"

    def get_turbo_boost(self):
        """
        Returns True if CPU Turbo Boost is currently enabled, False if disabled,
        or None if unsupported.
        """
        # AMD / generic cpufreq boost: 1 = boost enabled, 0 = boost disabled
        if os.path.isfile(self.AMD_BOOST_PATH):
            try:
                with open(self.AMD_BOOST_PATH, "r") as f:
                    val = f.read().strip()
                    return val == "1"
            except Exception:
                pass

        # Intel pstate no_turbo: 0 = boost enabled, 1 = boost disabled
        if os.path.isfile(self.INTEL_NO_TURBO_PATH):
            try:
                with open(self.INTEL_NO_TURBO_PATH, "r") as f:
                    val = f.read().strip()
                    return val == "0"
            except Exception:
                pass

        return None

    def set_turbo_boost(self, enable: bool):
        """Sets CPU Turbo Boost state (enable/disable)."""
        val = "1" if enable else "0"
        state_str = "enabled" if enable else "disabled"

        # 1. Try passwordless aliencontrol-helper first (instant, zero sudo prompt)
        try:
            res = subprocess.run(
                ["sudo", "-n", "/usr/local/bin/aliencontrol-helper", "cpuboost", val],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return True, f"CPU Turbo Boost {state_str}"
        except Exception:
            pass

        target_file = None
        target_val = None

        if os.path.isfile(self.AMD_BOOST_PATH):
            target_file = self.AMD_BOOST_PATH
            target_val = val
        elif os.path.isfile(self.INTEL_NO_TURBO_PATH):
            target_file = self.INTEL_NO_TURBO_PATH
            target_val = "0" if enable else "1"
        else:
            return False, "CPU Turbo Boost sysfs control node not found"

        # 2. Try direct write
        try:
            with open(target_file, "w") as f:
                f.write(target_val)
            return True, f"CPU Turbo Boost {state_str}"
        except PermissionError:
            # 3. Fallback to pkexec
            cmd = ["pkexec", "sh", "-c", f"echo {target_val} > {target_file}"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return True, f"CPU Turbo Boost {state_str}"
                return False, "Permission denied (pkexec authentication cancelled or failed)"
            except Exception as e:
                return False, f"pkexec execution failed: {e}"
        except Exception as e:
            return False, f"Error writing to boost node: {e}"

    def get_power_saver(self):
        """Returns True if Power-Saver profile or low-power EPP is active."""
        prof = self.get_current_profile()
        if prof in ("power-saver", "low-power"):
            return True
        try:
            res = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, check=False)
            if res.stdout.strip() == "power-saver":
                return True
        except Exception:
            pass
        # Check EPP
        epp_file = "/sys/devices/system/cpu/cpufreq/policy0/energy_performance_preference"
        if os.path.isfile(epp_file):
            try:
                with open(epp_file, "r") as f:
                    if f.read().strip() in ("power", "balance_power"):
                        return True
            except Exception:
                pass
        return False

    def set_power_saver(self, enable: bool):
        """Toggles power-saver profile and EPP power modes."""
        target_profile = "power-saver" if enable else "balanced"
        target_epp = "power" if enable else "balance_performance"
        target_platform = "quiet" if enable else "balanced"

        # 1. Try powerprofilesctl
        try:
            subprocess.run(["powerprofilesctl", "set", target_profile], capture_output=True, check=False)
        except Exception:
            pass

        # 2. Try helper cpuepp
        try:
            subprocess.run(["sudo", "-n", "/usr/local/bin/aliencontrol-helper", "cpuepp", target_epp], capture_output=True, check=False)
        except Exception:
            pass

        # 3. Set platform profile
        self.set_profile(target_platform if enable else "balanced")
        return True, f"Power Saver {'ENABLED (Eco mode active)' if enable else 'DISABLED (Balanced mode active)'}"

    def get_ollama_status(self):
        """Returns True if Ollama service is active."""
        try:
            res = subprocess.run(["systemctl", "--user", "is-active", "ollama"], capture_output=True, text=True, check=False)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def set_ollama_status(self, enable: bool):
        """Starts/enables or stops/disables Ollama user service."""
        cmd = ["systemctl", "--user", "enable", "--now", "ollama"] if enable else ["systemctl", "--user", "disable", "--now", "ollama"]
        try:
            subprocess.run(cmd, capture_output=True, check=False)
            return True, f"Ollama service {'started and enabled' if enable else 'stopped and disabled'}"
        except Exception as e:
            return False, f"Failed to modify Ollama service: {e}"

    def get_telemetry(self):
        """Reads live temperatures and fan RPMs from hwmon."""
        data = {"temps": [], "fans": []}
        if not self.hwmon_path or not os.path.isdir(self.hwmon_path):
            return data

        try:
            # Read fans
            for entry in sorted(os.listdir(self.hwmon_path)):
                if entry.startswith("fan") and entry.endswith("_input"):
                    fan_id = entry.replace("fan", "").replace("_input", "")
                    label_path = os.path.join(self.hwmon_path, f"fan{fan_id}_label")
                    label = f"Fan {fan_id}"
                    if os.path.isfile(label_path):
                        with open(label_path, "r") as lf:
                            label = lf.read().strip()
                    with open(os.path.join(self.hwmon_path, entry), "r") as f:
                        rpm = int(f.read().strip())
                    data["fans"].append({"label": label, "rpm": rpm})

            # Read temps
            for entry in sorted(os.listdir(self.hwmon_path)):
                if entry.startswith("temp") and entry.endswith("_input"):
                    temp_id = entry.replace("temp", "").replace("_input", "")
                    label_path = os.path.join(self.hwmon_path, f"temp{temp_id}_label")
                    label = f"Sensor {temp_id}"
                    if os.path.isfile(label_path):
                        with open(label_path, "r") as lf:
                            label = lf.read().strip()
                    with open(os.path.join(self.hwmon_path, entry), "r") as f:
                        raw_temp = int(f.read().strip())
                        temp_c = round(raw_temp / 1000.0, 1)
                    data["temps"].append({"label": label, "temp_c": temp_c})
        except Exception:
            pass

        return data


class AlienwareAppWindow(Adw.ApplicationWindow):
    """Main Application Window for Alienware Mode & Turbo Control."""

    PROFILE_METADATA = {
        "performance": {
            "title": "Performance (G-Mode)",
            "icon": "power-profile-performance-symbolic",
            "desc": "Maximum CPU/GPU clocks and aggressive fan cooling curve for intensive gaming.",
            "css_class": "mode-performance",
        },
        "balanced-performance": {
            "title": "Balanced Performance",
            "icon": "applications-games-symbolic",
            "desc": "Enhanced performance headroom with adaptive fan acoustic control.",
            "css_class": "mode-performance",
        },
        "balanced": {
            "title": "Balanced Mode",
            "icon": "power-profile-balanced-symbolic",
            "desc": "Optimal balance between responsive performance, thermals, and acoustics.",
            "css_class": "mode-balanced",
        },
        "quiet": {
            "title": "Quiet Mode",
            "icon": "weather-clear-night-symbolic",
            "desc": "Prioritizes silent operation by throttling acoustic fan curve limits.",
            "css_class": "mode-quiet",
        },
        "cool": {
            "title": "Cool Surface",
            "icon": "weather-snow-symbolic",
            "desc": "Higher fan speeds to keep laptop chassis surface cool to the touch.",
            "css_class": "mode-cool",
        },
        "low-power": {
            "title": "Power Saver",
            "icon": "power-profile-power-saver-symbolic",
            "desc": "Limits system energy consumption to maximize battery longevity.",
            "css_class": "mode-powersave",
        },
        "power-saver": {
            "title": "Power Saver",
            "icon": "power-profile-power-saver-symbolic",
            "desc": "Limits system energy consumption to maximize battery longevity.",
            "css_class": "mode-powersave",
        },
        "custom": {
            "title": "Custom / Manual",
            "icon": "emblem-system-symbolic",
            "desc": "Unlocks manual fan curve and power envelope offset controls.",
            "css_class": "mode-custom",
        },
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hw = HardwareManager()

        self.set_title("Alienware Mode & Turbo")
        self.set_icon_name("alienware-mode-control")
        self.set_default_size(600, 750)
        self.connect("close-request", self._on_close_request)

        # Flag to prevent signal loops during background live state updates
        self._is_updating_ui = False
        self._last_profile = None
        self._last_turbo = None

        # Build UI
        self._setup_css()
        self._build_ui()

        # Start live polling loop (every 1000ms)
        self.poll_live_states()
        self._poll_timer_id = GLib.timeout_add_seconds(1, self.poll_live_states)

    def _on_close_request(self, _window):
        if hasattr(self, "_poll_timer_id") and self._poll_timer_id:
            GLib.source_remove(self._poll_timer_id)
            self._poll_timer_id = None
        return False

    def _setup_css(self):
        """Adds custom styling for mode cards and status badges."""
        css_provider = Gtk.CssProvider()
        css = """
        .hero-card {
            padding: 16px;
            border-radius: 14px;
            background: alpha(currentColor, 0.05);
            border: 1px solid alpha(currentColor, 0.1);
        }
        .hero-title {
            font-size: 1.35rem;
            font-weight: 800;
        }
        .badge-pill {
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 0.8rem;
        }
        .badge-turbo-on {
            background-color: #e66100;
            color: white;
        }
        .badge-turbo-off {
            background-color: #26a269;
            color: white;
        }
        .mode-active-indicator {
            color: #3584e4;
            font-weight: bold;
        }
        .telemetry-val {
            font-family: monospace;
            font-weight: bold;
            font-size: 1.05rem;
        }
        """
        css_provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar View
        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        # Header bar
        header_bar = Adw.HeaderBar()
        window_title = Adw.WindowTitle(
            title="Alienware Mode & Turbo",
            subtitle="Live Hardware Management",
        )
        header_bar.set_title_widget(window_title)

        # Live sync indicator in header
        self.live_status_label = Gtk.Label(label="● Live", xalign=1)
        self.live_status_label.add_css_class("dim-label")
        self.live_status_label.set_margin_end(8)
        header_bar.pack_end(self.live_status_label)

        toolbar_view.add_top_bar(header_bar)

        # Preferences Page (Main scrollable container)
        pref_page = Adw.PreferencesPage()
        toolbar_view.set_content(pref_page)

        # -------------------------------------------------------------
        # Group 1: Live Status Hero Card
        # -------------------------------------------------------------
        hero_group = Adw.PreferencesGroup()
        hero_group.set_title("Current Active State")
        hero_group.set_description("Monitored continuously from hardware and kernel ACPI")
        pref_page.add(hero_group)

        hero_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hero_box.add_css_class("hero-card")

        self.hero_icon = Gtk.Image(icon_name="speedometer-symbolic", pixel_size=48)
        hero_box.append(self.hero_icon)

        hero_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero_text_box.set_hexpand(True)

        title_badge_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.hero_title = Gtk.Label(label="Checking Mode...", xalign=0)
        self.hero_title.add_css_class("hero-title")
        title_badge_box.append(self.hero_title)

        self.hero_turbo_badge = Gtk.Label(label="TURBO ...")
        self.hero_turbo_badge.add_css_class("badge-pill")
        self.hero_turbo_badge.add_css_class("badge-turbo-on")
        title_badge_box.append(self.hero_turbo_badge)

        hero_text_box.append(title_badge_box)

        self.hero_desc = Gtk.Label(
            label="Querying live platform profile and CPU boost parameters...",
            xalign=0,
            wrap=True,
        )
        self.hero_desc.add_css_class("dim-label")
        hero_text_box.append(self.hero_desc)

        hero_box.append(hero_text_box)
        hero_group.add(hero_box)

        # -------------------------------------------------------------
        # Group 2: Quick Controls (Performance Mode & Turbo Toggle)
        # -------------------------------------------------------------
        quick_group = Adw.PreferencesGroup()
        quick_group.set_title("Quick Controls")
        quick_group.set_description(
            "Instant toggles for high-performance mode and CPU turbo boost"
        )
        pref_page.add(quick_group)

        # 1. Performance / G-Mode quick toggle
        self.gmode_switch_row = Adw.SwitchRow()
        self.gmode_switch_row.set_title("Performance Mode (G-Mode)")
        self.gmode_switch_row.set_subtitle(
            "Toggle high performance profile on or off"
        )
        self.gmode_switch_row.add_prefix(Gtk.Image.new_from_icon_name("power-profile-performance-symbolic"))
        self.gmode_switch_row.connect("notify::active", self._on_gmode_switch_toggled)
        quick_group.add(self.gmode_switch_row)

        # 2. Power Saver (Eco / Cool) toggle
        self.powersave_switch_row = Adw.SwitchRow()
        self.powersave_switch_row.set_title("Power Saver (Eco / Cool Mode)")
        self.powersave_switch_row.set_subtitle(
            "Forces low-power EPP and quiet thermals to cool down CPU"
        )
        self.powersave_switch_row.add_prefix(Gtk.Image.new_from_icon_name("power-profile-power-saver-symbolic"))
        self.powersave_switch_row.connect("notify::active", self._on_powersave_switch_toggled)
        quick_group.add(self.powersave_switch_row)

        # 3. Turbo Boost toggle to turn off turbo
        self.turbo_switch_row = Adw.SwitchRow()
        self.turbo_switch_row.set_title("CPU Turbo Boost")
        self.turbo_switch_row.set_subtitle(
            "Toggle off to cap CPU at base clock (reduces heat and fan noise)"
        )
        self.turbo_switch_row.add_prefix(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        self.turbo_switch_row.connect("notify::active", self._on_turbo_switch_toggled)
        quick_group.add(self.turbo_switch_row)

        # 4. Ollama Local AI Service toggle
        self.ollama_switch_row = Adw.SwitchRow()
        self.ollama_switch_row.set_title("Ollama Local AI Service")
        self.ollama_switch_row.set_subtitle(
            "Disable when not in use to free ~8GB RAM and stop background CPU polling"
        )
        self.ollama_switch_row.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))
        self.ollama_switch_row.connect("notify::active", self._on_ollama_switch_toggled)
        quick_group.add(self.ollama_switch_row)

        # -------------------------------------------------------------
        # Group 3: All Power Profile Modes
        # -------------------------------------------------------------
        mode_group = Adw.PreferencesGroup()
        mode_group.set_title("All Power Profile Modes")
        mode_group.set_description(
            "Select specific ACPI platform profile"
        )
        pref_page.add(mode_group)

        self.mode_rows = {}
        supported = self.hw.supported_profiles

        for prof in supported:
            meta = self.PROFILE_METADATA.get(
                prof,
                {
                    "title": prof.replace("-", " ").title(),
                    "icon": "power-profile-balanced-symbolic",
                    "desc": f"Set power profile to {prof}",
                },
            )
            row = Adw.ActionRow()
            row.set_title(meta["title"])
            row.set_subtitle(meta["desc"])
            row.add_prefix(Gtk.Image.new_from_icon_name(meta["icon"]))
            row.set_activatable(True)

            # Active indicator check icon
            active_icon = Gtk.Image(icon_name="object-select-symbolic")
            active_icon.set_visible(False)
            row.add_suffix(active_icon)

            # Store references
            self.mode_rows[prof] = {"row": row, "icon": active_icon, "meta": meta}

            # Connect click handler
            row.connect("activated", self._make_mode_activator(prof))
            mode_group.add(row)

        # -------------------------------------------------------------
        # Group 4: Live Telemetry and Fans
        # -------------------------------------------------------------
        self.telemetry_group = Adw.PreferencesGroup()
        self.telemetry_group.set_title("Live Hardware Telemetry")
        self.telemetry_group.set_description("Live temperatures and fan speeds from alienware-wmi")
        pref_page.add(self.telemetry_group)

        # Containers for dynamic sensors
        self.temp_rows = {}
        self.fan_rows = {}

    def _on_gmode_switch_toggled(self, switch_row, _param):
        """User toggled Performance (G-Mode) switch."""
        if self._is_updating_ui:
            return

        is_active = switch_row.get_active()
        target_profile = "performance" if is_active else "balanced"
        self._apply_mode(target_profile)

    def _make_mode_activator(self, profile):
        """Returns an activation callback for a profile row."""

        def _handler(_widget):
            if self._is_updating_ui:
                return
            self._apply_mode(profile)

        return _handler

    def _apply_mode(self, profile):
        """Applies a power profile mode and updates the UI."""
        self.show_toast(f"Switching to {profile.title()} mode...")
        success, msg = self.hw.set_profile(profile)
        if success:
            self.show_toast(f"Mode active: {profile.title()}")
            self.poll_live_states()
        else:
            self.show_toast(f"Failed to set mode: {msg}")

    def _on_powersave_switch_toggled(self, switch_row, _param):
        """User toggled Power Saver (Eco / Cool Mode) switch."""
        if self._is_updating_ui:
            return

        target_state = switch_row.get_active()
        state_name = "Enabling" if target_state else "Disabling"
        self.show_toast(f"{state_name} Power Saver...")

        success, msg = self.hw.set_power_saver(target_state)
        if success:
            self.show_toast(msg)
            self.poll_live_states()
        else:
            self.show_toast(f"Failed: {msg}")
            self._is_updating_ui = True
            switch_row.set_active(self.hw.get_power_saver())
            self._is_updating_ui = False

    def _on_ollama_switch_toggled(self, switch_row, _param):
        """User toggled Ollama Local AI Service switch."""
        if self._is_updating_ui:
            return

        target_state = switch_row.get_active()
        state_name = "Starting" if target_state else "Stopping"
        self.show_toast(f"{state_name} Ollama service...")

        success, msg = self.hw.set_ollama_status(target_state)
        if success:
            self.show_toast(msg)
            self.poll_live_states()
        else:
            self.show_toast(f"Failed: {msg}")
            self._is_updating_ui = True
            switch_row.set_active(self.hw.get_ollama_status())
            self._is_updating_ui = False

    def _on_turbo_switch_toggled(self, switch_row, _param):
        """User toggled the CPU Turbo Boost switch."""
        if self._is_updating_ui:
            return

        target_state = switch_row.get_active()
        state_name = "Enabling" if target_state else "Disabling"
        self.show_toast(f"{state_name} CPU Turbo Boost...")

        success, msg = self.hw.set_turbo_boost(target_state)
        if success:
            self.show_toast(msg)
            self.poll_live_states()
        else:
            self.show_toast(f"Failed: {msg}")
            # Revert switch to actual live state
            self._is_updating_ui = True
            live_boost = self.hw.get_turbo_boost()
            if live_boost is not None:
                switch_row.set_active(live_boost)
            self._is_updating_ui = False

    def poll_live_states(self):
        """
        Polls live hardware states from sysfs/D-Bus and updates UI widgets.
        Returns True to keep GLib.timeout active.
        """
        current_profile = self.hw.get_current_profile()
        turbo_boost = self.hw.get_turbo_boost()
        power_saver = self.hw.get_power_saver()
        ollama_active = self.hw.get_ollama_status()
        telemetry = self.hw.get_telemetry()

        # Update Header live timestamp
        now = datetime.now().strftime("%H:%M:%S")
        self.live_status_label.set_label(f"● Live ({now})")

        # Guard UI updates from triggering signal handlers
        self._is_updating_ui = True

        try:
            # 1. Update G-Mode Switch
            is_performance = current_profile in ("performance", "balanced-performance")
            if self.gmode_switch_row.get_active() != is_performance:
                self.gmode_switch_row.set_active(is_performance)
            if is_performance:
                self.gmode_switch_row.set_subtitle(
                    "High Performance Profile is ACTIVE (Fans and clocks maxed)"
                )
            else:
                self.gmode_switch_row.set_subtitle(
                    "High Performance Profile is OFF (Click to activate Performance mode)"
                )

            # 2. Update Power Saver Switch
            if self.powersave_switch_row.get_active() != power_saver:
                self.powersave_switch_row.set_active(power_saver)
            if power_saver:
                self.powersave_switch_row.set_subtitle(
                    "Power Saver is ACTIVE — CPU low voltage and cool thermals"
                )
            else:
                self.powersave_switch_row.set_subtitle(
                    "Power Saver is OFF — Standard power delivery"
                )

            # 3. Update Turbo Boost Switch
            if turbo_boost is not None:
                if self.turbo_switch_row.get_active() != turbo_boost:
                    self.turbo_switch_row.set_active(turbo_boost)
                self.turbo_switch_row.set_sensitive(True)
                if turbo_boost:
                    self.turbo_switch_row.set_subtitle(
                        "Turbo Boost is ENABLED — Dynamic high clock speeds"
                    )
                    self.hero_turbo_badge.set_label("TURBO ON")
                    self.hero_turbo_badge.remove_css_class("badge-turbo-off")
                    self.hero_turbo_badge.add_css_class("badge-turbo-on")
                else:
                    self.turbo_switch_row.set_subtitle(
                        "Turbo Boost is DISABLED — Lower temps and silent fans"
                    )
                    self.hero_turbo_badge.set_label("TURBO OFF")
                    self.hero_turbo_badge.remove_css_class("badge-turbo-on")
                    self.hero_turbo_badge.add_css_class("badge-turbo-off")
            else:
                self.turbo_switch_row.set_sensitive(False)
                self.turbo_switch_row.set_subtitle("CPU Turbo Boost control not supported on this platform")
                self.hero_turbo_badge.set_label("TURBO N/A")

            # 4. Update Ollama Service Switch
            if self.ollama_switch_row.get_active() != ollama_active:
                self.ollama_switch_row.set_active(ollama_active)
            if ollama_active:
                self.ollama_switch_row.set_subtitle(
                    "Ollama is RUNNING (consuming background RAM/CPU)"
                )
            else:
                self.ollama_switch_row.set_subtitle(
                    "Ollama is STOPPED (RAM freed, zero CPU usage)"
                )

            # 3. Update Mode Rows Selection
            for prof, data in self.mode_rows.items():
                is_active = prof == current_profile
                data["icon"].set_visible(is_active)
                if is_active:
                    data["row"].add_css_class("mode-active-indicator")
                else:
                    data["row"].remove_css_class("mode-active-indicator")

            # 4. Update Hero Card
            meta = self.PROFILE_METADATA.get(
                current_profile,
                {
                    "title": current_profile.replace("-", " ").title(),
                    "icon": "power-profile-performance-symbolic",
                    "desc": f"System power profile is actively set to {current_profile}",
                },
            )
            self.hero_title.set_label(meta["title"])
            self.hero_icon.set_from_icon_name(meta["icon"])
            self.hero_desc.set_label(meta["desc"])

            # 5. Update Live Telemetry
            self._update_telemetry_ui(telemetry)

        except Exception as e:
            # Prevent unexpected hardware reading exceptions from crashing the loop
            pass
        finally:
            self._is_updating_ui = False

        return True

    def _update_telemetry_ui(self, telemetry):
        """Dynamically populates/updates temperature and fan rows."""
        # Temps
        for t in telemetry.get("temps", []):
            label = t["label"]
            temp_c = t["temp_c"]
            if label not in self.temp_rows:
                row = Adw.ActionRow()
                row.set_title(f"{label} Temperature")
                row.add_prefix(Gtk.Image.new_from_icon_name("org.gnome.Settings-device-diagnostics-symbolic"))
                val_label = Gtk.Label()
                val_label.add_css_class("telemetry-val")
                row.add_suffix(val_label)
                self.telemetry_group.add(row)
                self.temp_rows[label] = {"row": row, "label": val_label}

            self.temp_rows[label]["label"].set_label(f"{temp_c} °C")

        # Fans
        for f in telemetry.get("fans", []):
            label = f["label"]
            rpm = f["rpm"]
            if label not in self.fan_rows:
                row = Adw.ActionRow()
                row.set_title(f"{label} Speed")
                row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-devices-symbolic"))
                val_label = Gtk.Label()
                val_label.add_css_class("telemetry-val")
                row.add_suffix(val_label)
                self.telemetry_group.add(row)
                self.fan_rows[label] = {"row": row, "label": val_label}

            self.fan_rows[label]["label"].set_label(f"{rpm} RPM")

    def show_toast(self, text):
        """Displays an in-app banner toast notification."""
        toast = Adw.Toast(title=text)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)


class AlienwareApp(Adw.Application):
    """Application wrapper."""

    def __init__(self):
        super().__init__(
            application_id="io.github.alienfx.modecontroller",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = AlienwareAppWindow(application=self)
        win.present()


def main():
    app = AlienwareApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
