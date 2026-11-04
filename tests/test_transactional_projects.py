import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app import web_builder
from local_app.atomic_storage import atomic_write


class TransactionalProjectTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = web_builder.LocalAiWebStore(self.root, None)
        self.pid = self.store.create()['project']['id']
        self.store.write_files(self.pid, {'index.html': 'old index', 'style.css': 'old style'}, replace=True)
        self.site = self.store.project_dir(self.pid) / 'site'

    def test_invalid_second_file_does_not_destroy_first(self):
        with self.assertRaises(ValueError):
            self.store.write_files(self.pid, {'index.html': 'new', '../bad.js': 'bad'}, replace=True)
        self.assertEqual((self.site / 'index.html').read_text(), 'old index')
        self.assertEqual((self.site / 'style.css').read_text(), 'old style')

    def test_disk_error_rolls_back_whole_patch(self):
        def fail(path, raw):
            if Path(path) == self.site / 'new.js':
                raise OSError('disk full')
            return atomic_write(path, raw)
        with patch.object(web_builder, 'atomic_write', side_effect=fail):
            with self.assertRaises(OSError):
                self.store.write_files(self.pid, {'index.html': 'new', 'new.js': 'new'})
        self.assertEqual((self.site / 'index.html').read_text(), 'old index')
        self.assertFalse((self.site / 'new.js').exists())

    def test_real_process_death_recovers_old_files_on_restart(self):
        code = '''
import os,sys
from pathlib import Path
from local_app import web_builder
from local_app.atomic_storage import atomic_write
store=web_builder.LocalAiWebStore(sys.argv[1],None)
site=store.project_dir(sys.argv[2])/'site'
def crash(path,raw):
    atomic_write(path,raw)
    if Path(path)==site/'index.html': os._exit(73)
web_builder.atomic_write=crash
store.write_files(sys.argv[2],{'index.html':'new','style.css':'new'})
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.root), self.pid], check=False)
        self.assertEqual(result.returncode, 73)
        self.assertEqual((self.site / 'index.html').read_text(), 'new')
        web_builder.LocalAiWebStore(self.root, None)
        self.assertEqual((self.site / 'index.html').read_text(), 'old index')
        self.assertEqual((self.site / 'style.css').read_text(), 'old style')
        self.assertFalse((self.site.parent / '.site-transaction').exists())

    def test_snapshot_restores_media_and_preserves_secrets(self):
        asset = self.site / 'assets' / 'image.png'; asset.parent.mkdir(exist_ok=True)
        asset.write_bytes(b'original binary\x00\xff')
        private = self.site / '.env'; private.write_text('DO NOT EXPORT')
        version = self.store.snapshot(self.pid)
        asset.write_bytes(b'changed')
        (asset.parent / 'extra.png').write_bytes(b'new')
        self.store.write_files(self.pid, {'index.html':'new'})
        self.store.restore(self.pid, version['id'])
        self.assertEqual(asset.read_bytes(), b'original binary\x00\xff')
        self.assertFalse((asset.parent / 'extra.png').exists())
        self.assertEqual(private.read_text(), 'DO NOT EXPORT')
        self.assertEqual((self.site / 'index.html').read_text(), 'old index')
        self.assertNotIn(b'DO NOT EXPORT', self.store.export_zip(self.pid))

    def test_corrupt_archive_is_refused_without_site_changes(self):
        version = self.store.snapshot(self.pid)
        archive = self.site.parent / 'versions' / (version['id'] + '.zip')
        archive.write_bytes(b'broken')
        with self.assertRaises(ValueError):
            self.store.restore(self.pid, version['id'])
        self.assertEqual((self.site / 'index.html').read_text(), 'old index')

    def test_legacy_text_only_snapshot_still_restores(self):
        versions = self.site.parent / 'versions'; versions.mkdir(exist_ok=True)
        (versions / 'legacy1.json').write_text(json.dumps({'id':'legacy1','files':{'index.html':'legacy'}}))
        self.store.restore(self.pid, 'legacy1')
        self.assertEqual((self.site / 'index.html').read_text(), 'legacy')

    def test_atomic_replace_failure_keeps_previous_metadata(self):
        before = (self.site.parent / 'project.json').read_bytes()
        with patch('local_app.atomic_storage.os.replace', side_effect=OSError('interruption')):
            with self.assertRaises(OSError):
                self.store.write_meta(self.pid, {'new':'metadata'})
        self.assertEqual((self.site.parent / 'project.json').read_bytes(), before)
        self.assertFalse(list(self.site.parent.glob('*.pending')))
