"""PawMood screenshot regression: enforce actual client brief, not generic English SaaS."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from local_app import web_briefing, web_builder, web_content_contract, web_hybrid

PAWMOOD=(
    "PawMood est un site simple de toiletterie. C'est un site basique et simpliste "
    "tout en préservant le professionnalisme qu'il renvoie. Il sera bleu/vert et blanc "
    "avec de vrais photos d'animaux ayant réalisé un toiletage. Le site se constituera "
    "d'un formulaire de prise de rdv intuitif et rapide, une présentation des services "
    "de la boutique et une parties réalisations clientes."
)

GOOD_HTML=(
    '<!doctype html><html lang="fr"><head><title>PawMood | Toilettage</title>'
    '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
    '<body><header><h1>PawMood</h1><nav>Accueil Services Réalisations '
    'Prendre rendez-vous</nav></header><main><section><h2>Toilettage chien et chat</h2>'
    '<p>Bain, brossage et soin des animaux.</p></section><section><h2>Services</h2>'
    '<p>Nos prestations de toilettage.</p></section><section><h2>Réalisations</h2>'
    '<p>Exemples de coupes et de soins pour animaux.</p></section>'
    '<form><label>Animal<input name="animal"></label>'
    '<label>Date souhaitée<input type="date"></label>'
    '<button>Demander un rendez-vous</button></form></main></body></html>'
)
GOOD_CSS='body{background:#ffffff;color:#166cbb}section{border-color:#16b785}'
FORUM_HTML='<html lang="en"><head><title>forma.</title></head><body><h1>Make room for your best work.</h1><p>The workspace, Why Forma, Pricing, Try the workspace</p></body></html>'


class PawMoodContractTests(unittest.TestCase):
    def test_understands_exact_groomer_request(self):
        spec=web_content_contract.specification(PAWMOOD,'PawMood')
        self.assertEqual(spec['brand'],'PawMood')
        self.assertEqual(spec['locale'],'fr-FR')
        self.assertEqual(spec['business'],'toilettage pour animaux')
        self.assertTrue(spec['booking'])
        self.assertTrue(spec['gallery'])
        self.assertTrue(spec['services'])
        self.assertEqual(set(spec['colors']),{'bleu','vert','blanc'})
        self.assertFalse(web_briefing.infer(PAWMOOD)['shop'])
        self.assertEqual(web_briefing.questions_for(PAWMOOD),[])

    def test_does_not_confuse_salon_with_saas_template(self):
        spec=web_content_contract.specification(PAWMOOD,'PawMood')
        files={'index.html':FORUM_HTML,'src/App.tsx':'<main>The workspace. Pricing. Make room for your best work.</main>',
               'src/styles.css':'body{background:#fffcf1;color:#1b3523}'}
        ids={finding['id'] for finding in web_content_contract.check(files,spec)}
        self.assertIn('brand_identity',ids)
        self.assertIn('wrong_business',ids)
        self.assertIn('english_ui',ids)
        self.assertIn('french_document',ids)
        self.assertIn('booking_form',ids)
        self.assertIn('customer_gallery',ids)
        self.assertIn('blue_palette',ids)

    def test_accepts_customer_brief_in_french(self):
        spec=web_content_contract.specification(PAWMOOD,'PawMood')
        self.assertEqual(web_content_contract.check({
            'index.html':GOOD_HTML,'styles.css':GOOD_CSS,'app.js':'// interactions'
        },spec),[])

    def test_react_site_needs_business_content_even_when_build_succeeds(self):
        with tempfile.TemporaryDirectory() as temp:
            store=web_builder.LocalAiWebStore(temp,lambda *_:'{}')
            pid=store.create('PawMood')['project']['id']
            store.write_files(pid,{
                'index.html':'<!doctype html><html lang="fr"><head></head><body><div id="root"></div></body></html>',
                'src/App.tsx':'export default function App(){return <main>Make room for your best work. Why Forma? Pricing</main>}',
                'package.json':'{"scripts":{"build":"vite build"}}',
            })
            class Integrations:
                @staticmethod
                def validate_site(site):return {'ok':True,'issues':[]}
                @staticmethod
                def build_project(site):return {'ok':True,'kind':'vite','output_dir':str(Path(site)/'dist')}
            result=web_hybrid.code_quality_report(store,pid,PAWMOOD,Integrations)
            self.assertFalse(result['ok'])
            ids={row['id'] for row in result['findings']}
            self.assertIn('brand_identity',ids)
            self.assertIn('wrong_business',ids)
            self.assertIn('english_ui',ids)

    def test_agent_contract_is_present_in_all_steps_and_rejects_wrong_build(self):
        with tempfile.TemporaryDirectory() as temp:
            store=web_builder.LocalAiWebStore(temp,lambda *_:'{}')
            pid=store.create('PawMood')['project']['id']
            site=store.project_dir(pid)/'site'
            seen=[]
            def agent(cwd,instruction):
                seen.append(instruction)
                (site/'index.html').write_text(FORUM_HTML,encoding='utf-8')
                (site/'styles.css').write_text('body { color: #163c24; }',encoding='utf-8')
                return {'summary':'Site terminé'}
            class Integrations:
                @staticmethod
                def validate_site(site):return {'ok':True,'issues':[]}
            with patch('local_app.web_browser_qa.review') as reviewer:
                with self.assertRaisesRegex(RuntimeError,'Site refusé'):
                    web_hybrid.build_with_agent(store,pid,PAWMOOD,agent,Integrations,
                                                {'generated':[],'notes':[]})
                reviewer.assert_not_called()
            self.assertEqual(len(seen),2)
            self.assertTrue(all('PawMood' in x and 'français' in x.lower() for x in seen))
            self.assertIn(web_briefing.WAITING_MESSAGE,store.text_files(pid)['index.html'])

    def test_automatic_animal_image_plan(self):
        subjects=web_hybrid.visual_plan(PAWMOOD)
        self.assertEqual([a['role'] for a in subjects],['hero','groomed-dog','groomed-cat'])
        self.assertTrue(all(('groomed' in a['subject'] or 'grooming' in a['subject'])
                            for a in subjects))
        self.assertTrue(all('no text' in a['prompt'] for a in subjects))


if __name__=='__main__':
    unittest.main()
