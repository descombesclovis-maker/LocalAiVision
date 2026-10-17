"""Hybrid website agent and automatic product imagery regression tests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app import web_hybrid, web_briefing, web_builder


class HybridVisualTests(unittest.TestCase):
    REQUEST = ('Crée une boutique de pêche Poisson-Trap, bleu et vert clair, '
               'avec catalogue, catégories, recherche et un design exceptionnel.')

    def test_questions_focus_on_aesthetics_not_backend_or_uploads(self):
        questions = web_briefing.questions_for(self.REQUEST)
        self.assertLessEqual(len(questions), 2)
        keys = [x['key'] for x in questions]
        self.assertFalse({'checkout', 'inventory', 'model3d', 'visual'} & set(keys))

    def test_visual_plan_is_specific_to_fishing_products(self):
        items = web_hybrid.visual_plan(self.REQUEST)
        self.assertEqual([x['role'] for x in items], ['hero', 'product-one', 'product-two'])
        self.assertIn('fishing', items[0]['subject'])
        self.assertNotIn('watermark', items[0]['subject'])
        self.assertFalse(web_hybrid.visual_plan(self.REQUEST, existing=[{'path':'assets/old.png'}]))

    def test_auto_generated_images_are_real_files_in_project_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = web_builder.LocalAiWebStore(tmp, lambda *_:'{}')
            first = store.create('Poisson-Trap')['project']['id']
            second = store.create('Autre')['project']['id']
            calls=[]
            def generator(project_id, prompt):
                calls.append(prompt)
                folder = store.project_dir(project_id) / 'site' / 'assets'
                folder.mkdir(parents=True, exist_ok=True)
                filename = 'image-'+str(len(calls))+'.png'
                (folder / filename).write_bytes(b'\x89PNG\r\n\x1a\n' + b'synthetic-test')
                return {'path':'assets/'+filename}
            result = web_hybrid.make_visuals(store, first, self.REQUEST,
                                             local_generate=generator, local_ready=True)
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(result['generated']), 3)
            self.assertTrue(all(x['provider']=='comfyui' for x in result['generated']))
            self.assertEqual(store.assets(second), [])
            self.assertIn('assets/image-1.png', web_hybrid.developer_brief(self.REQUEST,result))
            repeat=web_hybrid.make_visuals(store,first,self.REQUEST,local_generate=generator,local_ready=True)
            self.assertEqual(len(calls),3)
            self.assertEqual(repeat['generated'],[])

    def test_no_fake_photos_and_no_paid_api_without_explicit_optin(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            pid=store.create('Preview')['project']['id']
            with patch.dict(os.environ,{'LOCALAIWEB_ALLOW_PAID_IMAGES':'0','OPENAI_API_KEY':'hidden'}):
                result=web_hybrid.make_visuals(store,pid,self.REQUEST,local_ready=False)
            self.assertFalse(result['ready'])
            self.assertEqual(store.assets(pid),[])
            self.assertTrue(result['notes'])

    def test_agent_uses_filesystem_and_reports_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            pid=store.create('Example')['project']['id']
            created=[]
            def agent(site, instruction):
                created.append(instruction)
                # Deliberately skeletal: validation triggers a second repair.
                (site/'index.html').write_text('<h1>Site</h1>',encoding='utf-8')
                return {'summary':'A first draft'}
            class Checks:
                @staticmethod
                def validate_site(site):return {'ok':True,'issues':[]}
            output=web_hybrid.build_with_agent(
                store,pid,self.REQUEST,agent,Checks,{'generated':[],'notes':[]})
            self.assertEqual(len(created),2)
            self.assertFalse(output['hybrid_validation']['ok'])
            self.assertTrue(output['hybrid_validation']['findings'])
            self.assertEqual(output['provider'] if 'provider' in output else 'unknown','unknown')


if __name__ == '__main__':
    unittest.main()
