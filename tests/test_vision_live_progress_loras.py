"""Real ComfyUI media status, preview, cancellation and LoRA UI regressions."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from local_app import server, comfy_progress

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class VisionMediaProgressTests(unittest.TestCase):
    def test_percent_is_sampler_only_and_not_guessed(self):
        pid="test-real-progress-01"
        comfy_progress.register(pid,"video")
        first=comfy_progress.status(pid)
        self.assertIsNone(first["percent"])
        comfy_progress.update(pid, state="running",node="sampling",value=7,maximum=20)
        self.assertEqual(comfy_progress.status(pid)["percent"],35)
        comfy_progress.update(pid,node="video-encode")
        self.assertIsNone(comfy_progress.status(pid)["percent"])
        comfy_progress.mark(pid,"done")
        self.assertEqual(comfy_progress.status(pid)["percent"],100)

    def test_real_first_preview_decoded_from_websocket_binary(self):
        pid="test-real-preview-01"
        comfy_progress.register(pid,"image")
        comfy_progress.update(pid,state="running")
        sample=b"\xff\xd8\xff"+b"frame-bytes"
        frame=(1).to_bytes(4,"big")+(1).to_bytes(4,"big")+sample
        class Socket:
            def __init__(self,buffer):
                self.buffer=buffer
            def recv(self,length):
                buf,self.buffer=self.buffer[:length],self.buffer[length:]
                return buf
        encoded=bytes((0x82,len(frame)))+frame+bytes((0x88,0))
        comfy_progress._receive(Socket(encoded))
        self.assertEqual(comfy_progress.get_preview(pid),("image/jpeg",sample))
        comfy_progress.mark(pid,"done")
        self.assertIsNone(comfy_progress.get_preview(pid))

    def test_media_cancellation_only_owned_current_prompt(self):
        with self.assertRaises(ValueError):
            server.cancel_studio_media("external-unknown-job")
        pid="our-own-prompt"
        comfy_progress.register(pid)
        with patch.object(server,"comfy_get",return_value={
                "queue_running":[],"queue_pending":[[1,pid,{}]]}),patch.object(
                server,"comfy_post",return_value={"ok":True}) as post:
            result=server.cancel_studio_media(pid)
        self.assertEqual(result["cancelled"],pid)
        post.assert_called_once_with("/queue",{"delete":[pid]})
        self.assertEqual(comfy_progress.status(pid)["state"],"cancelled")

    def test_media_cancel_csrf_guard(self):
        handler=server.Handler.__new__(server.Handler)
        handler.send_json=Mock()
        handler.headers={"Host":"pc.local","Origin":"https://outside.test",
                         "X-LocalAI-Media":"1"}
        self.assertFalse(handler._authorized_media_request())
        handler.headers["Origin"]="http://pc.local"
        self.assertTrue(handler._authorized_media_request())

    def test_previous_loras_are_visible_and_can_be_uploaded(self):
        vision=(WEB/"index.html").read_text(encoding="utf-8")
        app=(WEB/"app.js").read_text(encoding="utf-8")
        gallery=(WEB/"studio-redesign.js").read_text(encoding="utf-8")
        chip=(WEB/"studio-activity.js").read_text(encoding="utf-8")
        backend=(ROOT/"local_app"/"server.py").read_text(encoding="utf-8")
        self.assertIn('id="accordionLoras"',vision)
        self.assertIn('id="loraFileInput"',vision)
        self.assertIn("classList.toggle('hidden',!visual)",app)
        self.assertIn("lva_selected_loras",app)
        self.assertIn("'/api/loras/upload'",app)
        self.assertIn("def _upload_existing_lora(self)",backend)
        self.assertIn("/api/studio/media/jobs",gallery)
        self.assertIn("/api/studio/media/preview",gallery)
        self.assertIn("/api/studio/media/cancel",gallery)
        self.assertIn("Étape de calcul :",gallery)
        self.assertIn("/localaivision?view=creations",chip)
        self.assertIn("requestedCreations",gallery)
        self.assertIn("prefers-reduced-motion",(WEB/"vision-generation.css").read_text())

if __name__=="__main__":
    unittest.main()
