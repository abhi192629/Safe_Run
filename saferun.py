#!/usr/bin/env python3
"""
SafeRun v3.1 — Linux command safety guardian.
Uses structural NLP (shlex) + smart pattern matching.
Zero external dependencies — pure Python stdlib only.
"""

import re, sys, shlex, subprocess, os
from datetime import datetime
from enum import Enum
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache

# ── Terminal colors ───────────────────────────────────────────────────
class C:
    RED    = "\033[91m";  YELLOW = "\033[93m";  GREEN  = "\033[92m"
    CYAN   = "\033[96m";  ORANGE = "\033[38;5;208m"; WHITE = "\033[97m"
    BOLD   = "\033[1m";   DIM    = "\033[2m";   RESET  = "\033[0m"
    BG_RED = "\033[41m"

# ── Risk levels ───────────────────────────────────────────────────────
class Risk(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"

    @property
    def color(self):
        return {Risk.CRITICAL: C.RED, Risk.HIGH: C.YELLOW, Risk.MEDIUM: C.ORANGE}[self]

    @property
    def badge(self):
        icons = {Risk.CRITICAL: "☠", Risk.HIGH: "⚠", Risk.MEDIUM: "⚡"}
        i = icons[self]
        if self == Risk.CRITICAL:
            return f"{C.BG_RED}{C.WHITE}{C.BOLD} {i} {self.value} {C.RESET}"
        return f"{self.color}{C.BOLD} {i} {self.value} {C.RESET}"

# ── Data structures ───────────────────────────────────────────────────
@dataclass(frozen=True)
class Profile:
    level:        Risk
    title:        str
    explanation:  str
    consequences: tuple
    tip:          str
    danger_parts: tuple = field(default_factory=tuple)  # which parts are dangerous

@dataclass
class Cmd:
    """Parsed, normalised shell command."""
    raw:      str          # original input
    norm:     str          # normalised (collapsed whitespace, stripped)
    binary:   str          # first token e.g. "rm"
    flags:    List[str]    # expanded flags e.g. ["-r", "-f"]
    args:     List[str]    # non-flag args
    targets:  List[str]    # path-like args
    has_pipe: bool
    has_sudo: bool
    is_echo:  bool         # command is inside echo/printf quotes

# ── NLP Command Parser ────────────────────────────────────────────────
class Parser:
    """
    Structural NLP layer.
    - Normalises whitespace before analysis (fixes 'rm    -rf    /')
    - Uses shlex for proper quote/escape awareness
    - Detects echo/printf context to avoid false positives
    - Expands combined short flags (-rf → [-r, -f])
    """

    SYS_DIRS = frozenset([
        "/", "/bin", "/sbin", "/lib", "/lib64",
        "/usr", "/boot", "/etc", "/dev", "/proc", "/sys"
    ])
    DEV_DISK = re.compile(
        r'^/dev/(?:sd[a-z]\d*|hd[a-z]\d*|nvme\d+n\d+(?:p\d+)?|vd[a-z]\d*)$'
    )
    # Paths that are generally safe to delete recursively
    SAFE_PATHS = frozenset(["/tmp", "/var/tmp", "/var/cache", "/var/log"])

    @classmethod
    @lru_cache(maxsize=1024)
    def parse(cls, raw: str) -> Cmd:
        # ── Fix 1: Normalise whitespace before analysis ───────────────
        norm = " ".join(raw.strip().split())

        has_pipe = bool(re.search(r'\|', norm))

        # ── Fix 2: Detect echo/printf context (false positive prevention)
        is_echo = bool(re.match(r'^(?:echo|printf)\s', norm))

        try:
            tokens = shlex.split(norm)
        except ValueError:
            tokens = norm.split()

        if not tokens:
            return Cmd(raw, norm, "", [], [], [], has_pipe, False, is_echo)

        has_sudo = tokens[0] == "sudo"
        if has_sudo:
            tokens = tokens[1:]
        if not tokens:
            return Cmd(raw, norm, "", [], [], [], has_pipe, has_sudo, is_echo)

        binary = tokens[0]
        flags, args = [], []
        for tok in tokens[1:]:
            if tok.startswith("-"):
                # Expand combined flags: -rf → [-r, -f]
                if len(tok) > 2 and not tok.startswith("--"):
                    flags.extend(f"-{c}" for c in tok[1:])
                else:
                    flags.append(tok)
            else:
                args.append(tok)

        targets = [a for a in args if a.startswith(("/", "~", "."))]
        return Cmd(raw, norm, binary, flags, args, targets,
                   has_pipe, has_sudo, is_echo)

    @classmethod
    def flag(cls, c: Cmd, *fs: str) -> bool:
        return any(f in c.flags for f in fs)

    @classmethod
    def is_recursive(cls, c: Cmd) -> bool:
        return cls.flag(c, "-r", "-R", "--recursive")

    @classmethod
    def targets_system(cls, c: Cmd) -> bool:
        return any(
            t in cls.SYS_DIRS or t.rstrip("/") in cls.SYS_DIRS
            or re.match(r'^/\*', t) or cls.DEV_DISK.match(t)
            for t in c.targets
        )

    @classmethod
    def targets_safe_path(cls, c: Cmd) -> bool:
        """True if ALL targets are under known-safe directories like /tmp."""
        if not c.targets:
            return False
        return all(
            any(t.startswith(s) for s in cls.SAFE_PATHS)
            for t in c.targets
        )

    @classmethod
    def resolve_path(cls, path: str) -> str:
        """Resolve simple relative paths like ./../ to understand intent."""
        import os
        try:
            resolved = os.path.normpath(path)
            return resolved
        except Exception:
            return path

    @classmethod
    def targets_root_resolved(cls, c: Cmd) -> bool:
        """Check if any target resolves to / even via relative paths."""
        for t in c.targets:
            resolved = cls.resolve_path(t)
            if resolved in cls.SYS_DIRS or resolved == "/":
                return True
            # Variable expansion hint: $HOME, $PWD etc pointing to root
            if re.match(r'^\$(?:HOME|PWD|OLDPWD|USER)?$', t):
                return True
        return False

# ── Danger part highlighter ───────────────────────────────────────────
def highlight_danger(cmd: str, parts: tuple) -> str:
    """Underline the dangerous parts of the command string."""
    result = cmd
    for part in parts:
        result = result.replace(part, f"{C.RED}{C.BOLD}{part}{C.RESET}{C.CYAN}")
    return f"{C.CYAN}{result}{C.RESET}"

# ── Semantic detectors ────────────────────────────────────────────────
P = Parser

def _skip(c: Cmd) -> bool:
    """Skip if this is SafeRun calling itself (infinite loop prevention)."""
    return "saferun" in c.binary or "saferun" in " ".join(c.args)

def _is_rm(c: Cmd) -> bool:
    """True if command is rm and not inside echo/printf context."""
    return c.binary == "rm" and not c.is_echo

def _rm_root(c: Cmd) -> Optional[tuple]:
    """rm recursively targeting / or root wildcard."""
    if not _is_rm(c): return None
    if not P.is_recursive(c): return None
    for a in c.args:
        resolved = P.resolve_path(a)
        if a in ("/", "/*") or re.match(r'^/\*', a) or resolved == "/":
            return ("-r or -R or --recursive", a)
    return None

def _rm_sysdir(c: Cmd) -> Optional[tuple]:
    """rm recursively on critical system directories."""
    if not _is_rm(c): return None
    if not P.is_recursive(c): return None
    if P.targets_safe_path(c): return None   # /tmp etc are fine
    if P.targets_system(c):
        bad = [t for t in c.targets if t in P.SYS_DIRS or t.rstrip("/") in P.SYS_DIRS]
        return ("-r or -R", bad[0] if bad else "system path")
    return None

def _rm_wildcard(c: Cmd) -> Optional[tuple]:
    if not _is_rm(c): return None
    for a in c.args:
        if re.match(r'^/\*', a):
            return ("/*", a)
    return None

def _dd_disk(c: Cmd) -> Optional[tuple]:
    if c.binary != "dd": return None
    for a in c.args:
        if a.startswith("of="):
            dev = a.split("=", 1)[-1]
            if P.DEV_DISK.match(dev):
                return ("of=", dev)
    return None

def _mkfs(c: Cmd) -> Optional[tuple]:
    if not c.binary.startswith("mkfs"): return None
    for t in c.targets:
        if P.DEV_DISK.match(t):
            return (c.binary, t)
    return None

def _mv_null(c: Cmd) -> Optional[tuple]:
    if c.binary == "mv" and "/dev/null" in c.args:
        return ("/dev/null",)
    return None

def _chmod777(c: Cmd) -> Optional[tuple]:
    if c.binary == "chmod" and "777" in c.args and P.targets_system(c):
        return ("777",)
    return None

def _chmodR_sys(c: Cmd) -> Optional[tuple]:
    if c.binary == "chmod" and P.is_recursive(c) and P.targets_system(c):
        return ("-R on system path",)
    return None

def _kill1(c: Cmd) -> Optional[tuple]:
    if c.binary == "kill" and P.flag(c, "-9", "-SIGKILL"):
        # kill -9 1  → kill PID 1 (init/systemd) — "1" appears as arg
        if "1" in c.args:
            return ("-9", "PID 1")
        # kill -9 -1 → kill ALL processes — "-1" parsed as flag by shlex
        if "-1" in c.flags:
            return ("-9", "-1 (kills ALL processes)")
    if c.binary == "killall" and any(a in ("systemd", "init") for a in c.args):
        return ("systemd/init",)
    return None

def _net_disable(c: Cmd) -> Optional[tuple]:
    if c.binary != "systemctl": return None
    bad_actions   = {"disable", "mask", "stop"}
    bad_services  = {"NetworkManager", "network", "systemd-networkd",
                     "bluetooth", "wpa_supplicant"}
    act = next((a for a in c.args if a in bad_actions), None)
    svc = next((a for a in c.args if a in bad_services), None)
    if act and svc:
        return (act, svc)
    return None

def _rfkill(c: Cmd) -> Optional[tuple]:
    if c.binary == "rfkill" and "block" in c.args:
        target = next((a for a in c.args if a in ("wifi","wlan","bluetooth","bt","all")), None)
        if target:
            return ("block", target)
    return None

def _ifc_down(c: Cmd) -> Optional[tuple]:
    if c.binary == "ifconfig" and "down" in c.args:
        iface = next((a for a in c.args if a != "down"), "interface")
        return (iface, "down")
    return None

def _ip_down(c: Cmd) -> Optional[tuple]:
    if c.binary == "ip" and all(k in c.args for k in ("link","set","down")):
        return ("link set", "down")
    return None

def _nmcli(c: Cmd) -> Optional[tuple]:
    if c.binary == "nmcli" and "radio" in c.args and "off" in c.args:
        return ("radio", "off")
    return None

def _ipt_flush(c: Cmd) -> Optional[tuple]:
    if c.binary == "iptables" and P.flag(c, "-F", "--flush"):
        return ("-F (flush all rules)",)
    return None

def _uid0(c: Cmd) -> Optional[tuple]:
    if c.binary in ("useradd","usermod") and P.flag(c,"-u") and "0" in c.args:
        return ("-u 0",)
    return None

def _pipe_exec(c: Cmd) -> Optional[tuple]:
    """Fix 4: Better pipe detection — curl/wget piped to a shell."""
    if c.binary in ("curl","wget") and c.has_pipe:
        return ("| bash/sh",)
    return None

def _root_shell(c: Cmd) -> Optional[tuple]:
    if c.has_sudo and c.binary in ("bash","sh","zsh","fish","su","csh","ksh"):
        return (f"sudo {c.binary}",)
    return None

def _ip_forward(c: Cmd) -> Optional[tuple]:
    if c.binary == "sysctl" and any("ip_forward" in a and "1" in a for a in c.args):
        return ("ip_forward=1",)
    return None

def _rm_generic(c: Cmd) -> Optional[tuple]:
    """Fix 5: /tmp and /var/tmp are safe — don't flag as medium."""
    if not _is_rm(c): return None
    if not P.is_recursive(c): return None
    if P.targets_safe_path(c): return None
    if c.args:
        return ("-r or -R",)
    return None

def _sudo_rm(c: Cmd) -> Optional[tuple]:
    if c.has_sudo and c.binary == "rm":
        return ("sudo rm",)
    return None

def _dd_any(c: Cmd) -> Optional[tuple]:
    if c.binary == "dd" and any(a.startswith(("if=","of=")) for a in c.args):
        return ("dd raw I/O",)
    return None

def _chownR_sys(c: Cmd) -> Optional[tuple]:
    if c.binary == "chown" and P.is_recursive(c) and P.targets_system(c):
        return ("-R on system path",)
    return None

def _svc_stop(c: Cmd) -> Optional[tuple]:
    if c.binary == "systemctl" and "stop" in c.args:
        svc = next((a for a in c.args if a != "stop"), "service")
        return ("stop", svc)
    return None

def _apt_critical(c: Cmd) -> Optional[tuple]:
    if c.binary not in ("apt","apt-get"): return None
    if not any(a in ("remove","purge") for a in c.args): return None
    critical = {"linux-image","grub","grub2","systemd","udev","libc6","bash","init"}
    bad = next((a for a in c.args if any(k in a for k in critical)), None)
    return (bad,) if bad else None

def _shred(c: Cmd) -> Optional[tuple]:
    if c.binary == "shred" and c.args:
        return ("shred",)
    return None

# ── Compact rule builder ──────────────────────────────────────────────
def rule(lvl: str, title: str, expl: str, cons: tuple, tip: str,
         detector=None, pattern: str = None):
    """Build a rule dict. Cleaner than a class for this use case."""
    return {
        "profile_args": (lvl, title, expl, cons, tip),
        "detector":     detector,
        "pattern":      re.compile(pattern) if pattern else None,
    }


def _crontab_r(c: Cmd) -> Optional[tuple]:
    """crontab -r removes all scheduled cron jobs with no confirmation."""
    if c.binary == "crontab" and P.flag(c, "-r"):
        return ("-r",)
    return None

def _history_exec(c: Cmd) -> Optional[tuple]:
    """history | sh/bash re-executes every previously run command."""
    if c.binary == "history" and c.has_pipe:
        return ("history", "| sh/bash")
    return None


def _rm_boot(c: Cmd) -> Optional[tuple]:
    """rm targeting /boot — removes bootloader and kernel files."""
    if c.binary != "rm" or c.is_echo: return None
    if any(t.startswith("/boot") for t in c.targets):
        return ("/boot",)
    return None

def _rm_config(c: Cmd) -> Optional[tuple]:
    """rm targeting hidden user config dirs like ~/.ssh, ~/.gnupg."""
    if c.binary != "rm" or c.is_echo: return None
    # Dangerous even without -rf: rm ~/.ssh removes the dir if empty, -rf removes it always
    if any(t.startswith("~/.") and t not in ("~/.bashrc","~/.zshrc","~/.profile","~/.bash_profile") for t in c.targets):
        return ("user config directory",)
    return None

def _rm_shellrc(c: Cmd) -> Optional[tuple]:
    """rm targeting shell config files ~/.bashrc ~/.zshrc."""
    if not _is_rm(c): return None
    if any(t in ("~/.bashrc", "~/.zshrc", "~/.profile", "~/.bash_profile") for t in c.targets):
        return ("shell config file",)
    return None

def _stop_ssh(c: Cmd) -> Optional[tuple]:
    """systemctl stop/disable ssh — kills all active SSH connections."""
    if c.binary != "systemctl": return None
    has_action = any(a in c.args for a in ("stop", "disable", "mask"))
    has_ssh    = any(s in c.args for s in ("ssh", "sshd", "openssh-server"))
    if has_action and has_ssh:
        return ("ssh",)
    return None

def _umount_all(c: Cmd) -> Optional[tuple]:
    """umount -a — unmounts ALL filesystems including root."""
    if c.binary == "umount" and P.flag(c, "-a", "--all"):
        return ("-a (all filesystems)",)
    return None

RULES = [
    # ── CRITICAL ──────────────────────────────────────────────────────

    rule("CRITICAL", "Recursive delete of root filesystem",
         "Attempts to delete every file on the system starting from /.",
         ("Permanently destroys the OS", "All user data lost",
          "System becomes unbootable", "No undo possible"),
         "Almost no valid use case for this. Check your path carefully.",
         detector=_rm_root,
         pattern=r'rm\s+.*--no-preserve-root'),

    rule("CRITICAL", "Deleting the /boot directory",
         "Removes the bootloader, kernel, and initramfs — the files needed to start Linux.",
         ("System will not boot after next restart",
          "Requires a live USB to repair or reinstall",
          "Cannot be undone without recovery media"),
         "Never delete /boot. If you need to clean old kernels use: apt autoremove",
         detector=_rm_boot),

    rule("CRITICAL", "Recursive delete of critical system directory",
         "Removes core OS binaries, libraries, or configuration files.",
         ("System stops functioning immediately", "Critical services will fail",
          "May brick the installation"),
         "Verify path with ls first. Test dangerous operations in a VM.",
         detector=_rm_sysdir),

    rule("CRITICAL", "Root wildcard deletion — rm /*",
         "Deletes all files and directories directly under /.",
         ("Destroys top-level OS structure", "System becomes unbootable",
          "Permanent data loss"),
         "You likely meant ~/something not /*. Double-check the path.",
         detector=_rm_wildcard),

    rule("CRITICAL", "Fork bomb detected",
         "Self-replicating process that spawns exponentially until the system freezes.",
         ("System becomes completely unresponsive", "Requires a hard reboot",
          "May cause filesystem corruption"),
         "Only run fork bombs in isolated VMs with ulimit -u 50 set first.",
         pattern=r':\s*\(\s*\)\s*\{.*:\|:&.*\}'),

    rule("CRITICAL", "Writing directly to a block device",
         "Raw write to a storage device overwrites the partition table and all data.",
         ("Immediate permanent data loss", "OS may become unbootable",
          "Affects the entire disk not just a partition"),
         "Confirm the correct device with lsblk before writing.",
         detector=_dd_disk),

    rule("CRITICAL", "Formatting a disk or partition",
         "Wipes and reformats a disk partition erasing all existing data.",
         ("All data on the partition permanently erased",
          "Filesystem and partition structure overwritten"),
         "Run lsblk to confirm the correct device first.",
         detector=_mkfs),

    rule("CRITICAL", "Moving files into /dev/null",
         "Files moved to /dev/null are silently destroyed and unrecoverable.",
         ("Permanent and silent data loss", "No trash — gone immediately"),
         "Use rm with confirmation or move to a temp folder first.",
         detector=_mv_null),

    rule("CRITICAL", "Overwriting a critical system config file via redirect",
         "Using > to redirect output into /etc/passwd or /etc/shadow truncates the file.",
         ("Authentication breaks — no one can log in",
          "sudo access is lost if sudoers is wiped",
          "System may not boot if fstab is cleared"),
         "Edit config files with a text editor. Backup first: cp /etc/file /etc/file.bak",
         pattern=r'>\s*/etc/(passwd|shadow|sudoers|fstab|hosts|hostname)'),

    rule("CRITICAL", "Overwriting disk with empty data",
         "Redirecting output to a raw disk device destroys it byte by byte.",
         ("Immediate data loss on the target disk",
          "Partition table and all files destroyed"),
         "Only do this intentionally. Always confirm device with lsblk.",
         pattern=r'>\s*/dev/(?:sd[a-z]|nvme\d+n\d+|hd[a-z]|vd[a-z])'),

    # ── HIGH ──────────────────────────────────────────────────────────

    rule("HIGH", "World-writable permissions on system paths",
         "chmod 777 makes files writable by every user on the system.",
         ("Massive security vulnerability",
          "Any user can modify or delete system files",
          "SSHd and sudo refuse to work with 777 permissions"),
         "Use minimum permissions: 755 for directories, 644 for files.",
         detector=_chmod777),

    rule("HIGH", "Recursive permission change on system directory",
         "Changing permissions recursively breaks authentication and core services.",
         ("sudo and SSH may stop working", "System services may fail to start",
          "Hard to reverse without knowing original permissions"),
         "Check current permissions with stat. Apply only to user-owned dirs.",
         detector=_chmodR_sys),

    rule("HIGH", "Killing PID 1 or all processes",
         "kill -9 1 kills init/systemd causing kernel panic. kill -9 -1 kills ALL your processes.",
         ("Instant system crash or complete session wipeout",
          "Unsaved data in all running apps lost", "Requires hard reboot"),
         "Use systemctl restart service-name or kill specific PIDs instead.",
         detector=_kill1),

    rule("HIGH", "Stopping the SSH service",
         "Kills all active SSH sessions and prevents new remote connections.",
         ("All remote SSH sessions disconnect immediately",
          "Remote access to this machine is lost until SSH is restarted",
          "If managing a remote server you will be locked out"),
         "Use systemctl restart ssh instead of stop. Ensure console access before stopping.",
         detector=_stop_ssh),

    rule("HIGH", "Disabling a network or Bluetooth service",
         "Permanently disables network or Bluetooth connectivity.",
         ("Wi-Fi and Bluetooth stop working immediately",
          "May require a reboot to restore",
          "Remote SSH sessions over Wi-Fi will disconnect"),
         "Use systemctl restart NetworkManager instead of disable.",
         detector=_net_disable),

    rule("HIGH", "Blocking Wi-Fi or Bluetooth at hardware level",
         "rfkill block disables the radio at kernel level.",
         ("Stops working system-wide", "Persists across reboots on some systems"),
         "To restore: rfkill unblock wifi — Check status: rfkill list",
         detector=_rfkill),

    rule("HIGH", "Bringing down a network interface via ifconfig",
         "Disables a network interface cutting all traffic through it.",
         ("Internet drops instantly", "SSH sessions over this interface disconnect"),
         "To restore: ifconfig interface-name up",
         detector=_ifc_down),

    rule("HIGH", "Bringing down a network interface via ip link",
         "Disables a network interface at the kernel level.",
         ("Internet drops instantly", "SSH sessions terminate"),
         "To restore: ip link set interface-name up",
         detector=_ip_down),

    rule("HIGH", "Turning off Wi-Fi via nmcli",
         "NetworkManager disables the Wi-Fi radio immediately.",
         ("All Wi-Fi connections drop instantly", "May persist after reboot"),
         "To restore: nmcli radio wifi on",
         detector=_nmcli),

    rule("HIGH", "Flushing all firewall rules",
         "Removes all active firewall rules leaving the system fully exposed.",
         ("All ports become open", "Intrusion protection removed"),
         "Save rules first with iptables-save. Use ufw for simplicity.",
         detector=_ipt_flush,
         pattern=r'nft\s+flush\s+ruleset'),

    rule("HIGH", "Enabling IP forwarding",
         "Turns the machine into a network router.",
         ("Can expose internal network externally",
          "Security risk on public networks"),
         "Revert with: sysctl -w net.ipv4.ip_forward=0",
         detector=_ip_forward),

    rule("HIGH", "Creating a user with UID 0",
         "UID 0 grants unrestricted root access to any user.",
         ("Creates a hidden root backdoor", "Major security vulnerability"),
         "Use sudo or group membership instead of UID 0.",
         detector=_uid0),

    rule("HIGH", "Piping remote script directly into shell",
         "Downloads and immediately executes a script from the internet.",
         ("Arbitrary code runs with your privileges",
          "No chance to review what executes"),
         "Download first: curl -o script.sh url — inspect it — then run.",
         detector=_pipe_exec),

    rule("HIGH", "Dropping into a persistent root shell",
         "Opens an interactive shell with full unrestricted root privileges.",
         ("All commands run as root without prompts",
          "No per-command audit trail"),
         "Use sudo command for individual tasks instead.",
         detector=_root_shell),

    rule("HIGH", "Changing the root password",
         "Changes the password for the root superuser account.",
         ("Loss of root access if password is forgotten",),
         "Document the new password securely.",
         pattern=r'\bsudo\s+passwd\s+root\b'),

    rule("HIGH", "Aggressive network scan",
         "Sends crafted packets to remote hosts for OS detection or scripting.",
         ("May violate terms of service", "Could be illegal without permission"),
         "Only scan networks you own or have written permission to test.",
         pattern=r'\bnmap\s+.*(?:-sS|-sU|-O|--script)\b'),

    rule("HIGH", "Piping command history directly into shell",
         "history | sh re-executes every command you have previously run.",
         ("Runs potentially destructive past commands again",
          "May re-execute commands that were run by mistake"),
         "Never pipe history to a shell. Review history with just: history",
         detector=_history_exec),

    rule("HIGH", "Deleting a shell configuration file",
         "Removes ~/.bashrc or ~/.zshrc which store your aliases and environment settings.",
         ("Terminal loses all custom settings and aliases immediately",
          "SafeRun protection wrappers will be removed",
          "PATH and other variables may reset on next login"),
         "Back up first: cp ~/.bashrc ~/.bashrc.bak — then edit carefully.",
         detector=_rm_shellrc),

    rule("HIGH", "Deleting a hidden user configuration directory",
         "Removes config folders like ~/.ssh, ~/.gnupg that store SSH keys and settings.",
         ("SSH keys permanently lost — locked out of remote servers",
          "Application settings and credentials wiped",
          "Some losses like GPG keys cannot be recovered"),
         "Back up ~/.ssh and ~/.gnupg before deleting. Use ls -la ~ to check first.",
         detector=_rm_config),

    rule("HIGH", "Unmounting all filesystems",
         "umount -a attempts to unmount every mounted filesystem including critical ones.",
         ("Running processes lose access to their files",
          "System may become unstable or unresponsive",
          "Data being written may be corrupted"),
         "Only unmount specific filesystems. Use umount /dev/sdX instead.",
         detector=_umount_all),

    rule("HIGH", "Overwriting or clearing the system PATH variable",
         "Setting PATH to empty makes every command stop working immediately.",
         ("All commands fail with 'command not found'",
          "Cannot run any program — even ls or cd stop working",
          "Recovery requires knowing full paths like /bin/bash"),
         "Never clear PATH. Add to it safely: export PATH=$PATH:/new/dir",
         pattern=r'export\s+PATH=\s*$'),

    # ── MEDIUM ────────────────────────────────────────────────────────

    rule("MEDIUM", "Recursive file or directory deletion",
         "Permanently deletes a directory and everything inside it.",
         ("No trash — files are gone immediately",
          "Accidental wildcards can wipe unintended directories"),
         "Use rm -ri for interactive confirmation or install trash-cli.",
         detector=_rm_generic),

    rule("MEDIUM", "Removing files with root privileges",
         "sudo rm bypasses file ownership and can delete any file.",
         ("Can remove system-owned files",
          "No permission errors to warn you if the path is wrong"),
         "Double-check your path. Preview with ls before deleting.",
         detector=_sudo_rm),

    rule("MEDIUM", "Raw disk I/O with dd",
         "dd reads and writes raw bytes. Wrong source or destination is catastrophic.",
         ("Wrong of= target can overwrite a live disk",),
         "Always verify if= and of= carefully. Add status=progress bs=4M.",
         detector=_dd_any),

    rule("MEDIUM", "Overwriting a critical system config file",
         "Redirecting output to a core config file truncates its entire contents.",
         ("Authentication may break", "System may not boot",
          "sudo access may be lost"),
         "Edit config files with a text editor. Always backup first.",
         pattern=r'>\s*/etc/(?!passwd\b|shadow\b|sudoers\b|fstab\b|hosts\b|hostname\b)\w+'),

    rule("MEDIUM", "Recursive ownership change on system paths",
         "Changing ownership of system files breaks services that depend on it.",
         ("sudo and SSH may stop working",),
         "Limit recursive chown to your own data directories only.",
         detector=_chownR_sys),

    rule("MEDIUM", "Stopping a system service",
         "Terminates all processes of the service immediately.",
         ("Active connections through the service will drop",),
         "Use systemctl status service-name to check before stopping.",
         detector=_svc_stop),

    rule("MEDIUM", "Removing a critical system package",
         "Uninstalling the kernel, bootloader, or init system breaks the OS.",
         ("System may not boot after the next restart",),
         "Use apt-mark hold package-name to prevent accidental removal.",
         detector=_apt_critical),

    rule("MEDIUM", "Secure file or disk wipe",
         "Overwrites file contents multiple times to prevent forensic recovery.",
         ("Data is permanently unrecoverable",),
         "For SSDs shred is less effective. Use cryptsetup for full disk encryption.",
         detector=_shred),

    rule("MEDIUM", "Removing all cron jobs with crontab -r",
         "crontab -r silently deletes your entire crontab file with no confirmation.",
         ("All scheduled tasks are permanently deleted",
          "Easy to mistype — -r instead of -e opens the editor"),
         "Use crontab -e to edit safely. Backup first: crontab -l > crontab_backup.txt",
         detector=_crontab_r),
]


# ── Precomputed rule lists (Fix 5 — faster lookup) ───────────────────
# Split into detector-only and pattern-only lists at startup
# Detectors run first (structural NLP), patterns second (regex fallback)
DETECTOR_RULES = [r for r in RULES if r["detector"]]
PATTERN_RULES  = [r for r in RULES if r["pattern"]]

# ── Engine ────────────────────────────────────────────────────────────
@lru_cache(maxsize=1024)
def analyse(cmd: str):
    """
    Returns Profile or None.
    - Skips empty commands immediately
    - Skips SafeRun itself to prevent infinite loops
    - Runs detector rules first, pattern rules second
    """
    # Early exit — prevents unnecessary parsing
    if not cmd.strip():
        return None

    c = Parser.parse(cmd)

    # Prevent infinite loop — never analyse calls to saferun itself
    if _skip(c):
        return None

    # For echo/printf: only run PATTERN rules (catches redirects like echo '' > /etc/passwd)
    # Skip SEMANTIC detectors for echo (avoids false positive: echo "rm -rf /")

    # Step 1 — run semantic detectors (NLP structural analysis)
    # Skip for echo/printf context to avoid false positives
    if not c.is_echo:
        for r in DETECTOR_RULES:
            danger = r["detector"](c)
            if danger is not None:
                lvl, title, expl, cons, tip = r["profile_args"]
                return Profile(Risk[lvl], title, expl, cons, tip, danger)

    # Step 2 — run pattern rules (regex fallback)
    # Patterns run on echo context too UNLESS it is not a redirect
    # echo ":(){:|:&};:" is safe, but echo "" > /etc/passwd is dangerous
    pattern_target = cmd
    if c.is_echo:
        import re as _re
        if not _re.search(r'>\s*/(?:etc|dev)/', cmd):
            pattern_target = ""   # suppress patterns for non-redirect echo
    if pattern_target:
        for r in PATTERN_RULES:
            if r["pattern"].search(pattern_target):
                lvl, title, expl, cons, tip = r["profile_args"]
                return Profile(Risk[lvl], title, expl, cons, tip, ())

    return None

# ── Renderer ──────────────────────────────────────────────────────────
SEP_WIDTH = 66

def _sep(color): return f"{color}{'━' * SEP_WIDTH}{C.RESET}"

def warn(cmd: str, p: Profile) -> None:
    s = _sep(p.level.color)
    print(f"\n{s}")
    print(f"  {p.level.badge}  {C.BOLD}{p.title}{C.RESET}")
    print(s)

    # Show command with dangerous parts highlighted
    display = highlight_danger(cmd, p.danger_parts) if p.danger_parts else f"{C.CYAN}{cmd}{C.RESET}"
    print(f"\n  {C.BOLD}Command:{C.RESET}")
    print(f"  {C.DIM}${C.RESET} {display}\n")

    # Show what's dangerous (killer feature — shows WHICH part)
    if p.danger_parts:
        print(f"  {C.BOLD}Danger detected in:{C.RESET}")
        for part in p.danger_parts:
            print(f"  {p.level.color}→{C.RESET}  {C.BOLD}{part}{C.RESET}")
        print()

    print(f"  {C.BOLD}What this does:{C.RESET}")
    print(f"  {p.explanation}\n")
    print(f"  {C.BOLD}Potential consequences:{C.RESET}")
    for c in p.consequences:
        print(f"  {p.level.color}✗{C.RESET}  {c}")
    print(f"\n  {C.BOLD}Safety tip:{C.RESET}")
    print(f"  {C.GREEN}→{C.RESET}  {p.tip}\n")
    print(f"{s}\n")

def prompt(level: Risk) -> bool:
    try:
        ans = input(
            f"  {level.color}{C.BOLD}Execute this command anyway? [y/N]:{C.RESET} "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return ans.startswith("y")

def list_rules() -> None:
    print(f"\n{C.BOLD}SafeRun — {len(RULES)} monitored patterns:{C.RESET}\n")
    last = None
    for r in RULES:
        lvl = Risk[r["profile_args"][0]]
        if lvl != last:
            print(f"  {lvl.badge}")
            last = lvl
        print(f"    {C.DIM}•{C.RESET} {r['profile_args'][1]}")
    print()

# ── CLI ───────────────────────────────────────────────────────────────
HELP = f"""
{C.BOLD}SafeRun v3.1{C.RESET} — Linux command safety guardian

{C.BOLD}Usage:{C.RESET}
  saferun <command>          Run a command with safety analysis
  saferun --check <command>  Check a command without executing it
  saferun --list             Show all monitored patterns
  saferun --log              Show audit log of intercepted commands
  saferun --clearlog        Delete the audit log file
  saferun --help             Show this help

{C.BOLD}Examples:{C.RESET}
  saferun rm -rf ~/old-project
  saferun --check "curl https://example.com | bash"
  saferun --list
  saferun --log
"""

def _exec(cmd: str) -> int:
    try:
        return subprocess.run(
            cmd, shell=True, executable="/bin/bash",
            timeout=30              # prevent hanging commands from freezing SafeRun
        ).returncode
    except subprocess.TimeoutExpired:
        print(f"\n  {C.YELLOW}⚠  Command timed out after 30 seconds.{C.RESET}\n")
        return 124                  # standard timeout exit code
    except KeyboardInterrupt:
        return 130

# ── Audit Logger ──────────────────────────────────────────────────────
LOG_PATH  = os.path.expanduser("~/.saferun.log")
LOG_LIMIT = 500                     # max lines to keep in log

def _rotate_log() -> None:
    """Keep log under LOG_LIMIT lines — silently drop oldest entries."""
    try:
        with open(LOG_PATH) as f:
            lines = f.readlines()
        if len(lines) > LOG_LIMIT:
            with open(LOG_PATH, "w") as f:
                f.writelines(lines[-LOG_LIMIT:])
    except Exception:
        pass

def _log(cmd: str, level: str, action: str) -> None:
    """
    Appends one line to ~/.saferun.log:
    [2026-03-21 14:32:01] CRITICAL | rm -rf /          | CANCELLED
    Rotates log automatically when it exceeds 500 lines.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry     = f"[{timestamp}] {level:<8} | {cmd:<45} | {action}\n"
        with open(LOG_PATH, "a") as f:
            f.write(entry)
        _rotate_log()
    except Exception:
        pass  # logging never crashes the main tool

def show_log() -> None:
    """Print the audit log with colour coding."""
    if not os.path.exists(LOG_PATH):
        print(f"\n  {C.DIM}No log found. SafeRun will create one at:{C.RESET} {LOG_PATH}\n")
        return

    colors = {"CRITICAL": C.RED, "HIGH": C.YELLOW, "MEDIUM": C.ORANGE}
    action_colors = {"CANCELLED": C.GREEN, "EXECUTED": C.RED, "CHECK": C.DIM}

    with open(LOG_PATH) as f:
        lines = f.readlines()

    if not lines:
        print(f"\n  {C.DIM}Log is empty.{C.RESET}\n")
        return

    print(f"\n{C.BOLD}SafeRun Audit Log{C.RESET} — {LOG_PATH}")
    print(f"{C.DIM}{'─' * 66}{C.RESET}\n")
    for line in lines[-50:]:   # show last 50 entries
        line = line.rstrip()
        # Colour the risk level word
        for lvl, col in colors.items():
            if lvl in line:
                line = line.replace(lvl, f"{col}{C.BOLD}{lvl}{C.RESET}")
                break
        # Colour the action word
        for act, col in action_colors.items():
            if act in line:
                line = line.replace(act, f"{col}{C.BOLD}{act}{C.RESET}")
                break
        print(f"  {line}")
    print(f"\n{C.DIM}Showing last {min(50, len(lines))} of {len(lines)} entries.{C.RESET}")
    print(f"{C.DIM}Full log: {LOG_PATH}{C.RESET}\n")

def clear_log() -> None:
    """Delete the audit log file completely."""
    if not os.path.exists(LOG_PATH):
        print(f"\n  {C.DIM}No log file found — nothing to clear.{C.RESET}\n")
        return
    try:
        # Ask for confirmation before deleting
        print(f"\n  {C.YELLOW}This will permanently delete:{C.RESET} {LOG_PATH}")
        ans = input(f"  {C.BOLD}Are you sure? [y/N]:{C.RESET} ").strip().lower()
        if ans.startswith("y"):
            os.remove(LOG_PATH)
            print(f"  {C.GREEN}✓  Audit log deleted.{C.RESET}\n")
        else:
            print(f"  {C.GREEN}✓  Cancelled — log kept.{C.RESET}\n")
    except Exception as e:
        print(f"  {C.RED}✗  Could not delete log: {e}{C.RESET}\n")

def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(HELP); sys.exit(0)

    if args[0] in ("--list", "list"):
        list_rules(); sys.exit(0)

    if args[0] in ("--log", "log"):
        show_log(); sys.exit(0)

    if args[0] in ("--clearlog", "clearlog"):
        clear_log(); sys.exit(0)

    check_only = args[0] in ("--check", "check")
    if check_only:
        args = args[1:]

    if not args:
        print(f"{C.RED}Error: No command provided.{C.RESET}"); sys.exit(1)

    cmd    = " ".join(args)
    result = analyse(cmd)

    if result is None:
        if check_only:
            print(f"\n  {C.GREEN}✓  No known risks detected for:{C.RESET} {C.CYAN}{cmd}{C.RESET}\n")
            sys.exit(0)
        sys.exit(_exec(cmd))

    warn(cmd, result)

    if check_only:
        _log(cmd, result.level.value, "CHECK")
        print(f"  {C.DIM}(--check mode: command not executed){C.RESET}\n")
        sys.exit(1)

    if prompt(result.level):
        _log(cmd, result.level.value, "EXECUTED")
        print(f"\n  {C.DIM}Executing...{C.RESET}\n")
        sys.exit(_exec(cmd))
    else:
        _log(cmd, result.level.value, "CANCELLED")
        print(f"\n  {C.GREEN}✓  Command cancelled.{C.RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
