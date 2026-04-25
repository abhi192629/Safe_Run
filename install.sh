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
    local target_cmd=""
    local skip_next=0

    # Loop through arguments to isolate the actual command being executed
    for arg in "$@"; do
        # If the previous flag required an argument (e.g., -u root), skip this iteration
        if (( skip_next )); then
            skip_next=0
            continue
        fi

        # Check for sudo flags that expect an argument right after them
        if [[ "$arg" =~ ^(-u|-g|-C|-p|-U|-h|--user|--group|--host)$ ]]; then
            skip_next=1
            continue
        fi

        # The first argument that does not start with - is our target command
        if [[ "$arg" != -* ]]; then
            target_cmd="$arg"
            break
        fi
    done

    # Check the isolated command against our dangerous list
    case "$target_cmd" in
        rm|dd|curl|wget|chmod|chown|mkfs*|shred|rfkill|nmcli|ip|\
        systemctl|passwd|useradd|usermod|iptables|nft|sysctl|apt|apt-get|mv)
            saferun "$@" ;;
        *) command sudo "$@" ;;
    esac
}
if [ -n "$BASH_VERSION" ]; then
    export -f rm dd curl wget chmod chown mkfs shred rfkill nmcli _saferun_ip sudo
fi'

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

    # Remove audit log(s) — match Python LOG_PATH (HOME + SUDO_USER home when sudo)
    _removed_log=0
    _try_rm_log() {
        local f="$1"
        [ -f "$f" ] || return 1
        rm "$f"
        echo -e "  ${GREEN}✓${RESET}  Removed audit log $f"
        _removed_log=1
    }
    _try_rm_log "$HOME/.saferun.log"
    if [ -n "${SUDO_USER:-}" ]; then
        _su_home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)"
        if [ -n "$_su_home" ] && [ "$_su_home" != "$HOME" ]; then
            _try_rm_log "$_su_home/.saferun.log"
        fi
    fi
    [ "$_removed_log" -eq 0 ] && echo -e "  ${DIM}  No audit log found${RESET}"

    echo -e "\n${GREEN}${BOLD}SafeRun is fully removed from the system.${RESET}"
    echo -e "  ${CYAN}Restart your shell to fully remove active functions.${RESET}"
    echo -e "  ${DIM}→${RESET}  restart terminal ${DIM}or run${RESET} ${CYAN}exec \$SHELL${RESET}\n"

    hash -r 2>/dev/null || true
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
