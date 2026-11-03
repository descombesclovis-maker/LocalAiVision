"""iPhone / PWA layout and map reliability regressions."""
from pathlib import Path
import unittest

WEB=Path(__file__).resolve().parents[1]/"local_app"/"web"

def source(name):
    return (WEB/name).read_text(encoding="utf-8")

class IPhoneReliabilityTests(unittest.TestCase):
    def test_mobile_top_actions_remain_reachable(self):
        editor=source("localaiweb.html")
        style=source("localaiweb-mobile.css")
        js=source("localaiweb-mobile.js")
        for control in ("lawMobileMenuToggle","lawMobileTools",
                        "lawMobileAgentSlot","lawMobileVersionSlot",
                        "lawMobileToolsTab","lawMobileTabs"):
            self.assertIn('id="'+control+'"',editor)
        self.assertIn("closeMenu",js)
        self.assertIn("slot.append(agent)",js)
        self.assertIn("versionSlot.append(version)",js)
        self.assertIn("show('chat')",js)
        self.assertIn(".law-mobile-tools[hidden]{display:none!important;}",style)
        self.assertIn("env(safe-area-inset-top)",style)
        self.assertIn("pointer:coarse",style)
        self.assertIn("body:has(#lawPrompt:focus)",style)

    def test_map_can_fallback_to_two_cdns_and_recover(self):
        html=source("localaiweb-map.html")
        js=source("localaiweb-map.js")
        css=source("localaiweb-map.css")
        for control in ("mapRetry","mapUnavailable","mapFailureReason","businessMap"):
            self.assertIn('id="'+control+'"',html)
        self.assertNotIn("leaflet",html.lower())
        self.assertIn("failure.hidden=false",js)
        self.assertIn("setStatus('La carte Google Maps",js)
        self.assertIn("max-height:75%",css)

    def test_preview_eye_opens_phone_not_pc_and_two_taps_select(self):
        js=source("localaiweb-inspector.js")
        self.assertIn("window.open('/web-preview/'",js)
        js+=source("preview-inspector.js")
        self.assertIn("ev.pointerType==='touch'",js)
        self.assertIn("doubleTap",js)
        self.assertIn("noopener,noreferrer",js)

    def test_other_mobile_workspaces_preserve_navigation(self):
        for name in ("localaiweb.html","localaiweb-projects.html",
                     "localaiweb-map.html","localaiweb-clients.html",
                     "localaiweb-sales.html"):
            self.assertIn('studio-system.css',source(name))
            self.assertIn('viewport-fit=cover',source(name))

if __name__=="__main__":
    unittest.main()

