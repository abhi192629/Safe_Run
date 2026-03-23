<div align="center">

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
[![Rules](https://img.shields.io/badge/Rules-40-orange?style=flat-square)]()
[![Tests](https://img.shields.io/badge/Tests-21%2F21%20passing-brightgreen?style=flat-square)]()

</div>

---

## What is SafeRun?

SafeRun is a rule-based command safety tool for Linux. When you type a command, SafeRun checks it against 40 known dangerous patterns. If it matches, it pauses execution, shows a warning explaining what the command does and what could break, and asks whether you want to proceed.

Safe commands run immediately with no interruption. Only matched patterns trigger a warning.

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

- 40 safety rules across 3 risk levels (CRITICAL ☠, HIGH ⚠, MEDIUM ⚡)
- Rule-based detection engine for hazardous Linux commands
- Structural command parsing using shlex (understands command structure, not just text)
- Detects command variations — `rm --recursive /`, `rm    -rf    /`, `rm -Rf /` all caught
- Whitespace normalisation for consistent analysis
- Context-aware detection — safe paths like `/tmp` are not flagged
- False positive prevention — `echo "rm -rf /"` is correctly ignored
- sudo-aware detection for elevated-risk commands
- Infinite loop prevention — SafeRun never analyses itself
- Designed to reduce common bypass methods using shell functions instead of aliases
- Zero friction for safe commands — no delay, no prompts, no noise
- Danger highlighting — shows exactly which part of the command is risky
- Interactive confirmation before executing any risky command
- Command audit logging with `--log` — timestamp, risk level, and action recorded
- Works on bash and zsh
- Compatible with Ubuntu, Kali, Debian, Mint, Fedora, and WSL

---

## 📊 Performance

- 400 commands analysed in ~0.3ms (~0.001ms per command)
- Cached execution reduces repeated analysis to ~0.03ms (~11x faster)
- Early exit for empty inputs avoids unnecessary parsing
- Detector rules run first, pattern rules only if needed — faster on most commands

---

## 🔐 Security

- Uses `subprocess` with `timeout=30` to prevent hanging commands
- Uses `executable=/bin/bash` to ensure consistent shell execution
- Logging uses append mode `"a"` — never overwrites existing data
- Logs only intercepted commands — safe commands leave no trace
- `command sudo` used in uninstaller to avoid recursive wrapper issues

---

## ⚙️ Stability

- Handles edge cases (empty input, long strings, repeated flags) without crashes
- All 40 rules validated with complete metadata — title, explanation, consequences, tip
- Logging wrapped in `try/except` — log failures never affect execution

---

## ✅ Correctness

- 90 tested dangerous commands detected correctly
- 91 safe commands tested with zero false positives
- 21/21 automated tests passing

---

## ⚠️ Limitations

- Does not detect all possible dangerous commands — only the 40 patterns it knows about
- Rule-based detection — does not understand full command intent or context beyond predefined rules
- Cannot intercept commands executed as raw shell syntax before the shell wrapper fires (e.g. `^foo^bar` history substitution, fork bomb typed directly)
- Cannot fully prevent bypass using alternative execution methods such as `/bin/rm` or the `command` builtin
- Does not analyse commands inside shell scripts — `bash script.sh` runs without inspection
- Does not resolve shell variables — `rm -rf $VAR` is flagged as Medium but the variable value is unknown
- Some commands are intentionally flagged even if used safely (e.g. all `dd` operations show a Medium warning)
- Context awareness is limited to predefined safe paths and patterns
- Not an AI-based system — does not learn or adapt to new dangerous commands automatically
- Requires user awareness — SafeRun is a safety aid, not a substitute for understanding what a command does

---

## What it does

If you are new to Linux, here is what SafeRun actually does for you in plain terms:

**Watches every command you type**
Before anything runs, SafeRun checks whether the command matches a known dangerous pattern. If it does not match, the command runs instantly as normal — no delay, no interruption. You will not even notice SafeRun is there for safe commands.

**Shows you exactly what will break — before it breaks**
If a dangerous command is detected, SafeRun pauses and tells you in plain English what the command does, what will stop working, and what you should do instead. No technical jargon. No guessing.

**Points to the exact dangerous part**
SafeRun highlights which specific part of your command triggered the warning. For example if you type `sudo systemctl disable NetworkManager`, it will tell you that `disable` and `NetworkManager` are the dangerous parts — not just that the whole command is risky.

**Handles typos and variations**
It does not matter if you type `rm -rf /` or `rm    -rf    /` with extra spaces, or `rm -r /` or `rm --recursive /`. SafeRun understands all of these as the same dangerous intent and catches them all. It also understands relative paths like `rm -rf ./../../` that try to navigate up to the root directory.

**Knows the difference between talking about a command and running one**
If you type `echo "rm -rf /"` you are just printing text — not actually deleting anything. SafeRun correctly ignores this. Only commands that actually execute are checked.

**Knows which folders are safe to delete**
Deleting files inside `/tmp` is completely normal and safe — it is a temporary folder. SafeRun will not bother you for `rm -rf /tmp/test`. It only warns when the target is something that would genuinely cause damage.

**Catches commands run with admin privileges too**
Some dangerous commands are run with `sudo` in front of them. SafeRun intercepts those too. For example `sudo systemctl disable NetworkManager` — which would permanently kill your Wi-Fi — is caught and flagged as HIGH risk.

**Keeps a record of every close call**
Every time SafeRun intercepts a dangerous command, it saves a log entry to `~/.saferun.log` with the exact time, the command, and whether you ran it or cancelled it. This gives you a history of every time SafeRun protected you.

**Prevents long-running commands from hanging the terminal**
Some commands can run indefinitely and make your terminal unresponsive. SafeRun automatically stops any command that takes longer than 30 seconds, so your terminal stays usable.

**Cleans up after itself**
The log file never grows out of control. SafeRun automatically keeps only the last 500 entries and removes older ones.

**Never gets confused by its own commands**
SafeRun is smart enough to never check itself. If it accidentally tried to analyse its own commands it would create an infinite loop and freeze. This is handled automatically — you will never experience this as a user.

**Easy to remove if you change your mind**
One command uninstalls everything completely — the tool, the wrappers, and the log entries in your shell config. Nothing is left behind.

---

## What it does NOT detect — and why

These are real limitations, not hidden:

| Command | Detected? | Why not |
|---|---|---|
| `^foo^bar` | ❌ No | Raw bash history substitution — processed by the shell before SafeRun sees it. Impossible to intercept at this layer. |
| `bash script.sh` | ❌ No | SafeRun cannot read inside script files. Only the command itself is checked, not its contents. |
| `find / -delete` | ❌ No | Not in the current rule set. Rule-based tools only catch what they are explicitly taught. |
| `python3 -c "import os; os.system('rm -rf /')"` | ❌ No | Command is hidden inside a string argument. Detecting this would require executing the code, which defeats the purpose. |
| `/bin/rm -rf /` | ❌ No | Using the full binary path bypasses shell function wrappers. SafeRun intercepts `rm` not `/bin/rm`. |
| `command rm -rf /` | ❌ No | The `command` builtin explicitly bypasses shell functions. |
| `rm -rf $DANGEROUS_VAR` | ⚠ Partial | Flagged as MEDIUM but SafeRun cannot know what the variable contains at analysis time. |
| `:(){:\|:&};:` typed directly | ⚠ Partial | Detected when passed to SafeRun explicitly. As raw shell syntax typed directly, it executes before any wrapper fires. |

**In short:** SafeRun detects common hazardous command patterns. It is not a firewall and does not claim to prevent all possible damage. Users should still understand what a command does before running it.

---

## Risk levels

| Level | Meaning | Examples |
|---|---|---|
| ☠ CRITICAL | Permanent damage, no recovery | `rm -rf /`, `dd of=/dev/sda`, `mkfs /dev/sda`, `mv file /dev/null` |
| ⚠ HIGH | Major security or connectivity impact | `curl url \| bash`, `systemctl disable NetworkManager`, `kill -9 -1`, `history \| sh` |
| ⚡ MEDIUM | Significant but potentially recoverable | `rm -rf ~/folder`, `sudo rm`, overwriting `/etc/passwd`, `crontab -r` |

---

## All 40 rules

### ☠ CRITICAL (10 rules)
`rm -rf /` · `rm -rf /boot` · `rm -r /*` · root wildcard deletion · fork bomb · `dd of=/dev/sda` · `mkfs /dev/sda` · `mv file /dev/null` · `> /etc/passwd` · redirect to raw disk

### ⚠ HIGH (21 rules)
`chmod 777 /` · recursive chmod on system dirs · kill PID 1 · `kill -9 -1` · disable NetworkManager · disable Bluetooth · `rfkill block wifi` · `rfkill block bluetooth` · `ifconfig down` · `ip link set down` · `nmcli radio wifi off` · flush firewall · enable IP forwarding · UID 0 user creation · `curl/wget url | bash` · drop into root shell · change root password · aggressive nmap · `history | sh`

### ⚡ MEDIUM (9 rules)
recursive `rm -rf` · `sudo rm` · `dd` raw I/O · overwriting `/etc/passwd` `/etc/fstab` `/etc/sudoers` · recursive `chown` on system paths · `systemctl stop` · remove kernel or grub · secure wipe with `shred` · `crontab -r`

---

## Tested on

| Distro | Shell | Status |
|---|---|---|
| Kali Linux | zsh | ✅ Working |
| Ubuntu 22.04 / 24.04 | bash | ✅ Working |
| Linux Mint | bash | ✅ Working |
| Debian | bash / zsh | ✅ Working |
| Fedora | bash | ✅ Working |
| WSL (Windows) | bash | ✅ Working |

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
saferun --list                  # view all 40 rules
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
source ~/.zshrc
```

Removes the binary and all shell functions. Nothing is left behind.

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

<div align="center">
SafeRun detects common dangerous patterns. It is not a substitute for understanding what a command does before running it.
</div>
