import json
import tempfile
import unittest
from pathlib import Path
from local_app import web_builder, web_delivery


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=web_builder.LocalAiWebStore(tmp.name,None)
        self.pid=self.store.create()['project']['id'];self.site=self.store.project_dir(self.pid)/'site'
        self.store.write_files(self.pid,{'index.html':'<h1>Example</h1>'})
        self.visual={'status':'passed','reviewed':True,'issues':[],'screenshots':[]}
        for mode in ('ordinateur','tablette','telephone'):
            path=self.site/'.localaiweb-qa'/(mode+'.png');path.parent.mkdir(exist_ok=True);path.write_bytes(b'fixture only')
            self.visual['screenshots'].append({'mode':mode,'path':'.localaiweb-qa/'+path.name})
        self.checks={'revision':web_delivery.revision(self.site),'verified':True,'source':'unit-test fixture, not a real generation'}

    def test_unavailable_deferred_and_captured_are_not_passes(self):
        for status in ('unavailable','deferred_first_preview','captured','failed'):
            report=web_delivery.assess(self.site,{'ok':True},{**self.visual,'status':status},functional_checks=self.checks)
            self.assertFalse(report['ready_to_deliver'])

    def test_build_is_insufficient_and_business_checks_are_required(self):
        self.assertFalse(web_delivery.assess(self.site,{'ok':True},self.visual)['ready_to_deliver'])
        report=web_delivery.assess(self.site,{'ok':False},self.visual,functional_checks=self.checks)
        self.assertIn('technical_checks_failed',report['blocking_reasons'])
        self.assertTrue(web_delivery.assess(self.site,{'ok':True},self.visual,functional_checks=self.checks)['ready_to_deliver'])

    def test_changes_to_media_invalidate_delivery_but_internal_qa_does_not(self):
        root=self.store.project_dir(self.pid)
        (root/'functional_checks.json').write_text(json.dumps(self.checks))
        web_delivery.save(self.store,self.pid,{'ok':True},self.visual)
        self.assertTrue(web_delivery.current(self.store,self.pid)['ready_to_deliver'])
        (self.site/'.localaiweb-qa'/'new.png').write_bytes(b'internal')
        self.assertTrue(web_delivery.current(self.store,self.pid)['ready_to_deliver'])
        (self.site/'product.png').write_bytes(b'new public asset')
        self.assertFalse(web_delivery.current(self.store,self.pid)['ready_to_deliver'])

    def test_missing_capture_and_changed_business_evidence_block(self):
        (self.site/'.localaiweb-qa'/'telephone.png').unlink()
        report=web_delivery.assess(self.site,{'ok':True},self.visual,functional_checks={**self.checks,'revision':'old'})
        self.assertIn('missing_screenshot',report['blocking_reasons'])
        self.assertIn('business_acceptance_not_verified',report['blocking_reasons'])
