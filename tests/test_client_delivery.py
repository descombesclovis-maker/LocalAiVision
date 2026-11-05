"""End-to-end local receipts/documents/ZIPs, with no actual provider transactions."""
import io
import json
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from local_app import client_delivery as delivery, web_builder
from local_app.business_time import business_date

SELLER={'name':'Atelier Démonstration','siret':'53784237900027','address':'10 rue du Test, Paris',
 'legal_form':'EI','vat_mode':'franchise','payment_details':'Virement bancaire','late_penalty_rate':'Taux contractuel applicable'}
CUSTOMER={'name':'Client Fictif','address':'12 rue des Tests, Lyon','type':'business','siren':'123456789'}

class DeliveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.store=web_builder.LocalAiWebStore(self.root/'projects',lambda *_:'{}')
  self.pid=self.store.create('Site Démo')['project']['id'];self.db=self.root/'deliveries'
  self.store.write_files(self.pid,{'index.html':'<html lang="fr"><title>Site fictif</title><body>Démo</body></html>','package.json':'{"scripts":{"build":"vite build"},"dependencies":{}}'})
 def snap(self):return delivery.snapshot(self.db,self.store,self.pid)
 def act(self,action,**kw):return delivery.action(self.db,self.store,self.pid,{'action':action,'version':self.snap()['version'],**kw})
 def commercial(self):
  self.act('save',seller=SELLER,customer=CUSTOMER,service_date=business_date().isoformat(),items=[{'label':'Création du site','quantity':'1','unit_eur':'100','vat_rate':'20'}])
  self.act('quote',confirmed=True);self.act('accept',confirmed=True)
 def pay(self,amount='100',reference='fixture-virement'):
  return self.act('payment',amount=amount,reference=reference,confirmed=True)
 def technical(self,services=None):return self.act('technical',services=services or {},checks={k:True for k in ('design','pages','functions','rights')})
 def packet(self,download=False):
  d=self.snap();return delivery.package(self.db,self.store,self.pid,d['assessment']['revision'],download=download,expected_version=d['version'])
 def test_quote_payment_invoice_and_zip_no_unneeded_folders(self):
  self.commercial();d=self.pay();self.technical();preview=self.packet()
  self.assertTrue(d['invoice'].startswith('FAC-LIV-'))
  self.assertTrue(preview['name'].endswith('.zip'))
  name,blob=self.packet(True)
  with zipfile.ZipFile(io.BytesIO(blob)) as z:
   names=z.namelist();self.assertTrue(any(x.endswith('/02_Documents/Devis.pdf') for x in names))
   self.assertTrue(any(x.endswith('/02_Documents/Facture.pdf') for x in names))
   self.assertTrue(any(x.endswith('/01_Site_Web/Sources/index.html') for x in names))
   self.assertFalse(any('/03_Hebergement/' in x or '/04_Base_de_Donnees/' in x or '/05_Paiements/' in x for x in names))
   for n in names:
    if n.endswith('.pdf'):self.assertTrue(z.read(n).startswith(b'%PDF-'))
  self.act('delivered',confirmed=True);self.assertTrue(self.snap()['delivered'])
 def test_partial_manual_receipt_idempotent_and_frozen_invoice(self):
  self.commercial();d=self.pay('40','first');pdf=delivery.document(self.db,self.store,self.pid,d['invoice']);invoice=d['invoice']
  self.assertEqual(d['assessment']['payment']['status'],'partial')
  self.assertIn('Règlement complet requis avant livraison.',d['assessment']['missing'])
  self.pay('40','first');self.assertEqual(len(self.snap()['assessment']['payment']['receipts']),1)
  self.pay('60','second');self.assertEqual(self.snap()['invoice'],invoice)
  self.assertEqual(delivery.document(self.db,self.store,self.pid,invoice),pdf)
  with self.assertRaisesRegex(ValueError,'figé'):self.act('save',seller=SELLER)
 def test_incomplete_unpaid_stale_or_unconfirmed_cannot_release(self):
  with self.assertRaises(ValueError):self.packet()
  self.commercial();self.technical()
  with self.assertRaises(ValueError):self.pay('0')
  self.pay();old=self.snap()
  self.store.write_files(self.pid,{'new.html':'<h1>Modification</h1>'})
  with self.assertRaises(ValueError):delivery.package(self.db,self.store,self.pid,old['assessment']['revision'],expected_version=old['version'])
  self.assertIn('Validation finale à renouveler pour les sources actuelles.',self.snap()['assessment']['missing'])
  with self.assertRaises(ValueError):self.act('delivered',confirmed=False)
 def test_exclusion_and_secret_detection_in_sources_and_fiches(self):
  site=self.store.project_dir(self.pid)/'site'
  (site/'.env.production.local').write_text('PASSWORD=verysecret')
  (site/'seed.sql').write_text("INSERT INTO users VALUES ('real data')")
  (site/'credential.json').write_text('{"api_key":"a-secret-value-12345"}')
  (site/'private.pem').write_text('PRIVATE KEY')
  self.commercial();self.pay();self.technical()
  s=self.snap()['assessment'];self.assertIn('.env.production.local',s['excluded']);self.assertIn('seed.sql',s['excluded'])
  self.assertTrue(any('credential.json' in x for x in s['missing']))
  with self.assertRaises(ValueError):self.packet()
  with self.assertRaises(ValueError):self.technical({'vercel':{'instructions':'password="actual-secret"'}})
 def test_symlink_traversal_and_personal_database_rows_blocked(self):
  site=self.store.project_dir(self.pid)/'site';outside=self.root/'private.txt';outside.write_text('private data')
  try:(site/'leak.txt').symlink_to(outside)
  except OSError:self.skipTest('No symlink privilege')
  self.assertTrue(any('symbolique' in x for x in self.snap()['assessment']['missing']))
  with self.assertRaises(ValueError):delivery.snapshot(self.db,self.store,'../../outside')
 def test_detected_services_require_real_checklist_and_schema(self):
  self.store.write_files(self.pid,{'vercel.json':'{}','supabase/migrations/202611050001_schema.sql':'create table public.widgets(id bigint); alter table public.widgets enable row level security;',
   'supabase/functions/example/index.ts':'// configuration only','app.js':'// stripe paymentintent'})
  self.commercial();self.pay();self.technical()
  self.assertEqual(set(self.snap()['assessment']['services']),{'vercel','supabase','payment'})
  services={'vercel':{'enabled':True,'reviewed':True,'project_id':'prj_fixture','instructions':'Transfert à valider dans le compte du client'},
   'supabase':{'enabled':True,'reviewed':True,'project_ref':'abcdefghijklmnopqrst','auth':'URL client et redirections','storage':'Bucket privé et politiques','security':'RLS vérifiée','instructions':'Appliquer les migrations fournies après revue'},
   'payment':{'enabled':True,'reviewed':True,'provider':'Stripe','mode':'test','client_account':'acct_fixture','webhooks':'/api/webhook, signature requise','instructions':'Configurer le compte du client'}}
  self.technical(services)
  with self.assertRaises(ValueError):self.packet()
  services['payment']['mode']='live';self.technical(services)
  name,blob=self.packet(True)
  with zipfile.ZipFile(io.BytesIO(blob)) as z:
   self.assertTrue(any('/03_Hebergement/Vercel/' in n for n in z.namelist()))
   self.assertTrue(any(n.endswith('schema.sql') for n in z.namelist()))
   self.assertTrue(any('/05_Paiements/' in n for n in z.namelist()))
 def test_provider_metadata_and_test_mode_never_unlock_live_delivery(self):
  self.commercial()
  session={'id':'cs_test_abcdefghijklmnop','status':'complete','payment_status':'paid','currency':'eur','amount_total':10000,'livemode':False,
   'payment_intent':'pi_fixture','client_reference_id':self.pid,'metadata':{'project_id':self.pid,'delivery_quote':self.snap()['quote']}}
  intent={'status':'succeeded','latest_charge':{'amount_refunded':0}}
  with patch('local_app.web_sales_orders.setting',return_value='fixture'),patch('local_app.web_sales_orders._request',side_effect=[session,intent]):
   d=self.act('stripe',reference=session['id'],confirmed=True)
  self.assertIsNone(d['invoice']);self.assertEqual(d['assessment']['payment']['paid_eur'],'0');self.assertEqual(d['assessment']['payment']['test_eur'],'100.00')
  session['client_reference_id']='different'
  with patch('local_app.web_sales_orders.setting',return_value='fixture'),patch('local_app.web_sales_orders._request',return_value=session):
   with self.assertRaises(ValueError):self.act('stripe',reference=session['id'],confirmed=True)
 def test_refund_credit_keep_original_and_block_delivery(self):
  self.commercial();d=self.pay();invoice=d['invoice'];pdf=delivery.document(self.db,self.store,self.pid,invoice);self.technical()
  self.act('refund',amount='100',reference='refund-fixture',confirmed=True)
  self.assertEqual(self.snap()['assessment']['payment']['status'],'refunded')
  self.act('credit',reason='Annulation fictive',confirmed=True)
  self.assertEqual(delivery.document(self.db,self.store,self.pid,invoice),pdf)
  self.assertTrue(self.snap()['credit'].startswith('AV-LIV-'))
  with self.assertRaises(ValueError):self.packet()
 def test_dossier_lease_and_document_project_ownership(self):
  self.commercial();self.pay();self.technical();old=self.snap();self.technical()
  with self.assertRaisesRegex(ValueError,'dossier a changé'):delivery.package(self.db,self.store,self.pid,old['assessment']['revision'],expected_version=old['version'])
  other=self.store.create('Autre')['project']['id']
  with self.assertRaises(ValueError):delivery.document(self.db,self.store,other,self.snap()['quote'])
  self.assertEqual(delivery.listing(self.db,self.store)[0]['id'],self.pid)
 def test_rollback_reserves_no_duplicate_invoice_number(self):
  self.commercial();self.pay()
  with delivery.database(self.db) as db:
   self.assertEqual(db.execute("SELECT count(*) FROM documents WHERE kind='invoice'").fetchone()[0],1)
  self.assertEqual(self.snap()['version'],4)
 def test_large_multiline_documents_are_valid_pdf(self):
  self.act('save',seller={**SELLER,'address':'Adresse fictive très longue et détaillée, bâtiment test, étage 8\n'+('France '*40)},customer=CUSTOMER,service_date=business_date().isoformat(),items=[{'label':('Prestation détaillée avec un libellé long '*5)+str(i),'quantity':'1','unit_eur':'10','vat_rate':'20'} for i in range(25)])
  self.act('quote',confirmed=True);pdf=delivery.document(self.db,self.store,self.pid,self.snap()['quote'])
  from pypdf import PdfReader
  reader=PdfReader(io.BytesIO(pdf));self.assertGreater(len(reader.pages),1)
  self.assertIn('Prestation détaillée',''.join(p.extract_text() for p in reader.pages))

if __name__=='__main__':unittest.main()
