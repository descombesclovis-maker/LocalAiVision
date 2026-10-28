"""LocalAiWeb Pro map: user-selected OSM companies and auto-generated site drafts."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from local_app import web_business_map as business, web_builder, web_content_contract

ROOT=Path(__file__).resolve().parents[1]


class BusinessMapTests(unittest.TestCase):
    def setUp(self):
        business._cache.clear()
        business._selected.clear()
        business._rate.update(photon=0,overpass=0)

    def test_photon_search_returns_company_and_location_without_auto_request(self):
        response={"features":[
          {"geometry":{"coordinates":[4.840,46.775]},
           "properties":{"name":"Atelier Miel","osm_key":"shop","osm_value":"bakery",
                         "osm_type":"N","osm_id":234,"city":"Mercurey","country":"France"}},
          {"geometry":{"coordinates":[4.83,46.77]},
           "properties":{"name":"Mercurey","osm_key":"place","osm_value":"village",
                         "osm_type":"R","osm_id":42}},
          {"geometry":{"coordinates":[4.81,46.76]},
           "properties":{"name":"Rue de l'Église","osm_key":"highway","osm_value":"residential"}}
        ]}
        with patch.object(business,'_json_http',return_value=response) as call:
            result=business.location_or_business_search("Mercurey")
            again=business.location_or_business_search("Mercurey")
        self.assertEqual(call.call_count,1)
        self.assertEqual(len(result["results"]),2)
        company, village=result["results"]
        self.assertEqual(company["name"],"Atelier Miel")
        self.assertEqual(company["kind"],"business")
        self.assertTrue(company["selection_token"])
        self.assertEqual(village["kind"],"location")
        self.assertNotIn("selection_token",village)
        self.assertFalse(company["verified"])
        self.assertTrue(again["cached"])

    def test_overpass_small_area_with_rate_and_tokens(self):
        data={"elements":[{"type":"node","id":121,"lat":46.80,"lon":4.85,
           "tags":{"name":"PawMood","shop":"pet_grooming","addr:city":"Mercurey",
                   "opening_hours":"Mo-Fr 09:00-18:00","contact:website":"https://example.org"}}]}
        with patch.object(business,'_json_http',return_value=data) as call:
            found=business.nearby_businesses(46.8,4.85,900)
            business.nearby_businesses(46.8,4.85,900)
        self.assertEqual(call.call_count,1)
        arg=call.call_args.kwargs['post']
        self.assertIn("around%3A900",arg)
        self.assertEqual(found["results"][0]["name"],"PawMood")
        self.assertEqual(found["results"][0]["category"],"salon de toilettage pour animaux")
        self.assertIn("selection_token",found["results"][0])

    def test_picked_company_yields_separate_pro_project_and_one_auto_draft(self):
        item=business._result({
          "name":"PawMood","lat":46.78,"lon":4.84,"category":"pet_grooming",
          "address":"Mercurey","source":"photon"})
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            old=store.create("Mon portfolio libre")
            chosen=business.selected_business(item["selection_token"])
            pro=store.create_business_project(chosen)
            self.assertEqual(old["project"]["project_kind"],"libre")
            self.assertEqual(pro["project"]["name"],"PawMood")
            self.assertEqual(pro["project"]["project_kind"],"pro")
            self.assertFalse(pro["project"].get("business_authorized",False))
            self.assertEqual(pro["project"]["initial_generation"]["status"],"pending")
            pid=pro["project"]["id"]
            first=store.claim_initial_generation(pid)
            self.assertTrue(first["ready"])
            self.assertIn("PawMood",first["prompt"])
            self.assertIn("maquette",first["prompt"].lower())
            self.assertFalse(store.claim_initial_generation(pid)["ready"])
            store.settle_initial_generation(pid,False,"Agent non connecté")
            self.assertEqual(store.meta(pid)["initial_generation"]["status"],"failed")
            self.assertFalse(store.claim_initial_generation(pid)["ready"])
            self.assertTrue(store.claim_initial_generation(pid,retry=True)["ready"])
            store.settle_initial_generation(pid,True)
            self.assertEqual(store.meta(pid)["initial_generation"]["status"],"completed")
            self.assertFalse(store.claim_initial_generation(pid)["ready"])
            self.assertEqual(store.meta(old["project"]["id"])["name"],"Mon portfolio libre")
            self.assertFalse(store.meta(old["project"]["id"]).get("business"))

    def test_brand_safety_and_no_unverified_appointments_for_default_pro(self):
        item={"name":"Maison Douce","category":"coffee","address":"rue de Paris",
              "opening_hours":"","website":""}
        prompt=business.first_draft_prompt(item)
        spec=web_content_contract.specification(prompt,item["name"])
        self.assertEqual(spec["brand"],"Maison Douce")
        # The planning brief should not force fake appointments from warnings.
        self.assertFalse(spec["booking"])
        self.assertFalse(spec["gallery"])
        self.assertIn("OpenStreetMap",prompt)
        self.assertIn("non officielle",prompt.lower())
        self.assertIn("informations à confirmer",prompt.lower())
        self.assertIn("français",prompt)

    def test_authorization_is_explicit_and_only_for_pro(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            libre=store.create("Libre")["project"]["id"]
            pro=store.create_business_project({"name":"Ma société","category":"studio"})["project"]["id"]
            with self.assertRaises(ValueError):
                store.authorize_pro_publication(pro,False)
            with self.assertRaises(ValueError):
                store.authorize_pro_publication(libre,True)
            self.assertTrue(store.authorize_pro_publication(pro,True)["project"]["business_authorized"])
            self.assertFalse(store.meta(libre).get("business_authorized",False))

    def test_unknown_or_expired_search_token_cannot_create_project(self):
        with self.assertRaises(ValueError):
            business.selected_business("forged-token")
        item=business._result({"name":"Exemple","lat":46.8,"lon":4.8,"category":"shop"})
        token=item["selection_token"]
        instant,company=business._selected[token]
        business._selected[token]=(instant-business.TOKEN_TTL-1,company)
        with self.assertRaises(ValueError):
            business.selected_business(token)

    def test_map_ui_has_separate_pro_and_libre_and_user_initiated_fetch(self):
        dashboard=(ROOT/"local_app/web/localaiweb-projects.html").read_text(encoding="utf-8")
        dashboard_js=(ROOT/"local_app/web/localaiweb-projects.js").read_text(encoding="utf-8")
        map_html=(ROOT/"local_app/web/localaiweb-map.html").read_text(encoding="utf-8")
        map_js=(ROOT/"local_app/web/localaiweb-map.js").read_text(encoding="utf-8")
        editor=(ROOT/"local_app/web/localaiweb.js").read_text(encoding="utf-8")
        server=(ROOT/"local_app/server.py").read_text(encoding="utf-8")
        self.assertIn("id=\"createFromMap\"",dashboard)
        self.assertLess(dashboard.index('id="projectsGrid"'),dashboard.index('id="proProjectsGrid"'))
        self.assertIn("p.project_kind==='pro'",dashboard_js)
        self.assertIn("Générer une première maquette",map_html)
        self.assertIn("openstreetmap.org/copyright",map_html)
        self.assertNotIn('id="mapSearchForm"', map_html)
        self.assertNotIn('id="industryFilter"', map_html)
        self.assertNotIn('id="mapProvider"', map_html)
        self.assertIn("setView([46.60,2.28],6)",map_js)
        self.assertIn("/api/web/map/no-website/france",map_js)
        self.assertIn("/api/web/map/no-website/nearby",map_js)
        self.assertIn("/api/web/map/no-website/viewport",map_js)
        self.assertIn("map.on('moveend',scheduleNearby)",map_js)
        self.assertIn("radius:2.3",map_js)
        self.assertIn("stroke:false",map_js)
        self.assertIn("/api/web/project/create-from-map",map_js)
        self.assertIn("async function startProDraft",editor)
        self.assertIn("auto-claim",editor)
        self.assertIn('/localaiweb/map',server)
        self.assertIn('/api/web/map/search',server)
        self.assertIn('/api/web/map/nearby',server)
        self.assertIn('/api/web/project/pro/authorize',server)
        self.assertIn("Publication Pro interdite",server)

if __name__=="__main__":
    unittest.main()
