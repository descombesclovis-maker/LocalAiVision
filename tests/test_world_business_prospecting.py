"""Worldwide professional discovery, trade filters, opt-in official registry and updater."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

from local_app import web_business_categories as categories
from local_app import web_business_map as mapdata
from local_app import web_business_registry as registry
from local_app import web_builder

BASE=Path(__file__).resolve().parents[1]


class IndustryMapTests(unittest.TestCase):
    def setUp(self):
        mapdata._rate.update(overpass=0,photon=0)
        mapdata._cache.clear()
        mapdata._selected.clear()
        registry._CACHE.clear()
        registry._LAST=0.0

    def test_trade_catalog_has_grouped_full_list(self):
        result=categories.catalog()
        self.assertGreaterEqual(result['count'],75)
        self.assertGreaterEqual(len(result['groups']),6)
        self.assertEqual(categories.category('pet_grooming')['tag'],'shop')
        self.assertEqual(categories.category('dentist')['value'],'dentist')
        with self.assertRaises(ValueError):
            categories.category('shop\";out body;')

    def test_category_query_only_loads_user_selected_nearby_area(self):
        fake={"elements":[{"type":"node","id":55,"lat":48.9,"lon":2.3,"tags":{
            "name":"Aquarelle Salon","shop":"hairdresser","website":"https://example.org",
            "contact:email":"hello@example.org","operator":"ACME SARL"}}]}
        with patch.object(mapdata,"_json_http",return_value=fake) as network:
            filtered=mapdata.nearby_businesses(48.9,2.3,750,industry="hairdresser")
        body=network.call_args.kwargs["post"]
        query=parse_qs(body)["data"][0]
        self.assertIn('["shop"="hairdresser"]',query)
        self.assertIn("around:750,48.9,2.3",query)
        self.assertNotIn('["amenity"]["name"]',query)
        self.assertEqual(filtered["results"][0]["email"],"hello@example.org")
        self.assertEqual(filtered["results"][0]["operator"],"ACME SARL")
        with self.assertRaisesRegex(ValueError,"Métier inconnu"):
            mapdata.nearby_businesses(48.9,2.3,750,industry='"]["name"];out;')

    def test_business_profile_lookup_is_opt_in_and_token_preserves_profile(self):
        item=mapdata._result({"name":"Aquarelle","category":"hairdresser",
            "lat":48.9,"lon":2.3,"source":"overpass"})
        token=item["selection_token"]
        profile={"matched":True,"legal_name":"AQUARELLE SARL","siren":"123456789",
                 "naf":"96.02A","created":"2011-05-02",
                 "officers":[{"name":"Marie Demo","role":"Gérante"}],
                 "source":"https://annuaire-entreprises.data.gouv.fr/123456789"}
        saved=mapdata.attach_professional_profile(token,profile)
        self.assertEqual(saved["official_registry"]["siren"],"123456789")
        brief=mapdata.first_draft_prompt(mapdata.selected_business(token))
        self.assertIn("AQUARELLE SARL",brief)
        self.assertIn("Marie Demo",brief)
        self.assertIn("ne sont pas nécessairement les propriétaires",brief)

    def test_registry_fails_closed_outside_france(self):
        company={"name":"Hotel Sample","lat":51.5,"lon":-0.1,"country":"United Kingdom"}
        with patch.object(registry,"_query") as network:
            result=registry.professional_profile(company)
        self.assertFalse(result["matched"])
        network.assert_not_called()

    def test_registry_requires_same_name_and_establishment_not_similar(self):
        info={"name":"Maison des Fleurs","lat":46.8,"lon":4.8,"country":"France",
              "postcode":"71100","city":"Chalon-sur-Saône"}
        good={"nom_complet":"Maison des Fleurs","siren":"123456789",
              "siege":{"latitude":46.802,"longitude":4.799,"code_postal":"71100"},
              "activite_principale":"47.76Z","dirigeants":[{"prenoms":"A.","nom":"Martin",
              "qualite":"Président"}]}
        similar={**good,"nom_complet":"Maison des Fleurs Paris","siren":"987654321"}
        far={**good,"siege":{"latitude":43,"longitude":1,"code_postal":"31000"}}
        self.assertTrue(registry._match(good,info))
        self.assertFalse(registry._match(similar,info))
        self.assertFalse(registry._match(far,info))
        with patch.object(registry,"_query",return_value={"results":[similar,good]}):
            p=registry.professional_profile(info)
        self.assertTrue(p["matched"])
        self.assertEqual(p["siren"],"123456789")

    def test_registry_disclosure_will_not_include_private_details(self):
        info={"name":"Maison des Fleurs","lat":46.8,"lon":4.8,"country":"France","postcode":"71100"}
        record={"nom_complet":"Maison des Fleurs","siren":"123456789",
              "siege":{"latitude":46.8,"longitude":4.8},
              "dirigeants":[{"prenoms":"Anne","nom":"Dupont",
                           "date_de_naissance":"1983-12","adresse":"adresse privée",
                           "qualite":"Gérante","email":"private@example.com"}]}
        with patch.object(registry,"_query",return_value={"results":[record]}):
            p=registry.professional_profile(info)
        self.assertTrue(p["matched"])
        self.assertNotIn("adresse",str(p).lower())
        self.assertNotIn("date_de_naissance",str(p))
        self.assertNotIn("private@example.com",str(p))

    def test_globe_next_to_preview_controls_and_world_page(self):
        ui=(BASE/"local_app/web/localaiweb.html").read_text(encoding="utf-8")
        page=(BASE/"local_app/web/localaiweb-map.html").read_text(encoding="utf-8")
        script=(BASE/"local_app/web/localaiweb-map.js").read_text(encoding="utf-8")
        updater=(BASE/"local_app/web/localaiweb-update.js").read_text(encoding="utf-8")
        for name in ("lawInspectBtn","lawBrowserBtn","lawZipBtn","lawPublishBtn"):
            self.assertIn('id="'+name+'"',ui)
        self.assertIn('id="lawMapShortcut"',ui)
        self.assertNotIn('id="lawWorldMapBtn"',ui)
        for field in ("mapSelection","selectionTitle","selectionAddress",
                      "selectionPhone","selectionEmail","selectionHours",
                      "selectionWebsite","mapCreate"):
            self.assertIn('id="'+field+'"',page)
        self.assertIn("setView([46.60,2.28],6)",script)
        self.assertNotIn('id="industryFilter"',page)
        self.assertNotIn('id="mapQuery"',page)
        self.assertIn("/api/web/map/no-website/france",script)
        self.assertNotIn("/api/web/map/profile",script)
        self.assertIn("function scheduleNearby()",script)
        self.assertIn("/api/update/check",updater)
        self.assertIn("/api/update/install",updater)

    def test_existing_pro_project_and_unrelated_libre_projects_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            store=web_builder.LocalAiWebStore(folder,lambda *_:'{}')
            libre=store.create("Site Libre")["project"]["id"]
            business={"name":"Ma boutique","category":"florist",
                      "lat":48,"lon":2,"source":"OpenStreetMap / Overpass"}
            pro=store.create_business_project(business)["project"]["id"]
            self.assertEqual(store.meta(pro)["project_kind"],"pro")
            self.assertEqual(store.meta(libre)["project_kind"],"libre")
            self.assertNotIn("official_registry",store.meta(pro)["business"])


if __name__=="__main__":
    unittest.main()
