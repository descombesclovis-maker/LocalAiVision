import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app.web_builder import LocalAiWebStore
from local_app import server


class OriginalPrompt314(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = LocalAiWebStore(Path(self.tmp.name), lambda *_: '{}')

    def test_exact_first_prompt_survives_history_truncation_and_modifications(self):
        pid = self.store.create('Prompt exact')['project']['id']
        prompt = '  Crée mon site\navec café, accents et espaces.  ' + 'a' * 15000
        self.store.remember_original_prompt(pid, prompt)
        for i in range(205):
            self.store.append_chat(pid, 'user', 'Modification ' + str(i))
        self.store.remember_original_prompt(pid, 'Autre demande')
        self.assertEqual(self.store.meta(pid)['original_prompt'], prompt)
        self.assertEqual(len(self.store.chat_history(pid)), 200)

    def test_legacy_missing_prompt_is_never_invented_from_a_new_modification(self):
        pid = self.store.create('Ancien')['project']['id']
        meta = self.store.meta(pid)
        del meta['original_prompt']
        self.store.write_meta(pid, meta)
        self.store.remember_original_prompt(pid, 'Modifier la couleur')
        self.assertNotIn('original_prompt', self.store.meta(pid))

    def test_brief_records_raw_original_before_rewriting(self):
        pid = self.store.create('Brief')['project']['id']
        prompt = '  Un site de coiffure\navec rendez-vous.  '
        self.store.brief_begin(pid, prompt)
        self.assertEqual(self.store.meta(pid)['original_prompt'], prompt)

    def test_async_generation_keeps_user_text_instead_of_augmented_instructions(self):
        pid = self.store.create('Séparation du brief')['project']['id']
        meta = self.store.meta(pid)
        meta['settings']['ai_provider'] = 'local'
        self.store.write_meta(pid, meta)
        original = '  Mon site\nexact.  '
        with patch('local_app.web_local_engine.status',return_value={'ready':True}), patch.object(server, '_web_store', return_value=self.store), \
             patch.object(server.threading, 'Thread'), \
             patch.object(server, '_web_persist_generation'), \
             patch.object(server, '_web_progress'), \
             patch.dict(server._web_generation_jobs, {}, clear=True):
            server._web_start_generation(pid, 'BRIEF AUGMENTÉ PAR LE LOGICIEL', original)
        self.assertEqual(self.store.meta(pid)['original_prompt'], original)

    def test_delete_only_selected_project_and_reject_path_traversal(self):
        first = self.store.create('Premier')['project']['id']
        second = self.store.create('Second')['project']['id']
        before = self.store.payload(second)
        self.store.delete_project(first)
        self.assertEqual(self.store.payload(second), before)
        self.assertFalse(self.store.project_dir(first).exists())
        with self.assertRaises(ValueError):
            self.store.delete_project('../' + second)


if __name__ == '__main__':
    unittest.main()
