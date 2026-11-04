import unittest
from local_app.engine_qualification import assess


class QualificationTests(unittest.TestCase):
    def test_installed_is_not_available_or_tested(self):
        row=assess(installed=True,available=False)
        self.assertEqual(row['state'],'installed');self.assertFalse(row['qualified'])
        self.assertEqual(assess(installed=True,available=True)['state'],'available')

    def test_matching_outputs_and_three_visual_reviews_are_required(self):
        good={'prompt_id':'one','identity':'same','executed':True,'outputs_verified':True,'success':True}
        self.assertEqual(assess(installed=True,available=True,reports=[good],identity='same')['state'],'tested')
        self.assertFalse(assess(installed=True,available=True,reports=[good]*3,identity='changed')['tested'])
        reviewed={**good,'models':[{'sha256':'a'*64}],'quality_review':{'accepted':True,'reviewer':'operator'}}
        self.assertFalse(assess(installed=True,available=True,reports=[reviewed]*2,identity='same')['qualified'])
        self.assertFalse(assess(installed=True,available=True,reports=[reviewed]*3,identity='same')['qualified'])
        reports=[{**reviewed,'prompt_id':str(i)} for i in range(3)]
        self.assertTrue(assess(installed=True,available=True,reports=reports,identity='same')['qualified'])
