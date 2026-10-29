"""Regression coverage for Studio media quality, private UI and genuine progress."""
import json
import math
import unittest
from pathlib import Path

from local_app import comfy_progress, media_director, workflows

WEB = Path(__file__).resolve().parents[1] / "local_app" / "web"


class MediaBuild292Tests(unittest.TestCase):
    def test_hunyuan_landscape_respects_twelve_gb_pixel_budget(self):
        result = media_director.plan(
            "Photographie d'architecture au format paysage 16:9",
            "hunyuanimage21", {"aspect": "auto", "quality": "workflow"}
        )
        self.assertEqual(result["aspect"], "16:9")
        self.assertGreater(result["width"], result["height"])
        self.assertLessEqual(result["width"] * result["height"], 1280**2 * 1.05)
        self.assertEqual(result["width"] % 32, 0)
        self.assertEqual(result["height"] % 32, 0)

    def test_hunyuan_premium_portrait_quality_not_overwritten_by_stale_draft(self):
        result = media_director.plan(
            "Portrait photo réaliste 9:16, éclairage naturel",
            "hunyuanimage21", {"quality": "draft", "aspect": "auto"}
        )
        self.assertEqual(result["quality"], "quality")
        self.assertGreater(result["height"], result["width"])
        self.assertLessEqual(result["width"] * result["height"], 1536**2 * 1.05)

    def test_explicit_image_dimensions_are_preserved(self):
        result = media_director.plan(
            "Photo paysage photoréaliste 16:9",
            "hunyuanimage21", {"width": 1216, "height": 704, "quality": "workflow"}
        )
        self.assertEqual((result["width"], result["height"]), (1216, 704))

    def test_quality_square_video_is_not_forced_to_small_512_default(self):
        result = media_director.plan(
            "Vidéo 1:1 cinématographique", "omniweaving-i2v", {"quality": "workflow"}
        )
        self.assertEqual(result["quality"], "quality")
        self.assertEqual((result["width"], result["height"]), (640, 640))

    def test_short_video_duration_is_rounded_up_to_valid_latent_frames(self):
        graph = {"1": {"class_type": "WanSampler", "inputs": {
            "length": 5, "fps": 12, "width": 640, "height": 360, "steps": 18
        }}}
        result = workflows.apply_inputs(graph, "test", settings={"fps": 12, "duration": 0.5})
        self.assertEqual(result["1"]["inputs"]["length"], 9)

    def test_temporal_prompt_improvement_is_idempotent(self):
        first = media_director.enhance_video_continuity("Landscape", "", "wan")
        second = media_director.enhance_video_continuity(*first, "wan")
        self.assertEqual(first, second)

    def test_real_preview_tracks_executing_prompt_even_with_other_running_jobs(self):
        one, two = "292-video-one", "292-video-two"
        comfy_progress.register(one)
        comfy_progress.register(two)
        comfy_progress.update(one, state="running", node="sampler")
        comfy_progress.update(two, state="running", node="sampler")
        event = json.dumps({"type": "executing", "data": {
            "prompt_id": two, "node": "sampler"
        }}).encode("utf-8")
        image = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\xff\xd8\xff" + b"sample"
        def frame(opcode, data):
            return bytes((0x80 | opcode, len(data))) + data
        raw = frame(1, event) + frame(2, image) + bytes((0x88, 0))
        class Socket:
            def __init__(self, payload):
                self.payload = payload
            def recv(self, count):
                part, self.payload = self.payload[:count], self.payload[count:]
                return part
        comfy_progress._receive(Socket(raw))
        self.assertEqual(comfy_progress.get_preview(two), ("image/jpeg", b"\xff\xd8\xffsample"))
        self.assertIsNone(comfy_progress.get_preview(one))
        comfy_progress.mark(one, "done")
        comfy_progress.mark(two, "done")

    def test_adult_gallery_and_standard_i2v_exist_without_erasing_saved_data(self):
        js = (WEB / "app.js").read_text(encoding="utf-8")
        html = (WEB / "index.html").read_text(encoding="utf-8")
        css = (WEB / "studio-adult-workspace.css").read_text(encoding="utf-8")
        self.assertIn("sessionStorage.getItem('lva_nsfw_gate')", js)
        self.assertIn("String(code).trim()!=='2905'", js)
        self.assertIn("profile==='nsfw'", js)
        self.assertIn("renderNsfwGallery()", js)
        self.assertIn('id="nsfwGallery"', html)
        self.assertIn('value="i2v"', html)
        self.assertIn("body.nsfw-active", css)
        self.assertIn("lva_conversations_v2", js)
        self.assertIn("lva_library", js)


if __name__ == "__main__":
    unittest.main()
