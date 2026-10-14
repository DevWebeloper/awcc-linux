import os
import json
import subprocess
import decky  # type: ignore

STATE_FILE = "/home/alienware/.config/alienware-control-state.json"
SETTINGS_FILE = "/home/alienware/homebrew/settings/Alienware-Control/settings.json"

class Plugin:
    def _save_state(self, profile: str, turbo: bool, power_saver: bool = False):
        data = {
            "profile": profile,
            "turbo": turbo,
            "power_saver": power_saver
        }
        for path in [STATE_FILE, SETTINGS_FILE]:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                os.chmod(path, 0o666)
            except Exception as e:
                decky.logger.error(f"[Alienware-Control] Failed writing state to {path}: {e}")

    def _load_saved_state(self):
        for path in [STATE_FILE, SETTINGS_FILE]:
            if os.path.isfile(path):
                try:
                    with open(path, "r") as f:
                        return json.load(f)
                except Exception as e:
                    decky.logger.error(f"[Alienware-Control] Failed reading state from {path}: {e}")
        return None

    async def _main(self):
        decky.logger.info("[Alienware-Control] Plugin backend initialized")
        saved = self._load_saved_state()
        if saved:
            decky.logger.info(f"[Alienware-Control] Restoring last saved settings: {saved}")
            if "profile" in saved:
                await self.set_profile(saved["profile"])
            if "turbo" in saved:
                await self.set_turbo(saved["turbo"])
            if "power_saver" in saved and saved["power_saver"]:
                await self.set_power_saver(saved["power_saver"])
        else:
            status = await self.get_status()
            self._save_state(status["profile"], status["turbo"], status.get("power_saver", False))

    async def _unload(self):
        decky.logger.info("[Alienware-Control] Plugin backend unloaded")

    async def get_status(self):
        # 1. CPU Turbo / Boost
        turbo = False
        try:
            with open("/sys/devices/system/cpu/cpufreq/boost", "r") as f:
                turbo = (f.read().strip() == "1")
        except Exception as e:
            decky.logger.error(f"[Alienware-Control] Error reading boost: {e}")

        # 2. ACPI Platform Profile
        profile = "unknown"
        try:
            with open("/sys/firmware/acpi/platform_profile", "r") as f:
                profile = f.read().strip()
        except Exception as e:
            decky.logger.error(f"[Alienware-Control] Error reading platform_profile: {e}")

        # 3. Available Choices
        choices = ["quiet", "balanced", "balanced-performance", "performance", "cool"]
        try:
            with open("/sys/firmware/acpi/platform_profile_choices", "r") as f:
                c = f.read().strip().split()
                if c:
                    choices = c
        except Exception as e:
            decky.logger.error(f"[Alienware-Control] Error reading platform_profile_choices: {e}")

        # 4. Max CPU frequency (ceiling)
        max_freq = "N/A"
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", "r") as f:
                khz = int(f.read().strip())
                max_freq = f"{khz / 1000000:.2f} GHz"
        except Exception:
            pass

        # 5. Power Profiles Daemon & EPP State
        power_profile = "balanced"
        try:
            res = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                power_profile = res.stdout.strip()
        except Exception:
            pass

        power_saver = (power_profile == "power-saver")
        if not power_saver:
            epp_file = "/sys/devices/system/cpu/cpufreq/policy0/energy_performance_preference"
            if os.path.isfile(epp_file):
                try:
                    with open(epp_file, "r") as f:
                        if f.read().strip() in ("power", "balance_power"):
                            power_saver = True
                except Exception:
                    pass

        return {
            "turbo": turbo,
            "profile": profile,
            "choices": choices,
            "max_freq": max_freq,
            "power_saver": power_saver,
            "power_profile": power_profile
        }

    async def set_turbo(self, enabled: bool):
        val = "1" if enabled else "0"
        decky.logger.info(f"[Alienware-Control] Setting turbo to: {val}")
        try:
            with open("/sys/devices/system/cpu/cpufreq/boost", "w") as f:
                f.write(val)
        except Exception as e:
            decky.logger.warning(f"[Alienware-Control] Direct boost write failed: {e}. Falling back to aliencontrol-helper.")
            try:
                subprocess.run(["/usr/local/bin/aliencontrol-helper", "cpuboost", val], check=True)
            except Exception as ex:
                decky.logger.error(f"[Alienware-Control] aliencontrol-helper cpuboost failed: {ex}")

        status = await self.get_status()
        self._save_state(status["profile"], status["turbo"], status.get("power_saver", False))
        return status

    async def set_profile(self, profile: str):
        decky.logger.info(f"[Alienware-Control] Setting ACPI platform_profile to: {profile}")
        try:
            with open("/sys/firmware/acpi/platform_profile", "w") as f:
                f.write(profile)
        except Exception as e:
            decky.logger.warning(f"[Alienware-Control] Direct platform_profile write failed: {e}. Falling back to aliencontrol-helper.")
            try:
                subprocess.run(["/usr/local/bin/aliencontrol-helper", "profile", profile], check=True)
            except Exception as ex:
                decky.logger.error(f"[Alienware-Control] aliencontrol-helper profile failed: {ex}")

        status = await self.get_status()
        self._save_state(status["profile"], status["turbo"], status.get("power_saver", False))
        return status

    async def set_power_saver(self, enabled: bool):
        decky.logger.info(f"[Alienware-Control] Setting Power Saver mode to: {enabled}")
        target_profile = "power-saver" if enabled else "balanced"
        target_epp = "power" if enabled else "balance_performance"
        target_platform = "quiet" if enabled else "balanced"

        # 1. powerprofilesctl
        try:
            subprocess.run(["powerprofilesctl", "set", target_profile], capture_output=True, check=False)
        except Exception as e:
            decky.logger.warning(f"[Alienware-Control] powerprofilesctl set failed: {e}")

        # 2. aliencontrol-helper cpuepp
        try:
            subprocess.run(["/usr/local/bin/aliencontrol-helper", "cpuepp", target_epp], capture_output=True, check=False)
        except Exception as e:
            decky.logger.warning(f"[Alienware-Control] helper cpuepp failed: {e}")

        # 3. set platform profile
        await self.set_profile(target_platform)

        status = await self.get_status()
        self._save_state(status["profile"], status["turbo"], status.get("power_saver", False))
        return status
