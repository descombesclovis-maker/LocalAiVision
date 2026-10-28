"""Google Maps opt-in and prompt-only site editor with real optional style modal."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import tempfile

from local_app import web_design_profile, web_google_maps, web_business_map, web_builder, web_hybrid

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"


class GoogleMapsSmallCommerceTests(TestCase):
    def test_google_basemap_uses_french_registry_not_google_places_for_leads(self):
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        public=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        google=(WEB/"localaiweb-google-map.js").read_text(encoding="utf-8")
        self.assertIn('src="/assets/localaiweb-google-map.js"',html)
        self.assertIn("/api/web/map/config",public)
        self.assertIn("if(config.enabled",public)
        self.assertIn("maps.googleapis.com/maps/api/js?",google)
        self.assertIn("featureType:'poi'",google)
        self.assertIn("google.maps.Map",google)
        self.assertIn("/api/web/map/registry/city",google)
        self.assertIn("/api/web/map/no-website/france",google)
        self.assertNotIn("/api/web/map/google/place",google)
        self.assertNotIn("places:searchNearby",google)
        self.assertIn("choisis une fiche",google)
        self.assertIn("maxZoom:19",google)
        self.assertIn("Créer un site pour cette entreprise",html)

    def test_google_map_needs_billing_key_but_places_key_is_not_required(self):
        from unittest.mock import patch
        with patch.dict("os.environ",{"LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY":"test-browser",
                                      "LOCALAIWEB_GOOGLE_PLACES_API_KEY":""}):
            config=web_google_maps.configuration()
        self.assertTrue(config["enabled"])
        self.assertFalse(config["places_enabled"])
        self.assertTrue(config["requires_billing"])
        self.assertEqual(config["browser_key"],"test-browser")

    def test_independent_local_shops_include_several_pages(self):
        from local_app import web_map_no_website
        with patch.object(web_map_no_website,"_french_registry_near",
                          return_value={"results":[{"name":"Petite fleuriste"}]}) as client:
            result=web_map_no_website.registry_city(46.5,4.9,13)
        self.assertEqual(result["results"][0]["name"],"Petite fleuriste")
        self.assertEqual(client.call_args.kwargs["pages"],3)
        with self.assertRaises(ValueError):
            web_map_no_website.registry_city(46.5,4.9,6)


class FreeformDesignTests(TestCase):
    def test_modal_contains_genuine_aesthetic_options_not_a_chat_questionnaire(self):
        html=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        js=(WEB/"localaiweb.js").read_text(encoding="utf-8")
        self.assertIn('id="lawDesignDialog"',html)
        for field in ("style","colors","typography","layout","motion","cinema",
                      "dimension","interaction","visuals","surfaces","mobile","notes"):
            self.assertIn('name="'+field+'"',html)
        self.assertIn('id="lawDesignForm"',html)
        self.assertIn("/api/web/project/design-profile",js)
        self.assertIn("dialog.showModal()",js)
        self.assertNotIn("Signature 3D",html)
        self.assertNotIn("Décris-moi le site que tu imagines",html)
        self.assertNotIn("renderBriefQuestion",js)
        self.assertNotIn("async function beginSpecification",js)
        self.assertIn("if(role!=='user')",js)
        self.assertIn("await generate(text)",js)
        self.assertNotIn("choices.forEach(value",js)

    def test_profile_is_validated_stored_and_sent_to_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(Path(tmp)/"sites",lambda *_:"{}")
            p=store.create("Atelier du Centre")["project"]["id"]
            profile=web_design_profile.validate({
                "style":"luxury","colors":"copper","motion":"expressive",
                "cinema":"scroll","dimension":"interactive","notes":"Photographie chaleureuse"
            })
            self.assertEqual(profile["typography"],"auto")
            meta=store.meta(p)
            meta["design_profile"]=profile
            store.write_meta(p,meta)
            instruction=web_design_profile.prompt(store.meta(p)["design_profile"])
            self.assertIn("Luxe éditorial",instruction)
            self.assertIn("Objets 3D interactifs",instruction)
            self.assertIn("Récit au défilement",instruction)
            self.assertIn("Photographie chaleureuse",instruction)
            self.assertIn("nouvelles demandes de l'utilisateur",instruction)
        with self.assertRaises(ValueError):
            web_design_profile.validate({"dimension":"ultra-secret"})
        with self.assertRaises(ValueError):
            web_design_profile.validate({"notes":"!"*1201})

if __name__=="__main__":
    import unittest;unittest.main()
