"""Operational Codex Plus + cinematic rendering integration contracts."""
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from local_app import web_builder, web_hybrid, integrations_cli

ROOT=Path(__file__).resolve().parents[1]

class CodexPlusStudioTests(TestCase):
    def setUp(self):
        work=tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.store=web_builder.LocalAiWebStore(Path(work.name)/"projects",lambda *_:"{}")
        self.project=self.store.create("Parfumerie Atelier")
        self.pid=self.project["project"]["id"]

    def test_new_project_codex_and_persistent_cinematic_direction(self):
        meta=self.store.meta(self.pid)
        self.assertEqual(meta["settings"]["ai_provider"],"codex")
        self.assertEqual(meta["settings"]["art_direction"],"auto")
        self.store.update_settings(self.pid,{"ai_provider":"codex","art_direction":"spatial3d"})
        after=self.store.meta(self.pid)
        self.assertEqual(after["settings"]["art_direction"],"spatial3d")
        self.assertIn("Three.js",web_builder.generation_direction(after["settings"]))
        self.assertEqual(self.store.payload(self.pid)["project"]["id"],self.pid)

    def test_cinematic_preference_reaches_actual_agent_and_qa(self):
        self.store.update_settings(self.pid,{"art_direction":"spatial3d"})
        calls=[]
        def fake_agent(site,instruction):
            calls.append(instruction)
            return {"summary":"Exemple construit"}
        quality={"ok":True,"findings":[],"syntax":{"ok":True,"issues":[]},
                 "preflight":{"ok":True,"score":92,"blockers":[]},
                 "build":{"ok":True,"kind":"static"}}
        visual={"status":"unavailable","issues":[],"reviewed":False,"screenshots":[]}
        with patch("local_app.web_hybrid.code_quality_report",return_value=quality), \
             patch("local_app.web_browser_qa.review",return_value=visual):
            output=web_hybrid.build_with_agent(
                self.store,self.pid,"Site de parfum haut de gamme 3D",
                fake_agent,object(),{"generated":[],"notes":[]})
        self.assertEqual(len(calls),1)
        self.assertIn("Art direction: ",calls[0])
        self.assertIn("3D",calls[0])
        self.assertIn("real Three.js",calls[0])
        self.assertEqual(output["project"]["id"],self.pid)
        self.assertEqual(output["hybrid_validation"]["visual"]["status"],"unavailable")

    def test_cmd_found_from_standard_user_npm_install(self):
        with tempfile.TemporaryDirectory() as folder:
            npm=Path(folder)/"npm"
            npm.mkdir()
            cli=npm/"codex.cmd"
            cli.write_text("@echo off",encoding="utf-8")
            with patch.object(integrations_cli,"_which",return_value=None), \
                 patch.dict(os.environ,{"APPDATA":str(Path(folder))}):
                self.assertEqual(integrations_cli._codex_cmd(),[str(cli)])

    def test_provider_selector_and_login_are_real_not_an_api_key(self):
        js=(ROOT/"local_app/web/localaiweb-agent.js").read_text(encoding="utf-8")
        server=(ROOT/"local_app/server.py").read_text(encoding="utf-8")
        cli=(ROOT/"local_app/integrations_cli.py").read_text(encoding="utf-8")
        self.assertIn("selectedProvider()",js)
        self.assertIn("provider:'",js.replace('const provider=selectedProvider()',"provider:'"))
        self.assertIn("/api/web/project/agent-settings",js)
        self.assertIn("codex",server)
        self.assertIn('args = cmd + ["login"]',cli)
        self.assertNotIn('npx", "--yes", "@openai/codex"',cli)
