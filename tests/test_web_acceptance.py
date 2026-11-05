import json
import tempfile
import unittest
from pathlib import Path
from local_app import web_builder,web_acceptance,web_delivery


class WebAcceptanceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=web_builder.LocalAiWebStore(tmp.name,None);self.pid=self.store.create()['project']['id']
        self.site=self.store.project_dir(self.pid)/'site'
        self.store.write_files(self.pid,{'index.html':'<h1>Example</h1>','localai-functional.json':json.dumps({'schema':1,'features':[
            {'id':'contact','label':'Contact','acceptance':'Une demande test est reçue dans le stockage de test.','status':'functional'},
            {'id':'navigation','label':'Navigation','acceptance':'Chaque page est accessible au clavier.','status':'demonstration'}]})})

    def accept(self,key='contact',revision=None,outcome='passed'):
        return web_acceptance.record(self.store,self.pid,{'confirmed':True,'feature_id':key,'outcome':outcome,
            'revision':revision or web_delivery.revision(self.site),'evidence':'Fixture de test seulement : résultat observé et reçu local identifié.'})

    def test_generated_functional_claim_is_not_proof(self):
        plan=web_acceptance.describe(self.store,self.pid)
        self.assertFalse(plan['verified']);self.assertEqual(plan['features'][0]['status'],'demonstration')
        self.assertFalse(self.accept()['verified']);self.assertTrue(self.accept('navigation')['verified'])
        self.assertFalse(self.accept('contact',outcome='failed')['verified'])

    def test_changed_project_rejects_stale_acceptance_and_invalidates_old_checks(self):
        old=web_delivery.revision(self.site);self.accept();self.accept('navigation')
        (self.site/'product.png').write_bytes(b'new asset')
        self.assertFalse(web_acceptance.describe(self.store,self.pid)['verified'])
        with self.assertRaisesRegex(ValueError,'changé'):self.accept(revision=old)

    def test_manual_business_acceptance_cannot_certify_old_visual_review(self):
        old=web_delivery.revision(self.site)
        root=self.store.project_dir(self.pid)
        (root/'delivery_report.json').write_text(json.dumps({'revision':old,'ready_to_deliver':True,'technical':{'ok':True},'visual':{'status':'passed','reviewed':True}}))
        (self.site/'product.png').write_bytes(b'changed')
        self.accept();self.accept('navigation')
        self.assertFalse(web_delivery.current(self.store,self.pid)['ready_to_deliver'])

    def test_missing_contract_and_unconfirmed_operator_test_are_not_valid(self):
        (self.site/'localai-functional.json').unlink()
        self.assertFalse(web_acceptance.describe(self.store,self.pid)['verified'])
        with self.assertRaises(ValueError):web_acceptance.record(self.store,self.pid,{'confirmed':False})
