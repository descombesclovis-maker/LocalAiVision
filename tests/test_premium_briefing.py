import tempfile
import unittest
from local_app import web_briefing, web_builder

BRIEF = ("Créer un site commerce pour des accessoires de pêches. Il me faut une partie "
         "Accueil, une partie produits, et un champ de recherche. Les produits sont "
         "classés par catégories. Le site s'appelle Poisson-Trap, essentiellement "
         "constitué de bleu et de vert clair. Il me faut un site exceptionnel.")

class SpecificationTests(unittest.TestCase):
    def test_fishing_brief_preserves_brand_colors_and_features(self):
        info=web_briefing.infer(BRIEF)
        self.assertTrue(info['shop'])
        self.assertTrue(info['spectacular'])
        self.assertIn('bleu',info['colors'])
        self.assertIn('vert',info['colors'])
        self.assertTrue(info['light_green'])
        self.assertTrue(info['has_brand'])
        questions=web_briefing.questions_for(BRIEF)
        keys=[q['key'] for q in questions]
        self.assertNotIn('brand',keys)
        self.assertIn('inventory',keys)
        self.assertIn('checkout',keys)
        self.assertIn('visual',keys)

    def test_plan_is_saved_and_user_can_respond_to_missing_info(self):
        with tempfile.TemporaryDirectory() as root:
            store=web_builder.LocalAiWebStore(root,lambda *_:'{}')
            p=store.create('Poisson-Trap')['project']['id']
            plan=store.brief_begin(p,BRIEF)
            self.assertFalse(plan['ready'])
            self.assertTrue(plan['question'])
            for q in plan['plan']['questions']:
                answer=store.brief_answer(p,q['choices'][0])
            self.assertTrue(answer['ready'])
            self.assertIn('Poisson-Trap',answer['prompt'])
            self.assertIn('bleu',answer['prompt'])
            self.assertEqual(store.brief_status(p)['plan']['original'],BRIEF)

    def test_audit_rejects_generic_or_colorless_mockup(self):
        mocked={'index.html':'<html><body><h1>Poisson-Trap</h1><p>Produits</p></body></html>',
                'styles.css':'body{background:#170a22;color:white}',
                'app.js':''}
        defects={x['id'] for x in web_briefing.audit(mocked,BRIEF)}
        self.assertIn('depth',defects)
        self.assertIn('visual_polish',defects)
        self.assertIn('blue_palette',defects)
        self.assertIn('green_palette',defects)
        self.assertIn('search_ui',defects)

if __name__=='__main__':unittest.main()
