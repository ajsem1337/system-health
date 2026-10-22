import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import types
import unittest
from unittest.mock import patch

import test_health as baseline

health, ROOT = baseline.health, baseline.ROOT


class CheckTests(unittest.TestCase):
    def output(self, check, *args):
        stream = io.StringIO()
        health.report.clear()
        with contextlib.redirect_stdout(stream):
            check(*args)
        return stream.getvalue()

    def test_invalid_json_does_not_abort_checks(self):
        for payload in ('not json', 'null', '[]', '"string"'):
            for check in (health.check_filesystems, health.check_temperatures, health.check_disks):
                with self.subTest(payload=payload, check=check.__name__), patch.object(
                    health, 'run', return_value=(0, payload, '')
                ):
                    self.assertIn('[NOT CHECKED]', self.output(check))

    def test_invalid_nested_data_is_not_healthy(self):
        cases = ((health.check_filesystems, {'filesystems': None}),
                 (health.check_filesystems, {'filesystems': [None]}),
                 (health.check_disks, {'devices': [None]}),
                 (health.check_temperatures, {'coretemp-isa-0000': None}))
        for check, data in cases:
            with patch.object(health, 'run', return_value=(0, json.dumps(data), '')):
                output = self.output(check)
                self.assertIn('[NOT CHECKED]', output)
                self.assertNotIn('[OK]', output)

    def test_invalid_sensor_numbers_are_not_healthy(self):
        for value in (None, '80', True, float('nan'), float('inf'), 1000, 10**400):
            data = {'coretemp-isa-0000': {'Core 0': {'temp1_input': value}}}
            with patch.object(health, 'run', return_value=(0, json.dumps(data), '')):
                self.assertIn('[NOT CHECKED]', self.output(health.check_temperatures))

    def test_temperatures_use_sensor_threshold_and_safe_fallback(self):
        for value, limit, status in ((80, 85, 'WARNING'), (70, 100, 'OK'), (90, 'bad', 'WARNING')):
            data = {'coretemp-isa-0000': {'Core 0': {'temp1_input': value, 'temp1_crit': limit}}}
            with patch.object(health, 'run', return_value=(0, json.dumps(data), '')):
                self.assertIn(f'[{status}] coretemp', self.output(health.check_temperatures))

    def test_unreadable_or_incomplete_memory_is_not_checked(self):
        for text in ('MemTotal: 0 kB\nMemAvailable: 0 kB', 'MemTotal: 100 kB', 'malformed'):
            with patch.object(Path, 'read_text', return_value=text):
                self.assertIn('[NOT CHECKED] Available RAM', self.output(health.check_memory))
        with patch.object(Path, 'read_text', side_effect=PermissionError('denied')):
            self.assertIn('[NOT CHECKED] Available RAM', self.output(health.check_memory))

    def test_capacity_and_inode_warnings(self):
        data = {'filesystems': [{'target': '/', 'fstype': 'ext4'}]}
        for free, inodes in ((5, 100), (80, 1)):
            info = types.SimpleNamespace(f_blocks=100, f_bfree=free, f_bavail=free,
                                         f_files=100, f_favail=inodes, f_frsize=4096)
            with patch.object(health, 'run', return_value=(0, json.dumps(data), '')), \
                 patch.object(health.os, 'statvfs', return_value=info):
                self.assertIn('[WARNING] Filesystem /', self.output(health.check_filesystems))

    def test_smart_exit_status_precedence(self):
        cases = ((0, True, {}, 'OK'), (8, None, {}, 'ERROR'), (0, False, {}, 'ERROR'),
                 (64, True, {}, 'WARNING'), (66, True, {}, 'NOT CHECKED'),
                 (-9, True, {}, 'NOT CHECKED'), (256, None, {}, 'NOT CHECKED'), (125, None, {}, 'ERROR'),
                 (0, None, {}, 'NOT CHECKED'), (0, True, {'percentage_used': 100}, 'WARNING'),
                 (0, True, {'critical_warning': 1}, 'ERROR'))
        for code, passed, nvme, expected in cases:
            with self.subTest(code=code, passed=passed, nvme=nvme):
                self.assertEqual(health.smart_status(code, passed, nvme), expected)

    def test_partial_smart_data_and_messages_do_not_crash(self):
        scan = {'devices': [{'name': '/dev/test', 'type': 'sat'}]}
        for payload in ({'smart_status': None}, {'smart_status': {'passed': True}, 'smartctl': {'messages': [None]}},
                        {'nvme_smart_health_information_log': {'percentage_used': 'bad'}}):
            def run(cmd, timeout=30):
                return 0, json.dumps(scan if '--scan' in cmd else payload), ''
            with patch.object(health, 'run', side_effect=run):
                output = self.output(health.check_disks)
                self.assertIn('SMART', output)

    def test_terminal_controls_are_removed_everywhere(self):
        payload = '\x1b]52;c;clipboard\x07\x1b[31mRED\x1b[0m\rspoof\x08\u202e'
        text = ('first\n' * 19) + payload
        output = self.output(health.item, 'WARNING', payload, text)
        saved = '\n'.join(health.report)
        for value in (output, saved):
            self.assertNotIn('\x1b', value)
            self.assertNotIn('\r', value)
            self.assertNotIn('\u202e', value)
            self.assertNotIn('clipboard', value)
            self.assertIn('RED', value)

    def test_report_storage_is_private_and_rejects_directory_symlink(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            folder = Path(directory) / 'system-health'
            folder.mkdir(mode=0o755)
            path = health.save_report()
            self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.unlink()
            folder.rmdir()
            target = Path(directory) / 'other'
            target.mkdir()
            folder.symlink_to(target, target_is_directory=True)
            with self.assertRaises(OSError):
                health.save_report()
            self.assertEqual(list(target.iterdir()), [])

    def test_relative_xdg_path_uses_default(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(health.xdg_directory('XDG_STATE_HOME', Path('/default')), Path('/default'))

    def test_installer_replaces_symlink_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / 'important.txt'
            target.write_text('keep me')
            binary = home / '.local/bin/system-health'
            binary.parent.mkdir(parents=True)
            binary.symlink_to(target)
            with patch('pathlib.Path.home', return_value=home), patch('os.geteuid', return_value=1000), \
                 patch.dict(os.environ, {'XDG_DATA_HOME': str(home / 'data')}), \
                 contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT / 'install.py'), run_name='__main__')
            self.assertEqual(target.read_text(), 'keep me')
            self.assertFalse(binary.is_symlink())
            self.assertTrue(binary.read_text().startswith('#!/usr/bin/env python3'))

    def test_launcher_tries_next_terminal_after_spawn_failure(self):
        with patch.object(health.shutil, 'which', side_effect=lambda n: f'/usr/bin/{n}'), \
             patch.object(health.subprocess, 'Popen', side_effect=[OSError('broken'), None]) as spawn:
            health.launch_terminal()
        self.assertEqual(spawn.call_count, 2)
        self.assertEqual(spawn.call_args.args[0][0], '/usr/bin/kgx')


class FullReportTests(unittest.TestCase):
    report = baseline.HealthTests.report

    def test_missing_paccheck_is_not_missing_package_files(self):
        output = self.report("[Errno 2] No such file or directory: 'paccheck'", health.RUN_FAILED)
        self.assertIn('[NOT CHECKED] Other package-file check diagnostics', output)
        self.assertNotIn('[WARNING] Missing package files', output)

    def test_limited_crash_journal_is_not_healthy(self):
        def command(cmd, timeout=30):
            if cmd[0] == 'coredumpctl':
                return 1, '', 'You are not seeing messages from other users.\nNo coredumps found.'
            if cmd[0] == 'findmnt':
                return 0, '{"filesystems": []}', ''
            if cmd[0] == 'sensors':
                return 0, '{}', ''
            return health.RUN_FAILED, '', 'unavailable'
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(health, 'run', side_effect=command), \
             patch.object(health.sys, 'argv', ['system-health']), \
             patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            output = self.output_report()
        self.assertIn('[NOT CHECKED] Recorded application crashes', output)
        self.assertNotIn('[OK] Recorded application crashes', output)

    def output_report(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            health.main()
        return output.getvalue()

    def test_missing_sudo_does_not_abort_report(self):
        with patch.object(health.sys, 'argv', ['system-health', '--smart']), \
             patch.object(health.os, 'geteuid', return_value=1000), \
             patch.object(health.subprocess, 'run', side_effect=FileNotFoundError('sudo missing')), \
             patch.object(health, 'run', return_value=(health.RUN_FAILED, '', 'unavailable')), \
             patch.object(health, 'save_report', return_value=Path('/tmp/test-report.txt')):
            output = self.output_report()
        self.assertIn('[NOT CHECKED] Privileged check authentication', output)
        self.assertIn('SUMMARY', output)
        self.assertIn('Full report:', output)

    def test_report_write_failure_has_clear_error_and_exit_status(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(health.sys, 'argv', ['system-health']), \
             patch.object(health, 'run', return_value=(health.RUN_FAILED, '', 'unavailable')), \
             patch.object(health, 'save_report', side_effect=PermissionError('read-only directory')), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = health.main()
        self.assertEqual(result, 1)
        self.assertIn('SUMMARY', output.getvalue())
        self.assertIn('Unable to save report:', errors.getvalue())

    def test_malformed_tools_still_produce_summary_and_saved_report(self):
        def command(cmd, timeout=30):
            return (0, 'not JSON', '') if ('smartctl' in cmd or cmd[0] in ('sensors', 'findmnt')) else (0, '', '')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(health.sys, 'argv', ['system-health']), \
             patch.object(health, 'run', side_effect=command), \
             patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            output = self.output_report()
            self.assertEqual(len(list(Path(directory).glob('system-health/report-*.txt'))), 1)
        self.assertGreaterEqual(output.count('Invalid JSON:'), 3)
        self.assertIn('SUMMARY', output)
