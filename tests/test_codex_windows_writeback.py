"""Codex Windows no-write fallback and LocalAiWeb update-button contracts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from local_app import integrations_cli, web_codex_writeback as wb

ROOT=Path(__file__).resolve().parent.parent
PLACEHOLDER_HTML='<html><body><main>La prévisualisation devrait apparaitre ici.</main></body></html>'
REAL_HTML=('<!doctype html><html lang="fr"><head><title>PawMood</title>'
           '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
           '<body><header>PawMood</header><main><h1>Toilettage</h1>'
           '<p>Réservation, services, galerie de toilettage.</p></main></body></html>')


class SafeWritebackTests(unittest.TestCase):
    def test_normal_writable_codex_requires_actual_changed_website(self):
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory)
            (site/'index.html').write_text(PLACEHOLDER_HTML,encoding='utf-8')
            def direct(args,cwd=None,timeout=900,input_text=None):
                self.assertEqual(args[-1],'-')
                self.assertIn('PawMood',input_text)
                (site/'index.html').write_text(REAL_HTML,encoding='utf-8')
                return type('Result',(),{'returncode':0,'stdout':'done','stderr':''})()
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',side_effect=direct) as mock:
                result=integrations_cli.codex_apply(site,'Crée PawMood')
            self.assertEqual(mock.call_count,1)
            self.assertEqual(result['method'],'workspace-write')
            self.assertNotIn(wb.PLACEHOLDER,(site/'index.html').read_text())

    def test_silent_codex_success_uses_validated_files_not_empty_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory)
            (site/'index.html').write_text(PLACEHOLDER_HTML,encoding='utf-8')
            called=[]
            def mock_cli(args,cwd=None,timeout=900,input_text=None):
                called.append(args)
                if '--output-last-message' in args:
                    output=Path(args[args.index('--output-last-message')+1])
                    output.write_text(json.dumps({'files':{'index.html':REAL_HTML,
                        'styles.css':'body {font-family:sans-serif;color:navy}'}}),encoding='utf-8')
                return type('Result',(),{'returncode':0,'stdout':'done','stderr':''})()
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',side_effect=mock_cli):
                result=integrations_cli.codex_apply(site,'Crée un salon PawMood',timeout=180)
            self.assertEqual(len(called),2)
            self.assertIn('workspace-write',called[0])
            self.assertIn('read-only',called[1])
            self.assertEqual(result['method'],'validated-writeback')
            self.assertIn('PawMood',(site/'index.html').read_text(encoding='utf-8'))

    def test_no_unrestricted_codex_approvals_or_first_preview_json_only(self):
        main=(ROOT/'local_app/server.py').read_text(encoding='utf-8')
        cli=(ROOT/'local_app/integrations_cli.py').read_text(encoding='utf-8')
        hybrid=(ROOT/'local_app/web_hybrid.py').read_text(encoding='utf-8')
        self.assertIn('prefer_bundle=False',main)
        self.assertIn('allow_retry=True',main)
        self.assertIn('workspace-write',cli)
        self.assertNotIn('danger-full-access',cli)
        self.assertIn("deferred_first_preview",hybrid)

    def test_windows_read_only_codex_json_writeback(self):
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory)
            (site/'index.html').write_text(PLACEHOLDER_HTML,encoding='utf-8')
            (site/'assets').mkdir()
            (site/'assets'/'product.png').write_bytes(b'original')
            commands=[]
            def mocked(args,cwd=None,timeout=900,input_text=None):
                commands.append((list(args),input_text))
                if '--output-last-message' in args:
                    target=Path(args[args.index('--output-last-message')+1])
                    target.write_text(json.dumps({'files':{
                        'index.html':REAL_HTML,
                        'styles.css':'body { color: #188bc5; background: #f7f8fa; }',
                        'app.js':'document.title = "PawMood";'
                    }}),encoding='utf-8')
                return type('Result',(),{'returncode':0,'stdout':'Codex finished','stderr':''})()
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',side_effect=mocked):
                result=integrations_cli.codex_apply(site,'Crée PawMood')
            self.assertEqual(len(commands),2)
            self.assertIn('workspace-write',commands[0][0])
            self.assertEqual(commands[0][0][-1],'-')
            self.assertIn('PawMood',commands[0][1])
            self.assertIn('read-only',commands[1][0])
            self.assertEqual(commands[1][0][-1],'-')
            self.assertIn('USER REQUEST:',commands[1][1])
            self.assertEqual(result['method'],'validated-writeback')
            self.assertIn('PawMood',(site/'index.html').read_text())
            self.assertEqual((site/'assets'/'product.png').read_bytes(),b'original')

    def test_failed_readonly_fallback_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory);(site/'index.html').write_text(PLACEHOLDER_HTML)
            def mocked(args,cwd=None,timeout=900,input_text=None):
                if '--output-last-message' in args:
                    Path(args[args.index('--output-last-message')+1]).write_text('No code generated')
                return type('Result',(),{'returncode':0,'stdout':'done','stderr':''})()
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',side_effect=mocked):
                with self.assertRaisesRegex(RuntimeError,'JSON'):
                    integrations_cli.codex_apply(site,'Crée PawMood')
            self.assertIn(wb.PLACEHOLDER,(site/'index.html').read_text())

    def test_reject_escape_and_secret_files_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory);(site/'index.html').write_text(PLACEHOLDER_HTML)
            for bad in ('../outside.html','C:/bad.html','.env','assets/../outside.html',
                        'node_modules/payload.js','../../hack.js'):
                with self.subTest(path=bad):
                    with self.assertRaises(ValueError):
                        wb.apply_bundle(site,json.dumps({'files':{'index.html':REAL_HTML,bad:'evil'}}))
                    self.assertIn(wb.PLACEHOLDER,(site/'index.html').read_text())


class UpdaterButtonTests(unittest.TestCase):
    def test_updater_is_available_on_hub_and_editor(self):
        for file in ('localaiweb-projects.html','localaiweb.html'):
            text=(ROOT/'local_app/web'/file).read_text(encoding='utf-8')
            self.assertIn('id="lawUpdateBtn"',text)
            self.assertIn('localaiweb-update.js',text)
        script=(ROOT/'local_app/web/localaiweb-update.js').read_text(encoding='utf-8')
        self.assertIn('/api/update/check',script)
        self.assertIn('/api/update/install',script)
        self.assertIn("method:'POST'",script)
        self.assertIn('window.confirm(',script)
        self.assertIn('btn.disabled=true',script)
        main=(ROOT/'local_app/server.py').read_text(encoding='utf-8')
        self.assertIn('def install_latest_update(manual=False)',main)
        self.assertIn('if u.path == "/api/update/install":',main)


if __name__=='__main__':
    unittest.main()
