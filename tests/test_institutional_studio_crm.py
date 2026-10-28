"""Functional commercial workflow and interface regressions."""
import tempfile
from datetime import date
from pathlib import Path
import unittest

from local_app import web_crm, web_builder, web_sales_invoice, web_assets_bridge

ROOT=Path(__file__).resolve().parents[1]
SELLER={"name":"Agence Démo","siret":"53784237900027",
        "address":"10 rue de l'Atelier, Paris","legal_form":"EI",
        "vat_mode":"franchise","payment_details":"Virement bancaire",
        "late_penalty_rate":"taux contractuel communiqué"}
BUYER={"name":"Salon Démo","address":"1 rue des Tests, Lyon",
       "type":"business","siret":"12345678900000","email":"contact@demo.example"}

class CommercialWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.store=web_builder.LocalAiWebStore(self.root/"projects",lambda *_:"{}")
        self.project_id=self.store.create("Site du Salon")["project"]["id"]
        self.store.write_files(self.project_id,{
          "index.html":'<html lang="fr"><head><title>Salon</title></head><body><h1>Salon</h1></body></html>',
          "styles.css":"body{transition: color .2s}"})
        self.crm=self.root/"crm"

    def test_client_stage_persistence_and_validation(self):
        record=web_crm.upsert_client(self.crm,self.store,{"name":"Salon Démo",
            "project_id":self.project_id,"stage":"prospect"})
        changed=web_crm.upsert_client(self.crm,self.store,{"id":record["id"],
            "name":"Salon Démo","stage":"proposal","notes":"Rappeler mardi"})
        self.assertEqual(changed["id"],record["id"])
        data=web_crm.snapshot(self.crm,self.store)
        self.assertEqual(data["stages"]["proposal"],1)
        self.assertEqual(data["clients"][0]["projects"][0]["id"],self.project_id)
        with self.assertRaises(ValueError):
            web_crm.upsert_client(self.crm,self.store,{"id":record["id"],
                "name":"Salon Démo","stage":"inconnu"})

    def test_followup_priorities_and_project_ownership(self):
        first=web_crm.upsert_client(self.crm,self.store,{
            "name":"Client Alpha","project_id":self.project_id,
            "stage":"contacted","next_contact":"2020-03-04"})
        snapshot=web_crm.snapshot(self.crm,self.store)
        self.assertEqual(len(snapshot["followups_due"]),1)
        self.assertEqual(snapshot["followups_due"][0]["name"],"Client Alpha")
        with self.assertRaisesRegex(ValueError,"Date de relance"):
            web_crm.upsert_client(self.crm,self.store,{
                "id":first["id"],"name":"Client Alpha","next_contact":"demain"})
        second=web_crm.upsert_client(self.crm,self.store,{
            "name":"Client Beta","stage":"prospect","next_contact":"2099-01-01"})
        with self.assertRaisesRegex(ValueError,"déjà rattaché"):
            web_crm.upsert_client(self.crm,self.store,{
                "id":second["id"],"name":"Client Beta","project_id":self.project_id})
        snapshot=web_crm.snapshot(self.crm,self.store)
        self.assertEqual(len(snapshot["followups_upcoming"]),1)
        self.assertEqual(len(snapshot["clients"]),2)
        self.assertEqual(snapshot["stage_labels"]["proposal"],"Devis préparé")

    def test_issue_actual_quote_and_register_invoice_once(self):
        lines=web_sales_invoice.estimate(self.store,self.project_id)["items"]
        request={"project_id":self.project_id,"seller":SELLER,"customer":BUYER,
                 "items":[x["id"] for x in lines],"valid_days":30,"confirmed":True}
        with self.assertRaises(ValueError):
            web_crm.create_quote(self.crm,self.store,{**request,"confirmed":False})
        first=web_crm.create_quote(self.crm,self.store,request)
        second=web_crm.create_quote(self.crm,self.store,request)
        self.assertTrue(first["quote_number"].endswith("-00001"))
        self.assertTrue(second["quote_number"].endswith("-00002"))
        self.assertTrue(web_crm.quote_file(self.crm,first["quote_number"]).read_bytes().startswith(b"%PDF"))
        invoice=web_sales_invoice.issue(self.store,self.project_id,self.root/"invoices",
                SELLER,BUYER,["landing"],accepted=True,service_date=date.today().isoformat())
        web_crm.register_invoice(self.crm,self.store,invoice)
        web_crm.register_invoice(self.crm,self.store,invoice)
        data=web_crm.snapshot(self.crm,self.store)
        self.assertEqual(len(data["invoices"]),1)
        self.assertEqual(len(data["quotes"]),2)
        self.assertEqual(len(data["clients"]),1)

    def test_media_asset_is_copied_into_site_and_source_is_untouched(self):
        comfy=self.root/"comfy"
        output=comfy/"output"
        output.mkdir(parents=True)
        source=output/"generated.png"
        source.write_bytes(bytes.fromhex("89504e470d0a1a0a")+b"image-data-bytes")
        result=web_assets_bridge.import_generation(
            self.store,comfy,self.project_id,"generated.png")
        target=self.store.project_dir(self.project_id)/"site"/result["path"]
        self.assertEqual(target.read_bytes(),source.read_bytes())
        self.assertTrue(source.exists())
        self.assertIn(result["path"],self.store.assets(self.project_id)[0]["path"])
        self.assertIn("Nouvelle ressource locale importée",self.store.chat_history(self.project_id)[-1]["text"])
        with self.assertRaises(ValueError):
            web_assets_bridge.import_generation(
                self.store,comfy,self.project_id,"script.exe")

    def test_studio_navigation_and_commercial_routes_exist(self):
        html=(ROOT/"local_app/web/index.html").read_text(encoding="utf-8")
        sidebar=html.split('<aside class="sidebar closed" id="sidebar"')[1].split("</aside>")[0]
        for label in ("navCreations","navPhoto","navVideo","navNsfw"):
            self.assertIn('id="'+label+'"',sidebar)
        self.assertEqual(sidebar.count('class="studio-nav-entry"'),4)
        self.assertNotIn("Que veux tu créer ?",html)
        self.assertIn('id="historyDialog"',html)
        script=(ROOT/"local_app/web/studio-redesign.js").read_text(encoding="utf-8")
        self.assertIn("historyDialog.showModal()",script)
        self.assertIn("selectAssetForProject(entry)",script)
        self.assertIn('id="assetDialog"',html)
        client_html=(ROOT/"local_app/web/localaiweb-clients.html").read_text(encoding="utf-8")
        client_js=(ROOT/"local_app/web/localaiweb-clients.js").read_text(encoding="utf-8")
        self.assertIn('id="crmNextContact"',client_html)
        self.assertIn('id="auditDialog"',client_html)
        self.assertIn("showAudit(p.id,p.name)",client_js)
        self.assertIn("/api/web/preflight?id=",client_js)
        self.assertIn('id="exportClients"',client_html)
        self.assertIn("function exportClients()",client_js)
        self.assertIn("URL.createObjectURL",client_js)
        self.assertIn("LocalAiWeb-clients-",client_js)
        self.assertIn("/api/web/asset/import-generation",(ROOT/"local_app/server.py").read_text(encoding="utf-8"))
        server=(ROOT/"local_app/server.py").read_text(encoding="utf-8")
        for route in ("/localaiweb/clients","/api/web/crm/overview",
                      "/api/web/crm/client/upsert","/api/web/crm/quote/create",
                      "/api/web/crm/quote/file"):
            self.assertIn(route,server)

if __name__=="__main__":
    unittest.main()
