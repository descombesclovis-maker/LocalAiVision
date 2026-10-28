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
        self.assertIn('nwr(around:800,48.8566,2.3522)',query)
        self.assertIn('nwr(around:800,45.764,4.8357)',query)
        for tag in mapdata.WEBSITE_KEYS:
            self.assertIn(f'[!"{tag}"]',query)
        self.assertGreaterEqual(query.count("out center 6;"),80)
        self.assertEqual([a["name"] for a in result["results"]],
                         ["Café Eiffel","La Librairie"])
        self.assertTrue(all(not item["website_recorded"] for item in result["results"]))
        self.assertFalse(result["website_verified"])
        self.assertTrue(result["partial"])
        self.assertIn("≠",result["notice"])
        self.assertTrue(cached["cached"])

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
        self.assertIn('[!"website"]',query)
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
        self.assertIn('[!"contact:url"]',query)
        self.assertEqual([item["name"] for item in result["results"]],
                         ["Atelier sans site"])
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
        self.assertIn("radius:2.3",script)
        self.assertIn("'#a868f6'",script)
        self.assertNotIn("'#e14959'",script)
        self.assertNotIn("'#27bd72'",script)
        self.assertIn("website_recorded",script)
        self.assertIn("stroke:false",script)
        self.assertIn("map.on('moveend',scheduleNearby)",script)
        self.assertIn("overview();",script)
        self.assertIn("aucun site renseigné",html)
        self.assertIn("Violet",html)
        self.assertNotIn("Rouge : site internet",html)
        self.assertIn("doit être vérifié",html)
        self.assertIn("ne prouve pas",script)
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
