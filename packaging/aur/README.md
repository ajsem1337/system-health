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

### Publish through GitHub Actions

The **Publish to AUR** workflow runs manually from `main`. It runs tests, verifies `.SRCINFO` using Arch's `makepkg`, verifies the AUR server's SSH host fingerprint, then publishes only `PKGBUILD` and `.SRCINFO` to the AUR `master` branch. Existing history is retained, with no force push. Repeating a publication without changes is a no-op.

This public repository uses a standard `ubuntu-latest` GitHub-hosted runner. Its execution time is free under [GitHub's public repository policy](https://docs.github.com/en/billing/concepts/product-billing/github-actions). The workflow does not upload artifacts or use paid larger runners.

One-time setup:

1. Create a dedicated, unencrypted Ed25519 key for this automation (do not reuse a personal login key):

   ```sh
   ssh-keygen -t ed25519 -N '' -f ~/.ssh/aur-system-health-actions -C 'system-health GitHub Actions to AUR'
   ```

   If that path already exists, use the existing pair or choose a different name; do not overwrite it.

2. Copy the public key and add it under **SSH Public Key** in your AUR account settings:

   ```sh
   wl-copy < ~/.ssh/aur-system-health-actions.pub
   ```

3. Open the repository's [new Actions secret page](https://github.com/ajsem1337/system-health/settings/secrets/actions/new). Set the name to `AUR_SSH_PRIVATE_KEY`. Copy the private key into the value field and save:

   ```sh
   wl-copy < ~/.ssh/aur-system-health-actions
   ```

   `wl-copy` requires `wl-clipboard` on Wayland. Alternatively, paste the file contents using a trusted local editor. The private key belongs in an Actions secret, never in a commit, issue, chat, or log. The workflow requires an unencrypted key for noninteractive use. Anyone able to change and execute trusted repository workflows can potentially use the credential; keep repository write access limited.

4. Open **Actions → Publish to AUR → Run workflow**, select `main`, and run it. The account is identified by its SSH key; no separate username secret is needed.

The initial run creates the package's AUR repository if the name is available and the account is allowed to submit it. If the package already belongs to someone else, it will fail rather than replace their history. The AUR account must be fully activated and permitted to submit packages.

Once the secret is saved, the local key is not needed for workflow runs after reinstalling your computer. GitHub does not provide a normal interface to download an existing secret; keep an independent encrypted backup if you want to retain the key. If it is lost, replace the key in both AUR account settings and the GitHub secret.

The SSH host fingerprint is pinned to the [official Arch announcement](https://archlinux.org/news/aur-migration-new-ssh-hostkeys/). If Arch rotates that key, verify the new official fingerprint and update the workflow before retrying.

### Manual submission

Clone the AUR repository for the available package name, copy **only** `PKGBUILD` and `.SRCINFO` into it, review, commit and push. GitHub hosts the upstream application; AUR hosts the build recipe.

For updates, publish the upstream source first, update `_commit`, `pkgver` / `pkgrel`, regenerate checksums, test the build, then regenerate metadata:

```sh
makepkg --printsrcinfo > .SRCINFO
```

Never commit package archives, source caches, `src/` or `pkg/` to AUR.
