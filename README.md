```
 ███████╗ █████╗ ███████╗███████╗██████╗ ██╗   ██╗███╗   ██╗
 ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║   ██║████╗  ██║
 ███████╗███████║█████╗  █████╗  ██████╔╝██║   ██║██╔██╗ ██║
 ╚════██║██╔══██║██╔══╝  ██╔══╝  ██╔══██╗██║   ██║██║╚██╗██║
 ███████║██║  ██║██║     ███████╗██║  ██║╚██████╔╝██║ ╚████║
 ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
```

**A safety layer for your Linux terminal.**
Detects common dangerous command patterns, warns you before execution, and asks for confirmation.

[![Python](https://img.shields.io/badge/Python-3.6+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?style=flat-square&logo=linux&logoColor=black)](https://kernel.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Shell](https://img.shields.io/badge/Shell-bash%20%7C%20zsh-89e051?style=flat-square)](https://gnu.org/software/bash)
[![Rules](https://img.shields.io/badge/Rules-42-orange?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Tests-21%2F21%20passing-brightgreen?style=flat-square)]()

---

## What is SafeRun?

SafeRun is a rule-based command safety tool for Linux. Every command you type is checked against 42 known dangerous patterns. If a pattern matches, SafeRun pauses, explains what the command does, what could break, and asks whether you want to continue.

Commands that do not match any rule run immediately with no interruption. Only risky patterns trigger a warning.

```
$ sudo systemctl disable NetworkManager

 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚠ HIGH    Disabling a network or Bluetooth service
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Command:
   $ sudo systemctl disable NetworkManager

   Danger detected in:
   →  disable
   →  NetworkManager

   What this does:
   Permanently disables network or Bluetooth connectivity.

   Potential consequences:
   ✗  Wi-Fi and Bluetooth stop working immediately
   ✗  May require a reboot to restore
   ✗  Remote SSH sessions over Wi-Fi will disconnect

   Safety tip:
   →  Use systemctl restart NetworkManager instead of disable.

 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Execute this command anyway? [y/N]:
```

---

## 🚀 Features

- 42 safety rules across 3 risk levels (CRITICAL ☠, HIGH ⚠, MEDIUM ⚡)
- Rule-based detection engine for hazardous Linux commands
- Structural command parsing using `shlex` (understands command structure, not just text)
- Detects variations of the same intent — `rm --recursive /`, `rm    -rf    /`, `rm -Rf /` all caught
- Whitespace normalisation for consistent analysis
- Context-aware detection — safe paths like `/tmp` are not flagged
- False positive prevention — `echo "rm -rf /"` is correctly ignored
- sudo-aware detection — `sudo mv file /dev/null` is intercepted correctly
- Smart sudo parsing — skips flags like `-u root` to find the actual command
- Infinite loop prevention — SafeRun never analyses itself
- Uses shell functions instead of aliases to reduce common bypass methods
- Detects `kill -s KILL 1` and `kill --signal KILL 1` alongside `kill -9 1`
- Wildcard path resolution — `rm -rf /tmp/../*` correctly detected as CRITICAL
- Variable detection — `rm -rf ${HOME}` and `rm -rf ${PWD}` are flagged
- Placeholder device detection — `/dev/sdX` treated as MEDIUM, real disks as CRITICAL
- Binary-grouped rule lookup — only relevant rules checked per command
- Zero friction for safe commands — no delay, no prompts, no noise
- Danger highlighting — shows exactly which part of the command is risky
- Interactive confirmation before executing any risky command
- Command audit logging with `--log` — timestamp, risk level, and action recorded
- Works on bash and zsh
- Compatible with Ubuntu, Kali, Debian, Mint, Fedora, and WSL

---

## 📊 Performance

- Lightweight analysis — negligible delay per command (sub-millisecond in typical usage)
- Binary-grouped rules — only relevant rules checked per command for faster lookup
- Early exit for empty inputs avoids unnecessary parsing
- Detector rules run first, pattern rules only if needed — faster on most commands

---

## 🔐 Security

- Uses `subprocess` with `timeout=30` to prevent hanging commands
- Uses direct argument execution via subprocess (no shell=True) to prevent shell re-evaluation risks
- Commands are executed exactly as parsed — no secondary shell interpretation
- Logging uses append mode `"a"` — never overwrites existing data
- Logs only intercepted commands — safe commands leave no trace
- `command sudo` used in uninstaller to avoid recursive wrapper issues

---

## ⚙️ Stability

- Handles edge cases (empty input, long strings, repeated flags) without crashes
- All 42 rules validated with complete metadata — title, explanation, consequences, tip
- Logging wrapped in `try/except` — log failures never affect execution

---

## ✅ Correctness

- 95+ tested dangerous commands detected correctly including kill -s KILL and wildcard paths
- 91 safe commands tested with zero false positives
- 22/22 automated tests passing

---

## ⚠️ Limitations

- Does not modify or replace system binaries — operates only at the shell wrapper level
- Does not detect all possible dangerous commands — only the 42 patterns it knows about
- Rule-based detection — does not understand full command intent or context beyond predefined rules
- Cannot intercept commands executed as raw shell syntax before the shell wrapper fires (e.g. `^foo^bar` history substitution, fork bomb typed directly)
- Cannot fully prevent bypass using alternative execution methods such as `/bin/rm` or the `command` builtin
- Does not analyse commands inside shell scripts — `bash script.sh` runs without inspection
- Shell variables in commands like `rm -rf $VAR` are expanded by Bash *before* SafeRun sees them. While SafeRun analyzes the expanded path, extreme caution is still required.
- Some commands are intentionally flagged even if used safely (e.g. all `dd` operations show a Medium warning)
- Context awareness is limited to predefined safe paths and patterns
- Not an AI-based system — does not learn or adapt to new dangerous commands automatically
- Requires user awareness — SafeRun is a safety aid, not a substitute for understanding what a command does

---

## What it does

If you are new to Linux, here is what SafeRun does in simple terms:

- **Watches every command:** SafeRun structurally parses your command before it executes. Safe commands run instantly.
- **Explains & Highlights:** When a dangerous pattern is caught, it pauses, highlights the exact risky syntax, explains the potential damage, and asks for confirmation.
- **Handles variations:** Catches the same intent across different syntax (e.g. `rm -r /`, `rm    -rf    /`, or relative paths reaching root like `/tmp/../*`).
- **Context-aware:** Ignores safe temporary folders (like `/tmp`) and respects context (like skipping `echo "rm -rf /"` since it's just text).
- **sudo-aware:** Intelligently checks the real command inside `sudo`, skipping irrelevant flags.
- **Audit Logging:** Keeps a rotating history of intercepted commands at `~/.saferun.log`.
- **Easy to remove:** The uninstaller cleanly removes all components, requiring only a shell reload to drop active memory wrappers.

---

## What it does NOT detect — and why

These are real limitations, not hidden:


| Command                                         | Detected?             | Why not                                                                                                                 |
| ----------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `^foo^bar`                                      | ❌ No                  | Raw bash history substitution — processed by the shell before SafeRun sees it. Impossible to intercept at this layer.   |
| `bash script.sh`                                | ❌ No                  | SafeRun cannot read inside script files. Only the command itself is checked, not its contents.                          |
| `find / -delete`                                | ❌ No                  | Not in the current rule set. Rule-based tools only catch what they are explicitly taught.                               |
| `python3 -c "import os; os.system('rm -rf /')"` | ❌ No                  | Command is hidden inside a string argument. Detecting this would require executing the code, which defeats the purpose. |
| `/bin/rm -rf /`                                 | ❌ No                  | Using the full binary path bypasses shell function wrappers. SafeRun intercepts `rm` not `/bin/rm`.                     |
| `command rm -rf /`                              | ❌ No                  | The `command` builtin explicitly bypasses shell functions.                                                              |
| `rm -rf $DANGEROUS_VAR`                         | ⚠ Partial             | Handled via Bash expansion before SafeRun executes, so the expanded path is analyzed. Some edge cases with unexpanded literals exist.   |
| `:(){:                                          | :&};:` typed directly | ⚠ Partial                                                                                                               |


**In short:** SafeRun detects common hazardous command patterns. It is not a firewall and does not claim to prevent all possible damage. Users should still understand what a command does before running it.

---

## Risk levels


| Level      | Meaning                                 | Examples                                                              |
| ---------- | --------------------------------------- | --------------------------------------------------------------------- |
| ☠ CRITICAL | Permanent damage, no recovery           | `rm -rf /`, `dd of=/dev/sda`, `mkfs /dev/sda`, `mv file /dev/null`    |
| ⚠ HIGH     | Major security or connectivity impact   | `curl url | bash`, `systemctl disable NetworkManager`                 |
| ⚡ MEDIUM   | Significant but potentially recoverable | `rm -rf ~/folder`, `sudo rm`, overwriting `/etc/passwd`, `crontab -r` |


---

## All 42 rules

### ☠ CRITICAL (10 rules)

`rm -rf /` · `rm -rf /boot` · `rm -r /`* · root wildcard deletion · fork bomb · `dd of=/dev/sda` · `mkfs /dev/sda` · `mv file /dev/null` · `> /etc/passwd` · redirect to raw disk

### ⚠ HIGH (21 rules)

`chmod 777 /` · recursive chmod on system dirs · kill PID 1 · `kill -9 -1` · disable NetworkManager · disable Bluetooth · `rfkill block wifi` · `rfkill block bluetooth` · `ifconfig down` · `ip link set down` · `nmcli radio wifi off` · flush firewall · enable IP forwarding · UID 0 user creation · `curl/wget url | bash` · drop into root shell · change root password · aggressive nmap · `history | sh`

### ⚡ MEDIUM (11 rules)

recursive `rm -rf` · `sudo rm` · `dd` raw I/O · overwriting `/etc/passwd` `/etc/fstab` `/etc/sudoers` · recursive `chown` on system paths · `systemctl stop` · remove kernel or grub · secure wipe with `shred` · `crontab -r`

---

## Tested on


| Distro               | Shell      | Status    |
| -------------------- | ---------- | --------- |
| Kali Linux           | zsh        | ✅ Working |
| Ubuntu 22.04 / 24.04 | bash       | ✅ Working |
| Linux Mint           | bash       | ✅ Working |
| Debian               | bash / zsh | ✅ Working |
| Fedora               | bash       | ✅ Working |
| WSL (Windows)        | bash       | ✅ Working |


---

## Installation — copy and paste one at a time

**Step 1 — Install git**

Ubuntu / Debian / Kali / Mint:

```bash
sudo apt install git -y
```

Fedora:

```bash
sudo dnf install git -y
```

**Step 2 — Download SafeRun**

```bash
git clone https://github.com/abhi192629/Safe_Run.git
```

**Step 3 — Enter the folder**

```bash
cd Safe_Run
```

**Step 4 — Run the installer**

```bash
chmod +x install.sh && ./install.sh
```

**Step 5 — Activate**

Kali Linux (zsh):

```bash
source ~/.zshrc
```

Ubuntu / Mint / Debian / Fedora / WSL (bash):

```bash
source ~/.bashrc
```

**Step 6 — Verify it is working**

```bash
rm -rf /
```

You should see a CRITICAL warning. Type `n` and press Enter to cancel safely.

---

## Usage

After installation use your terminal normally. SafeRun runs silently in the background.

```bash
ls -la ~/Documents                     # Safe — runs instantly, no prompt
rm -rf ~/old-project                   # Matches a rule — warning shown
sudo systemctl disable NetworkManager  # Matches a rule — warning shown
curl https://example.com | bash        # Matches a rule — warning shown
echo "rm -rf /"                        # Safe — echo context, string not executed
rm -rf /tmp/test                       # Safe — /tmp is treated as a safe path
```

When a warning appears type `y` to proceed or `n` to cancel. Pressing Enter alone also cancels.

---

## Extra commands

```bash
saferun --list                  # view all 42 rules
saferun --check "your command"  # check a command without running it
saferun --log                   # view audit log of intercepted commands
saferun --clearlog             # permanently delete the audit log
saferun --help                  # usage guide
```

---

## Audit log

Every intercepted command is logged to `~/.saferun.log`:

```
[2026-03-21 14:32:01] CRITICAL | rm -rf /                        | CANCELLED
[2026-03-21 14:45:18] HIGH     | sudo systemctl disable NetworkManager | CANCELLED
[2026-03-21 15:01:44] MEDIUM   | rm -rf ~/old-project            | EXECUTED
```

The log keeps the last 500 entries and rotates automatically.

To delete the log at any time:

```bash
saferun --clearlog
```

When you uninstall SafeRun, the log is also deleted automatically so no data is left behind.

---

## Uninstall

```bash
cd Safe_Run
./install.sh --uninstall
```

This removes the `saferun` binary, the SafeRun block from `~/.bashrc` or `~/.zshrc`, and the audit log (including the `SUDO_USER` home log when uninstall is run under `sudo`, matching the installer script).

**Note:** It is fully removed from the system, but the current shell must be reloaded because functions are stored in memory. Reload this shell so in-memory wrappers go away: `source ~/.bashrc` or `source ~/.zshrc` (whichever you use), **or** restart the terminal, **or** run `exec $SHELL`. Check with `type rm` — it should no longer show a function.

---

## How it works

The installer adds shell functions to `~/.bashrc` or `~/.zshrc`. When you type `rm`, the shell silently calls `saferun rm` instead. SafeRun normalises whitespace, tokenises the command using `shlex` (which understands shell quoting and escaping), runs structural checks on the parsed tokens, and falls back to pattern matching for expressions that cannot be tokenised structurally. If a rule matches it shows the warning and waits for your input. The `sudo()` wrapper catches commands prefixed with sudo that would otherwise bypass the function wrappers.

---

## Troubleshooting

**saferun: command not found after installing**

```bash
source ~/.zshrc
```

**SafeRun not intercepting commands**

```bash
grep "SafeRun" ~/.zshrc
```

If nothing appears reinstall with `./install.sh`.

**Run one command without SafeRun**

```bash
command rm -rf ~/folder-i-trust
```

---

## License

MIT — free to use, modify, and share.

---

SafeRun reduces accidental damage, but users should still understand what a command does before executing it.