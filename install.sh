#!/usr/bin/env bash
# SafeRun v3.0 — Installer & Uninstaller
# Tested on: Kali Linux (zsh), Ubuntu 22/24 (bash), Debian, Mint

BOLD="\033[1m"; GREEN="\033[92m"; CYAN="\033[96m"
RED="\033[91m"; YELLOW="\033[93m"; DIM="\033[2m"; RESET="\033[0m"

INSTALL_DIR="/usr/local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKER="# >>> SafeRun protection (managed by SafeRun installer)"
MARKER_END="# <<< SafeRun protection"

# Shell functions — bypass-resistant
# _saferun_ip avoids conflict with Kali zsh built-in ip alias
PROTECTION='# SafeRun shell functions (bypass-resistant)
rm()          { saferun rm "$@"; }
dd()          { saferun dd "$@"; }
curl()        { saferun curl "$@"; }
wget()        { saferun wget "$@"; }
chmod()       { saferun chmod "$@"; }
chown()       { saferun chown "$@"; }
mkfs()        { saferun mkfs "$@"; }
shred()       { saferun shred "$@"; }
rfkill()      { saferun rfkill "$@"; }
nmcli()       { saferun nmcli "$@"; }
_saferun_ip() { saferun ip "$@"; }
alias ip="_saferun_ip"
sudo() {
    local cmd="$1"
    case "$cmd" in
        rm|dd|curl|wget|chmod|chown|mkfs|shred|rfkill|nmcli|ip|\
        systemctl|passwd|useradd|usermod|iptables|nft|sysctl|apt|apt-get|mv)
            saferun "$@" ;;
        *) command sudo "$@" ;;
    esac
}'

detect_shell_config() {
    [ "$(basename "$SHELL")" = "zsh" ] || [ -n "$ZSH_VERSION" ] \
        && echo "$HOME/.zshrc" || echo "$HOME/.bashrc"
}

remove_block() {
    local cfg="$1"
    python3 - "$cfg" "$MARKER" "$MARKER_END" <<'PYEOF'
import sys
path, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: lines = f.readlines()
out, skip = [], False
for line in lines:
    if line.strip() == start: skip = True
    if not skip: out.append(line)
    if skip and line.strip() == end: skip = False
with open(path, "w") as f: f.writelines(out)
PYEOF
}

do_install() {
    echo -e "\n${BOLD}SafeRun Installer${RESET}"
    echo -e "────────────────────────────────────────"

    [ ! -f "$SCRIPT_DIR/saferun.py" ] && {
        echo -e "${RED}✗  saferun.py not found in $SCRIPT_DIR${RESET}"
        echo -e "   Make sure install.sh and saferun.py are in the same folder."
        exit 1
    }

    command -v python3 &>/dev/null || {
        echo -e "${RED}✗  Python 3 not found. Run: sudo apt install python3${RESET}"
        exit 1
    }

    # Install saferun binary
    echo -e "  ${CYAN}→${RESET}  Installing saferun to $INSTALL_DIR ..."
    sudo cp "$SCRIPT_DIR/saferun.py" "$INSTALL_DIR/saferun"
    sudo chmod +x "$INSTALL_DIR/saferun"
    echo -e "  ${GREEN}✓${RESET}  Installed saferun binary"

    # Install click if missing
    if ! python3 -c "import click" 2>/dev/null; then
        echo -e "  ${CYAN}→${RESET}  Installing click (required) ..."
        sudo apt-get install -y python3-click -qq 2>/dev/null || \
        pip3 install click --break-system-packages -q 2>/dev/null
        echo -e "  ${GREEN}✓${RESET}  click installed"
    fi

    # Detect and update shell config
    local cfg
    cfg=$(detect_shell_config)
    echo -e "  ${CYAN}→${RESET}  Shell config: ${BOLD}$cfg${RESET}"

    grep -q "$MARKER" "$cfg" 2>/dev/null && {
        remove_block "$cfg"
        echo -e "  ${YELLOW}!${RESET}  Removed previous SafeRun config"
    }

    { echo ""; echo "$MARKER"; echo "$PROTECTION"; echo "$MARKER_END"; } >> "$cfg"
    echo -e "  ${GREEN}✓${RESET}  Shell functions added to $cfg"

    echo -e "\n${GREEN}${BOLD}SafeRun installed successfully!${RESET}"
    echo -e "${DIM}────────────────────────────────────────${RESET}"
    echo -e "  Protection is ${GREEN}automatic${RESET} — just use your terminal normally."
    echo -e ""
    echo -e "  ${DIM}Activate now:${RESET}  ${CYAN}source $cfg${RESET}"
    echo -e "  ${DIM}Uninstall:${RESET}     ${CYAN}./install.sh --uninstall${RESET}\n"
}

do_uninstall() {
    echo -e "\n${BOLD}SafeRun Uninstaller${RESET}"
    echo -e "────────────────────────────────────────"

    [ -f "$INSTALL_DIR/saferun" ] && {
        command sudo rm "$INSTALL_DIR/saferun"
        echo -e "  ${GREEN}✓${RESET}  Removed $INSTALL_DIR/saferun"
    } || echo -e "  ${YELLOW}!${RESET}  Binary not found — already removed"

    local cfg
    cfg=$(detect_shell_config)
    grep -q "$MARKER" "$cfg" 2>/dev/null && {
        remove_block "$cfg"
        echo -e "  ${GREEN}✓${RESET}  Removed SafeRun functions from $cfg"
    } || echo -e "  ${YELLOW}!${RESET}  No SafeRun config found in $cfg"

    # Remove audit log if it exists
    LOG="$HOME/.saferun.log"
    if [ -f "$LOG" ]; then
        rm "$LOG"
        echo -e "  ${GREEN}✓${RESET}  Removed audit log $LOG"
    else
        echo -e "  ${DIM}  No audit log found${RESET}"
    fi

    echo -e "\n${GREEN}${BOLD}SafeRun uninstalled completely.${RESET}"
    echo -e "  ${DIM}Run: source $cfg${RESET}\n"
}

case "${1:-}" in
    --uninstall|-u) do_uninstall ;;
    --install|-i|"") do_install ;;
    *)
        echo -e "\n${BOLD}Usage:${RESET}"
        echo -e "  ./install.sh              Install SafeRun"
        echo -e "  ./install.sh --uninstall  Uninstall SafeRun\n"
        exit 1 ;;
esac
