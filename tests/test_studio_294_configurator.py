"""Contracts for non-destructive LocalAI Studio design customization."""
import json
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class StudioConfiguratorTests(TestCase):
    def test_schema_has_many_valid_unique_options(self):
        data=json.loads((WEB/"studio-design-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"],1)
        self.assertGreaterEqual(len(data["questions"]),40)
        self.assertEqual(set(data["groups"]),{"structure","visual","motion","workflow"})
        keys=[q["key"] for q in data["questions"]]
        self.assertEqual(len(keys),len(set(keys)))
        for q in data["questions"]:
            self.assertGreaterEqual(len(q["options"]),2)
            self.assertEqual(len({o["value"] for o in q["options"]}),len(q["options"]))

    def test_dialog_is_accessible_and_separate_from_projects(self):
        html=(WEB/"localai-studio.html").read_text(encoding="utf-8")
        js=(WEB/"studio-configurator.js").read_text(encoding="utf-8")
        for token in ('id="studioConfigDialog"','id="studioCustomize"','id="studioConfigForm"',
                      'id="studioConfigSave"','id="studioConfigExport"','id="studioConfigImport"',
                      'studio-configurator.css','studio-configurator.js'):
            self.assertIn(token,html)
        for target in ('href="/localaiweb"','href="/localaivision"','studio-activity.js'):
            self.assertIn(target,html)
        self.assertIn("localStorage.setItem(KEY",js)
        self.assertIn("studio-design-schema.json",js)
        self.assertIn("safeValue",js)
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')",js)
        self.assertNotIn("/api/web/project/delete",js)
        self.assertNotIn("/api/loras",js)

    def test_layout_and_motion_have_real_css_targets(self):
        css=(WEB/"studio-configurator.css").read_text(encoding="utf-8")
        cases=["layout","order","width","height","heading","nav","cards","spacing","labels",
               "buttons","buttonAlign","icons","descriptions","footer","palette","mood",
               "contrast","type","titleSize","background","lighting","glass","shadow",
               "art","logos","stroke","motion","tilt","transition","buttonMotion",
               "cardMotion","effects","speed","reveal","iconMotion","ambient"]
        # CSS variables & data states are consumed by the UI, not merely stored.
        for key in cases:
            attribute="data-studio-"+''.join(('-'+c.lower() if c.isupper() else c) for c in key)
            if key in ("spacing","speed","transition"):
                self.assertIn("--studio-",css)
            else:
                self.assertIn(attribute,css,key)
        self.assertIn("@media(prefers-reduced-motion:reduce)",css)

    def test_master_roadmap_preserves_all_new_features(self):
        roadmap=(ROOT/"docs/LOCALAI_STUDIO_MASTER_ROADMAP.md").read_text(encoding="utf-8")
        for token in ("LocalAI Intelligence","Cinema","Brand DNA","Google Maps","Autopilot",
                      "VRAM","Codex","LoRA","100 %","RTX 3060"):
            self.assertIn(token,roadmap)
