import collections
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from test_health import health


class CompactTests(unittest.TestCase):
    def setUp(self):
        for name, value in (('display_verbose', False), ('current_group', 'Other'),
                            ('results', []), ('report', ['SYSTEM HEALTH — test']),
                            ('counts', collections.Counter())):
            context = patch.object(health, name, value)
            context.start()
            self.addCleanup(context.stop)

    def render(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            health.render_compact()
        return output.getvalue()

    def test_history_is_separate_from_current_findings(self):
        health.item('OK', 'Failed system services', group='Services')
        health.item('WARNING', 'Current boot errors — up to 60 latest entries',
                    'old event', group='History')
        health.item('WARNING', 'Recorded application crashes in the last 24 hours',
                    'browser crash\nterminal crash', group='History')
        output = self.render()
        self.assertIn('OK — no issues found in completed checks.', output)
        self.assertIn('History        INFO', output)
        self.assertIn('2 app crashes / 24h', output)
        self.assertNotIn('REVIEW —', output)

    def test_real_disk_error_remains_prominent(self):
        health.item('ERROR', '/dev/test — SMART', group='Disk health')
        output = self.render()
        self.assertIn('ATTENTION — 1 reported error.', output)
        self.assertIn('Disk health    ERROR', output)
        self.assertIn('back up important data', output)
        self.assertNotIn('no critical findings', output)

    def test_all_unknown_is_incomplete(self):
        health.item('NOT CHECKED', 'Available RAM', group='RAM / storage')
        output = self.render()
        self.assertIn('INCOMPLETE', output)
        self.assertIn('Coverage: 1 check unavailable', output)
        self.assertNotIn('OK —', output)

    def test_partial_temperatures_keep_valid_peaks_and_unknown_state(self):
        health.item('OK', 'CPU reading', group='Temperatures', facts={'temperatures': {'CPU': 45.2}})
        health.item('OK', 'CPU second reading', group='Temperatures', facts={'temperatures': {'CPU': 72.1}})
        health.item('NOT CHECKED', 'GPU sensor', group='Temperatures')
        output = self.render()
        self.assertIn('Temperatures   PARTIAL', output)
        self.assertIn('CPU 72°C', output)
        self.assertIn('1 reading unavailable', output)

    def test_no_password_is_not_a_disk_failure(self):
        health.item('NOT CHECKED', 'Unable to enumerate SMART disks',
                    'sudo: a password is required', group='Disk health')
        output = self.render()
        self.assertIn('Disk health    NOT CHECKED', output)
        self.assertIn('system-health --smart', output)
        self.assertNotIn('ERROR', output)
        self.assertNotIn('ATTENTION', output)

    def test_unknown_groups_and_extra_findings_remain_visible(self):
        for number in range(8):
            health.item('ERROR', f'Unexpected check {number}', group='Other')
        output = self.render()
        self.assertIn('8 reported errors', output)
        self.assertIn('Other          ERROR', output)
        self.assertIn('more in report', output)

    def sample_report(self, verbose=False):
        def run(cmd, timeout=30):
            if cmd[0] == 'systemctl':
                return 0, '', ''
            if cmd[0] == 'journalctl':
                return 0, '\n'.join(f'STACK_DETAIL_{n}' for n in range(80)), ''
            if cmd[0] == 'coredumpctl':
                return 0, 'browser crash\nterminal crash', ''
            if cmd[0] == 'timedatectl':
                return 0, 'yes', ''
            if cmd[0] == 'pacman':
                return 1, '', "error: 'package-notice': description file is missing"
            if cmd[0] == 'checkrebuild':
                return 0, 'foreign\tapp-alpha\nforeign\tapp-beta\n\nldd /lib/test.so\nlibmissing => not found', ''
            if cmd[0] == 'pacdiff':
                return 0, '\n'.join(f'/etc/test-{n}.pacnew' for n in range(5)), ''
            if cmd[0] == 'findmnt':
                return 0, json.dumps({'filesystems': [{'target': '/', 'fstype': 'ext4'}]}), ''
            if cmd[0] == 'sensors':
                return 0, json.dumps({
                    'coretemp-isa-0000': {f'Core {n}': {'temp1_input': 40 + n} for n in range(12)},
                    'amdgpu-pci-0000': {'edge': {'temp1_input': 58}},
                    'nvme-pci-0000': {'Composite': {'temp1_input': 39}},
                }), ''
            return 1, '', 'sudo: a password is required'
        def memory():
            health.item('OK', 'Available RAM', '19.1 / 31.2 GiB available',
                        facts={'brief': 'RAM 19.1/31.2 GiB available'})
        usage = types.SimpleNamespace(f_blocks=100, f_bfree=38, f_bavail=38,
                                      f_files=100, f_favail=80, f_frsize=4096)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'XDG_STATE_HOME': directory}), \
             patch.object(health.sys, 'argv', ['system-health'] + (['--verbose'] if verbose else [])), \
             patch.object(health, 'run', side_effect=run), \
             patch.object(health, 'check_memory', side_effect=memory), \
             patch.object(health.os, 'statvfs', return_value=usage), \
             patch.object(health.shutil, 'get_terminal_size', return_value=os.terminal_size((100, 24))):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(health.main(), 0)
            paths = list(Path(directory).glob('system-health/report-*.txt'))
            self.assertEqual(len(paths), 1)
            return output.getvalue(), paths[0].read_text()

    def test_default_report_fits_one_screen_and_keeps_full_diagnostics(self):
        output, saved = self.sample_report()
        self.assertLessEqual(len(output.splitlines()), 24)
        self.assertIn('REVIEW — 3 items to review', output)
        self.assertIn('CPU 51°C | GPU 58°C | NVMe 39°C', output)
        self.assertIn('5 .pacnew / .pacsave files', output)
        self.assertNotIn('STACK_DETAIL', output)
        self.assertNotIn('ldd /lib/test.so', output)
        self.assertIn('STACK_DETAIL_79', saved)
        self.assertIn('libmissing => not found', saved)
        self.assertEqual(saved.count('[OK] coretemp-'), 12)
        self.assertIn('Full report:', output)

    def test_verbose_is_available_without_losing_saved_details(self):
        output, saved = self.sample_report(verbose=True)
        self.assertIn('STACK_DETAIL_0', output)
        self.assertIn('coretemp-isa-0000 / Core 0', output)
        self.assertIn('STACK_DETAIL_79', saved)
        self.assertIn('SUMMARY', output)

    def test_verbose_flag_is_forwarded_by_desktop_launcher(self):
        with patch.object(health.shutil, 'which', return_value='/usr/bin/kitty'), \
             patch.object(health.subprocess, 'Popen') as spawn:
            health.launch_terminal(verbose=True)
        self.assertIn('--verbose', spawn.call_args.args[0])
