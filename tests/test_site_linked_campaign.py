import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PublishedCampaignIntegration(unittest.TestCase):
 def test_published_project_prepopulates_visual_campaign(self):
  web=(ROOT/'local_app/web/localaiweb.js').read_text(encoding='utf-8')
  vision=(ROOT/'local_app/web/studio-ads.js').read_text(encoding='utf-8')
  self.assertIn("'/localaivision?campaign_project='",web)
  self.assertIn("new URLSearchParams(window.location.search).get('campaign_project')",vision)
  self.assertIn("project.deployment?.production_url",vision)
  self.assertIn("select.value=project.brand_id",vision)
  self.assertIn("sans inventer de tarifs",vision)
  self.assertIn("studioAdOpen",vision)
if __name__=='__main__': unittest.main()
