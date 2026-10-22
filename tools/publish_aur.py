#!/usr/bin/env python3
"""Publish only the reviewed AUR recipe, without force-pushing history."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def git(directory, *args, check=True):
    return subprocess.run(['git', '-C', str(directory), *args], check=check,
                          capture_output=True, text=True, timeout=120)


def publish(recipe, remote, destination):
    recipe, destination = Path(recipe), Path(destination)
    metadata = (recipe / '.SRCINFO').read_text()
    if not re.search(r'^pkgbase = system-health$', metadata, re.M):
        raise ValueError('Unexpected package base; refusing to publish.')
    versions = re.findall(r'^\s+pkgver = ([A-Za-z0-9._+]+)$', metadata, re.M)
    releases = re.findall(r'^\s+pkgrel = ([0-9]+(?:\.[0-9]+)?)$', metadata, re.M)
    if len(versions) != 1 or len(releases) != 1:
        raise ValueError('Missing or invalid package version/release; refusing to publish.')
    version, release = versions[0], releases[0]
    subprocess.run(['git', 'clone', '--', str(remote), str(destination)], check=True, timeout=180)
    if git(destination, 'show-ref', '--verify', '--quiet', 'refs/remotes/origin/master', check=False).returncode == 0:
        git(destination, 'checkout', '-B', 'master', 'origin/master')
    elif git(destination, 'rev-parse', '--verify', 'HEAD', check=False).returncode == 0:
        raise ValueError('Existing remote has no master branch; refusing to replace its history.')
    else:
        git(destination, 'symbolic-ref', 'HEAD', 'refs/heads/master')
    git(destination, 'config', 'user.name', 'ajsem1337')
    git(destination, 'config', 'user.email', '64779622+ajsem1337@users.noreply.github.com')
    for name in ('PKGBUILD', '.SRCINFO'):
        shutil.copyfile(recipe / name, destination / name)
    git(destination, 'add', '--', 'PKGBUILD', '.SRCINFO')
    if git(destination, 'diff', '--cached', '--quiet', check=False).returncode == 0:
        print('AUR already contains this recipe; nothing to publish.')
        return False
    git(destination, 'commit', '-m', f'Update system-health to {version}-{release}')
    result = git(destination, 'push', 'origin', 'HEAD:master')
    print(result.stdout + result.stderr)
    print(f'Published system-health {version}-{release} to AUR.')
    return True


def main():
    recipe = Path(__file__).resolve().parents[1] / 'packaging/aur'
    with tempfile.TemporaryDirectory(prefix='publish-aur-') as folder:
        publish(recipe, 'ssh://aur@aur.archlinux.org/system-health.git', Path(folder) / 'repo')


if __name__ == '__main__':
    main()
