"""Known CLI failures must not trigger an unrelated second model call."""
from pathlib import Path
import tempfile
import subprocess
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from local_app import integrations_cli as cli

class CodexFailureTests(TestCase):
    def test_network_quota_and_login_errors_do_not_retry_or_expose_raw_cli_output(self):
        for stderr,expected in [('error sending request: connection reset','réseau'),('429 quota exceeded','limite'),('401 Unauthorized','authentification')]:
            with self.subTest(stderr=stderr),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'index.html';path.write_text('<p>Existing project stays intact</p>')
                result=SimpleNamespace(returncode=1,stdout='',stderr=stderr+' token=DO_NOT_EXPOSE')
                with patch.object(cli,'_codex_cmd',return_value=['codex']),patch.object(cli,'_run',return_value=result) as run:
                    with self.assertRaises(RuntimeError) as error:cli.codex_apply(folder,'Improve my project')
                self.assertIn(expected,str(error.exception));self.assertNotIn('DO_NOT_EXPOSE',str(error.exception))
                self.assertEqual(run.call_count,1);self.assertIn('Existing project',path.read_text())

    def test_timeout_is_not_a_missing_authentication(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(cli,'_codex_cmd',return_value=['codex']),patch.object(cli,'_run',side_effect=subprocess.TimeoutExpired(['codex'],900)) as run:
            with self.assertRaisesRegex(RuntimeError,'réseau'):cli.codex_apply(folder,'My site')
            self.assertEqual(run.call_count,1)

    def test_recovery_keeps_real_files_written_before_transport_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            def partial(*args,**kwargs):
                (Path(folder)/'index.html').write_text('<!doctype html><html lang="fr"><title>Existing work</title><main>Real written project content preserved for the build and QA gates.</main></html>')
                return SimpleNamespace(returncode=1,stdout='',stderr='connection reset')
            with patch.object(cli,'_codex_cmd',return_value=['codex']),patch.object(cli,'_run',side_effect=partial) as run:
                result=cli.codex_apply(folder,'My site')
            self.assertEqual(run.call_count,1);self.assertEqual(result['method'],'workspace-write')

    def test_successful_no_write_response_with_numbers_or_cdn_mentions_can_use_writeback(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            def run(args,**kwargs):
                if '--output-last-message' in args:
                    output=Path(args[args.index('--output-last-message')+1])
                    output.write_text(json.dumps({'files':{'index.html':'<!doctype html><html lang="fr"><head><title>Atelier de recette</title></head><body><header>Atelier de recette</header><main><h1>Nos créations</h1><p>Présentation complète des services de cet atelier fictif, avec informations et coordonnées de démonstration clairement identifiées.</p></main></body></html>'}}))
                return SimpleNamespace(returncode=0,stdout='Use CDNs; image width 429 pixels.',stderr='')
            with patch.object(cli,'_codex_cmd',return_value=['codex']),patch.object(cli,'_run',side_effect=run) as mocked:
                result=cli.codex_apply(folder,'My site')
            self.assertEqual(mocked.call_count,2);self.assertEqual(result['method'],'validated-writeback')
