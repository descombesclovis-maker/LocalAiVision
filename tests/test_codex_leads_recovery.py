"""Regression tests for blocked Windows Codex, daily leads, checkbox UI and map imagery."""
import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from local_app import integrations_cli, web_business_map, web_design_profile
from local_app import web_prospects, web_map_no_website, web_builder, server

ROOT=Path(__file__).resolve().parents[1]
HTML='<html lang="fr"><head><title>Salon local</title></head><body><main><h1>Salon local</h1><p>Bienvenue dans notre salon.</p></main></body></html>'

class CodexPolicyRecovery(unittest.TestCase):
    def test_first_generation_windows_avoids_blocked_shell_edits(self):
        with tempfile.TemporaryDirectory() as root:
            site=Path(root)
            (site/"index.html").write_text("<html>La prévisualisation devrait apparaitre ici.</html>",encoding="utf-8")
            calls=[]
            def cli(args,**kwargs):
                calls.append((args,kwargs))
                self.assertNotIn("workspace-write",args)
                self.assertIn("read-only",args)
                self.assertIn("STRICT:",kwargs["input_text"])
                target=Path(args[args.index("--output-last-message")+1])
                target.write_text(json.dumps({"files":{"index.html":HTML,
                    "styles.css":"body { color: #333; }"}}),encoding="utf-8")
                return SimpleNamespace(returncode=0,stdout="done",stderr="")
            with patch.object(integrations_cli,"_codex_cmd",return_value=["codex.cmd"]), \
                 patch.object(integrations_cli,"_run",side_effect=cli):
                result=integrations_cli.codex_apply(site,"Crée un salon",timeout=240,
                                                allow_retry=False,prefer_bundle=True)
            self.assertEqual(len(calls),1)
            self.assertEqual(result["method"],"validated-writeback")
            self.assertIn("Salon local",(site/"index.html").read_text())

    def test_policy_blocked_direct_write_always_gets_safe_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            site=Path(root)
            (site/"index.html").write_text("La prévisualisation devrait apparaitre ici.",encoding="utf-8")
            def cli(args,**kwargs):
                if "--output-last-message" in args:
                    Path(args[args.index("--output-last-message")+1]).write_text(
                        json.dumps({"files":{"index.html":HTML}}),encoding="utf-8")
                    return SimpleNamespace(returncode=0,stdout="ok",stderr="")
                return SimpleNamespace(returncode=1,stdout="",stderr="Rejected: blocked by policy")
            with patch.object(integrations_cli,"_codex_cmd",return_value=["codex"]), \
                 patch.object(integrations_cli,"_run",side_effect=cli) as runner:
                result=integrations_cli.codex_apply(site,"Un salon",timeout=300,allow_retry=False)
            self.assertEqual(runner.call_count,2)
            self.assertEqual(result["method"],"validated-writeback")

class DailyFrenchProspects(unittest.TestCase):
    def test_many_points_can_be_indexed_and_five_ranked_without_guessing_websites(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ,{"LOCALVISIONAI_DATA":tmp}):
            rows=[{"id":"siret/"+str(n).zfill(14),"name":"Petit commerce "+str(n),
                   "lat":43.2+(n%500)/70,"lon":-4.5+(n%900)/75,
                   "category":"bakery" if n%2 else "hairdresser",
                   "city":"Ville "+str(n%200),
                   "source":"API Recherche d'entreprises / data.gouv.fr"}
                  for n in range(5005)]
            web_prospects.save(rows)
            indexed=web_prospects.browse(limit=10000)
            self.assertGreaterEqual(indexed["count"],5000)
            self.assertEqual(len(indexed["results"]),5005)
            self.assertNotIn("selection_token",indexed["results"][0])
            today=datetime.date(2026,10,28)
            suggestions=web_prospects.daily(today=today)
            self.assertEqual(len(suggestions["results"]),5)
            self.assertEqual(suggestions["pool"],5005)
            self.assertTrue(all("à vérifier" in row["reason"] for row in suggestions["results"]))
            self.assertEqual(
                [r["id"] for r in suggestions["results"]],
                [r["id"] for r in web_prospects.daily(today=today)["results"]])
            clicked=web_prospects.find(suggestions["results"][0]["id"])
            self.assertTrue(clicked["selection_token"])
            self.assertEqual(web_business_map.selected_business(
                clicked["selection_token"])["name"],clicked["name"])

    def test_real_osm_photo_is_used_only_for_commons_files(self):
        self.assertIn("commons.wikimedia.org",web_business_map._commons_photo(
            {"image":"File:Example bakery.png"}))
        self.assertEqual(web_business_map._commons_photo(
            {"image":"https://suspicious.example/stock.png"}),"")
        record=web_map_no_website._normalize({"id":1,"type":"node","lat":47.3,"lon":5.2,
            "tags":{"name":"Boulangerie réelle","shop":"bakery",
                    "image":"File:Example bakery.png"}})
        self.assertIn("commons.wikimedia.org",record["image_url"])

class ArtistCheckboxesAndBackground(unittest.TestCase):
    def test_each_design_option_can_be_checked_or_unchecked(self):
        html=(ROOT/"local_app/web/localaiweb.html").read_text(encoding="utf-8")
        frontend=(ROOT/"local_app/web/localaiweb.js").read_text(encoding="utf-8")
        for field in ("style","colors","typography","layout","motion","cinema",
                      "dimension","interaction","visuals","surfaces","mobile"):
            self.assertIn('type="checkbox" name="'+field+'"',html)
        self.assertNotIn('<select name="style"',html)
        self.assertIn("form.getAll(key)",frontend)
        self.assertIn("include_notes",frontend)
        profile=web_design_profile.validate({
            "style":["luxury","boutique"],"motion":["smooth","expressive"],
            "cinema":["scroll","camera"]})
        prompt=web_design_profile.prompt(profile)
        for phrase in ("Luxe éditorial","Commerce chaleureux","Animations très fluides",
                       "Transitions expressives","Récit au défilement"):
            self.assertIn(phrase,prompt)

    def test_generation_thread_is_independent_of_browser_and_status_is_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(Path(tmp)/"projects",lambda *_:"{}")
            project=store.create("Site indépendant")["project"]["id"]
            with server._web_generation_lock:server._web_generation_jobs.clear()
            with patch.object(server,"_web_store",return_value=store), \
                 patch.object(integrations_cli,"coding_agent_status",
                     return_value={"codex":{"installed":True,"ready":True}}), \
                 patch.object(server.threading,"Thread") as thread:
                task=server._web_start_generation(project,"Créer un salon")
                self.assertEqual(task["state"],"running")
                self.assertTrue(thread.call_args.kwargs["daemon"])
                self.assertTrue((store.project_dir(project)/"generation_status.json").is_file())
            with server._web_generation_lock:server._web_generation_jobs.clear()
            with patch.object(server,"_web_store",return_value=store):
                status=server._web_generation_status(project)
            self.assertEqual(status["state"],"error")
            self.assertIn("interrompue",status["error"])

if __name__=="__main__":unittest.main()
