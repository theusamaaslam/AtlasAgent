---
sidebar_position: 2
title: "Installation"
description: "Install Atlas Agent on Linux, macOS, WSL2, native Windows, or Android via Termux"
---

# Installation

Get Atlas Agent up and running in under two minutes!

:::tip Platform Support
For the full platform support matrix (which OSes, distribution methods, and
platform-gated features are supported), see **[Platform Support](./platform-support.md)**.
:::

## Quick Install
### From the AtlasAgent repository

The standard installation path is to clone this repository, then run the installer script from the local checkout. This keeps every install script inspectable and versioned with the code you are installing.

#### Linux / macOS / WSL2 / Android (Termux)
```bash
git clone https://github.com/theusamaaslam/AtlasAgent.git
cd AtlasAgent
bash scripts/install.sh
```

#### Windows (native)

Run in powershell:
```powershell
git clone https://github.com/theusamaaslam/AtlasAgent.git
cd AtlasAgent
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

If you want to install & run Atlas Desktop after a command-line only install, simply run
```bash
atlas desktop
```

### What the Installer Does

The installer handles everything automatically — all dependencies (Python, Node.js, ripgrep, ffmpeg), the repo clone, virtual environment, global `atlas` command setup, and LLM provider configuration. By the end, you're ready to chat.

#### Install Layout

Where the installer puts things depends on whether you're installing as a normal user or as root:

| Installer                              | Code lives at                  | `atlas` binary                         | Data directory                       |
| -------------------------------------- | ------------------------------ | --------------------------------------- | ------------------------------------ |
| Per-user (git installer)               | `~/.atlas/atlas-agent/`      | `~/.local/bin/atlas` (symlink)         | `~/.atlas/`                         |
| Root-mode (`sudo bash scripts/install.sh`) | `/usr/local/lib/atlas-agent/` | `/usr/local/bin/atlas`                 | `/root/.atlas/` (or `$ATLAS_HOME`) |

The root-mode **FHS layout** (`/usr/local/lib/…`, `/usr/local/bin/atlas`) matches where other system-wide developer tools land on Linux. It's useful for shared-machine deployments where one system install should serve every user. Per-user config (auth, skills, sessions) still lives under each user's `~/.atlas/` or explicit `ATLAS_HOME`.

### After Installation

Reload your shell and start chatting:

```bash
source ~/.bashrc   # or: source ~/.zshrc
atlas             # Start chatting!
```

To reconfigure individual settings later, use the dedicated commands:

```bash
atlas model          # Choose your LLM provider and model
atlas tools          # Configure which tools are enabled
atlas gateway setup  # Set up messaging platforms
atlas config set     # Set individual config values
atlas setup          # Or run the full setup wizard to configure everything at once
```

:::tip Fastest path: guided setup
Use the setup wizard after installation to choose your provider, configure API keys, and enable the tools you want:

```bash
atlas setup
```
:::

---

## Prerequisites

**Installer:** On non-Windows platforms, the only prerequisite is **Git**. On Linux, also make sure `curl` and `xz-utils` are available (the installer downloads Node.js as a `.tar.xz` archive). The desktop app additionally requires `g++` (or `build-essential` on Debian/Ubuntu) to compile native modules. The installer automatically handles everything else:

- **uv** (fast Python package manager)
- **Python 3.11** (via uv, no sudo needed)
- **Node.js v22** (for browser automation and WhatsApp bridge)
- **ripgrep** (fast file search)
- **ffmpeg** (audio format conversion for TTS)

:::info
You do **not** need to install Python, Node.js, ripgrep, or ffmpeg manually. The installer detects what's missing and installs it for you. Just make sure `git` is available (`git --version`). On Linux, ensure `curl` and `xz-utils` are installed (`sudo apt install curl xz-utils` on Debian/Ubuntu). For the desktop app, also install `build-essential` (`sudo apt install build-essential`).
:::

:::tip Nix users
Nix is **no longer an explicitly supported install path** (best-effort only). If you already use Nix (on NixOS, macOS, or Linux), there's a dedicated setup path with a Nix flake, declarative NixOS module, and optional container mode. See the **[Nix & NixOS Setup](./nix-setup.md)** guide.
:::

---

## Manual / Developer Installation

If you want to clone the repo and install from source — for contributing, running from a specific branch, or having full control over the virtual environment — see the [Development Setup](../developer-guide/contributing.md#development-setup) section in the Contributing guide.

---

## Non-Sudo / System Service User Installs

Running Atlas as a dedicated unprivileged user (e.g. a `atlas` systemd service account, or any user without `sudo` access) is supported. The only thing on the install path that genuinely needs root is Playwright's `--with-deps` step, which `apt`-installs shared libraries (`libnss3`, `libxkbcommon`, etc.) used by Chromium. The installer detects whether sudo is available and gracefully degrades when it isn't — it will install the Chromium binary into the service user's own Playwright cache and print the exact command an administrator needs to run separately.

**Recommended split (Debian/Ubuntu):**

1. **One time, as an admin user with sudo**, install the system libraries Chromium needs:
   ```bash
   sudo npx playwright install-deps chromium
   ```
   (You can run this from anywhere — `npx` will fetch Playwright on the fly.)

2. **As the unprivileged service user**, run the regular installer. It will detect the missing sudo, skip `--with-deps`, and install Chromium into the user's local Playwright cache:
   ```bash
   git clone https://github.com/theusamaaslam/AtlasAgent.git
   cd AtlasAgent
   bash scripts/install.sh
   ```

   If you want to skip the Playwright step entirely — for example because you're running headless and don't need browser automation — pass `--skip-browser`:
   ```bash
   bash scripts/install.sh --skip-browser
   ```

3. **Make `atlas` available to the service user's shells.** The installer writes the launcher to `~/.local/bin/atlas`. System service accounts often have a minimal PATH that doesn't include `~/.local/bin`. Either add it to the user's environment, or symlink the launcher into a system location:
   ```bash
   # Option A — add to the service user's profile
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

   # Option B — symlink system-wide (run as an admin)
   sudo ln -s /home/atlas/.atlas/atlas-agent/venv/bin/atlas /usr/local/bin/atlas
   ```

4. **Verify:** `atlas doctor` should now run cleanly. If you get `ModuleNotFoundError: No module named 'dotenv'`, you're invoking the repo source `atlas` file (`~/.atlas/atlas-agent/atlas`) with system Python instead of the venv launcher (`~/.atlas/atlas-agent/venv/bin/atlas`) — fix step 3.

The same pattern works on Arch (the installer uses pacman with the same sudo-detection logic), Fedora/RHEL, and openSUSE — those distros don't support `--with-deps` at all, so an administrator always installs the system libraries separately. The relevant `dnf`/`zypper` commands are printed by the installer.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `atlas: command not found` | Reload your shell (`source ~/.bashrc`) or check PATH |
| `API key not set` | Run `atlas model` to configure your provider, or `atlas config set OPENROUTER_API_KEY your_key` |
| Missing config after update | Run `atlas config check` then `atlas config migrate` |

For more diagnostics, run `atlas doctor` — it will tell you exactly what's missing and how to fix it.

## Install method auto-detection

Atlas auto-detects whether it was installed via `pip`, the git installer, Homebrew, or NixOS, and `atlas update` prints the matching update command for that path. There's no env var to set — the detection is based on the install layout (Python site-packages, `~/.atlas/atlas-agent/`, Homebrew prefix, or Nix store path). `atlas doctor` also surfaces the detected method under its environment summary.
