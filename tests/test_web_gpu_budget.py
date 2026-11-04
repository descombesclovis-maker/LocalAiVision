"""The media-GPU budget only throttles the LocalAiWeb preview renderer."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebGpuBudgetTests(unittest.TestCase):
    def test_parent_sends_preview_only_budget_from_live_media_state(self):
        source = (ROOT / "local_app/web/studio-activity.js").read_text(encoding="utf-8")
        self.assertIn("Number(media.running||0)>0||Number(media.preparing||0)>0", source)
        self.assertIn("document.body.dataset.studioPage!=='editor'", source)
        self.assertIn("type:'localaiweb-resource-budget',mediaBusy", source)
        self.assertIn("location.origin", source)

    def test_preview_accepts_only_trusted_loopback_parent_messages(self):
        source = (ROOT / "local_app/web/templates/cinematic3d/app.js").read_text(encoding="utf-8")
        self.assertIn("event.source!==window.parent", source)
        self.assertIn("isTrustedBudgetOrigin(event.origin,window.location.origin)", source)
        self.assertIn("localaiweb-resource-budget", source)
        self.assertIn("1000/effectiveFrameRate(state.profile,state.mediaBusy)", source)
        self.assertIn("!state.mediaBusy && elapsed>0", source)

    def test_no_model_or_workflow_generation_settings_are_part_of_the_budget(self):
        source = (ROOT / "local_app/web/templates/cinematic3d/quality.mjs").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"(?i)prompt|sampler|cfg|workflow|lora")
        self.assertIn("Math.min(normal, 8)", source)


if __name__ == "__main__":
    unittest.main()
