#!/usr/bin/env python3
"""Install System Health for the current user. No root access required."""
import os
from pathlib import Path
import tempfile


def atomic_write(path, data, mode):
    """Replace the entry itself, never an existing symlink's target."""
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if os.geteuid() == 0:
        raise SystemExit('Run this installer as your regular desktop user, without sudo.')
    root = Path(__file__).resolve().parent
    binary = Path.home() / '.local/bin/system-health'
    data = Path(os.environ.get('XDG_DATA_HOME', ''))
    if not data.is_absolute():
        data = Path.home() / '.local/share'
    apps = data / 'applications'
    binary.parent.mkdir(parents=True, exist_ok=True)
    apps.mkdir(parents=True, exist_ok=True)
    atomic_write(binary, (root / 'system-health').read_bytes(), 0o755)
    # Desktop Entry Exec escaping is different from shell quoting.
    escaped = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop = '\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Name=System Health',
        'Comment=Read-only Arch Linux and CachyOS health report',
        f'Exec="{escaped}" --launch',
        'Icon=utilities-system-monitor', 'Terminal=false', 'Categories=System;Monitor;', '',
    ])
    atomic_write(apps / 'system-health.desktop', desktop.encode('utf-8'), 0o644)
    print(f'Installed: {binary}')
    print('Open System Health from your application menu.')
    print('Terminal: ~/.local/bin/system-health --smart --full')


if __name__ == '__main__':
    main()
