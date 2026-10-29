"""Directory card, cross-France progressive results and safe commercial strategy."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_app import web_business_map, web_map_no_website, web_business_intelligence, web_builder

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class FranceBusinessCardTests(unittest.TestCase):
    def test_single_color_and_clickable_groups_without_zoom(self):
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        js=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        css=(WEB/"localaiweb-map.css").read_text(encoding="utf-8")
        for name in ("selectionTitle","selectionAddress","selectionPhone","selectionEmail",
                     "selectionHours","selectionWebsite","selectionSiret","mapCreate"):
            self.assertIn('id="'+name+'"',html)
        self.assertIn("Créer un site pour cette entreprise",html)
        self.assertIn("groupedPopup(entries)",js)
        self.assertIn("sans zoomer davantage",js)
        self.assertIn("L.divIcon(",js)
        self.assertIn("hit=mobile.matches?44:32",js)
        self.assertIn("iconSize:[hit,hit]",js)
        self.assertIn("company-marker-single",css)
        self.assertIn("/api/web/map/registry/city",js)
        self.assertIn("Promise.allSettled(operations)",js)
        self.assertIn("company-marker-group",css)
        self.assertNotIn("legend-red",html)
        self.assertNotIn("legend-green",html)
        self.assertNotIn("#ef535e",js)
        self.assertIn("Non renseigné",js)
        self.assertIn("Oui, renseigné",js)
        self.assertIn("absence non vérifiée",js)
        self.assertNotIn('id="mapRegistry"',html)
        self.assertNotIn('id="verifyWebPresence"',html)
        self.assertNotIn('id="companyWebsite"',html)

    def test_france_batch_collects_multiple_real_region_centers(self):
        seen=[]
        def region(lat,lon,radius=2.5,pages=1):
            seen.append((lat,lon))
            company=web_business_map._result({
              "name":"Entreprise "+str(len(seen)), "osm_id":"siret/"+str(len(seen)).zfill(14),
              "siret":str(len(seen)).zfill(14), "lat":lat,"lon":lon,
              "category":"hairdresser","source":"french_registry"})
            company["website_status"]="inconnu_registre"
            company["website_recorded"]=False
            return {"results":[company],"source":"API Recherche d'entreprises / data.gouv.fr"}
        with patch.object(web_map_no_website,"_french_registry_near",side_effect=region), \
             patch.object(web_map_no_website,"_load",side_effect=AssertionError("Do not fallback")):
            response=web_map_no_website.france_overview(0)
        self.assertEqual(len(seen),web_map_no_website.FRANCE_BATCH_SIZE)
        self.assertEqual(len(response["results"]),web_map_no_website.FRANCE_BATCH_SIZE)
        self.assertGreater(response["total_batches"],1)
        self.assertTrue(response["partial"])
        self.assertIn("ne contient pas tous",response["notice"])

    def test_sector_brief_is_saved_to_pro_project_without_personal_profiling(self):
        business=web_business_map._result({
          "name":"Salon du Centre","lat":46.573,"lon":4.981,
          "osm_id":"node/102","category":"hairdresser","city":"Tournus",
          "address":"Rue du Centre, Tournus",
          "phone":"03 00 00 00 00","source":"overpass"})
        with tempfile.TemporaryDirectory() as root:
            store=web_builder.LocalAiWebStore(Path(root)/"projects",lambda *_:"{}")
            project=store.create_business_project(business)
            meta=store.meta(project["project"]["id"])
        self.assertEqual(meta["market_brief"]["sector"],"coiffure")
        self.assertIn("Réservation",meta["market_brief"]["suggested_pages"])
        self.assertIn("site officiel",meta["initial_generation"]["prompt"])
        self.assertIn("Ne pas collecter de données sensibles",meta["initial_generation"]["prompt"])
        self.assertNotIn("faux avis",str(meta["market_brief"]))
        self.assertEqual(meta["project_kind"],"pro")

    def test_missing_website_does_not_mean_confirmed_absence(self):
        item=web_business_map._result({
          "name":"Atelier public","lat":46.57,"lon":4.97,
          "osm_id":"siret/12345678900000",
          "category":"coiffure","source":"french_registry"})
        self.assertFalse(item["website"])
        self.assertNotIn("Sans site confirmé",str(web_business_intelligence.plan(item)))
        self.assertIn("NON confirmée",web_business_intelligence.plan(item)["uncertainties"][0])

if __name__=="__main__":
    unittest.main()
