"""Google Maps opt-in and prompt-only site editor with real optional style modal."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import tempfile

from local_app import web_design_profile, web_google_maps, web_business_map, web_builder, web_hybrid

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"


class GoogleMapsSmallCommerceTests(TestCase):
    def setUp(self):
        web_google_maps._NEARBY_CACHE.clear()
        web_google_maps._NEARBY_RATE.clear()
        web_business_map._selected.clear()

    def test_google_nearby_targets_small_businesses_not_only_popular_chains(self):
        sample={"places":[{"id":"ChIJ12345678","location":{"latitude":46.56,
                 "longitude":4.98},"displayName":{"text":"Petite boulangerie"},
                 "formattedAddress":"Rue Centrale, France",
                 "primaryTypeDisplayName":{"text":"Boulangerie"}}]}
        with patch.object(web_google_maps,"_request",return_value=sample) as service:
            result=web_google_maps.nearby_small_businesses(46.56,4.98,13,1)
            cached=web_google_maps.nearby_small_businesses(46.56,4.98,13,1)
        self.assertEqual(service.call_count,1)
        payload=service.call_args.kwargs["data"]
        self.assertEqual(payload["maxResultCount"],20)
        self.assertEqual(payload["rankPreference"],"DISTANCE")
        self.assertIn("bakery",payload["includedPrimaryTypes"])
        self.assertIn("florist",payload["includedPrimaryTypes"])
        self.assertNotIn("supermarket",payload["includedPrimaryTypes"])
        self.assertEqual(result["results"][0]["name"],"Petite boulangerie")
        self.assertEqual(result["results"][0]["source"],"Google Maps / Places")
        self.assertTrue(result["results"][0]["selection_token"])
        self.assertTrue(cached["cached"])
        self.assertEqual(result["max_per_segment"],20)

    def test_api_requests_limited_to_city_and_three_shop_segments(self):
        for args in [(46.5,2.5,6,0),(46.5,2.5,12,7),(52.0,4.0,13,1)]:
            with self.assertRaises(ValueError):
                web_google_maps.nearby_small_businesses(*args)
        # Neither code nor UX may scrape Google Maps to obtain all firms.
        code=(ROOT/"local_app/web_google_maps.py").read_text(encoding="utf-8")
        self.assertIn("places:searchNearby",code)
        self.assertIn('maxResultCount":20',code)
        self.assertNotIn("requests.get('https://www.google.com/maps",code)

    def test_map_switch_uses_actual_official_provider_when_configured(self):
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        public=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        google=(WEB/"localaiweb-google-map.js").read_text(encoding="utf-8")
        self.assertIn('src="/assets/localaiweb-google-map.js"',html)
        self.assertIn("/api/web/map/config",public)
        self.assertIn("if(config.enabled",public)
        self.assertIn("maps.googleapis.com/maps/api/js?",google)
        self.assertIn("featureType:'poi'",google)
        self.assertIn("/api/web/map/google/local-shops",google)
        self.assertIn("/api/web/map/google/place?place_id=",google)
        self.assertIn("choisis une fiche",google)
        self.assertIn("google.maps.Map",google)
        self.assertIn("maxZoom:19",google)
        self.assertIn("Créer un site pour cette entreprise",html)


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
        self.assertIn("designDialog.showModal()",js)
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
