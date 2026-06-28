#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  IPVanish Client — Linux Installer                                      ║
# ║  Supports: Debian / Ubuntu / Mint / Parrot OS and derivatives           ║
# ║  Author:   DitherZ  <https://github.com/DitherZ>                        ║
# ║  Version:  1.0.0                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── ANSI colour helpers ───────────────────────────────────────────────────────
RC=$'\e[0m'; BOLD=$'\e[1m'; RED=$'\e[1;31m'; GRN=$'\e[1;32m'
YLW=$'\e[1;33m'; CYN=$'\e[1;36m'; MAG=$'\e[1;35m'; WHT=$'\e[1;37m'
_DIM=$'\e[2m'
print_info() { printf "  ${CYN}INFO${RC}  %s\n" "$*"; }
print_task() { printf "  ${MAG}TASK${RC}  %s\n" "$*"; }
print_done() { printf "  ${GRN}DONE${RC}  %s\n" "$*"; }
print_warn() { printf "  ${YLW}WARN${RC}  %s\n" "$*"; }
print_fail() { printf "  ${RED}FAIL${RC}  %s\n" "$*"; }

# ── Constants ────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/DitherZ/ipvanish-client"
INSTALL_DIR="${HOME}/.local/share/ipvanish-client"
BIN_LINK="/usr/local/bin/ipvanish"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Helpers ──────────────────────────────────────────────────────────────────
die() {
    print_fail "$*"
    exit 1
}

require_cmd() {
    command -v "$1" &>/dev/null || die "Required command not found: $1"
}

check_debian() {
    [[ -f /etc/debian_version ]] || die "This installer requires a Debian-based distribution."
}

apt_install() {
    local missing=()
    for pkg in "$@"; do
        dpkg -s "${pkg}" &>/dev/null || missing+=("${pkg}")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        print_task "Installing system packages: ${missing[*]}"
        sudo apt-get install -y "${missing[@]}" || die "apt-get install failed."
        print_done "System packages installed."
    else
        print_info "System packages already present: $*"
    fi
}

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
printf "  ${BOLD}${WHT}IPVanish Client${RC}  ${_DIM}Linux Installer v1.0.0${RC}\n"
printf "  ${_DIM}%s${RC}\n" "${REPO_URL}"
echo ""

# ── Preflight ────────────────────────────────────────────────────────────────
print_task "Checking system compatibility..."
check_debian
require_cmd python3
require_cmd pip3 || require_cmd pip

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [[ "${PYTHON_MAJOR}" -lt 3 ]] || { [[ "${PYTHON_MAJOR}" -eq 3 ]] && [[ "${PYTHON_MINOR}" -lt 11 ]]; }; then
    die "Python 3.11+ required. Found: ${PYTHON_VERSION}"
fi
print_done "Python ${PYTHON_VERSION} — OK"

# ── System dependencies ───────────────────────────────────────────────────────
print_task "Installing system dependencies..."
sudo apt-get update -qq
apt_install openvpn policykit-1

# WireGuard is optional — warn if missing, don't abort
if ! dpkg -s wireguard-tools &>/dev/null; then
    print_warn "wireguard-tools not installed. WireGuard profiles will not work."
    print_warn "Install manually: sudo apt install wireguard-tools"
fi

# ── Determine source directory ────────────────────────────────────────────────
# If this script is already inside a cloned repo, install from there.
# Otherwise clone from GitHub.
if [[ -f "${SCRIPT_DIR}/ipvanish" ]] && [[ -f "${SCRIPT_DIR}/pyproject.toml" ]]; then
    SOURCE_DIR="${SCRIPT_DIR}"
    print_info "Using local source: ${SOURCE_DIR}"
else
    print_task "Cloning repository to ${INSTALL_DIR}..."
    require_cmd git
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        print_info "Existing clone found — pulling latest..."
        git -C "${INSTALL_DIR}" pull --ff-only
    else
        git clone --depth=1 "${REPO_URL}.git" "${INSTALL_DIR}"
    fi
    SOURCE_DIR="${INSTALL_DIR}"
    print_done "Repository ready."
fi

# ── Python dependencies ───────────────────────────────────────────────────────
print_task "Installing Python dependencies..."
pip3 install --quiet --break-system-packages \
    "PyQt6>=6.6.0" \
    "PyQt6-Qt6>=6.6.0" \
    "requests>=2.31.0" \
    "beautifulsoup4>=4.12.0" \
    || pip install --quiet --break-system-packages \
        "PyQt6>=6.6.0" \
        "PyQt6-Qt6>=6.6.0" \
        "requests>=2.31.0" \
        "beautifulsoup4>=4.12.0"
print_done "Python dependencies installed."

# ── Symlink project root to install dir (if cloned externally) ───────────────
if [[ "${SOURCE_DIR}" == "${SCRIPT_DIR}" ]] && [[ "${SCRIPT_DIR}" != "${INSTALL_DIR}" ]]; then
    if [[ ! -e "${INSTALL_DIR}" ]]; then
        print_task "Symlinking project to ${INSTALL_DIR}..."
        ln -s "${SOURCE_DIR}" "${INSTALL_DIR}"
        print_done "Symlink created."
    else
        print_info "Install dir already exists: ${INSTALL_DIR}"
    fi
fi

# ── Entry point permissions ───────────────────────────────────────────────────
print_task "Setting executable permissions on entry point..."
chmod +x "${SOURCE_DIR}/ipvanish"
print_done "chmod +x ipvanish"

# ── Symlink to PATH ───────────────────────────────────────────────────────────
print_task "Symlinking 'ipvanish' to ${BIN_LINK}..."
sudo ln -sf "${SOURCE_DIR}/ipvanish" "${BIN_LINK}"
print_done "'ipvanish' available system-wide."

# ── Application icon ──────────────────────────────────────────────────────────
print_task "Installing application icon..."
mkdir -p "${ICON_DIR}/512x512/apps" "${ICON_DIR}/64x64/apps"

ICON_512="${SOURCE_DIR}/assets/PNG/IPVanish_icon_512x512.png"
ICON_64="${SOURCE_DIR}/assets/PNG/IPVanish_icon_64x64.png"

if [[ -f "${ICON_512}" ]]; then
    cp "${ICON_512}" "${ICON_DIR}/512x512/apps/ipvanish.png"
fi
if [[ -f "${ICON_64}" ]]; then
    cp "${ICON_64}" "${ICON_DIR}/64x64/apps/ipvanish.png"
fi

# Refresh icon cache if gtk-update-icon-cache is available
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qtf "${ICON_DIR}" 2>/dev/null || true
fi
print_done "Icons installed."

# ── .desktop file ─────────────────────────────────────────────────────────────
print_task "Installing .desktop entry..."
mkdir -p "${DESKTOP_DIR}"

DESKTOP_SRC="${SOURCE_DIR}/IPVanish.desktop"
DESKTOP_DEST="${DESKTOP_DIR}/IPVanish.desktop"

if [[ -f "${DESKTOP_SRC}" ]]; then
    # Rewrite Exec= to absolute path for portability
    sed "s|^Exec=.*|Exec=${BIN_LINK}|" "${DESKTOP_SRC}" > "${DESKTOP_DEST}"
else
    # Generate minimal fallback
    cat > "${DESKTOP_DEST}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=IPVanish Client
GenericName=VPN Client
Comment=Unofficial IPVanish Linux GUI client
Exec=${BIN_LINK}
Icon=ipvanish
Terminal=false
Categories=Network;Security;
Keywords=VPN;IPVanish;OpenVPN;WireGuard;Privacy;Security;
StartupNotify=true
StartupWMClass=IPVanish Client
EOF
fi

chmod 644 "${DESKTOP_DEST}"

# Refresh desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database -q "${DESKTOP_DIR}" 2>/dev/null || true
fi
print_done ".desktop entry installed."

# ── Config directory permissions ──────────────────────────────────────────────
CONFIG_DIR="${SOURCE_DIR}/config"
if [[ -d "${CONFIG_DIR}" ]]; then
    chmod 700 "${CONFIG_DIR}"
    [[ -f "${CONFIG_DIR}/credentials" ]] && chmod 600 "${CONFIG_DIR}/credentials"
    print_done "config/ permissions set (700 / credentials 600)."
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
printf "  ${GRN}${BOLD}Installation complete.${RC}\n\n"
printf "  ${_DIM}Launch from your application menu or run:${RC}\n"
printf "  ${WHT}  ipvanish${RC}\n\n"
printf "  ${_DIM}First-time setup:${RC}\n"
printf "  ${_DIM}  1. Settings → Account Credentials — enter your IPVanish email + password${RC}\n"
printf "  ${_DIM}  2. Settings → OpenVPN Config Files → Download Config Files${RC}\n"
printf "  ${_DIM}  3. Locations tab — pick a server, double-click to select${RC}\n"
printf "  ${_DIM}  4. Click Connect${RC}\n"
echo ""
