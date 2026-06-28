#!/usr/bin/env bash
# install-widget.sh — installs IPVanish Plasma widget + daemon

set -o errexit
set -o nounset
set -o pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLASMOID_SRC="${REPO_DIR}/plasmoid/com.ditherz.ipvanish"
DAEMON_SRC="${REPO_DIR}/daemon/ipvanish-widget-daemon.py"
UNIT_SRC="${REPO_DIR}/daemon/ipvanish-widget-daemon.service"

echo "[1/4] Copying daemon..."
mkdir -p "${HOME}/.local/bin"
cp "${DAEMON_SRC}" "${HOME}/.local/bin/ipvanish_widget_daemon.py"
ln -sf "${HOME}/.local/bin/ipvanish_widget_daemon.py" \
       "${HOME}/.local/bin/ipvanish-widget-daemon.py"
chmod +x "${HOME}/.local/bin/ipvanish_widget_daemon.py"

echo "[2/4] Installing systemd user unit..."
mkdir -p "${HOME}/.config/systemd/user"
cp "${UNIT_SRC}" "${HOME}/.config/systemd/user/ipvanish-widget-daemon.service"
systemctl --user daemon-reload
systemctl --user enable --now ipvanish-widget-daemon.service

echo "[3/4] Installing plasmoid..."
kpackagetool6 --type Plasma/Applet --install "${PLASMOID_SRC}" 2>/dev/null || \
kpackagetool6 --type Plasma/Applet --upgrade "${PLASMOID_SRC}"

echo "[4/4] Done. Add 'IPVanish Status' widget from the desktop widget picker."
