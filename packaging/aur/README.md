# Arch Linux / AUR packaging

`PKGBUILD` and `.SRCINFO` are ready for an AUR submission. Sources are pinned to an immutable upstream Git commit and verified with SHA-256 checksums; building does not follow `main`.

## Build and install

From this directory, as your regular user:

```sh
makepkg -si
```

This installs `/usr/bin/system-health` and `/usr/share/applications/system-health.desktop`, with dependencies managed by pacman. It does not use the per-user `install.py` installer.

If you previously installed the per-user version, remove its executable and desktop shortcut **after** installing the package, so they do not shadow the system package:

```sh
rm ~/.local/bin/system-health
rm "${XDG_DATA_HOME:-$HOME/.local/share}/applications/system-health.desktop"
```

Reports are retained in the user's state directory. Installing or removing the package does not run checks or change system configuration.

## Submit to AUR

An AUR account and an SSH key registered with AUR are required. GitHub credentials do not grant AUR access. Check that the package name is available before submission.

Clone the AUR repository for the available package name, copy **only** `PKGBUILD` and `.SRCINFO` into it, review, commit and push. GitHub hosts the upstream application; AUR hosts the build recipe.

For updates, publish the upstream source first, update `_commit`, `pkgver` / `pkgrel`, regenerate checksums, test the build, then regenerate metadata:

```sh
makepkg --printsrcinfo > .SRCINFO
```

Never commit package archives, source caches, `src/` or `pkg/` to AUR.
