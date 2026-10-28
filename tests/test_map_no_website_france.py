"""OSM map: France start, violet unlisted-site prospects and bounded sampling."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

from local_app import web_business_map as shared
from local_app import web_map_no_website as mapdata

BASE=Path(__file__).resolve().parents[1]


class WebsiteProspectMapTests(unittest.TestCase):
    def setUp(self):
        mapdata.CACHE.clear()
        mapdata.LAST_REQUEST=0.
        shared._selected.clear()
        shared._rate["overpass"]=0.
        # Default-France API is intentionally independent of Overpass.
        # Mock its outage for tests that specifically exercise OSM queries.
        self.real_french_registry=mapdata._french_registry_near
        self.registry_patcher=patch.object(
            mapdata,"_french_registry_near",side_effect=RuntimeError("Simulation annuaire indisponible"))
        self.registry_patcher.start()
        self.addCleanup(self.registry_patcher.stop)

    def test_no_recorded_website_and_only_credible_business_tags(self):
        hotel={"type":"node","id":1,"lat":47.2,"lon":5.1,
               "tags":{"name":"Hôtel de la Place","tourism":"hotel","website":"https://example.fr"}}
        barber={"type":"node","id":2,"lat":47.25,"lon":5.05,
                "tags":{"name":"Salon Joli","shop":"hairdresser","contact:phone":"+33 3 00 00 00 00"}}
        municipal={"type":"node","id":3,"lat":47.2,"lon":5.15,
                   "tags":{"name":"Mairie","amenity":"townhall"}}
        contact_url={"type":"node","id":4,"lat":47.2,"lon":5.2,
                     "tags":{"name":"Boutique B","shop":"florist","contact:website":"https://example.org"}}
        site=mapdata._normalize(hotel)
        self.assertTrue(site["website_recorded"])
        self.assertEqual(site["website"],"https://example.fr")
        self.assertTrue(site["website_link_available"])
        self.assertIsNone(mapdata._normalize(municipal))
        external=mapdata._normalize(contact_url)
        self.assertTrue(external["website_recorded"])
        self.assertEqual(external["website"],"https://example.org")
        result=mapdata._normalize(barber)
        self.assertEqual(result["name"],"Salon Joli")
        self.assertEqual(result["website_status"],"non_renseigne_osm")
        self.assertFalse(result["website_recorded"])
        self.assertEqual(result["website"],"")
        self.assertTrue(result["selection_token"])
        self.assertFalse(result["verified"])

    def test_france_overview_uses_one_distributed_bounded_request(self):
        response={"elements":[
            {"type":"node","id":5,"lat":48.856,"lon":2.35,
             "tags":{"name":"Café Eiffel","amenity":"cafe"}},
            {"type":"node","id":6,"lat":45.764,"lon":4.84,
             "tags":{"name":"La Librairie","shop":"books"}},
            {"type":"node","id":7,"lat":45.765,"lon":4.841,
             "tags":{"name":"Salon Web","shop":"hairdresser","website":"https://website.com"}}
        ]}
        with patch.object(shared,"_json_http",return_value=response) as call:
            result=mapdata.france_overview()
            cached=mapdata.france_overview()
        self.assertEqual(call.call_count,1)
        query=parse_qs(call.call_args.kwargs["post"])["data"][0]
        self.assertIn('nwr(around:850,48.8566,2.3522)',query)
        self.assertIn('nwr(around:850,45.764,4.8357)',query)
        for tag in mapdata.WEBSITE_KEYS:
            self.assertNotIn(f'[!"{tag}"]',query)
        self.assertEqual(query.count("out center 18;"),10)
        self.assertNotIn("41.9192,8.7386",query)  # Corsica is loaded in a later batch.
        self.assertEqual([a["name"] for a in result["results"]],
                         ["Café Eiffel","La Librairie","Salon Web"])
        self.assertEqual([a["website_recorded"] for a in result["results"]],
                         [False,False,True])
        self.assertFalse(result["website_verified"])
        self.assertTrue(result["partial"])
        self.assertEqual(result["batch"],0)
        self.assertGreater(result["total_batches"],1)
        self.assertEqual(result["next_batch"],1)
        self.assertIn("non confirmée",result["notice"])
        self.assertTrue(cached["cached"])

    def test_france_batches_are_bounded_and_cache_per_region(self):
        with patch.object(shared,"_json_http",return_value={"elements":[]}) as request:
            first=mapdata.france_overview(0)
            again=mapdata.france_overview(0)
            mapdata.LAST_REQUEST=0.0
            later=mapdata.france_overview(2)
        self.assertEqual(request.call_count,2)
        self.assertTrue(again["cached"])
        self.assertEqual(later["batch"],2)
        self.assertNotEqual(first["batch"],later["batch"])
        with self.assertRaises(ValueError):
            mapdata.france_overview(-1)
        with self.assertRaises(ValueError):
            mapdata.france_overview(99)

    def test_overpass_fallback_preserves_real_osm_records(self):
        real={"elements":[{"type":"node","id":11,"lat":48.85,"lon":2.34,
                             "tags":{"name":"Boulangerie réelle","shop":"bakery"}}]}
        with patch.object(shared,"_json_http",side_effect=[
                RuntimeError("Instance temporairement occupée"),real]) as call:
            result=mapdata.france_overview()
        self.assertEqual(call.call_count,2)
        self.assertEqual(call.call_args.args[0],"overpass_backup")
        self.assertEqual(result["results"][0]["name"],"Boulangerie réelle")

    def test_offline_cache_only_returns_previous_real_osm_responses(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mapdata,"CACHE_DIR",Path(folder)):
                response={"elements":[{"type":"node","id":301,"lat":48.8,"lon":2.3,
                    "tags":{"name":"Boulangerie cached","shop":"bakery"}}]}
                with patch.object(shared,"_json_http",return_value=response):
                    online=mapdata.france_overview()
                self.assertFalse(online["offline"])
                mapdata.CACHE.clear()
                mapdata.LAST_REQUEST=0.0
                with patch.object(shared,"_json_http",side_effect=RuntimeError("OSM indisponible")):
                    cached=mapdata.france_overview()
                self.assertTrue(cached["offline"])
                self.assertEqual([x["name"] for x in cached["results"]],["Boulangerie cached"])

    def test_official_french_api_produces_real_businesses_if_overpass_unavailable(self):
        from io import BytesIO
        from json import dumps
        company={"nom_complet":"SALON D'EXEMPLE","siren":"123456789",
                 "matching_etablissements":[{
                    "siret":"12345678900012","latitude":"48.8568","longitude":"2.3524",
                    "nom_commercial":"Salon Exemple","adresse":"10 rue des tests 75001 PARIS",
                    "activite_principale":"96.02A","etat_administratif":"A"}]}
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(mapdata,"CACHE_DIR",Path(folder)):
                with patch.object(mapdata,"_french_registry_near",self.real_french_registry):
                    with patch("urllib.request.urlopen",return_value=BytesIO(
                         dumps({"results":[company]}).encode("utf-8"))):
                        result=mapdata.france_overview()
        self.assertEqual(result["source"],"API Recherche d'entreprises / data.gouv.fr")
        self.assertEqual(result["results"][0]["name"],"Salon Exemple")
        self.assertEqual(result["results"][0]["website_status"],"inconnu_registre")
        self.assertFalse(result["results"][0]["website_recorded"])
        self.assertEqual(result["results"][0]["source"],"API Recherche d'entreprises / data.gouv.fr")
        self.assertTrue(result["results"][0]["selection_token"])

    def test_safe_website_links_reject_executable_or_internal_targets(self):
        self.assertEqual(mapdata.safe_website("www.coiffeur.fr"),"https://www.coiffeur.fr")
        self.assertEqual(mapdata.safe_website("https://www.coiffeur.fr/services"),
                         "https://www.coiffeur.fr/services")
        for malformed in ("javascript:alert(1)","data:text/html,hello",
                          "http://127.0.0.1/private","http://localhost",
                          "https://example.com\\n<script>","file:///etc/passwd"):
            self.assertEqual(mapdata.safe_website(malformed),"")
        suspicious=mapdata._normalize({"type":"node","id":101,"lat":47.25,"lon":5.05,
                        "tags":{"name":"Entreprise X","shop":"books",
                                "website":"javascript:alert(1)"}})
        self.assertTrue(suspicious["website_recorded"])
        self.assertFalse(suspicious["website_link_available"])
        self.assertEqual(suspicious["website"],"")

    def test_zoomed_area_rejects_world_scale_and_limits_radius(self):
        with self.assertRaises(ValueError):
            mapdata.area_details(46.5,2.3,6)
        with self.assertRaises(ValueError):
            mapdata.area_details(46.5,2.3,20)
        with patch.object(shared,"_json_http",return_value={"elements":[]}) as request:
            result=mapdata.area_details(47.3,5.01,13)
        query=parse_qs(request.call_args.kwargs["post"])["data"][0]
        self.assertIn("around:1100,47.3,5.01",query)
        self.assertIn("out center 220;",query)
        self.assertNotIn('[!"website"]',query)
        self.assertEqual(result["results"],[])
        self.assertEqual(result["mode"],"nearby")

    def test_visible_viewport_is_bounded_and_excludes_all_site_keys(self):
        company={"type":"node","id":3,"lat":47.35,"lon":5.02,
                 "tags":{"shop":"hairdresser","name":"Atelier sans site"}}
        company_with_url={"type":"node","id":4,"lat":47.34,"lon":5.03,
                 "tags":{"shop":"hairdresser","name":"Avec site","contact:url":"https://example.org"}}
        with patch.object(shared,"_json_http",return_value={
            "elements":[company,company_with_url]}) as call:
            result=mapdata.viewport_details(47.30,4.98,47.37,5.06,14)
        query=parse_qs(call.call_args.kwargs["post"])["data"][0]
        self.assertIn("nwr(47.3,4.98,47.37,5.06)",query)
        self.assertIn("out center 350;",query)
        self.assertNotIn('[!"contact:url"]',query)
        self.assertEqual([item["name"] for item in result["results"]],
                         ["Atelier sans site","Avec site"])
        self.assertEqual(result["mode"],"viewport")
        with self.assertRaisesRegex(ValueError,"Zone trop vaste"):
            mapdata.viewport_details(44.0,2.0,45.0,3.0,14)
        with self.assertRaisesRegex(ValueError,"Zoome"):
            mapdata.viewport_details(47.3,4.98,47.37,5.06,10)
        with self.assertRaisesRegex(ValueError,"invalides"):
            mapdata.viewport_details(47.4,4.98,47.3,5.06,14)

    def test_public_rate_limit_prevents_overpass_request_flood(self):
        with patch.object(shared,"_json_http",return_value={"elements":[]}) as request:
            mapdata.france_overview()
            with self.assertRaisesRegex(RuntimeError,"recharge progressivement"):
                mapdata.area_details(47.3,5.01,14)
        self.assertEqual(request.call_count,1)

    def test_no_location_search_or_filter_present(self):
        html=(BASE/"local_app/web/localaiweb-map.html").read_text(encoding="utf-8")
        script=(BASE/"local_app/web/localaiweb-map.js").read_text(encoding="utf-8")
        for item in ('id="mapSearchForm"','id="mapQuery"','id="industryFilter"',
                     'id="industrySearch"','id="mapNearby"','id="mapProvider"'):
            self.assertNotIn(item,html)
        self.assertIn("setView([46.60,2.28],6)",script)
        self.assertIn("radius:3.0",script)
        self.assertIn("'#36d77f'",script)
        self.assertIn("'#ef535e'",script)
        self.assertIn("website_recorded",script)
        self.assertIn("stroke:false",script)
        self.assertIn("map.on('moveend',scheduleNearby)",script)
        self.assertIn("overview();",script)
        self.assertIn("fitBounds(franceBounds",script)
        self.assertIn("map.invalidateSize",script)
        self.assertIn("overview(next)",script)
        self.assertIn("mapFeedbackText",script)
        self.assertIn('id="mapReload"',html)
        self.assertIn("statut inconnu",html)
        self.assertIn("Vert",html)
        self.assertIn("Rouge",html)
        self.assertIn("vérification externe est nécessaire",html)
        self.assertIn("Absence NON confirmée",script)
        self.assertIn('id="companyWebsite"',html)
        self.assertIn('id="verifyWebPresence"',html)
        self.assertIn("/api/web/map/no-website/viewport",script)
        self.assertIn("function pruneOffscreen()",script)
        self.assertIn("target=\"_blank\"",html)
        self.assertIn("rel=\"noopener noreferrer nofollow\"",html)
        self.assertIn('id="mapSelection"',html)
        self.assertIn('/api/web/project/create-from-map',script)

    def test_map_api_routes_and_windows_bundle(self):
        server=(BASE/"local_app/server.py").read_text(encoding="utf-8")
        windows=(BASE/".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        self.assertIn("/api/web/map/no-website/france",server)
        self.assertIn("/api/web/map/no-website/nearby",server)
        self.assertIn("/api/web/map/no-website/viewport",server)
        self.assertIn("--hidden-import local_app.web_map_no_website",windows)
        self.assertIn("Smoke test native EXE and extracted Python DLL",windows)


if __name__=="__main__":
    unittest.main()
