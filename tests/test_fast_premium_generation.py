"""Low-latency quality checks without weakening visual/site validation."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from local_app import integrations_cli, web_browser_qa, web_hybrid, web_builder


class FastPremiumGenerationTests(unittest.TestCase):
    def test_javascript_validation_skips_build_artifacts_and_reuses_unchanged_checks(self):
        with TemporaryDirectory() as workspace:
            site=Path(workspace)
            (site/"src").mkdir()
            (site/"dist").mkdir()
            (site/"node_modules").mkdir()
            (site/".localaiweb-qa").mkdir()
            (site/"src"/"app.js").write_text("const ok=1;\n",encoding="utf-8")
            (site/"src"/"view.mjs").write_text("export const page='fr';\n",encoding="utf-8")
            (site/"dist"/"bundle.js").write_text("missing generated syntax",encoding="utf-8")
            (site/"node_modules"/"thirdparty.js").write_text("thirdparty code",encoding="utf-8")
            (site/".localaiweb-qa"/"temp.js").write_text("temporary code",encoding="utf-8")
            calls=[]
            def fake_run(args, **kwargs):
                calls.append(Path(args[-1]).relative_to(site).as_posix())
                return SimpleNamespace(returncode=0,stderr="",stdout="")
            with patch.object(integrations_cli,"_which",return_value="node"),patch.object(
                integrations_cli,"_run",side_effect=fake_run):
                first=integrations_cli.validate_site(site)
                self.assertEqual(first["checked"],2)
                self.assertEqual(first["cached"],0)
                second=integrations_cli.validate_site(site)
                self.assertEqual(second["checked"],2)
                self.assertEqual(second["cached"],2)
                self.assertEqual(sorted(calls),["src/app.js","src/view.mjs"])
                (site/"src"/"app.js").write_text("const ok=2;\n",encoding="utf-8")
                changed=integrations_cli.validate_site(site)
                self.assertEqual(changed["cached"],1)
                self.assertEqual(calls.count("src/app.js"),2)

    def test_bad_javascript_is_still_reported_and_rechecked_after_repair(self):
        with TemporaryDirectory() as workspace:
            site=Path(workspace);source=site/"app.js"
            source.write_text("let = broken",encoding="utf-8")
            def fake_run(args, **kwargs):
                data=source.read_text(encoding="utf-8")
                return SimpleNamespace(returncode=int("broken" in data),
                                       stderr="SyntaxError",stdout="")
            with patch.object(integrations_cli,"_which",return_value="node"),patch.object(
                integrations_cli,"_run",side_effect=fake_run):
                self.assertFalse(integrations_cli.validate_site(site)["ok"])
                source.write_text("const repaired=true;",encoding="utf-8")
                self.assertTrue(integrations_cli.validate_site(site)["ok"])

    def test_site_generation_records_actual_stage_durations(self):
        with TemporaryDirectory() as workspace:
            store=web_builder.LocalAiWebStore(Path(workspace),lambda *_:"{}")
            pid=store.create("Atelier couleur")["project"]["id"]
            quality={"ok":True,"findings":[],"syntax":{"ok":True,"issues":[]},
                     "preflight":{"ok":True,"score":92,"blockers":[]},
                     "build":{"ok":True,"kind":"static","output_dir":str(store.project_dir(pid)/"site")}}
            visual={"status":"unavailable","issues":[],"reviewed":False,"screenshots":[]}
            def agent(site,instruction):
                (site/"index.html").write_text("<!doctype html><html lang='fr'><body><main>Atelier couleur site</main></body></html>",encoding="utf-8")
                return {"summary":"Site réalisé"}
            progress=[]
            with patch.object(web_hybrid,"code_quality_report",return_value=quality),patch.object(
                web_browser_qa,"review",return_value=visual):
                payload=web_hybrid.build_with_agent(
                    store,pid,"Créer un atelier sur mesure",agent,integrations_cli,
                    {"assets":[],"generated":[]},first_preview=True,
                    progress=lambda phase,message:progress.append(phase))
            self.assertEqual(payload["generation_metrics"]["repairs"],0)
            self.assertGreaterEqual(payload["generation_metrics"]["total_seconds"],0)
            self.assertIn("preview",progress)
            self.assertEqual(store.meta(pid)["last_generation_metrics"]["visual_review"],"deferred_first_preview")
            self.assertIn("quality",payload)
            self.assertIn("hybrid_validation",payload)

    def test_real_browser_qa_catches_missing_local_images(self):
        source=Path(web_browser_qa.__file__).read_text(encoding="utf-8")
        self.assertIn("brokenLocalImages",source)
        self.assertIn("img.naturalWidth>0",source)
        self.assertIn("new URL(url,location.href).origin===location.origin",source)
        self.assertIn("images locales introuvables",source)


if __name__=="__main__":
    unittest.main()
