#!/usr/bin/env bash
# Installer for Alienware Control Suite (Decky Plugin + Desktop GUI)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Installing Alienware Control ==="

# 1. Install helper
echo "[1/4] Installing /usr/local/bin/aliencontrol-helper..."
sudo cp "$SCRIPT_DIR/system/aliencontrol-helper" /usr/local/bin/aliencontrol-helper
sudo chmod 755 /usr/local/bin/aliencontrol-helper
sudo chown root:root /usr/local/bin/aliencontrol-helper

# Ensure sudoers entry exists
SUDOERS_FILE="/etc/sudoers.d/99-aliencontrol"
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "Creating sudoers rule for aliencontrol-helper..."
    echo "ALL ALL=(root) NOPASSWD: /usr/local/bin/aliencontrol-helper" | sudo tee "$SUDOERS_FILE" >/dev/null
    sudo chmod 440 "$SUDOERS_FILE"
fi

# 2. Install udev rules
echo "[2/4] Installing udev rules..."
sudo cp "$SCRIPT_DIR/system/99-cpu-boost.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 3. Install Desktop application
echo "[3/4] Installing Desktop Application..."
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
cp "$SCRIPT_DIR/gui/run_gui.sh" "$HOME/.local/bin/alienware-control"
chmod +x "$HOME/.local/bin/alienware-control" "$SCRIPT_DIR/gui/alienware_adwaita_app.py"

cp "$SCRIPT_DIR/gui/alienware-mode-control.desktop" "$HOME/.local/share/applications/"
cp "$SCRIPT_DIR/gui/alienware-mode-control.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/"

# 4. Deploy Decky Plugin if Decky is installed
DECKY_DIR="$HOME/homebrew/plugins/Alienware-Control"
if [ -d "$HOME/homebrew/plugins" ]; then
    echo "[4/4] Deploying Decky Loader plugin to $DECKY_DIR..."
    sudo mkdir -p "$DECKY_DIR/dist"
    sudo cp "$SCRIPT_DIR/main.py" "$DECKY_DIR/"
    sudo cp "$SCRIPT_DIR/plugin.json" "$DECKY_DIR/"
    sudo cp "$SCRIPT_DIR/package.json" "$DECKY_DIR/"
    sudo cp "$SCRIPT_DIR/dist/index.js" "$DECKY_DIR/dist/"
    if systemctl is-active --quiet plugin_loader; then
        echo "Restarting Decky Loader service..."
        sudo systemctl restart plugin_loader
    fi
fi

echo "=== Installation complete! ==="
