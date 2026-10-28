"""Updater integrity and rollback regressions (no user files are touched)."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from local_app import server


def release_zip():
    output=io.BytesIO()
    # Test binary has a PE header and meets the update minimum-size rule.
    exe=b"MZ"+b"\0"*(5*1024*1024+50)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_STORED) as z:
        z.writestr("LocalVisionAI.exe",exe)
    return output.getvalue(),exe


class UpdateSafetyTests(unittest.TestCase):
    def test_release_size_and_sha256_and_extracted_binary(self):
        payload,exe=release_zip()
        fake={"tag_name":"build-9991"}
        asset={"browser_download_url":"https://github.com/descombesclovis-maker/LocalAiVision/releases/download/build-9991/LocalVisionAI-Windows.zip",
               "digest":"sha256:"+hashlib.sha256(payload).hexdigest(),"size":len(payload)}
        with tempfile.TemporaryDirectory() as path:
            with patch.object(server,"DATA",Path(path)),patch.object(server,"urlopen",return_value=io.BytesIO(payload)):
                installed=server._download_update_exe(fake,asset)
                self.assertEqual(installed.read_bytes(),exe)
                self.assertEqual(installed.name,"LocalVisionAI.new.exe")

    def test_digest_mismatch_blocks_update_before_extraction(self):
        payload,_=release_zip()
        asset={"browser_download_url":"https://github.com/descombesclovis-maker/LocalAiVision/releases/download/build-99/LocalVisionAI-Windows.zip",
               "digest":"sha256:"+"0"*64,"size":len(payload)}
        with tempfile.TemporaryDirectory() as path:
            with patch.object(server,"DATA",Path(path)),patch.object(server,"urlopen",return_value=io.BytesIO(payload)):
                with self.assertRaises(RuntimeError):
                    server._download_update_exe({"tag_name":"build-99"},asset)

    def test_download_length_mismatch_is_refused(self):
        payload,_=release_zip()
        asset={"browser_download_url":"https://github.com/descombesclovis-maker/LocalAiVision/releases/download/build-99/LocalVisionAI-Windows.zip",
               "digest":"sha256:"+hashlib.sha256(payload).hexdigest(),
               "size":len(payload)+123}
        with tempfile.TemporaryDirectory() as path:
            with patch.object(server,"DATA",Path(path)),patch.object(server,"urlopen",return_value=io.BytesIO(payload)):
                with self.assertRaisesRegex(RuntimeError,"incomplet"):
                    server._download_update_exe({"tag_name":"build-99"},asset)

    @unittest.skipUnless(os.name=="nt","PowerShell updater is Windows-only")
    def test_updater_script_keeps_backup_until_healthcheck(self):
        with tempfile.TemporaryDirectory() as path:
            with patch.object(server,"DATA",Path(path)),patch.object(server.sys,"frozen",True,create=True):
                script,_,_=server._write_update_helper(Path(path)/"staged.exe")
                text=script.read_text(encoding="utf-8")
        for expected in ("Get-FileHash","$CurrentExe.previous","$CurrentExe.incoming",
                         "Start-Process","Invoke-RestMethod","build_tag",
                         "$ExpectedBuild","Rollback successful","Stop-Process"):
            self.assertIn(expected,text)
        self.assertLess(text.index("if (-not $healthy)"),text.index('Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue',text.index('Write-UpdateLog "Update confirmed healthy')))
        self.assertIn("Wait-Process -Id $ParentPid",text)
        self.assertIn("Get-NetTCPConnection -State Listen -LocalPort 3000",text)
        self.assertIn("Port 3000 toujours utilise",text)
        self.assertIn("STARTUP: ",text)
        self.assertIn("$observedBuild",text)
        self.assertIn("Rollback successful",text)
        self.assertIn("Safe per-user installation",text)
        self.assertIn("Original installation restarted unchanged",text)
        self.assertIn("Get-AuthenticodeSignature",text)
        self.assertIn("SHChangeNotify",text)

    def test_updater_does_not_wait_for_unbounded_engine_cleanup(self):
        import inspect
        source=inspect.getsource(server._exit_for_update)
        self.assertIn("threading.Thread(target=stop_engines",source)
        self.assertIn("os._exit(0)",source)

    def test_diagnostics_show_latest_update_failure_not_binary_failed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs=Path(tmp)/"logs"
            logs.mkdir()
            entry=logs/"update.log"
            entry.write_text(
                "[1] Updater started. Target build: build-267\\n"
                "[1] Update failed: port indisponible\\n"
                "[1] Rollback successful.\\n", encoding="utf-8")
            with patch.object(server,"DATA",Path(tmp)):
                issue=server.update_diagnostics()
                self.assertEqual(issue["state"],"failed")
                self.assertIn("port indisponible",issue["message"])
                entry.write_text(entry.read_text(encoding="utf-8")+
                    "[2] Updater started. Target build: build-268\\n"
                    "[2] Update confirmed healthy: build-268\\n",encoding="utf-8")
                resolved=server.update_diagnostics()
                self.assertEqual(resolved["state"],"success")

    def test_update_endpoint_returns_build_tag_for_health_check(self):
        source=Path(server.__file__).read_text(encoding="utf-8")
        self.assertIn('"build_tag": build_info().get("build_tag")',source)
        self.assertIn("'-ExpectedBuild', latest_tag",source)

    def test_ci_starts_real_frozen_exe_and_polls_health(self):
        pipeline=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        self.assertIn("Smoke test native EXE and extracted Python DLL",pipeline)
        self.assertIn("LOCALVISIONAI_UPDATE_SMOKE",pipeline)
        self.assertIn("dist\\LocalVisionAI.exe",pipeline)


if __name__=="__main__":
    unittest.main()
