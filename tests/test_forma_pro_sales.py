"""FORMA commercial workflow, site map UX and explicit legal invoice safeguards."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date
from local_app import web_builder, web_sales_invoice as sales, web_site_architecture as arch

ROOT=Path(__file__).resolve().parents[1]
SELLER={"name":"Lilian Descombes","siret":"53784237900027",
        "address":"15 rue Exemple, 75000 Paris",
        "legal_form":"EI","vat_mode":"franchise",
        "payment_details":"Virement bancaire sur demande",
        "late_penalty_rate":"taux BCE + 10 points"}
CLIENT={"name":"Établissement Test","address":"2 rue du Commerce 75000 Paris",
        "type":"business","siret":"12345678900000"}

class ProSaleTests(unittest.TestCase):
    def test_service_sector_site_map(self):
        salon=arch.plan("Site d'un salon de coiffure pour un coiffeur à Paris.")
        self.assertEqual([part[0] for part in salon["pages"]],["home","booking"])
        soap=arch.plan("Vendeur de savons artisanaux, catalogue et produits.")
        self.assertEqual([part[0] for part in soap["pages"]],
                         ["home","catalog","product","contact"])
        landing=arch.plan("Page unique de présentation simple.")
        self.assertEqual(landing["mode"],"single")

    def test_map_has_top_optional_filters_and_right_company_rail(self):
        page=(ROOT/"local_app/web/localaiweb-map.html").read_text(encoding="utf-8")
        js=(ROOT/"local_app/web/localaiweb-map.js").read_text(encoding="utf-8")
        css=(ROOT/"local_app/web/localaiweb-map.css").read_text(encoding="utf-8")
        self.assertIn("map-top-filters",page)
        self.assertIn("map-side-rail",page)
        self.assertIn('id="industryFilter"',page)
        self.assertIn('id="mapCreate"',page)
        self.assertIn("Créer un site pour cette entreprise",page)
        self.assertIn("scheduleNearby",js)
        self.assertIn("autoViewKey",js)
        self.assertIn("Date.now()<suppressAutoUntil",js)
        self.assertIn(".map-fullscreen .map-top-filters",css)

    def test_single_project_estimate_30_percent_and_not_invoice(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:"{}")
            pid=store.create("Atelier Test")["project"]["id"]
            empty=sales.estimate(store,pid)
            self.assertEqual(empty["items"],[])
            store.write_files(pid,{
                "index.html":'<html lang="fr"><head><title>Atelier</title></head>'
                             '<body><main><h1>Atelier</h1></main></body></html>',
                "styles.css":"body{color:green}"})
            quote=sales.estimate(store,pid)
            self.assertEqual(quote["currency"],"EUR")
            self.assertTrue(quote["estimate_only"])
            landing=next(x for x in quote["items"] if x["id"]=="landing")
            self.assertEqual(landing["market_eur"],"900.00")
            self.assertEqual(landing["subtotal_eur"],"630.00")
            self.assertEqual(landing["discount_pct"],30)
            self.assertIn("Ne constitue pas une facture",quote["notice"])

    def test_final_pdf_requires_real_legal_and_client_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:"{}")
            pid=store.create("Vitrine test")["project"]["id"]
            store.write_files(pid,{
                "index.html":'<html><head><title>Vitrine</title></head><body>'
                             '<h1>Vitrine</h1></body></html>'})
            folder=Path(tmp)/"invoices"
            with self.assertRaisesRegex(ValueError,"Validation explicite"):
                sales.issue(store,pid,folder,SELLER,CLIENT,["landing"],
                            service_date=date.today().isoformat())
            with self.assertRaisesRegex(ValueError,"Adresse professionnelle"):
                sales.issue(store,pid,folder,{**SELLER,"address":""},CLIENT,
                            ["landing"],accepted=True,service_date=date.today().isoformat())
            with self.assertRaisesRegex(ValueError,"Date de prestation"):
                sales.issue(store,pid,folder,SELLER,CLIENT,["landing"],accepted=True)
            invoice=sales.issue(store,pid,folder,SELLER,CLIENT,["landing"],accepted=True,
                                service_date=date.today().isoformat())
            self.assertEqual(invoice["invoice_number"],"FORMA-"+str(date.today().year)+"-00001")
            self.assertEqual(invoice["total_eur"],"630.00")
            self.assertTrue((folder/(invoice["invoice_number"]+".pdf")).read_bytes().startswith(b"%PDF"))
            self.assertEqual(invoice["data"]["vat_eur"],"0")
            second=sales.issue(store,pid,folder,SELLER,CLIENT,["landing"],accepted=True,
                               service_date=date.today().isoformat())
            self.assertTrue(second["invoice_number"].endswith("00002"))
            self.assertTrue((folder/"invoice-sequence.json").exists())

    def test_invoice_rejects_unbuilt_site_or_unverified_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:"{}")
            pid=store.create("Sans site")["project"]["id"]
            with self.assertRaisesRegex(ValueError,"fonctionnalités"):
                sales.issue(store,pid,Path(tmp)/"invoices",SELLER,CLIENT,["landing"],
                            accepted=True,service_date=date.today().isoformat())

    def test_sales_page_has_legal_gate_and_domain_button(self):
        html=(ROOT/"local_app/web/localaiweb-sales.html").read_text(encoding="utf-8")
        script=(ROOT/"local_app/web/localaiweb-sales.js").read_text(encoding="utf-8")
        editor=(ROOT/"local_app/web/localaiweb.html").read_text(encoding="utf-8")
        server=(ROOT/"local_app/server.py").read_text(encoding="utf-8")
        self.assertIn("F<span>O</span>RMA",html)
        self.assertIn("53784237900027",html)
        self.assertIn('id="invoiceApproval"',html)
        self.assertIn('id="latePenaltyRate"',html)
        self.assertIn("/api/web/domain/attach",script)
        self.assertIn("/api/web/invoice/issue",script)
        self.assertIn('id="lawSalesBtn"',editor)
        self.assertIn('/api/web/sales/estimate',server)
        self.assertIn('/api/web/invoice/file',server)
        self.assertIn("vercel_attach_purchased_domain",server)

if __name__=="__main__":
    unittest.main()
