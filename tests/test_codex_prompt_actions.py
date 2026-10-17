"""Targeted regressions for Codex CLI compatibility and chat-only prompt actions."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from local_app import integrations_cli

ROOT=Path(__file__).resolve().parent.parent


class CodexExecCommandTests(unittest.TestCase):
    def test_new_codex_exec_uses_workspace_sandbox_not_removed_full_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            response=SimpleNamespace(returncode=0,stdout='Fichiers créés.',stderr='')
            with patch.object(integrations_cli,'_codex_cmd',return_value=['codex.cmd']), \
                 patch.object(integrations_cli,'_run',return_value=response) as runner:
                result=integrations_cli.codex_apply(Path(tmp),'Créer mon site PawMood')
            self.assertTrue(result['ok'])
            argv=runner.call_args.args[0]
            self.assertEqual(argv[:2],['codex.cmd','exec'])
            self.assertEqual(argv[argv.index('--sandbox')+1],'workspace-write')
            self.assertIn('--skip-git-repo-check',argv)
            self.assertNotIn('--full-auto',argv)
            self.assertIn('Créer mon site PawMood',argv[-1])
            self.assertEqual(runner.call_args.kwargs['cwd'],Path(tmp))

    def test_other_agent_arguments_are_untouched(self):
        code=(ROOT/'local_app'/'integrations_cli.py').read_text(encoding='utf-8')
        self.assertIn('def claude_apply(',code)
        self.assertIn('def codex_apply(',code)


class ChatMessageActionsContractTests(unittest.TestCase):
    def test_sent_messages_have_context_actions_and_full_history(self):
        script=(ROOT/'local_app'/'web'/'localaiweb.js').read_text(encoding='utf-8')
        self.assertIn("makeAction('Copier'",script)
        self.assertIn("makeAction('Renvoyer'",script)
        self.assertIn("if(isLastUserMessage(item))",script)
        self.assertIn("makeAction('Modifier'",script)
        self.assertIn("sendText(text,{preserveDraft:true})",script)
        self.assertIn("rows.forEach(row=>message(",script)
        self.assertNotIn("rows.slice(-24)",script)
        html=(ROOT/'local_app'/'web'/'localaiweb.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('data-view='),3)


if __name__=='__main__':
    unittest.main()
