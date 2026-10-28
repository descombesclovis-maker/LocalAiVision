"""No-website OSM map: bounded sample, negative tag checks, France start, UI simplicity."""
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
        self.assertIsNone(mapdata._normalize(hotel))
        self.assertIsNone(mapdata._normalize(municipal))
        self.assertIsNone(mapdata._normalize(contact_url))
        result=mapdata._normalize(barber)
        self.assertEqual(result["name"],"Salon Joli")
        self.assertEqual(result["website_status"],"non_renseigne_osm")
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
        self.assertIn('[!"website"]',query)
        self.assertIn('[!"contact:website"]',query)
        self.assertIn('[!"url"]',query)
        self.assertGreaterEqual(query.count("out center 12;"),20)
        self.assertEqual([a["name"] for a in result["results"]],["Café Eiffel","La Librairie"])
        self.assertTrue(result["partial"])
        self.assertIn("≠",result["notice"])
        self.assertTrue(cached["cached"])

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
        self.assertEqual(result["results"],[])
        self.assertEqual(result["mode"],"nearby")

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
        self.assertIn("radius:3.2",script)
        self.assertIn("fillColor:'#995afa'",script)
        self.assertIn("stroke:false",script)
        self.assertIn("map.on('moveend',scheduleNearby)",script)
        self.assertIn("overview();",script)
        self.assertIn("sans site renseigné",html)
        self.assertIn("ne prouve pas",html)
        self.assertIn('id="mapSelection"',html)
        self.assertIn('/api/web/project/create-from-map',script)

    def test_map_api_routes_and_windows_bundle(self):
        server=(BASE/"local_app/server.py").read_text(encoding="utf-8")
        windows=(BASE/".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        self.assertIn("/api/web/map/no-website/france",server)
        self.assertIn("/api/web/map/no-website/nearby",server)
        self.assertIn("--hidden-import local_app.web_map_no_website",windows)
        self.assertIn("Smoke test native EXE and extracted Python DLL",windows)


if __name__=="__main__":
    unittest.main()
