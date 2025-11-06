#!/usr/bin/env bash
# uninstall.sh — completely removes Sour System Monitor (SSM)
# Robust, idiot-proof, self-deleting

set -euo pipefail  # exit on error, undefined variable, or failed pipe

# Determine absolute path of the SSM directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSM_DIR_NAME="$(basename "$SCRIPT_DIR")"

APP_PATH="/usr/local/bin/ssm"
PKG_DIR="/usr/local/bin/ssm_pkg"
CONFIG_DIR="$HOME/.config/ssm"

echo "=== Uninstalling Sour System Monitor (SSM) ==="

# Safety check: confirm we're actually in an SSM directory
if [[ "$SSM_DIR_NAME" != "SSM" ]]; then
    echo "[!] Warning: Script not located in an 'SSM' directory. Aborting."
    exit 1
fi

# Remove launcher
if [[ -f "$APP_PATH" ]]; then
    sudo rm -f "$APP_PATH"
    echo "Removed launcher at $APP_PATH"
else
    echo "Launcher not found at $APP_PATH"
fi

# Remove package directory
if [[ -d "$PKG_DIR" ]]; then
    sudo rm -rf "$PKG_DIR"
    echo "Removed package directory at $PKG_DIR"
else
    echo "Package directory not found at $PKG_DIR"
fi

# Remove user config directory
if [[ -d "$CONFIG_DIR" ]]; then
    rm -rf "$CONFIG_DIR"
    echo "Removed user config directory at $CONFIG_DIR"
else
    echo "User config directory not found at $CONFIG_DIR"
fi

# Confirm with user before removing the entire local SSM directory
echo
echo "This will delete the entire local SSM folder at: $SCRIPT_DIR"
read -p "Are you sure you want to continue? [y/N]: " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted by user."
    exit 0
fi

# Move up one directory to safely delete SSM
cd "$SCRIPT_DIR/.." || exit 1
rm -rf "$SSM_DIR_NAME"

echo "=== SSM successfully uninstalled ==="
echo "You are now safe to use the terminal."
