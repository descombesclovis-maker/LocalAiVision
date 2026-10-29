"""Natural-language quality planning and prompt-fidelity regressions."""
import unittest
from local_app import media_director,nsfw_profile

class MediaDirectorTests(unittest.TestCase):
 def test_exact_ten_seconds_creates_real_duration_and_sampling_controls(self):
  p=media_director.plan("Génère une vidéo de 10 secondes d'une danseuse", "omniweaving-t2v",
                        {"quality":"workflow","aspect":"auto","fps":None,"steps":None})
  self.assertEqual(p["duration"],10)
  self.assertEqual(p["fps"],12)
  self.assertEqual(p["steps"],18)
  self.assertEqual((p["width"],p["height"]),(640,360))
  self.assertEqual(p["quality"],"balanced")
 def test_high_quality_is_explicitly_slower_not_secretly_low_res(self):
  p=media_director.plan("une vidéo photoréaliste de 10 secondes en format vertical",
                        "omniweaving-t2v",{"quality":"workflow","aspect":"auto"})
  self.assertEqual((p["width"],p["height"]),(480,832))
  self.assertEqual(p["fps"],16)
  self.assertEqual(p["steps"],24)
  self.assertEqual(p["aspect"],"9:16")
 def test_fast_is_user_requested_only(self):
  p=media_director.plan("vidéo rapide 10 secondes", "wan",
                        {"quality":"workflow","aspect":"auto"})
  self.assertEqual((p["width"],p["height"]),(512,288))
  self.assertEqual(p["steps"],12)
  self.assertEqual(p["fps"],8)
 def test_explicit_steps_and_frame_rate_override_defaults(self):
  p=media_director.plan("Vidéo 10 secondes 20 fps 32 étapes", "wan",{"quality":"workflow"})
  self.assertEqual(p["duration"],10)
  self.assertEqual(p["fps"],20)
  self.assertEqual(p["steps"],32)
 def test_distilled_model_sampler_not_force_overridden(self):
  p=media_director.plan("Vidéo 5 secondes","hunyuan15-i2v-step",{"quality":"workflow"})
  self.assertIsNone(p.get("steps"))
 def test_1440p_is_not_forced_on_small_photo_gpu(self):
  p=media_director.plan("Photographie de produit", "hunyuanimage21",{"quality":"workflow","aspect":"auto"})
  self.assertEqual((p["width"],p["height"]),(1280,1280))
 def test_original_adult_prompt_is_preserved_without_generic_stereotypes(self):
  prompt="Une adulte nue danse, lumière douce, gros plan sur les mains"
  text,negative,_=nsfw_profile.prepare_visual_request(prompt,technical_quality=True)
  self.assertTrue(text.startswith(prompt))
  self.assertNotIn("trending girls",text)
  self.assertNotIn("latina",text)
  self.assertIn("temporal flicker",negative)
 def test_pass_through_unknown_workflows(self):
  self.assertEqual(media_director.plan("10 seconds","unknown",{"seed":12}),{"seed":12})

if __name__=="__main__":unittest.main()
