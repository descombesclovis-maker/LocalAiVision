"""Small independent, no recorded website and genuine photo card contract."""
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from unittest.mock import patch

from local_app import web_prospect_filter as eligibility
from local_app import web_business_photos as photos
from local_app import web_map_no_website as osm
from local_app import web_prospects as index


class LocalSmallBusinessTests(unittest.TestCase):
    def setUp(self):
        photos._CACHE.clear()

    def test_named_chains_and_franchise_brand_are_excluded(self):
        chains=("Auchan Clermont-Ferrand","Picard Lyon","Maxi Zoo Dijon","GiFi Grenoble",
                "Carrefour Market Nantes","Lidl Brest","McDonald's Paris")
        for name in chains:
            with self.subTest(name=name):
                self.assertFalse(eligibility.eligible({"name":name}))
                self.assertIsNone(osm._normalize({"id":12,"type":"node","lat":45,"lon":5,
                    "tags":{"name":name,"shop":"convenience"}}))
        self.assertFalse(eligibility.eligible({
            "name":"Une boutique du coin","brand":"Auchan"}))
        self.assertFalse(eligibility.eligible({
            "name":"Un commerce local","operator":"Carrefour"}))

    def test_local_trades_without_listed_site_are_kept(self):
        row={"name":"Les fleurs de Jeanne","osm_category":"florist"}
        self.assertTrue(eligibility.eligible(row))
        self.assertTrue(eligibility.eligible({"name":"Boulangerie des Lilas",
                                             "naf_code":"47.11B"}))
        self.assertFalse(eligibility.eligible({**row,"website":"https://shop.fr"}))
        self.assertFalse(eligibility.eligible({**row,"website_recorded":True}))
        self.assertFalse(eligibility.eligible({**row,"company_size":"ETI"}))
        self.assertFalse(eligibility.eligible({**row,"workforce_band":"21"}))
        self.assertFalse(eligibility.eligible({**row,"establishment_count":42}))
        self.assertFalse(eligibility.eligible({**row,"osm_category":"industrial"}))

    def test_old_database_cannot_reintroduce_large_chains(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"prospects.sqlite3"
            with patch.object(index,"database_path",return_value=path):
                base={"id":"node/1","name":"L'atelier des fleurs",
                      "lat":45.764,"lon":4.835,"city":"Lyon"}
                index.save([base, {**base,"id":"node/2","name":"Auchan Lyon"},
                            {**base,"id":"node/3","name":"Salon avec site","website":"https://s.fr"}])
                # Simulate a database populated by an earlier application version.
                import sqlite3, json, time
                with closing(sqlite3.connect(path)) as db:
                    old={**base,"id":"node/4","name":"Picard Lyon"}
                    db.execute("insert into companies values(?,?,?,?,?,?)",
                         (old["id"],old["lat"],old["lon"],old["name"],
                          json.dumps(old),time.time()))
                    db.commit()
                result=index.browse()
                self.assertEqual([x["id"] for x in result["results"]],["node/1"])
                self.assertEqual(result["count"],1)
                self.assertEqual([x["id"] for x in index.daily(limit=5)["results"]],
                                 ["node/1"])
                with self.assertRaisesRegex(ValueError,"critères"):
                    index.find("node/4")

    def test_osm_commons_photo_follows_establishment_wikidata(self):
        company={"id":"node/381","name":"Le vrai salon du centre",
                 "city":"Dijon","wikidata":"Q12345"}
        def fake_json(host,params):
            if "wikidata.org" in host:
                return {"entities":{"Q12345":{"claims":{"P18":[{
                  "mainsnak":{"datavalue":{"value":"Salon du centre Dijon.jpg"}}
                }]}}}}
            return {"query":{"pages":{"1":{"imageinfo":[{
                "thumburl":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/salon.jpg",
                "descriptionurl":"https://commons.wikimedia.org/wiki/File:Salon_du_centre_Dijon.jpg",
                "extmetadata":{"License":{"value":"cc-by-sa-4.0"},
                               "LicenseShortName":{"value":"CC BY-SA 4.0"}}
            }]}}}}
        with patch.object(photos,"_json",side_effect=fake_json) as source:
            result=photos.resolve(company)
        self.assertTrue(result["image_url"].startswith("https://upload.wikimedia.org/"))
        self.assertIn("CC BY-SA",result["image_credit"])
        self.assertEqual(source.call_count,2)

    def test_unlicensed_or_unmatched_photos_are_not_invented(self):
        item={"id":"node/456","name":"Maison des orchidées","city":"Paris","wikidata":"Q12345"}
        with patch.object(photos,"_json",side_effect=lambda host,params:
            {"entities":{"Q12345":{"claims":{"P18":[{"mainsnak":{
                "datavalue":{"value":"Maison des orchidées.jpg"}}}]}}}}
            if "wikidata.org" in host else
            {"query":{"pages":{"1":{"imageinfo":[{
                "url":"https://upload.wikimedia.org/some-photo.jpg",
                "extmetadata":{"License":{"value":"all-rights-reserved"}}
            }]}}}}):
            result=photos.resolve(item)
        self.assertFalse(result["image_url"])
        self.assertIn("Aucune photographie",result["notice"])


if __name__=="__main__":
    unittest.main()
