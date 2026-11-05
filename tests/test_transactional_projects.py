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

    def test_reader_process_cannot_rollback_a_live_writer_transaction(self):
        import threading
        code = """
import sys
from pathlib import Path
from local_app import web_builder
from local_app.atomic_storage import atomic_write
store=web_builder.LocalAiWebStore(sys.argv[1],None)
site=store.project_dir(sys.argv[2])/'site'
def pause(path,raw):
    atomic_write(path,raw)
    if Path(path)==site/'index.html':
        print('written',flush=True);sys.stdin.readline()
web_builder.atomic_write=pause
store.write_files(sys.argv[2],{'index.html':'new','style.css':'new'})
"""
        proc=subprocess.Popen([sys.executable,'-c',code,str(self.root),self.pid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        self.assertEqual(proc.stdout.readline().strip(),'written')
        done=threading.Event()
        def reader():
            web_builder.LocalAiWebStore(self.root,None)
            done.set()
        thread=threading.Thread(target=reader);thread.start()
        try:
            self.assertFalse(done.wait(.15),'An active writer must retain its journal')
        finally:
            proc.stdin.write('continue\n');proc.stdin.flush()
        self.assertEqual(proc.wait(timeout=10),0)
        thread.join(timeout=10);self.assertTrue(done.is_set())
        self.assertEqual((self.site/'index.html').read_text(),'new')
        self.assertEqual((self.site/'style.css').read_text(),'new')
        proc.stdin.close();proc.stdout.close()

    def test_unsupported_replacement_cannot_erase_existing_site(self):
        with self.assertRaises(ValueError):
            self.store.write_files(self.pid, {'image.png':'invalid text image'}, replace=True)
        self.assertEqual((self.site/'index.html').read_text(),'old index')
        self.assertEqual((self.site/'style.css').read_text(),'old style')

    def test_editor_cannot_rename_a_secret_into_a_public_file(self):
        secret=self.site/'.env'
        secret.write_text('PRIVATE TOKEN')
        with self.assertRaises(ValueError):
            self.store.rename_file(self.pid,'.env','public.txt')
        self.assertEqual(secret.read_text(),'PRIVATE TOKEN')
        self.assertFalse((self.site/'public.txt').exists())

    def test_real_process_death_recovers_rename_without_duplicate_or_loss(self):
        code = """
import os,sys
from pathlib import Path
from local_app import web_builder
from local_app.atomic_storage import atomic_copy
store=web_builder.LocalAiWebStore(sys.argv[1],None)
site=store.project_dir(sys.argv[2])/'site'
def crash(source,destination):
    atomic_copy(source,destination)
    if Path(destination)==site/'renamed.html':os._exit(74)
web_builder.atomic_copy=crash
store.rename_file(sys.argv[2],'index.html','renamed.html')
"""
        result=subprocess.run([sys.executable,'-c',code,str(self.root),self.pid],check=False)
        self.assertEqual(result.returncode,74)
        self.assertTrue((self.site/'renamed.html').exists())
        web_builder.LocalAiWebStore(self.root,None)
        self.assertEqual((self.site/'index.html').read_text(),'old index')
        self.assertFalse((self.site/'renamed.html').exists())
        self.assertFalse((self.site.parent/'.site-transaction').exists())

    def test_deletion_recovers_if_transaction_commit_cannot_be_written(self):
        def fail_commit(path,raw):
            if Path(path).name=='manifest.json' and json.loads(raw).get('committed'):
                raise OSError('Commit interrupted')
            return atomic_write(path,raw)
        with patch.object(web_builder,'atomic_write',side_effect=fail_commit):
            with self.assertRaises(OSError):self.store.delete_file(self.pid,'index.html')
        self.assertEqual((self.site/'index.html').read_text(),'old index')
        self.assertFalse((self.site.parent/'.site-transaction').exists())

    def test_directory_is_rejected_before_it_can_leave_an_unrecoverable_journal(self):
        folder=self.site/'styles.css'
        folder.mkdir()
        media=folder/'original.png'
        media.write_bytes(b'original media')
        for operation in (lambda:self.store.delete_file(self.pid,'styles.css'),
                          lambda:self.store.write_files(self.pid,{'index.html':'new','styles.css':'new'})):
            with self.assertRaises(ValueError):operation()
            self.assertFalse((self.site.parent/'.site-transaction').exists())
            self.assertEqual(media.read_bytes(),b'original media')
        # A new store must still start normally after both invalid operations.
        reopened=web_builder.LocalAiWebStore(self.root,None)
        self.assertEqual(reopened.text_files(self.pid)['index.html'],'old index')
