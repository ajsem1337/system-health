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

Python 3.11+, systemd, pacman and util-linux, plus:

```sh
sudo pacman -S --needed python pacutils rebuild-detector pacman-contrib lm_sensors smartmontools sudo
```

`gsmartcontrol` is an optional graphical companion for inspecting disks and running self-tests. No Python packages from PyPI are needed.

## Install

### Arch package

An Arch package recipe is provided in [`packaging/aur`](packaging/aur). From a checkout:

```sh
cd packaging/aur
makepkg -si
```

This installs the command and menu entry system-wide using pacman. The recipe is prepared for AUR submission; its presence on GitHub does not mean it has been published to AUR.

Maintainers can publish the recipe using the manual **Publish to AUR** GitHub Actions workflow. See the [one-time SSH secret setup](packaging/aur/README.md#publish-through-github-actions).

### Per-user installation

From a checkout of this repository, as your normal desktop user:

```sh
git clone https://github.com/ajsem1337/system-health.git
cd system-health
python3 install.py
```

This installs `~/.local/bin/system-health` and a **System Health** application-menu entry. The menu entry directly starts a supported terminal (Kitty, GNOME Console/Terminal, Konsole, Xfce Terminal, foot, Alacritty or xterm), asks for sudo authentication for disk reads, and waits for Enter before closing. It does not rely on a desktop terminal handler that may interpret commands as URLs.

## Run

```sh
# Basic checks; no password prompt
~/.local/bin/system-health

# Authenticate SMART reads and check installed package file presence
~/.local/bin/system-health --smart --full
```

Run the program as your regular user. `--smart` authenticates sudo; individual SMART reads and, with `--full`, the package file check can then use it. Running the whole program as root changes which user's services are checked. Without permission, a check is marked **NOT CHECKED**, not healthy or missing.

Reports and their directory use owner-only permissions. Terminal control sequences
are stripped from diagnostics before display and storage. Reports are saved under `$XDG_STATE_HOME/system-health`, defaulting to `~/.local/state/system-health`. They remain local; nothing is uploaded. Reports can contain paths, package names and journal entries: review them before sharing.

## Limits

- No repairs, updates, cleanup, configuration changes, SMART self-tests or stress tests are performed. Local report files are written.
- Does not check available package updates, vulnerability advisories, or firmware updates.
- `checkrebuild` may flag optional libraries or libraries found through an application's private search path. Its verbose diagnostics are included for review.
- Historical journal entries and disk error counters are not necessarily current failures.
- Temperature checks cover `k10temp`, `coretemp`, `amdgpu`, `nouveau` and NVMe sensor families. Unidentified motherboard AUXTIN inputs are excluded. Unsupported hardware is not a successful temperature check.
- Package file checks verify presence, not content hashes. Temperature and capacity thresholds are heuristics.
- Intended for an interactive report: exit status is not an aggregate health verdict. A report-write failure returns exit status 1.

## Uninstall

```sh
rm ~/.local/bin/system-health
rm "${XDG_DATA_HOME:-$HOME/.local/share}/applications/system-health.desktop"
```

Saved reports are retained.

For a pacman-managed installation, use `sudo pacman -R system-health` instead. If migrating from a per-user installation to the package, remove the old user executable and menu entry as described in the [packaging notes](packaging/aur/README.md).

## License

MIT. See [LICENSE](LICENSE).

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Version 0.2.0

Malformed or incomplete JSON from disk, mount and sensor tools is reported as
**NOT CHECKED** while the remaining checks continue. Missing `paccheck` is
reported separately from missing package files. Restricted crash journals are
never reported as a clean crash check.

SMART status follows the [smartctl exit-status bitmask](https://github.com/smartmontools/smartmontools/blob/master/smartmontools/smartctl.8.in):
a failing-health flag is an **ERROR**, while incomplete device access remains
**NOT CHECKED**. Invalid temperature readings are excluded from healthy results.

The user installer replaces files atomically, preserving the targets of existing
symlinks. Relative XDG directory settings fall back to the standard home paths.
Use `system-health --version` to check the installed version.
