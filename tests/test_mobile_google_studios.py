"""Regression checks for private mobile PWA, Google Places opt-in and studio separation."""
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from local_app import web_business_map, web_creative_direction, web_google_maps, web_hybrid, server

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class MobileStudiosTests(unittest.TestCase):
    def test_both_creation_studios_have_real_event_targets(self):
        home=(WEB/"index.html").read_text(encoding="utf-8")
        app=(WEB/"app.js").read_text(encoding="utf-8")
        for button in ("studioPhotoVideo","studioNsfw"):
            self.assertIn('id="'+button+'"',home)
            self.assertIn("$('#"+button+"').onclick",app)
        self.assertIn("activateStudio",app)
        self.assertIn("lva_conversations_v2",app)
        self.assertIn("lva_nsfw_gate",app)

    def test_map_shortcut_opens_france_focused_map_without_search(self):
        editor=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        page=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        js=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        self.assertIn('id="lawMapShortcut"',editor)
        self.assertIn('href="/localaiweb/map"',editor)
        self.assertIn('id="businessMap"',page)
        self.assertNotIn('id="mapProvider"',page)
        self.assertNotIn('id="mapQuery"',page)
        self.assertIn("setView([46.60,2.28],6)",js)
        self.assertIn("/api/web/map/no-website/france",js)
        self.assertIn('id="companyWebsite"',page)

    def test_private_pwa_cache_excludes_api_and_projects(self):
        sw=(WEB/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("if(!STATIC.has(url.pathname))return",sw)
        self.assertNotIn("'/api/",sw)
        self.assertNotIn("'/web-preview/",sw)
        self.assertEqual(server.HOST,"127.0.0.1")
        manifest=(WEB/"manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('"display": "standalone"',manifest)
        for name in ("index.html","localaiweb.html","localaiweb-map.html","localaiweb-projects.html"):
            self.assertIn('manifest.webmanifest',(WEB/name).read_text(encoding="utf-8"))
        self.assertTrue((ROOT/"ACTIVER_ACCES_TELEPHONE.bat").exists())

    def test_google_is_opt_in_and_secrets_never_sent_to_browser(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(web_google_maps.configuration()["enabled"])
            with self.assertRaises(ValueError):
                web_google_maps.place_details("ChIJ12345678")
        with patch.dict(os.environ,{"LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY":"public-browser",
                                   "LOCALAIWEB_GOOGLE_PLACES_API_KEY":"PRIVATE-SECRET"}):
            config=web_google_maps.configuration()
            self.assertTrue(config["enabled"])
            self.assertEqual(config["browser_key"],"public-browser")
            self.assertNotIn("PRIVATE-SECRET",repr(config))

    def test_google_place_yields_token_from_verified_provider_response(self):
        place={"id":"ChIJ12345678",
               "displayName":{"text":"Atelier Lumière"},
               "location":{"latitude":46.77,"longitude":4.85},
               "formattedAddress":"12 rue des Fleurs",
               "websiteUri":"https://example.com",
               "primaryTypeDisplayName":{"text":"artisan"}}
        with patch.object(web_google_maps,"_request",return_value={"places":[place]}):
            result=web_google_maps.search("Atelier Lumière")
        self.assertEqual(result["source"],"Google Maps / Places")
        item=result["results"][0]
        self.assertEqual(item["name"],"Atelier Lumière")
        self.assertEqual(item["google_place_id"],place["id"])
        self.assertTrue(web_business_map.selected_business(item["selection_token"]))
        self.assertIn("Google Maps",web_business_map.first_draft_prompt(item))

    def test_codex_is_default_and_claude_remains_explicit_opt_in(self):
        status={"codex":{"ready":True},"claude":{"ready":True}}
        self.assertEqual(web_hybrid.select_coding_agent("auto",status),"codex")
        self.assertEqual(web_hybrid.select_coding_agent("claude",status),"claude")
        self.assertEqual(web_hybrid.select_coding_agent("codex",status),"codex")
        with self.assertRaisesRegex(RuntimeError,"Codex"):
            web_hybrid.select_coding_agent(
                "auto",{"claude":{"ready":True},"codex":{"ready":False}},
                allow_local_fallback=True)

    def test_new_project_defaults_to_codex_chatgpt_plus(self):
        from local_app import web_builder
        with tempfile.TemporaryDirectory() as folder:
            store=web_builder.LocalAiWebStore(folder,lambda *_:'{}')
            project=store.create("Un site premium")["project"]
            self.assertEqual(project["settings"]["ai_provider"],"codex")

    def test_project_brand_affects_design_direction(self):
        a=web_creative_direction.brand_composition("marque de parfum artisanal", "Parfumerie A")
        b=web_creative_direction.instructions("marque de parfum artisanal","Parfumerie A")
        self.assertIn(a,b)
        self.assertIn("ombres",b)
        self.assertEqual(a,web_creative_direction.brand_composition("marque de parfum artisanal","Parfumerie A"))

if __name__=="__main__":
    unittest.main()
