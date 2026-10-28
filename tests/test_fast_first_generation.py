"""First LocalAiWeb generation must be observable, fail fast and avoid GPU work."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from local_app import server, web_hybrid, web_builder, integrations_cli

class FastFirstGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=web_builder.LocalAiWebStore(Path(self.tmp.name)/"projects",lambda *_:"{}")
        self.pid=self.store.create("Salon Demo")["project"]["id"]
        with server._web_generation_lock:
            server._web_generation_jobs.clear()
        with server._web_progress_lock:
            server._web_progress_rows.clear()

    def test_async_start_returns_ticket_and_prevents_duplicate_coding(self):
        with patch.object(server,"_web_store",return_value=self.store), \
             patch.object(integrations_cli,"coding_agent_status",
                          return_value={"codex":{"installed":True,"ready":True}}), \
             patch.object(server.threading,"Thread") as thread:
            first=server._web_start_generation(self.pid,"Création d'un site moderne et responsive")
            second=server._web_start_generation(self.pid,"Autre demande")
            self.assertEqual(first["state"],"running")
            self.assertEqual(second["ticket"],first["ticket"])
            self.assertTrue(second["already_running"])
            self.assertEqual(thread.call_count,1)
            self.assertEqual(thread.call_args.kwargs["daemon"],True)
            status=server._web_generation_status(self.pid)
            self.assertEqual(status["state"],"running")
            self.assertFalse(status["preview_ready"])

    def test_unavailable_codex_fails_before_starting_a_job(self):
        with patch.object(server,"_web_store",return_value=self.store), \
             patch.object(integrations_cli,"coding_agent_status",
                          return_value={"codex":{"installed":True,"ready":False}}), \
             patch.object(server.threading,"Thread") as thread:
            with self.assertRaisesRegex(RuntimeError,"Codex"):
                server._web_start_generation(self.pid,"Création d'un site moderne")
            thread.assert_not_called()
            self.assertNotIn(self.pid,server._web_generation_jobs)

    def test_stored_files_mark_first_preview_real_only(self):
        with patch.object(server,"_web_store",return_value=self.store):
            status=server._web_generation_status(self.pid)
            self.assertFalse(status["preview_ready"])
            site=self.store.project_dir(self.pid)/"site"
            (site/"index.html").write_text(
                "<!doctype html><html lang='fr'><head><title>Salon</title></head>"
                "<body><main><h1>Salon</h1><p>Bienvenue dans notre salon.</p></main></body></html>",
                encoding="utf-8")
            status=server._web_generation_status(self.pid)
            self.assertTrue(status["preview_ready"])
            self.assertTrue(status["preview_version"])

    def test_first_preview_never_starts_expensive_image_engine(self):
        def prohibited(*args,**kwargs):
            raise AssertionError("ComfyUI must not be invoked during the first preview")
        with patch.object(self.store,"assets",return_value=[]):
            assets=web_hybrid.make_visuals(
                self.store,self.pid,
                "Site immersif avec photographie de produit en 3D",
                local_generate=prohibited,local_ready=True,defer_new_images=True)
        self.assertEqual(assets["generated"],[])
        self.assertIn("différés",assets["notes"][0])

    def test_agent_check_does_not_probe_github_or_vercel(self):
        with patch.object(integrations_cli,"_codex_cmd",return_value=["codex.cmd"]), \
             patch.object(integrations_cli,"_run",return_value=SimpleNamespace(returncode=0)) as run:
            status=integrations_cli.coding_agent_status("codex")
        self.assertTrue(status["codex"]["ready"])
        self.assertEqual(run.call_args.args[0],["codex.cmd","login","status"])
        self.assertLessEqual(run.call_args.kwargs["timeout"],12)

    def test_frontend_starts_background_job_and_surfaces_preview_early(self):
        src=(Path(__file__).resolve().parents[1]/"local_app"/"web"/"localaiweb.js").read_text(encoding="utf-8")
        self.assertIn("/api/web/generate/start",src)
        self.assertIn("/api/web/generation/status",src)
        self.assertIn("preview_version",src)
        self.assertIn("already_running",src)
        self.assertNotIn("await api('/api/web/generate',{",src)

    def test_cached_npm_dependencies_do_not_reinstall_after_first_build(self):
        site=Path(self.tmp.name)/"site";site.mkdir()
        (site/"package.json").write_text('{"scripts":{"build":"vite build"}}',encoding="utf-8")
        (site/"node_modules").mkdir()
        calls=[]
        def fake_run(argv,**kwargs):
            calls.append(list(argv))
            (site/"dist").mkdir(exist_ok=True)
            (site/"dist"/"index.html").write_text("<html/>",encoding="utf-8")
            return SimpleNamespace(returncode=0,stderr="",stdout="")
        with patch.object(integrations_cli,"_which",return_value="npm.cmd"), \
             patch.object(integrations_cli,"_run",side_effect=fake_run):
            integrations_cli.build_project(site)
            integrations_cli.build_project(site)
        installs=[c for c in calls if c[1] in ("install","ci")]
        builds=[c for c in calls if c[1:3]==["run","build"]]
        self.assertEqual(len(installs),1)
        self.assertEqual(len(builds),2)

if __name__=="__main__":
    unittest.main()
