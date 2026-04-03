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

[Python](https://python.org)
[Platform](https://kernel.org)
[License](LICENSE)
[Shell](https://gnu.org/software/bash)
[Rules]()
[Tests]()

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

- 400 commands analysed in ~~5ms (~~0.012ms per command)
- Binary-grouped rules — only relevant rules checked per command for faster lookup
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
- All 42 rules validated with complete metadata — title, explanation, consequences, tip
- Logging wrapped in `try/except` — log failures never affect execution

---

## ✅ Correctness

- 95+ tested dangerous commands detected correctly including kill -s KILL and wildcard paths
- 91 safe commands tested with zero false positives
- 22/22 automated tests passing

---

## ⚠️ Limitations

- Does not detect all possible dangerous commands — only the 42 patterns it knows about
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

If you are new to Linux, here is what SafeRun does in simple terms:

**Watches every command you type**  
Before anything runs, SafeRun checks whether the command matches a known dangerous pattern. If it does not match, the command runs instantly as normal — no delay, no interruption. For safe commands you will not notice SafeRun at all.

**Shows what will break — before it breaks**  
When a dangerous command is detected, SafeRun pauses and explains in plain English what the command does, what will stop working, and what you should do instead.

**Points to the exact dangerous part**  
SafeRun highlights the specific part of your command that triggered the warning. For example, for `sudo systemctl disable NetworkManager` it highlights `disable` and `NetworkManager`, not just the whole line.

**Handles typos and variations**  
It treats variations like `rm -rf /`, `rm    -rf    /`, `rm -r /`, and `rm --recursive /` as the same intent and catches them all. It also understands relative paths like `rm -rf ./../../` that try to reach the root directory.

**Knows the difference between text and execution**  
If you type `echo "rm -rf /"` you are only printing text. SafeRun ignores this. It only analyses commands that will actually execute.

**Understands which folders are usually safe**  
Deleting files inside `/tmp` is normal and safe — it is a temporary folder. SafeRun will not warn for `rm -rf /tmp/test`. It focuses on paths that could cause real damage.

**Handles commands run with sudo**  
Dangerous commands run with `sudo` are also intercepted. For example `sudo systemctl disable NetworkManager` — which would permanently kill your Wi-Fi — is flagged as HIGH risk.

**Keeps a record of close calls**  
Each intercepted command is logged to `~/.saferun.log` with the time, the command, and whether you executed or cancelled it. This gives you a simple history of risky commands.

**Prevents long-running commands from hanging the terminal**  
Commands that run too long can make your terminal unresponsive. SafeRun automatically stops any command that takes more than 30 seconds to finish.

**Manages its log automatically**  
The log file is rotated automatically. SafeRun keeps only the last 500 entries and discards older ones.

**Avoids analysing itself**  
SafeRun does not check its own commands. This prevents infinite loops where it would otherwise analyse itself repeatedly.

**Easy to remove**  
The uninstaller removes the binary, shell functions, and log entries from your shell config so nothing is left behind.

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
| `rm -rf $DANGEROUS_VAR`                         | ⚠ Partial             | Flagged as MEDIUM but SafeRun cannot know what the variable contains at analysis time.                                  |
| `:(){:                                          | :&};:` typed directly | ⚠ Partial                                                                                                               |


**In short:** SafeRun detects common hazardous command patterns. It is not a firewall and does not claim to prevent all possible damage. Users should still understand what a command does before running it.

---

## Risk levels


| Level      | Meaning                                 | Examples                                                              |
| ---------- | --------------------------------------- | --------------------------------------------------------------------- |
| ☠ CRITICAL | Permanent damage, no recovery           | `rm -rf /`, `dd of=/dev/sda`, `mkfs /dev/sda`, `mv file /dev/null`    |
| ⚠ HIGH     | Major security or connectivity impact   | `curl url                                                             |
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

SafeRun detects common dangerous patterns. It is not a substitute for understanding what a command does before running it.