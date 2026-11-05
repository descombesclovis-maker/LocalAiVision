import tempfile
import unittest
from pathlib import Path
from local_app import generation_provenance as provenance


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.graph={'1':{'class_type':'KSampler','inputs':{'seed':12,'steps':35,'cfg':5.5}},
                    '2':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'model.safetensors'}}}

    def test_exact_submission_and_no_invented_metrics(self):
        row=provenance.submitted(self.root,'job-1',build={'version':'3.1.6'},workflow={'nodes':[]},graph=self.graph,
            original_prompt='chien sans personne',effective_prompt='dog only',negative='hands',settings={'seed':None})
        self.assertEqual(provenance.read(self.root,'job-1')['submitted_graph']['1']['inputs']['seed'],12)
        self.assertEqual(row['original_prompt'],'chien sans personne')
        self.assertEqual(row['effective_prompt'],'dog only')
        self.assertIsNone(row['models'][0]['sha256'])
        self.assertTrue(all(v is None for v in row['measurements'].values()))
        info={'status':{'completed':True,'status_str':'success'},'outputs':{'3':{'images':[{'filename':'x.png','subfolder':''}]}}}
        done=provenance.complete(self.root,'job-1',info)
        self.assertEqual(done['state'],'done');self.assertIsNone(done['outputs'][0]['sha256'])
        self.assertFalse(provenance.record_output_bytes(self.root,'job-1','x.png','',b'wrong input bytes','input'))
        self.assertTrue(provenance.record_output_bytes(self.root,'job-1','x.png','',b'actual image bytes'))
        self.assertEqual(provenance.read(self.root,'job-1')['outputs'][0]['hash_status'],'measured_on_download')
        self.assertEqual(provenance.complete(self.root,'job-1',info)['observed_finished_at_utc_epoch'],done['observed_finished_at_utc_epoch'])

    def test_legacy_or_private_jobs_are_not_published(self):
        self.assertIsNone(provenance.complete(self.root,'unknown',{'status':{'completed':True}}))
        with self.assertRaises(ValueError):provenance.read(self.root,'../../private')
        self.assertFalse((self.root/'public-provenance').exists())
