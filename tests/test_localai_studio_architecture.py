"""End-to-end checks for the LocalAI Studio dual-universe and brand workflow."""
import base64
from io import BytesIO
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from PIL import Image

from local_app import brand_catalog, server, web_assets_bridge, web_builder

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"


def logo_data():
    buf=BytesIO()
    Image.new("RGBA",(92,64),(25,180,200,255)).save(buf,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode("ascii")


class StudioArchitectureTests(unittest.TestCase):
    def test_real_universe_routes_keep_existing_modules(self):
        studio=(WEB/"localai-studio.html").read_text(encoding="utf-8")
        server_text=(ROOT/"local_app/server.py").read_text(encoding="utf-8")
        launcher=(ROOT/"local_app/launcher.py").read_text(encoding="utf-8")
        self.assertIn('href="/localaiweb"',studio)
        self.assertIn('href="/localaivision"',studio)
        self.assertIn('href="/studio"',studio)
        self.assertIn("LocalAI Studio",launcher)
        for route in ("/studio/brands","/api/studio/brands","/api/studio/brand/save",
                      "/api/studio/advert/render","/api/web/generations/active"):
            self.assertIn(route,server_text)
        self.assertIn('studio-activity.js',studio)
        self.assertIn('studio-ui-polish.css',studio)
        self.assertIn("prefers-reduced-motion",(WEB/"localai-studio.css").read_text())

    def test_real_active_generation_pill_links_to_selected_project(self):
        with tempfile.TemporaryDirectory() as temp:
            store=web_builder.LocalAiWebStore(Path(temp)/"projects",lambda *_:"{}")
            pid=store.create("Atelier Nova")["project"]["id"]
            jobs={pid:{"state":"running","started_at":time.time()-90,"phase":"planning",
                       "ticket":"test"}}
            phases={pid:{"phase":"building","detail":"Création des pages…"}}
            with patch.object(server,"_web_store",return_value=store),patch.object(
                server,"_web_generation_jobs",jobs),patch.object(server,"_web_progress_rows",phases):
                result=server._web_active_generations()
            self.assertEqual(result["count"],1)
            self.assertEqual(result["jobs"][0]["id"],pid)
            self.assertEqual(result["jobs"][0]["name"],"Atelier Nova")
            self.assertGreaterEqual(result["jobs"][0]["elapsed_seconds"],89)
            self.assertEqual(result["jobs"][0]["detail"],"Création des pages…")
        activity=(WEB/"studio-activity.js").read_text(encoding="utf-8")
        self.assertIn("/api/web/generations/active",activity)
        self.assertIn("window.location.assign(dest(first.id))",activity)

    def test_logo_brand_round_trip_and_separate_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            brand=brand_catalog.save_brand(root,{"name":"PawMood","sector":"Toilettage",
                "slogan":"Animaux heureux","primary_color":"#48C1A8",
                "secondary_color":"#173145","cta":"Réservez","logo_data":logo_data()})
            self.assertEqual(brand["name"],"PawMood")
            self.assertTrue(brand["logo_url"].endswith(brand["id"]))
            self.assertEqual(len(brand_catalog.list_brands(root)["brands"]),1)
            self.assertTrue(brand_catalog.logo_bytes(root,brand["id"]).startswith(b"\x89PNG"))
            updated=brand_catalog.save_brand(root,{"id":brand["id"],"name":"PawMood Plus"})
            self.assertEqual(updated["name"],"PawMood Plus")
            self.assertTrue(updated["logo_url"])
            with self.assertRaises(ValueError):
                brand_catalog.save_brand(root,{"name":"Bad","primary_color":"red"})
            with self.assertRaises(ValueError):
                brand_catalog.save_brand(root,{"name":"Bad","logo_data":
                    "data:image/svg+xml;base64,"+base64.b64encode(b"<svg/>").decode()})

    def test_render_branded_ad_image_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            brand=brand_catalog.save_brand(root,{"name":"Maison Nova","slogan":"Soin et style",
                "cta":"Réserver","logo_data":logo_data()})
            raw=BytesIO()
            Image.new("RGB",(800,450),(72,104,150)).save(raw,format="PNG")
            payload=raw.getvalue()
            with patch.object(brand_catalog,"urlopen",return_value=BytesIO(payload)):
                result=brand_catalog.render_advert(root,"http://127.0.0.1:8188",{
                    "brand_id":brand["id"],"format":"portrait",
                    "filename":"rendered.png","subfolder":"","type":"output"})
            self.assertTrue(result["ok"])
            self.assertTrue(result["url"].startswith("/api/studio/advert/file?name=pub-"))
            image=brand_catalog.advert_file(root,result["filename"])
            with Image.open(image) as pic:
                self.assertEqual(pic.size,(1080,1920))
                self.assertNotEqual(pic.getpixel((50,1880)),(72,104,150))
            self.assertEqual(raw.getvalue(),payload)
            self.assertTrue(brand_catalog.delete_advert(root,result["filename"])["deleted"])
            self.assertFalse(image.exists())

    def test_branded_ad_can_be_copied_to_web_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            store=web_builder.LocalAiWebStore(root/"projects",lambda *_:"{}")
            pid=store.create("Salon clientèle")["project"]["id"]
            folder=root/"advertising"/"output"
            folder.mkdir(parents=True)
            name="pub-"+("a"*24)+".png"
            image=folder/name
            image.write_bytes(bytes.fromhex("89504e470d0a1a0a")+b"test-bytes")
            result=web_assets_bridge.import_generation(
                store,root/"nonexistent-comfy",pid,name,kind="advert",advert_root=root)
            target=store.project_dir(pid)/"site"/result["path"]
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(),image.read_bytes())
            self.assertTrue(image.exists())
            self.assertIn("publicité",store.meta(pid)["asset_imports"][0]["source"])

    def test_invalid_output_and_missing_ffmpeg_never_fake_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            brand=brand_catalog.save_brand(root,{"name":"Maison Nova"})
            with self.assertRaises(ValueError):
                brand_catalog.render_advert(root,"http://127.0.0.1:8188",{
                    "brand_id":brand["id"],"filename":"../foo.png","format":"square"})
            with patch.object(brand_catalog,"urlopen",return_value=BytesIO(b"video data")),\
                 patch.object(brand_catalog.shutil,"which",return_value=None):
                with self.assertRaisesRegex(RuntimeError,"FFmpeg"):
                    brand_catalog.render_advert(root,"http://127.0.0.1:8188",{
                        "brand_id":brand["id"],"filename":"final.mp4","format":"square"})
            with self.assertRaises(ValueError):
                brand_catalog.advert_file(root,"../../etc/passwd")

    def test_brand_api_requires_same_origin_custom_header(self):
        handler=server.Handler.__new__(server.Handler)
        handler.send_json=Mock()
        handler.headers={"Origin":"https://outside.example","Host":"studio.private.ts.net",
                         "X-LocalAI-Brand":"1"}
        self.assertFalse(handler._authorized_brand_request())
        handler.headers["Origin"]="https://studio.private.ts.net"
        self.assertTrue(handler._authorized_brand_request())
        del handler.headers["X-LocalAI-Brand"]
        self.assertFalse(handler._authorized_brand_request())

    def test_advertising_controls_use_real_paths_and_button_targets(self):
        vision=(WEB/"index.html").read_text(encoding="utf-8")
        script=(WEB/"studio-ads.js").read_text(encoding="utf-8")
        core=(WEB/"app.js").read_text(encoding="utf-8")
        brands=(WEB/"studio-brands.html").read_text(encoding="utf-8")
        for control in ("studioAdOpen","studioAdDialog","studioAdBrand",
                        "studioAdFormat","studioAdType","studioAdCreate"):
            self.assertIn('id="'+control+'"',vision)
        for control in ("brandName","brandLogo","brandSave","brandList"):
            self.assertIn('id="'+control+'"',brands)
        self.assertIn("window.StudioAds={enhancePrompt,finishMedia,getBrands}",script)
        self.assertIn("window.onStudioAdvert=",core)
        self.assertIn("x.ad_url||'/api/view",core)
        self.assertIn("onStudioAdvertError",core)
        self.assertIn("/api/web/project/brand",(WEB/"localaiweb-brand.js").read_text())


if __name__=="__main__":
    unittest.main()
