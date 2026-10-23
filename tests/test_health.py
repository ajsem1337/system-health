import contextlib
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('system_health', str(ROOT / 'system-health'))
spec = importlib.util.spec_from_loader(loader.name, loader)
health = importlib.util.module_from_spec(spec)
loader.exec_module(health)


class HealthTests(unittest.TestCase):
    def report(self, diagnostic='', code=0):
        def command(cmd, timeout=30):
            if 'paccheck' in cmd:
                return code, '', diagnostic
            if cmd[:3] == ['sudo', '-n', 'true']:
                return 1, '', 'authentication required'
            if cmd[0] == 'findmnt':
                return 0, '{"filesystems": []}', ''
            if cmd[0] == 'sensors':
                return 0, '{}', ''
            if cmd[0] == 'timedatectl':
                return 0, 'yes', ''
            if cmd[0] == 'coredumpctl':
                return 1, '', 'No coredumps found.'
            return 0, '', ''

        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with patch.object(health, 'run', side_effect=command), \
                 patch.object(health.sys, 'argv', ['system-health', '--full', '--verbose']), \
                 patch.dict(os.environ, {'XDG_STATE_HOME': directory}), \
                 contextlib.redirect_stdout(output):
                health.main()
            reports = list(Path(directory).glob('system-health/report-*.txt'))
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0].stat().st_mode & 0o777, 0o600)
            return output.getvalue()

    def test_permission_denied_is_not_missing(self):
        output = self.report("warning: bind: '/var/named/a' read error (Permission denied)", 1)
        self.assertIn('[NOT CHECKED] Package files not checked: access denied', output)
        self.assertNotIn('[WARNING] Missing package files', output)

    def test_missing_files(self):
        output = self.report("warning: example: '/usr/bin/a' read error (No such file or directory)", 1)
        self.assertIn('[WARNING] Missing package files', output)

    def test_mixed_diagnostics(self):
        output = self.report('read error (Permission denied)\nread error (No such file or directory)', 1)
        self.assertIn('[WARNING] Missing package files', output)
        self.assertIn('[NOT CHECKED] Package files not checked: access denied', output)

    def test_clean_check(self):
        self.assertIn('[OK] Package file presence', self.report())

    def test_timeout_is_not_missing(self):
        output = self.report('command timed out', health.RUN_FAILED)
        self.assertIn('[NOT CHECKED] Other package-file check diagnostics', output)
        self.assertNotIn('[WARNING] Missing package files', output)

    def test_unknown_failure_is_not_success(self):
        output = self.report('', 1)
        self.assertIn('Exit status: 1', output)
        self.assertNotIn('[OK] Package file presence', output)

    def test_user_install_is_portable(self):
        with tempfile.TemporaryDirectory(prefix='health user ') as directory:
            home = Path(directory)
            with patch('pathlib.Path.home', return_value=home), \
                 patch('os.geteuid', return_value=1000), \
                 patch.dict(os.environ, {'XDG_DATA_HOME': str(home / 'data')}), \
                 contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / 'install.py'), run_name='__main__')
            binary = home / '.local/bin/system-health'
            desktop = (home / 'data/applications/system-health.desktop').read_text()
            self.assertTrue(binary.stat().st_mode & 0o100)
            self.assertIn(f'Exec="{binary}" --launch', desktop)
            self.assertNotIn(str(ROOT), desktop)
            self.assertIn('Terminal=false', desktop)

    def test_launcher_executes_report_in_kitty_without_url_handler(self):
        with patch.object(health.shutil, 'which', side_effect=lambda name: '/usr/bin/kitty' if name == 'kitty' else None), \
             patch.object(health.subprocess, 'Popen') as spawn:
            health.launch_terminal(full=True)
        command = spawn.call_args.args[0]
        self.assertEqual(command[:2], ['/usr/bin/kitty', '--'])
        self.assertIn('--smart', command)
        self.assertIn('--pause', command)
        self.assertIn('--full', command)
        self.assertNotIn('+open', command)
        self.assertNotIn('--launch', command)

    def test_launcher_falls_back_to_gnome_console(self):
        with patch.object(health.shutil, 'which', side_effect=lambda name: '/usr/bin/kgx' if name == 'kgx' else None), \
             patch.object(health.subprocess, 'Popen') as spawn:
            health.launch_terminal()
        self.assertEqual(spawn.call_args.args[0][:2], ['/usr/bin/kgx', '--'])

    def test_launcher_reports_missing_terminal(self):
        with patch.object(health.shutil, 'which', return_value=None), \
             patch.object(health.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(SystemExit, 'No supported terminal'):
                health.launch_terminal()
        spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
