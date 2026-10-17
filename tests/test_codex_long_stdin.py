"""Prevent long Codex prompts from reentering the Windows CreateProcess command line."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from local_app import integrations_cli


HTML = ('<!doctype html><html lang="fr"><head><title>PawMood</title></head>'
        '<body><h1>PawMood</h1><p>Toilettage de chiens et de chats.</p>'
        '</body></html>')


class CodexStdinTests(unittest.TestCase):
    def test_subprocess_uses_utf8_stdin_not_a_command_argument(self):
        huge='Éléments esthétiques et précisions utilisateur. ' * 1500
        with patch.object(integrations_cli.subprocess, 'run', return_value=SimpleNamespace(
             returncode=0,stdout='ok',stderr='')) as runner:
            integrations_cli._run(['codex.cmd','exec','-'],input_text=huge)
        self.assertEqual(runner.call_args.args[0], ['codex.cmd','exec','-'])
        self.assertEqual(runner.call_args.kwargs['input'], huge)
        self.assertEqual(runner.call_args.kwargs['encoding'], 'utf-8')
        self.assertNotIn(huge, str(runner.call_args.args[0]))

    def test_very_long_prompt_is_piped_on_both_codex_attempts(self):
        huge='PawMood doit être très professionnel et conserver le bleu vert. ' * 1200
        with tempfile.TemporaryDirectory() as tmp:
            site=Path(tmp)
            (site/'index.html').write_text(
                '<html><body>La prévisualisation devrait apparaitre ici.</body></html>',
                encoding='utf-8')
            commands=[]
            def fake_run(args,cwd=None,timeout=900,input_text=None):
                commands.append((list(args),input_text))
                if '--output-last-message' in args:
                    target=Path(args[args.index('--output-last-message')+1])
                    target.write_text(json.dumps({'files': {'index.html':HTML}}),encoding='utf-8')
                return SimpleNamespace(returncode=0,stdout='Terminé.',stderr='')
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',side_effect=fake_run):
                result=integrations_cli.codex_apply(site,huge)
            self.assertEqual(len(commands),2)
            for argv,stdin in commands:
                self.assertEqual(argv[-1],'-')
                self.assertLess(len(' '.join(argv)),1000)
                self.assertGreater(len(stdin),32767)
                self.assertIn('PawMood',stdin)
            self.assertEqual(result['method'],'validated-writeback')
            self.assertIn('PawMood',(site/'index.html').read_text())


if __name__=='__main__':
    unittest.main()
