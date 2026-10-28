"""Exercise the real Windows updater hand-off with the packaged executable.

A staging copy is swapped only in a temporary test folder. Runs in the
Windows GitHub Actions runner; never changes the developer's own install.
The smoke flag validates PyInstaller startup and HTTP build tags without GUI.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
# A script started as `python scripts/foo.py` has scripts/ on sys.path,
# not necessarily the repository root. Resolve imports independent of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from urllib.request import urlopen


def main():
    if os.name != "nt":
        raise RuntimeError("Windows integration test only")
    source = Path(sys.argv[1]).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    with tempfile.TemporaryDirectory(prefix="localaiweb-update-smoke-", ignore_cleanup_errors=True) as workspace:
        root=Path(workspace)
        old=root/"LocalVisionAI.exe"
        shutil.copy2(source,old)
        data=root/"data"
        env=os.environ.copy()
        env["LOCALVISIONAI_SKIP_SETUP"]="1"
        env["LOCALVISIONAI_UPDATE_SMOKE"]="1"
        env["LOCALVISIONAI_DATA"]=str(data)
        from local_app import server
        server.DATA=data
        log=data/"logs"/"update.log"
        original=None
        helper_proc=None
        try:
            original=subprocess.Popen([str(old)],env=env,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            for _ in range(90):
                time.sleep(1)
                try:
                    with urlopen("http://127.0.0.1:3000/api/ping",timeout=1) as response:
                        ping=json.load(response)
                    if ping.get("app")=="LocalVisionAI":
                        break
                except Exception:
                    continue
            else:
                raise RuntimeError("Old EXE did not open localhost:3000")
            build=server.build_info()["build_tag"]
            with patch.object(server.sys,"frozen",True,create=True), patch.object(
                server.sys,"executable",str(old)):
                script,_,_=server._write_update_helper(source)
            cmd=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass",
                "-File",str(script),"-ParentPid",str(original.pid),
                "-CurrentExe",str(old),"-NewExe",str(source),
                "-LogPath",str(log),"-ExpectedBuild",build]
            helper_proc=subprocess.Popen(cmd,env=env,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            time.sleep(2)
            subprocess.run(["taskkill.exe","/PID",str(original.pid),"/T","/F"],
                           capture_output=True,check=False)
            helper_proc.wait(timeout=180)
            if helper_proc.returncode:
                raise RuntimeError("PowerShell updater exited "+str(helper_proc.returncode))
            logs=log.read_text(encoding="utf-8-sig",errors="replace")
            print(logs[-3800:])
            if "Update confirmed healthy:" not in logs:
                raise RuntimeError("Update swap did not pass HTTP validation")
            if "Rollback successful" in logs:
                raise RuntimeError("Unexpected rollback during integration test")
            if not old.is_file() or old.read_bytes()[:2]!=b"MZ":
                raise RuntimeError("Final EXE is missing or invalid")
            if (root/"LocalVisionAI.exe.previous").exists():
                raise RuntimeError("Updater left an unnecessary backup after success")
            print("Windows update hand-off passed:",build)
        finally:
            if original and original.poll() is None:
                subprocess.run(["taskkill.exe","/PID",str(original.pid),"/T","/F"],
                               capture_output=True,check=False)
            if helper_proc and helper_proc.poll() is None:
                helper_proc.kill()
            # The restarted PyInstaller executable has a bootloader parent
            # that can retain a file handle even after its HTTP child dies.
            # Stop ONLY processes whose executable is this temporary test EXE.
            command=(
                "$target='_"+str(old).replace("'","''")+"'".replace("_","")+"; "
                "Get-CimInstance Win32_Process | Where-Object { "
                "$_.ExecutablePath -eq $target } | ForEach-Object { "
                "& taskkill.exe /PID $_.ProcessId /T /F 2>$null | Out-Null }"
            )
            subprocess.run(["powershell.exe","-NoProfile","-Command",command],
                           capture_output=True,check=False,timeout=30)
            for _ in range(30):
                try:
                    with old.open("rb+") as handle:
                        handle.read(2)
                    break
                except PermissionError:
                    time.sleep(0.5)


if __name__=="__main__":
    main()
