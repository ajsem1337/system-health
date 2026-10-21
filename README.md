# System Health

A readable, read-only health report for CachyOS and Arch Linux. Written in Python using only the standard library, with English output and an optional application-menu shortcut.

## What it checks

- Failed system and user services, current-boot errors, recorded application crashes, clock synchronization.
- Package database consistency, potential linkage problems (`checkrebuild`), pending `.pacnew` / `.pacsave` files.
- Optional package file presence checks, distinguishing **missing files** from **permission denied**.
- Available RAM, filesystem capacity and free inodes.
- Supported CPU, GPU and NVMe temperature sensors.
- SMART health and NVMe endurance/error counters.

Results use **OK**, **WARNING**, **ERROR**, **NOT CHECKED**, and **INFO**. A warning is something to review, not an instruction to reinstall or delete anything. Missing tools, denied permissions and timeouts are reported explicitly.

## Dependencies

Python 3.9+, systemd, pacman and util-linux, plus:

```sh
sudo pacman -S --needed python pacutils rebuild-detector pacman-contrib lm_sensors smartmontools sudo
```

`gsmartcontrol` is an optional graphical companion for inspecting disks and running self-tests. No Python packages from PyPI are needed.

## Install

From a checkout of this repository, as your normal desktop user:

```sh
git clone https://github.com/ajsem1337/system-health.git
cd system-health
python3 install.py
```

This installs `~/.local/bin/system-health` and a **System Health** application-menu entry. The menu entry uses your desktop's default terminal, asks for sudo authentication for disk reads, and waits for Enter before closing.

## Run

```sh
# Basic checks; no password prompt
~/.local/bin/system-health

# Authenticate SMART reads and check installed package file presence
~/.local/bin/system-health --smart --full
```

Run the program as your regular user. `--smart` authenticates sudo; individual SMART reads and, with `--full`, the package file check can then use it. Running the whole program as root changes which user's services are checked. Without permission, a check is marked **NOT CHECKED**, not healthy or missing.

Reports are saved with owner-only permissions under `$XDG_STATE_HOME/system-health`, defaulting to `~/.local/state/system-health`. They remain local; nothing is uploaded. Reports can contain paths, package names and journal entries: review them before sharing.

## Limits

- No repairs, updates, cleanup, configuration changes, SMART self-tests or stress tests are performed. Local report files are written.
- Does not check available package updates, vulnerability advisories, or firmware updates.
- `checkrebuild` may flag optional libraries or libraries found through an application's private search path. Its verbose diagnostics are included for review.
- Historical journal entries and disk error counters are not necessarily current failures.
- Temperature checks cover `k10temp`, `coretemp`, `amdgpu`, `nouveau` and NVMe sensor families. Unidentified motherboard AUXTIN inputs are excluded. Unsupported hardware is not a successful temperature check.
- Package file checks verify presence, not content hashes. Temperature and capacity thresholds are heuristics.
- Intended for an interactive report: exit status is not an aggregate health verdict.

## Uninstall

```sh
rm ~/.local/bin/system-health
rm "${XDG_DATA_HOME:-$HOME/.local/share}/applications/system-health.desktop"
```

Saved reports are retained.

## Tests

```sh
python3 -m unittest discover -s tests -v
```
