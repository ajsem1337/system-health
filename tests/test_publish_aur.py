import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_aur', ROOT / 'tools/publish_aur.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublishTests(unittest.TestCase):
    def test_initial_publish_repeat_and_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / 'remote.git'
            subprocess.run(['git', 'init', '--bare', '--initial-branch=master', str(remote)],
                           check=True, capture_output=True)
            recipe = root / 'recipe'
            recipe.mkdir()
            metadata = 'pkgbase = system-health\n\tpkgver = 0.1.0\n\tpkgrel = 1\n'
            (recipe / '.SRCINFO').write_text(metadata)
            (recipe / 'PKGBUILD').write_text('pkgname=system-health\n')
            (recipe / 'do-not-upload.txt').write_text('local report')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(publisher.publish(recipe, remote, root / 'first'))
                self.assertFalse(publisher.publish(recipe, remote, root / 'second'))
                (recipe / '.SRCINFO').write_text(metadata.replace('pkgrel = 1', 'pkgrel = 2'))
                self.assertTrue(publisher.publish(recipe, remote, root / 'third'))
            files = subprocess.check_output(['git', '--git-dir', str(remote), 'ls-tree', '--name-only', 'master'], text=True)
            self.assertEqual(set(files.splitlines()), {'PKGBUILD', '.SRCINFO'})
            count = subprocess.check_output(['git', '--git-dir', str(remote), 'rev-list', '--count', 'master'], text=True)
            self.assertEqual(count.strip(), '2')

    def test_incomplete_version_is_rejected_before_cloning(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory)
            (recipe / '.SRCINFO').write_text('pkgbase = system-health\n')
            with self.assertRaisesRegex(ValueError, 'version/release'):
                publisher.publish(recipe, 'unused', recipe / 'destination')
            self.assertFalse((recipe / 'destination').exists())

    def test_wrong_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory)
            (recipe / '.SRCINFO').write_text('pkgbase = unrelated\n')
            with self.assertRaises(ValueError):
                publisher.publish(recipe, 'unused', recipe / 'destination')
