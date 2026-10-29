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
        css=source("localaiweb-mobile.css")
        for control in ("dailyProspectsToggle","mapRetryLibrary","mapUnavailable","businessMap"):
            self.assertIn('id="'+control+'"',html)
        self.assertIn("async function ensureLeaflet()",js)
        self.assertIn("cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4",js)
        self.assertIn("cdn.jsdelivr.net/npm/leaflet@1.9.4",js)
        self.assertNotIn("document.write(",html)
        self.assertIn("hit=mobile.matches?44:32",js)
        self.assertIn("if(!(await ensureLeaflet()))",js)
        self.assertIn("if(!map){location.reload();return}",js)
        self.assertIn("setProspectsOpen(!mobile.matches)",js)
        self.assertIn(".map-unavailable{z-index:400",css)
        self.assertIn("pointer:coarse",source("localaiweb-google-map.js"))

    def test_preview_eye_opens_phone_not_pc_and_two_taps_select(self):
        js=source("localaiweb-inspector.js")
        self.assertIn("window.open('/web-preview/'",js)
        self.assertIn("ev.pointerType==='touch'",js)
        self.assertIn("doubleTap",js)
        self.assertIn("api('/api/web/open-browser'",js)  # desktop still works

    def test_other_mobile_workspaces_preserve_navigation(self):
        for name in ("localaiweb.html","localaiweb-projects.html",
                     "localaiweb-map.html","localaiweb-clients.html",
                     "localaiweb-sales.html"):
            self.assertIn('localaiweb-mobile.css',source(name))
            self.assertIn('viewport-fit=cover',source(name))

if __name__=="__main__":
    unittest.main()
