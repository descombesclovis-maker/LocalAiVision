"""Multi-page planning, conditional preview actions and contextual selection regressions."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from local_app import server, web_builder, web_creative_direction, web_site_architecture

ROOT=Path(__file__).resolve().parents[1]
PAWMOOD=("PawMood est un salon de toilettage d'animaux, "
         "avec des services, nos réalisations et un formulaire de prise de rdv.")
SINGLE=("Une landing page unique sur un studio créatif "
        "qui affiche un seul argument et un formulaire contact.")


class SiteMapTests(unittest.TestCase):
    def test_paw_mood_gets_dedicated_pages_for_practical_tasks(self):
        plan=web_site_architecture.plan(PAWMOOD)
        self.assertEqual(plan['mode'],'multi')
        self.assertEqual([p[0] for p in plan['pages']],
                         ['home','services','gallery','booking'])
        prompt=web_site_architecture.instructions(PAWMOOD)
        self.assertIn('VRAIES pages',prompt)
        self.assertIn('/rendez-vous',prompt)

    def test_explicit_landing_is_not_forced_into_multi_page(self):
        self.assertEqual(web_site_architecture.plan(SINGLE)['mode'],'single')
        self.assertEqual(web_site_architecture.check({'index.html':'<html/>'},SINGLE),[])

    def test_anchor_sections_are_not_real_pages(self):
        files={'index.html':('<html><a href="#services">Prestations</a>'
                             '<a href="#realisations">Réalisations</a>'
                             '<a href="#rdv">RDV</a>'
                             '<section id="services">Services</section>'
                             '<section id="realisations">Réalisations</section></html>')}
        findings=web_site_architecture.check(files,PAWMOOD)
        self.assertEqual(findings[0]['id'],'site_architecture')

    def test_real_html_pages_with_links_are_recognized(self):
        files={'index.html':('<html><nav><a href="prestations.html">Prestations</a>'
                             '<a href="realisations.html">Réalisations</a>'
                             '<a href="rendez-vous.html">Rendez-vous</a></nav></html>'),
               'prestations.html':'<html>Prestations</html>',
               'realisations.html':'<html>Réalisations</html>',
               'rendez-vous.html':'<html>Rendez-vous</html>'}
        self.assertEqual(web_site_architecture.check(files,PAWMOOD),[])

    def test_react_spa_hash_routes_are_allowed(self):
        files={'package.json':'{"scripts":{"build":"vite build"}}',
               'index.html':'<html><div id="root"></div></html>',
               'src/App.jsx':("""const links=['#/prestations','#/realisations','#/rendez-vous'];"""
                              """function Home(){return links.map(path=><a href={path}>Page</a>)}""")}
        self.assertEqual(web_site_architecture.check(files,PAWMOOD),[])


class CreativeIntentTests(unittest.TestCase):
    def test_brand_specific_directions_are_not_all_dropshipping(self):
        dog=web_creative_direction.instructions(PAWMOOD,'PawMood')
        perfume=web_creative_direction.instructions('Marque de parfum artisanal de luxe','Parfumerie')
        self.assertIn('soin animalier',dog)
        self.assertIn('rendez-vous',dog)
        self.assertIn('DESIGN_INTENT.md',dog)
        self.assertIn('réduced-motion' if False else 'reduced-motion',dog)
        self.assertIn('beauté et soin',perfume)
        self.assertNotEqual(dog,perfume)
        self.assertIn('Chaque clic',dog)
        self.assertIn('PAS davantage de complexité',dog)


class PreviewToolsTests(unittest.TestCase):
    def test_html_controls_are_conditional_and_slim(self):
        html=(ROOT/'local_app/web/localaiweb.html').read_text(encoding='utf-8')
        logic=(ROOT/'local_app/web/localaiweb-inspector.js').read_text(encoding='utf-8')
        for button in ('lawInspectBtn','lawBrowserBtn','lawZipBtn'):
            self.assertIn('id="'+button+'"',html)
        self.assertIn('id="lawSiteTools" class="site-tools" hidden',html)
        self.assertIn("toolbar.hidden=!v.ready",logic)
        self.assertIn('dblclick',logic)
        self.assertIn('pointerdown',logic)
        self.assertIn('pointermove',logic)
        self.assertIn('pointerup',logic)
        self.assertIn('shiftKey',logic)
        self.assertIn('law-picked',logic)
        self.assertIn('await sendText(text)',logic)
        self.assertIn('/api/web/open-browser',logic)
        self.assertIn('exportSite()',logic)

    def test_ready_checks_placeholder_and_real_compiled_site(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            with patch.object(server,'WEB_PROJECTS',folder):
                store=web_builder.LocalAiWebStore(folder,lambda *_:'{}')
                project=store.create('PawMood')
                pid=project['project']['id']
                self.assertFalse(server._web_site_ready(pid))
                site=store.project_dir(pid)/'site'
                (site/'index.html').write_text(
                    '<!doctype html><html><body><h1>PawMood</h1>'
                    '<p>Un salon de toilettage pour vos animaux, prise de rendez-vous et soins.</p>'
                    '</body></html>',encoding='utf-8')
                self.assertTrue(server._web_site_ready(pid))
                (site/'package.json').write_text('{"scripts":{"build":"vite build"}}',
                                                 encoding='utf-8')
                self.assertFalse(server._web_site_ready(pid))
                dist=site/'dist';dist.mkdir()
                (dist/'index.html').write_text(
                    '<!doctype html><html><body><h1>Version React PawMood</h1>'
                    '<p>Un salon de toilettage pour vos animaux, prise de rendez-vous.</p>'
                    '</body></html>',encoding='utf-8')
                self.assertTrue(server._web_site_ready(pid))


if __name__=='__main__':
    unittest.main()
