"""Adapter, routing and no-download checks; no synthetic inference is called real."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app import web_local_engine, web_hybrid, web_builder, server, llm


class LocalEngineTests(unittest.TestCase):
    def test_missing_engine_never_invokes_chat_setup_or_agent(self):
        with patch.object(llm,'status',return_value={'online':False}),patch.object(web_local_engine,'_ollama',side_effect=OSError),patch.object(server,'_ensure_chat_components') as install,patch.object(llm,'chat') as chat:
            status=web_local_engine.status()
            self.assertFalse(status['ready'])
            with self.assertRaisesRegex(RuntimeError,'Aucun modèle|Aucun modèle|Moteur local'):web_local_engine.generate('system','{}','brief')
            install.assert_not_called();chat.assert_not_called()

    def test_ollama_uses_only_installed_local_models_and_json_files(self):
        with patch.object(llm,'status',return_value={'online':False}),patch.object(web_local_engine,'_ollama',return_value={'models':[{'name':'qwen-cloud','size':1},{'name':'qwen-coder:7b','size':2}]}) as api:
            state=web_local_engine.status();self.assertEqual(state['model'],'qwen-coder:7b')
            api.return_value={'message':{'content':json.dumps({'files':{'index.html':'<h1>Fixture</h1>'}})}}
            result=web_local_engine.generate('system','{}','brief',engine=state)
            self.assertIn('index.html',result)
            self.assertEqual(api.call_args.args[0],'/api/chat')
            payload=api.call_args.args[1];self.assertFalse(payload['stream']);self.assertEqual(payload['format'],'json')
            self.assertEqual(payload['model'],'qwen-coder:7b')

    def test_native_model_does_not_need_download_setup(self):
        with patch.object(llm,'chat',return_value='{"files":{}}') as chat,patch.object(server,'_ensure_chat_components') as install,patch.object(server,'comfy_online',return_value=(False,'')),patch.object(web_local_engine,'status',return_value={'ready':True,'backend':'llama.cpp','model':'installed.gguf'}):
            self.assertEqual(server._web_llm_generate('system','context','brief'),'{"files":{}}')
            chat.assert_called_once();install.assert_not_called()

    def test_old_automatic_provider_is_not_an_explicit_remote_choice(self):
        for provider in ('codex','claude','auto','local'):
            self.assertEqual(server._web_project_provider({'settings':{'ai_provider':provider}}),'local')
        self.assertEqual(server._web_project_provider({'settings':{'ai_provider':'codex'},'agent_selected_by_user':True}),'codex')
        self.assertEqual(web_hybrid.select_coding_agent('auto',{'codex':{'ready':True}}),'local')

    def test_missing_model_fails_before_accepting_background_job(self):
        with tempfile.TemporaryDirectory() as folder:
            store=web_builder.LocalAiWebStore(folder,lambda *_:'{}');pid=store.create('Fixture')['project']['id']
            with patch.object(server,'_web_store',return_value=store),patch.object(web_local_engine,'status',return_value={'ready':False,'detail':'Modèle local absent'}),patch.object(server.threading,'Thread') as thread,patch.object(server.integrations_cli,'coding_agent_status') as remote:
                with self.assertRaisesRegex(RuntimeError,'Modèle local absent'):server._web_start_generation(pid,'Créer un portfolio')
                thread.assert_not_called();remote.assert_not_called()
