"""Automatic Windows updates driven by the PC monitor and iPhone PWA.

No network, GPU, Windows binary, or personal file is touched by these tests.
"""
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from local_app import server

WEB=Path(__file__).resolve().parents[1]/"local_app"/"web"


class RemoteAutoUpdateTests(unittest.TestCase):
    def test_builds_are_monotonic(self):
        self.assertTrue(server._is_newer_update("build-284","build-283"))
        self.assertTrue(server._is_newer_update("build-1001","build-999"))
        self.assertFalse(server._is_newer_update("build-282","build-283"))
        self.assertFalse(server._is_newer_update("build-283","build-283"))
        self.assertFalse(server._is_newer_update("main","build-283"))
        self.assertFalse(server._is_newer_update("build-284","source"))

    def test_work_and_draft_block_background_restart(self):
        with patch.object(server,"_auto_update_draft_seen",time.time()):
            self.assertIn("Saisie",server._update_busy_reason())
        with patch.object(server,"_auto_update_draft_seen",0.0),patch.object(
            server,"_web_generation_jobs",{"web-abc":{"state":"running"}}):
            self.assertIn("Création de site",server._update_busy_reason())

    def test_running_chat_increments_activity_counter(self):
        calls=[]
        def fake_chat():
            calls.append(server._auto_update_active_jobs)
            return 4
        self.assertEqual(server._work_guard(fake_chat),4)
        self.assertEqual(calls,[1])
        self.assertEqual(server._auto_update_active_jobs,0)

    def test_streaming_chat_is_tracked_until_finished(self):
        counts=[]
        def chunks():
            counts.append(server._auto_update_active_jobs)
            yield "token"
        self.assertEqual(list(server._work_guard_stream(chunks())),["token"])
        self.assertEqual(counts,[1])
        self.assertEqual(server._auto_update_active_jobs,0)

    def test_remote_install_requires_app_header_and_matching_origin(self):
        h=server.Handler.__new__(server.Handler)
        h.send_json=Mock()
        h.headers={"Host":"pc.tailnet.ts.net",
                   "Origin":"https://bad.example",
                   "X-LocalAiVision-Update":"1"}
        self.assertFalse(h._authorized_update_request())
        h.send_json.assert_called_once()
        h.headers["Origin"]="https://pc.tailnet.ts.net"
        self.assertTrue(h._authorized_update_request())
        del h.headers["X-LocalAiVision-Update"]
        self.assertFalse(h._authorized_update_request())

    def test_unattended_monitor_retries_deferred_install(self):
        class FakeEvent:
            times=0
            def wait(self, seconds):
                self.times+=1
                return self.times>=3
            def is_set(self):
                return False
        installer=Mock(return_value={"ok":True,"updated":False,"deferred":True,
                                     "message":"Création en cours"})
        with patch.object(server,"_update_busy_reason",return_value=""),patch.object(
            server,"_latest_update_release",return_value={"tag_name":"build-99999"}),patch.object(
            server,"build_info",return_value={"build_tag":"build-283"}),patch.object(
            server,"install_latest_update",installer):
            server._auto_update_monitor(FakeEvent(),initial_delay=0,interval=1)
        installer.assert_called_once()
        self.assertEqual(server.automatic_update_status()["state"],"deferred")

    def test_mobile_can_install_pc_release_without_binary_download(self):
        app=(WEB/"pwa-install.js").read_text(encoding="utf-8")
        mobile=(WEB/"localaiweb-update.js").read_text(encoding="utf-8")
        launcher=(Path(__file__).resolve().parents[1]/"local_app"/"launcher.py").read_text(encoding="utf-8")
        self.assertIn("window.localAiWebPcUpdate",app)
        self.assertIn("'/api/update/install'",app)
        self.assertIn("'/api/update/check'",app)
        self.assertIn("'/api/update/draft'",app)
        self.assertIn("waitForPcBuild",app)
        self.assertIn("X-LocalAiVision-Update",app)
        self.assertIn("↻ Mettre à jour le PC",mobile)
        self.assertIn("server.start_auto_updates()",launcher)


if __name__=="__main__":
    unittest.main()
