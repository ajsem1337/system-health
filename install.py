#!/usr/bin/env python3
"""Install System Health for the current user. No root access required."""
import os
from pathlib import Path
import shutil

if os.geteuid() == 0:
    raise SystemExit('Run this installer as your regular desktop user, without sudo.')
root = Path(__file__).resolve().parent
binary = Path.home() / '.local/bin/system-health'
apps = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'applications'
binary.parent.mkdir(parents=True, exist_ok=True)
apps.mkdir(parents=True, exist_ok=True)
shutil.copyfile(root / 'system-health', binary)
binary.chmod(0o755)
# Desktop Entry Exec escaping is different from shell quoting.
escaped = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
desktop = '\n'.join([
    '[Desktop Entry]', 'Type=Application', 'Name=System Health',
    'Comment=Read-only Arch Linux and CachyOS health report',
    f'Exec="{escaped}" --smart --pause',
    'Icon=utilities-system-monitor', 'Terminal=true', 'Categories=System;Monitor;', '',
])
(apps / 'system-health.desktop').write_text(desktop)
print(f'Installed: {binary}')
print('Open System Health from your application menu.')
print('Terminal: ~/.local/bin/system-health --smart --full')
