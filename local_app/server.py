import base64, hashlib, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, uuid, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
try:
    from local_app import llm, workflows, web_builder, integrations_cli, web_briefing
except ImportError:
    import llm, workflows, web_builder, integrations_cli

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LOCALVISIONAI_DATA", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LocalVisionAI")))
WEB = ROOT / "local_app" / "web"
IMPORTED = DATA / "workflows" / "imported"
IMPORTED.mkdir(parents=True, exist_ok=True)
LOCALAIWEB_DATA = DATA / "localaiweb"
WEB_PROJECTS = LOCALAIWEB_DATA / "projects"
WEB_PROJECTS.mkdir(parents=True, exist_ok=True)
_web_progress_lock = threading.Lock()
_web_progress_rows = {}
_web_generation_lock = threading.Lock()
_web_generation_jobs = {}

def _web_async_generate(project_id, prompt, ticket):
    """Run the existing, tested synchronous generation route in a worker.

    The UI keeps receiving progress and previews. A second submission to the
    same project never spawns a concurrent writer that corrupts its files.
    """
    try:
        result = http_json("http://127.0.0.1:%d/api/web/generate" % PORT,
                           method="POST", payload={"id": project_id, "prompt": prompt},
                           timeout=1600)
        outcome = {
            "state": "done", "summary": str(result.get("summary") or "")[:2500],
            "quality": result.get("quality", {}),
            "visuals": result.get("visuals", {}),
            "provider": result.get("provider", ""),
        }
    except HTTPError as exc:
        try:
            details = json.loads(exc.read(7000).decode("utf-8"))
            message = str(details.get("error") or exc.reason)
        except (ValueError, UnicodeError, AttributeError):
            message = str(exc)
        outcome = {"state": "error", "error": message[:900]}
    except Exception as exc:
        outcome = {"state": "error", "error": str(exc)[:900]}
    with _web_generation_lock:
        if _web_generation_jobs.get(project_id, {}).get("ticket") == ticket:
            _web_generation_jobs[project_id].update(outcome)
            _web_generation_jobs[project_id]["finished_at"] = time.time()
    if outcome["state"] == "error":
        _web_progress(project_id, "error", outcome["error"])

def _web_generation_status(project_id):
    _web_store().meta(project_id)
    with _web_generation_lock:
        job = dict(_web_generation_jobs.get(project_id) or {})
    with _web_progress_lock:
        progress = dict(_web_progress_rows.get(project_id) or {})
    result = {**progress, **job}
    if not job:
        result["state"] = "idle"
    # Never report a site as ready based on the placeholder index.html.
    try:
        if _web_site_ready(project_id):
            index = _web_preview_root(project_id) / "index.html"
            result["preview_ready"] = True
            result["preview_version"] = str(index.stat().st_mtime_ns)
        else:
            result["preview_ready"] = False
    except (OSError, ValueError):
        result["preview_ready"] = False
    return result

def _web_start_generation(project_id, prompt):
    store = _web_store()
    meta = store.meta(project_id)
    request = str(prompt or "").strip()
    if not request or len(request) > 25000:
        raise ValueError("Décris ton site en 25 000 caractères maximum.")
    with _web_generation_lock:
        previous = _web_generation_jobs.get(project_id)
        if previous and previous.get("state") == "running":
            return {"ok": True, "already_running": True, "ticket": previous["ticket"]}
        # Validate the active coding agent BEFORE accepting a long job.
        settings = meta.get("settings") or {}
        provider = str(settings.get("ai_provider") or "codex")
        if provider == "claude" and not meta.get("agent_selected_by_user", False):
            provider = "codex"
        if provider in ("codex", "claude"):
            from local_app import web_hybrid
            web_hybrid.select_coding_agent(provider, integrations_cli.coding_agent_status(provider))
        ticket = uuid.uuid4().hex
        _web_generation_jobs[project_id] = {
            "state": "running", "ticket": ticket,
            "started_at": time.time(), "phase": "planning",
        }
    _web_progress(project_id, "planning", "L'agent prépare la première proposition…")
    worker = threading.Thread(
        target=_web_async_generate, args=(project_id, request, ticket),
        name="LocalAiWeb-"+project_id, daemon=True)
    worker.start()
    return {"ok": True, "ticket": ticket, "state": "running"}


def _web_progress(project_id, phase, detail):
    key = str(project_id or '')
    if not key:
        return
    with _web_progress_lock:
        _web_progress_rows[key] = {
            "phase": str(phase), "detail": str(detail)[:240], "updated": time.time()
        }

HOST = "127.0.0.1"
PORT = 3000
COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
_comfy_info_cache = {"time": 0, "data": {}}
_engine_lock = threading.RLock()
_comfy_lock = threading.Lock()
_setup_lock = threading.Lock()
_update_lock = threading.Lock()
_comfy_proc = None
_comfy_cwd = None
_comfy_vram_args_cache = None
STARTUP = {"state": "idle", "message": "Prêt", "error": None, "started_at": None}
VERSION = "3.1.0"
LORA_CATALOG = ROOT / "local_app" / "data" / "bjornulf_hunyuan_general.json"
BUILD_INFO_PATH = ROOT / "local_app" / "data" / "build_info.json"
UPDATE_REPO = "descombesclovis-maker/LocalAiVision"
UPDATE_API = "https://api.github.com/repos/" + UPDATE_REPO + "/releases/latest"
UPDATE_ASSET = "LocalVisionAI-Windows.zip"


IGNORE_JSON = {"package.json", "tsconfig.json", "config.json"}

# An explicit medium in the user's prompt must win over a stale graphical
# style saved in the UI. This prevents e.g. "une photo ..." from turning into
# a watercolor simply because Aquarelle had been selected during an earlier
# generation.
_STYLE_PATTERNS = (
    ("photo", re.compile(r"\b(photo(?:graph(?:ie|ique)?)?|photoreal(?:istic|ism)?|photor[ée]al(?:iste|isme)?)\b", re.I)),
    ("watercolor", re.compile(r"\b(aquarelle|watercolou?r)\b", re.I)),
    ("comic", re.compile(r"\b(bande\s+dessin[ée]e?|comic(?:\s*book)?|bd)\b", re.I)),
    ("render3d", re.compile(r"\b(rendu\s*3d|3d\s*render|image\s*3d)\b", re.I)),
    ("illustration", re.compile(r"\b(illustration|gouache|dessin(?:[ée]e?)?)\b", re.I)),
    ("cinema", re.compile(r"\b(cin[ée]ma(?:tographique)?|cinematic|film\s*still)\b", re.I)),
)


def build_info():
    info = {'version': VERSION, 'build_tag': 'source', 'commit': '', 'run_number': 0}
    try:
        saved = json.loads(BUILD_INFO_PATH.read_text(encoding='utf-8-sig'))
        if isinstance(saved, dict):
            info.update(saved)
    except Exception:
        pass
    info['version'] = str(info.get('version') or VERSION)
    info['build_tag'] = str(info.get('build_tag') or 'source')
    return info


def _latest_update_release():
    req = Request(
        UPDATE_API,
        headers={
            'User-Agent': 'LocalVisionAI/' + VERSION,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )
    with urlopen(req, timeout=15) as response:
        release = json.load(response)
    if not isinstance(release, dict):
        raise RuntimeError('Réponse GitHub invalide.')
    return release


def _update_asset_from_release(release):
    for asset in release.get('assets') or []:
        if isinstance(asset, dict) and asset.get('name') == UPDATE_ASSET:
            url = str(asset.get('browser_download_url') or '')
            if url.startswith('https://github.com/' + UPDATE_REPO + '/releases/download/'):
                return asset
    raise RuntimeError('Le dernier build ne contient pas le paquet Windows de mise à jour.')


def update_status():
    current = build_info()
    release = _latest_update_release()
    asset = _update_asset_from_release(release)
    latest_tag = str(release.get('tag_name') or '')
    available = bool(latest_tag and latest_tag != current.get('build_tag'))
    return {
        'ok': True,
        'available': available,
        'current_version': current.get('version'),
        'current_build': current.get('build_tag'),
        'latest_version': str(release.get('name') or latest_tag).replace('LocalVisionAI ', '').strip(),
        'latest_build': latest_tag,
        'published_at': release.get('published_at'),
        'size': int(asset.get('size') or 0),
    }


def update_diagnostics():
    """Read a bounded local updater log; the .failed file is a binary, not a log."""
    path=DATA / "logs" / "update.log"
    if not path.is_file():
        return {"ok":True, "state":"never", "message":"Aucune mise à jour effectuée.", "log_path":str(path)}
    with path.open("rb") as stream:
        stream.seek(max(0,path.stat().st_size-32000))
        lines=stream.read().decode("utf-8-sig",errors="replace").splitlines()
    starts=[i for i,line in enumerate(lines) if "Updater started." in line]
    tail=lines[starts[-1]:] if starts else lines[-50:]
    failed=next((line for line in reversed(tail) if "Update failed:" in line),"")
    healthy=any("Update confirmed healthy:" in line for line in tail)
    if healthy:
        state="success"
        message="La dernière mise à jour a démarré correctement."
    elif failed:
        state="failed"
        message=failed.split("Update failed:",1)[-1].strip()
    else:
        state="in_progress"
        message="Dernier journal : "+(tail[-1][-300:] if tail else "en cours")
    return {"ok":True,"state":state,"message":message[:500],
            "log_path":str(path),"recent_lines":tail[-22:]}


def _download_update_exe(release, asset):
    safe_tag = re.sub(r'[^A-Za-z0-9._-]+', '_', str(release.get('tag_name') or 'latest'))
    folder = DATA / 'updates' / safe_tag
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / UPDATE_ASSET
    part = archive.with_suffix('.zip.part')
    req = Request(
        str(asset['browser_download_url']),
        headers={'User-Agent': 'LocalVisionAI/' + VERSION, 'Accept': 'application/octet-stream'},
    )
    digest = hashlib.sha256()
    with urlopen(req, timeout=60) as response, part.open('wb') as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
    size = part.stat().st_size
    expected_size = int(asset.get('size') or 0)
    if size < 5 * 1024 * 1024 or (expected_size and size != expected_size):
        part.unlink(missing_ok=True)
        raise RuntimeError('Paquet de mise à jour incomplet ou de taille inattendue.')
    expected = str(asset.get('digest') or '')
    if expected.startswith('sha256:') and digest.hexdigest().lower() != expected[7:].lower():
        part.unlink(missing_ok=True)
        raise RuntimeError('La vérification SHA-256 de la mise à jour a échoué.')
    part.replace(archive)
    staged = folder / 'LocalVisionAI.new.exe'
    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() is not None:
            raise RuntimeError('Archive téléchargée corrompue (contrôle ZIP CRC).')
        member = next((n for n in zf.namelist() if Path(n).name.lower() == 'localvisionai.exe'), None)
        if member is None:
            raise RuntimeError('LocalVisionAI.exe est absent du paquet téléchargé.')
        with zf.open(member) as src, staged.open('wb') as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    if staged.stat().st_size < 5 * 1024 * 1024 or staged.read_bytes()[:2] != b'MZ':
        staged.unlink(missing_ok=True)
        raise RuntimeError('Le nouvel exécutable Windows est invalide.')
    return staged


def _write_update_helper(staged):
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('La mise à jour automatique est disponible uniquement dans LocalVisionAI.exe sous Windows.')
    current = Path(sys.executable).resolve()
    folder = DATA / 'updates'
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / 'apply_update.ps1'
    log = DATA / 'logs' / 'update.log'
    script.write_text(r'''param(
  [int]$ParentPid,
  [string]$CurrentExe,
  [string]$NewExe,
  [string]$LogPath,
  [string]$ExpectedBuild
)
$ErrorActionPreference = "Stop"
$backup = "$CurrentExe.previous"
$incoming = "$CurrentExe.incoming"
$failed = "$CurrentExe.failed"
$newProcess = $null
$replaced = $false
$fallbackInstall = $false
$originalExe = $CurrentExe

function Write-UpdateLog([string]$Text) {
  try {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logFolder = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
    Add-Content -LiteralPath $LogPath -Value "[$stamp] $Text" -Encoding UTF8
  } catch { }
}

try {
  Write-UpdateLog "Updater started. Target build: $ExpectedBuild"
  if (-not (Test-Path -LiteralPath $NewExe -PathType Leaf)) {
    throw "Fichier EXE telecharge introuvable."
  }
  $expectedLength = (Get-Item -LiteralPath $NewExe).Length
  if ($expectedLength -lt 5MB) { throw "Fichier EXE telecharge trop petit." }
  $expectedHash = (Get-FileHash -LiteralPath $NewExe -Algorithm SHA256).Hash
  # Always copy to the installation volume before swapping executable paths.
  # An interrupted Copy-Item cannot leave the installation half-written.
  Remove-Item -LiteralPath $incoming -Force -ErrorAction SilentlyContinue
  Copy-Item -LiteralPath $NewExe -Destination $incoming -Force
  if ((Get-Item -LiteralPath $incoming).Length -ne $expectedLength) {
    throw "Copie locale incomplete avant remplacement."
  }
  if ((Get-FileHash -LiteralPath $incoming -Algorithm SHA256).Hash -ne $expectedHash) {
    throw "SHA256 different apres copie locale."
  }
  Write-UpdateLog "Staged EXE verified: $expectedLength bytes, SHA256 $expectedHash"
  # Signature policies are never bypassed. If a verified publisher already
  # signed the installed EXE, reject unsigned/differently signed replacements.
  $oldSignature = Get-AuthenticodeSignature -FilePath $CurrentExe -ErrorAction SilentlyContinue
  $newSignature = Get-AuthenticodeSignature -FilePath $NewExe -ErrorAction SilentlyContinue
  if ($oldSignature -and $oldSignature.Status -eq "Valid") {
    if (-not $newSignature -or $newSignature.Status -ne "Valid") {
      throw "Mise a jour non signee refusee : l'ancienne version possede une signature valide."
    }
    if ($oldSignature.SignerCertificate.Thumbprint -ne $newSignature.SignerCertificate.Thumbprint) {
      throw "Certificat de signature different : mise a jour refusee."
    }
  } elseif (-not $newSignature -or $newSignature.Status -ne "Valid") {
    Write-UpdateLog "EXE unsigned: release SHA256 was verified, but Windows SmartScreen reputation is not guaranteed."
  }

  # Wait for the old frozen bootloader process to release LocalVisionAI.exe.
  if ($ParentPid -gt 0) {
    Wait-Process -Id $ParentPid -Timeout 120 -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 900
  # Another process can keep the old HTTP port open even after the updater
  # parent has exited. Never swap while a different server owns localhost.
  $portBusy = $false
  for ($portAttempt=0; $portAttempt -lt 60; $portAttempt++) {
    try {
      $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction Stop)
      if ($listeners.Count -eq 0) { $portBusy = $false; break }
      $portBusy = $true
    } catch {
      $portBusy = $false
      break
    }
    Start-Sleep -Milliseconds 500
  }
  if ($portBusy) {
    throw "Port 3000 toujours utilise par une autre instance : installation reportee pour eviter un redemarrage defectueux."
  }
  Write-UpdateLog "Original app stopped; HTTP port 3000 is available."
  if (-not (Test-Path -LiteralPath $CurrentExe -PathType Leaf)) {
    throw "Ancien executable absent ; abandon pour proteger les donnees."
  }
  # Only clear an older .previous after the new staged binary has been verified.
  Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
  $swapped = $false
  for ($i = 0; $i -lt 90 -and -not $swapped; $i++) {
    try {
      Move-Item -LiteralPath $CurrentExe -Destination $backup -Force
      try {
        Move-Item -LiteralPath $incoming -Destination $CurrentExe -Force
        $swapped = $true
        $replaced = $true
      } catch {
        Move-Item -LiteralPath $backup -Destination $CurrentExe -Force
        throw
      }
    } catch {
      Start-Sleep -Milliseconds 400
    }
  }
  if (-not $swapped) {
    # Some desktop/cloud-synced/Program Files locations cannot be replaced by
    # a non-elevated user. Install a verified per-user copy instead of asking
    # to bypass Windows Defender or to grant administrator privileges.
    $fallbackInstall = $true
    $portableDir = Join-Path $env:LOCALAPPDATA "LocalVisionAI\\app"
    New-Item -ItemType Directory -Path $portableDir -Force | Out-Null
    $CurrentExe = Join-Path $portableDir "LocalVisionAI.exe"
    $backup = "$CurrentExe.previous"
    $failed = "$CurrentExe.failed"
    Write-UpdateLog "Original EXE locked/protected. Safe per-user installation: $CurrentExe"
    Copy-Item -LiteralPath $NewExe -Destination "$CurrentExe.incoming" -Force
    if ((Get-FileHash -LiteralPath "$CurrentExe.incoming" -Algorithm SHA256).Hash -ne $expectedHash) {
      throw "Verification de la copie utilisateur echouee."
    }
    if (Test-Path -LiteralPath $CurrentExe) {
      Move-Item -LiteralPath $CurrentExe -Destination $backup -Force
    }
    Move-Item -LiteralPath "$CurrentExe.incoming" -Destination $CurrentExe -Force
    $replaced = $true
  }
  if ((Get-FileHash -LiteralPath $CurrentExe -Algorithm SHA256).Hash -ne $expectedHash) {
    throw "SHA256 different apres installation."
  }
  Write-UpdateLog "EXE replaced; launching and waiting for expected build health check."

  $newProcess = Start-Process -FilePath $CurrentExe -WorkingDirectory (Split-Path -Parent $CurrentExe) -PassThru
  $healthy = $false
  $observedBuild = "aucun"
  for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    $newProcess.Refresh()
    try {
      $ping = Invoke-RestMethod -Uri "http://127.0.0.1:3000/api/ping" -TimeoutSec 2
      $observedBuild = [string]$ping.build_tag
      if ($ping.app -eq "LocalVisionAI" -and $ping.build_tag -eq $ExpectedBuild) {
        $healthy = $true
        break
      }
    } catch { }
    if ($newProcess.HasExited -and $i -ge 5) {
      throw "Nouvel EXE termine avec code $($newProcess.ExitCode) sans demarrer le build $ExpectedBuild. Port observe : $observedBuild."
    }
  }
  if (-not $healthy) {
    throw "Nouvelle version non operationnelle apres verification HTTP. Build attendu : $ExpectedBuild, observe : $observedBuild."
  }
  Write-UpdateLog "Update confirmed healthy: $ExpectedBuild. Keeping project and model data unchanged."
  if ($fallbackInstall) {
    try {
      $shell = New-Object -ComObject WScript.Shell
      $desktop = [Environment]::GetFolderPath('Desktop')
      $updated = $false
      Get-ChildItem -LiteralPath $desktop -Filter '*.lnk' -ErrorAction SilentlyContinue | ForEach-Object {
        $shortcut = $shell.CreateShortcut($_.FullName)
        if ([string]::Equals([string]$shortcut.TargetPath, [string]$originalExe, [StringComparison]::OrdinalIgnoreCase)) {
          $shortcut.TargetPath = $CurrentExe
          $shortcut.WorkingDirectory = Split-Path -Parent $CurrentExe
          $shortcut.IconLocation = "$CurrentExe,0"
          $shortcut.Save()
          $updated = $true
        }
      }
      if (-not $updated) {
        $shortcut = $shell.CreateShortcut((Join-Path $desktop "LocalAiVision.lnk"))
        $shortcut.TargetPath = $CurrentExe
        $shortcut.WorkingDirectory = Split-Path -Parent $CurrentExe
        $shortcut.IconLocation = "$CurrentExe,0"
        $shortcut.Save()
      }
      Write-UpdateLog "Desktop shortcut points to verified per-user build."
    } catch {
      Write-UpdateLog ("Shortcut could not be updated: " + $_.Exception.Message)
    }
  }
  # Ask Windows Explorer to refresh its icon cache; do not tamper with security
  # providers or Defender configuration.
  try {
    $member='[System.Runtime.InteropServices.DllImport("shell32.dll")] public static extern void SHChangeNotify(uint eventId, uint flags, System.IntPtr item1, System.IntPtr item2);'
    Add-Type -Namespace ShellRefresh -Name Native -MemberDefinition $member -ErrorAction SilentlyContinue
    [ShellRefresh.Native]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
  } catch { }
  Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $failed -Force -ErrorAction SilentlyContinue
} catch {
  Write-UpdateLog ("Update failed: " + $_.Exception.Message)
  # Preserve the actual reason in update.log. A .failed file is a renamed
  # Windows executable, not the diagnostic log.
  try {
    $startupLog = Join-Path (Split-Path -Parent $LogPath) "startup.log"
    if (Test-Path -LiteralPath $startupLog -PathType Leaf) {
      Get-Content -LiteralPath $startupLog -Tail 16 -ErrorAction SilentlyContinue | ForEach-Object {
        Write-UpdateLog ("STARTUP: " + $_)
      }
    }
  } catch { }
  try {
    if ($newProcess) {
      $newProcess.Refresh()
      if (-not $newProcess.HasExited) {
        Stop-Process -Id $newProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 800
      }
    }
  } catch { }
  if ($fallbackInstall -and -not (Test-Path -LiteralPath $backup -PathType Leaf)) {
    # A first-time per-user fallback had no prior file to restore.
    # Keep the original installation intact and restart that trusted copy.
    try {
      if (Test-Path -LiteralPath $CurrentExe) {
        Move-Item -LiteralPath $CurrentExe -Destination $failed -Force
      }
      Start-Process -FilePath $originalExe -WorkingDirectory (Split-Path -Parent $originalExe)
      Write-UpdateLog "Fallback failed. Original installation restarted unchanged."
    } catch {
      Write-UpdateLog ("Fallback recovery failed: " + $_.Exception.Message)
    }
  } elseif ($replaced -and (Test-Path -LiteralPath $backup -PathType Leaf)) {
    try {
      # Retain the failed build separately for diagnostics, then revert.
      Remove-Item -LiteralPath $failed -Force -ErrorAction SilentlyContinue
      if (Test-Path -LiteralPath $CurrentExe) {
        Move-Item -LiteralPath $CurrentExe -Destination $failed -Force
      }
      Move-Item -LiteralPath $backup -Destination $CurrentExe -Force
      Write-UpdateLog "Rollback successful. Restarting prior installed version."
      Start-Process -FilePath $CurrentExe -WorkingDirectory (Split-Path -Parent $CurrentExe)
    } catch {
      Write-UpdateLog ("Automatic rollback failed: " + $_.Exception.Message)
    }
  }
} finally {
  Remove-Item -LiteralPath $incoming -Force -ErrorAction SilentlyContinue
}
''', encoding='utf-8')
    return script, current, log


def _exit_for_update():
    # Never leave the old local web server holding port 3000 if a model worker
    # refuses to terminate. Engine shutdown remains best-effort.
    try:
        threading.Thread(target=stop_engines, daemon=True).start()
    except Exception:
        pass
    time.sleep(0.8)
    os._exit(0)


def install_latest_update():
    if not _update_lock.acquire(blocking=False):
        raise RuntimeError('Une mise à jour est déjà en cours.')
    try:
        current = build_info()
        release = _latest_update_release()
        asset = _update_asset_from_release(release)
        latest_tag = str(release.get('tag_name') or '')
        if latest_tag == current.get('build_tag'):
            return {'ok': True, 'updated': False, 'message': 'LocalVisionAI est déjà à jour.'}
        staged = _download_update_exe(release, asset)
        script, current_exe, log = _write_update_helper(staged)
        subprocess.Popen(
            [
                'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(script),
                '-ParentPid', str(os.getpid()),
                '-CurrentExe', str(current_exe),
                '-NewExe', str(staged),
                '-LogPath', str(log),
                '-ExpectedBuild', latest_tag,
            ],
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        threading.Timer(1.5, _exit_for_update).start()
        return {'ok': True, 'updated': True, 'restarting': True, 'latest_build': latest_tag}
    finally:
        _update_lock.release()


def _style_catalog():
    try:
        return json.loads((WEB / 'styles.json').read_text(encoding='utf-8'))
    except Exception:
        return []


def _explicit_style(prompt):
    text = prompt or ''
    for style_id, pattern in _STYLE_PATTERNS:
        if pattern.search(text):
            return style_id
    return None


def prepare_visual_request(prompt, selected_style='none', negative=None, reserved_profile=None, technical_quality=True):
    if reserved_profile == 'nsfw':
        try:
            from local_app import nsfw_profile
        except ImportError:
            import nsfw_profile
        prepared, neg, style = nsfw_profile.prepare_visual_request(
            prompt, selected_style, negative, technical_quality)
        raw = (prompt or '').strip()
        # The user's own request must remain the first semantic instruction.
        # Keep the profile's existing context, but move it after the raw prompt
        # instead of letting a broad profile prefix dominate composition.
        if raw and not prepared.startswith(raw):
            remainder = prepared
            pos = remainder.find(raw)
            if pos >= 0:
                remainder = (remainder[:pos] + remainder[pos + len(raw):]).strip()
            prepared = raw + (('\n\n' + remainder) if remainder else '')
        fidelity = (
            "Prompt fidelity only: preserve the user's requested viewpoint, framing, "
            "pose, clothing, scene, subject orientation and composition; do not replace "
            "specified details with a generic studio pose."
        )
        prepared += '\n\n' + fidelity
        return prepared, neg, style
    """Preserve the user's request and add only neutral technical quality hints.

    The original prompt is never paraphrased, softened, expanded with age/clothing/
    pose assumptions, or translated into composition instructions. A deliberately
    selected graphic style can still add its visual rendering preset. Technical
    hints only target rendering quality and common diffusion artefacts.
    """
    raw = (prompt or '').strip()
    explicit = _explicit_style(raw)
    # An explicit medium written by the user wins over a stale UI style. We do
    # not append another style prompt in that case: the user's wording is enough.
    effective_style = explicit or (selected_style if selected_style and selected_style != 'none' else None)
    prepared = raw

    if not explicit and effective_style:
        style = next((x for x in _style_catalog() if x.get('id') == effective_style), None)
        if style and style.get('prompt'):
            prepared += '\n\nVisual rendering style only: ' + style['prompt']

    if technical_quality:
        if effective_style == 'photo':
            quality = 'high detail, coherent anatomy, accurate hands, realistic texture, natural lighting, sharp focus, clean edges, low artifacts'
        elif effective_style in ('illustration', 'comic', 'watercolor'):
            quality = 'high detail, coherent anatomy, accurate hands, clean linework, consistent shapes, sharp focus, low artifacts'
        else:
            quality = 'high detail, coherent anatomy, accurate hands, clean edges, sharp focus, consistent shapes, low artifacts'
        prepared += '\n\nTechnical quality only: ' + quality + '.'

    neg = negative
    if technical_quality and not (negative or '').strip():
        neg = 'lowres, blurry, compression artifacts, watermark, unwanted text, malformed hands, fused fingers, extra fingers, missing fingers, extra limbs, duplicate limbs, broken anatomy, rendering artifacts'
    return prepared, neg, effective_style

def http_json(url, method="GET", payload=None, timeout=20, headers=None):
    data = None
    hdr = {"Content-Type": "application/json"}
    if headers:
        hdr.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=hdr, method=method)
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw.decode("utf-8")) if raw else {}

def comfy_get(path):
    return http_json(COMFY + path)

def comfy_post(path, payload):
    return http_json(COMFY + path, "POST", payload, timeout=60)

def _candidate_comfy_roots():
    here = Path(__file__).resolve().parent.parent
    roots = [
        here / "engine" / "ComfyUI",
        here / "ComfyUI",
        DATA / "ComfyUI",
        Path.home() / "ComfyUI",
        Path("D:/IA LOCAL/ComfyUI"),
    ]
    seen = set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key not in seen:
            seen.add(key)
            yield root

def _managed_comfy_vram_args():
    """Use low-VRAM mode automatically only on genuinely constrained NVIDIA GPUs."""
    global _comfy_vram_args_cache
    if _comfy_vram_args_cache is not None:
        return list(_comfy_vram_args_cache)

    mode = os.environ.get("LOCALVISION_COMFY_VRAM_MODE", "auto").strip().lower()
    if mode in ("low", "lowvram"):
        _comfy_vram_args_cache = ("--lowvram",)
        return list(_comfy_vram_args_cache)
    if mode in ("normal", "none", "off", "disabled"):
        _comfy_vram_args_cache = ()
        return []

    args = ()
    if mode in ("", "auto"):
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            probe = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3, check=False,
                creationflags=creationflags,
            )
            totals = [int(line.strip()) for line in probe.stdout.splitlines() if line.strip().isdigit()]
            if totals and totals[0] <= 12288:
                args = ("--lowvram",)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    _comfy_vram_args_cache = args
    return list(args)


def _comfy_command(root):
    # Launch the Python child directly: no BAT wrapper, no frozen EXE recursion.
    launch = ["--listen", HOST, "--port", "8188", "--disable-auto-launch"] + _managed_comfy_vram_args()
    for py, main in ((root / "python_embeded/python.exe", root / "ComfyUI/main.py"),
                     (root / "python_embeded/python.exe", root / "main.py"),
                     (root / ".venv/Scripts/python.exe", root / "main.py"),
                     (root / "venv/Scripts/python.exe", root / "main.py")):
        if py.exists() and main.exists():
            return [str(py), str(main)] + launch, main.parent
    if not getattr(sys, "frozen", False) and (root / "main.py").exists():
        return [sys.executable, str(root / "main.py")] + launch, root
    return None, None


def _comfy_working_dir():
    """Return the ComfyUI directory that the active server actually uses.

    Older builds simply returned the first installation found on disk. On a
    machine with several ComfyUI copies this could install models/custom nodes
    into one tree while requests were sent to another one.
    """
    if _comfy_proc is not None and _comfy_proc.poll() is None and _comfy_cwd:
        return Path(_comfy_cwd)
    online, detail = comfy_online()
    if online and isinstance(detail, dict):
        system = detail.get('system') or {}
        argv = system.get('argv') or []
        if isinstance(argv, list):
            try:
                if '--base-directory' in argv:
                    at = argv.index('--base-directory')
                    base = Path(str(argv[at + 1])).expanduser()
                    if base.is_absolute() and base.exists():
                        return base.resolve()
            except Exception:
                pass
            if argv:
                try:
                    main = Path(str(argv[0])).expanduser()
                    if main.is_absolute() and main.name.lower() == 'main.py' and main.is_file():
                        return main.resolve().parent
                except Exception:
                    pass
    for root in _candidate_comfy_roots():
        cmd, cwd = _comfy_command(root)
        if cmd and cwd:
            return Path(cwd)
    return None


def _general_lora_catalog():
    try:
        rows = json.loads(LORA_CATALOG.read_text(encoding='utf-8'))
    except Exception:
        return []
    local = {x.get('filename') for x in _local_lora_metadata()} if '_local_lora_metadata' in globals() else set()
    result = []
    for item in rows if isinstance(rows, list) else []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row['filename'] = str(row.get('name') or 'lora') + '.safetensors'
        row['installed'] = row['filename'] in local
        row['compatibility'] = row.get('compatibility') or 'Hunyuan Video · compatibilité HY-OmniWeaving non garantie'
        row['source'] = row.get('source') or 'Bjornulf/CivitAI'
        result.append(row)
    return result


def _install_general_lora(lora_id):
    item = next((x for x in _general_lora_catalog() if str(x.get('lora_id')) == str(lora_id)), None)
    if item is None:
        raise ValueError('LoRA absent du catalogue général intégré.')
    cwd = _comfy_working_dir()
    if cwd is None:
        raise RuntimeError('ComfyUI local introuvable.')
    folder = cwd / 'models' / 'loras' / 'LocalVisionAI_catalog' / 'hunyuan_video'
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^\w .()\-]+', '_', str(item.get('name') or 'lora'), flags=re.UNICODE).strip('. ') or 'lora'
    target = folder / (safe_name + '.safetensors')
    if not target.exists():
        part = target.with_suffix(target.suffix + '.part')
        req = Request(str(item['download_url']), headers={'User-Agent':'LocalVisionAI/2.4'})
        try:
            with urlopen(req, timeout=60) as response, part.open('wb') as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            if part.stat().st_size < 1024:
                raise RuntimeError('Téléchargement LoRA incomplet.')
            part.replace(target)
        except Exception:
            try: part.unlink(missing_ok=True)
            except Exception: pass
            raise
    sidecar = target.with_suffix('.json')
    sidecar.write_text(json.dumps({
        'name': item.get('name'),
        'base_model': item.get('base_model'),
        'compatibility': item.get('compatibility'),
        'trained_words': item.get('trained_words') or [],
        'category': item.get('category'),
        'description': item.get('description'),
        'source': item.get('source') or 'Catalogue LocalVisionAI',
        'source_url': item.get('source_url') or item.get('original_model_url') or '',
        'sha256': item.get('sha256') or '',
        'lora_id': item.get('lora_id'),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    rel = target.relative_to(cwd / 'models' / 'loras').as_posix()
    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    restart_required = False
    if comfy_online()[0]:
        info = object_info()
        node = info.get('LoraLoaderModelOnly') or info.get('LoraLoader') or {}
        choices = []
        for section in ('required', 'optional'):
            definition = (node.get('input') or {}).get(section, {}).get('lora_name')
            if definition and isinstance(definition[0], list):
                choices.extend(definition[0])
        if choices and rel not in choices:
            if _restart_owned_comfyui():
                _comfy_info_cache['time'] = 0
                _comfy_info_cache['data'] = {}
            else:
                restart_required = True
    return {'ok': True, 'path': rel, 'restart_required': restart_required}


def _local_lora_metadata():
    """Return metadata for LoRA files already present on this machine."""
    cwd = _comfy_working_dir()
    if cwd is None:
        return []
    root = cwd / 'models' / 'loras'
    if not root.is_dir():
        return []

    catalog = {}
    bjornulf = cwd / 'custom_nodes' / 'Bjornulf_custom_nodes' / 'civitai' / 'parsed_lora_hunyuan_video_loras.json'
    if bjornulf.is_file():
        try:
            for item in json.loads(bjornulf.read_text(encoding='utf-8')):
                name = str(item.get('name') or '').strip()
                if name:
                    catalog[name + '.safetensors'] = item
        except Exception:
            pass

    result = []
    for path in sorted(root.rglob('*.safetensors'), key=lambda p: str(p).lower()):
        try:
            rel = path.relative_to(root).as_posix()
            meta = dict(catalog.get(path.name, {}))
            sidecar = path.with_suffix('.json')
            if sidecar.is_file():
                try:
                    local = json.loads(sidecar.read_text(encoding='utf-8'))
                    if isinstance(local, dict):
                        meta.update(local)
                except Exception:
                    pass
            words = meta.get('trained_words') or meta.get('trigger_words') or []
            if isinstance(words, str):
                words = [x.strip() for x in words.split(',') if x.strip()]
            result.append({
                'name': meta.get('name') or path.stem,
                'filename': path.name,
                'path': rel,
                'size': path.stat().st_size,
                'base_model': meta.get('base_model') or meta.get('compatibility') or '',
                'trained_words': words if isinstance(words, list) else [],
                'source': meta.get('source') or ('Bjornulf/CivitAI' if path.name in catalog else 'local'),
                'category': meta.get('category') or '',
                'description': meta.get('description') or '',
            })
        except OSError:
            continue
    return result


def _apply_lora_stack(api, selections):
    """Insert standard ComfyUI LoraLoader nodes for explicitly selected local LoRAs."""
    if not selections:
        return api
    available = {x['path'] for x in _local_lora_metadata()}
    clean = []
    for raw in selections[:8]:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get('path') or '').replace('\\', '/').strip('/')
        if path not in available:
            raise ValueError('LoRA local introuvable : ' + path)
        strength = float(raw.get('strength', 1.0))
        if not -2.0 <= strength <= 2.0:
            raise ValueError('La force LoRA doit être comprise entre -2 et 2.')
        clean.append((path, strength))
    if not clean:
        return api

    model_source = next(((nid, 0) for nid, n in api.items()
                         if n['class_type'] in ('UNETLoader', 'CheckpointLoaderSimple', 'HYOmniWeavingUNetLoader')), None)
    if model_source is None:
        raise ValueError('Ce workflow ne permet pas encore l’empilement automatique de LoRA.')

    original_ids = list(api)
    model_ref = [model_source[0], model_source[1]]
    first_model_ref = list(model_ref)
    next_id = max([int(x) for x in api if str(x).isdigit()] or [0]) + 1
    omni = api[model_source[0]]['class_type'] == 'HYOmniWeavingUNetLoader'

    if omni:
        for path, strength in clean:
            nid = str(next_id); next_id += 1
            api[nid] = {
                'class_type': 'LoraLoaderModelOnly',
                'inputs': {'model': list(model_ref), 'lora_name': path, 'strength_model': strength},
                '_meta': {'title': 'LocalVisionAI OmniWeaving LoRA · ' + Path(path).stem},
            }
            model_ref = [nid, 0]
        for nid in original_ids:
            node = api[nid]
            for key, value in list(node.get('inputs', {}).items()):
                if value == first_model_ref:
                    node['inputs'][key] = list(model_ref)
        return api

    clip_source = next(((nid, 0) for nid, n in api.items() if n['class_type'] in ('DualCLIPLoader', 'CLIPLoader')), None)
    if clip_source is None:
        raise ValueError('Ce workflow ne permet pas encore l’empilement automatique de LoRA.')
    clip_ref = [clip_source[0], clip_source[1]]
    first_clip_ref = list(clip_ref)
    for path, strength in clean:
        nid = str(next_id); next_id += 1
        api[nid] = {
            'class_type': 'LoraLoader',
            'inputs': {
                'model': list(model_ref),
                'clip': list(clip_ref),
                'lora_name': path,
                'strength_model': strength,
                'strength_clip': strength,
            },
            '_meta': {'title': 'LocalVisionAI LoRA · ' + Path(path).stem},
        }
        model_ref, clip_ref = [nid, 0], [nid, 1]

    for nid in original_ids:
        node = api[nid]
        for key, value in list(node.get('inputs', {}).items()):
            if value == first_model_ref:
                node['inputs'][key] = list(model_ref)
            elif value == first_clip_ref:
                node['inputs'][key] = list(clip_ref)
    return api


def store_comfy_input(name, data):
    cwd = _comfy_working_dir()
    if cwd is None:
        raise RuntimeError("Impossible de localiser le dossier input de ComfyUI pour cette vidéo.")
    folder = cwd / 'input'
    folder.mkdir(parents=True, exist_ok=True)
    original = Path(name or 'input.bin').name
    safe = re.sub(r'[^\w .()\-]', '_', original, flags=re.UNICODE).strip('. ') or 'input.bin'
    filename = 'lva_' + uuid.uuid4().hex + '_' + safe
    target = (folder / filename).resolve()
    if not target.is_relative_to(folder.resolve()):
        raise ValueError('Nom de fichier invalide.')
    target.write_bytes(data)
    return {'name': filename, 'subfolder': '', 'type': 'input'}


def delete_comfy_output(filename, subfolder='', typ='output'):
    if typ != 'output':
        raise ValueError('Seuls les fichiers générés peuvent être supprimés depuis la bibliothèque.')
    cwd = _comfy_working_dir()
    if cwd is None:
        raise RuntimeError('Installation ComfyUI locale introuvable.')
    base = (cwd / 'output').resolve()
    safe_name = Path(filename or '').name
    if not safe_name:
        raise ValueError('Fichier manquant.')
    rel = Path(subfolder or '') / safe_name
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise ValueError('Chemin de sortie invalide.')
    existed = target.is_file()
    if existed:
        target.unlink()
    return existed


def ensure_comfyui(timeout=180):
    global _comfy_proc, _comfy_cwd
    with _comfy_lock:
        if comfy_online()[0]:
            return True
        if _comfy_proc is None or _comfy_proc.poll() is not None:
            for root in _candidate_comfy_roots():
                cmd, cwd = _comfy_command(root)
                if not cmd:
                    continue
                logs = DATA / "logs"
                logs.mkdir(parents=True, exist_ok=True)
                with (logs / "comfy.log").open("ab") as log:
                    _comfy_proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=log, stderr=log,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    _comfy_cwd = Path(cwd)
                break
            else:
                return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if comfy_online()[0]:
                return True
            if _comfy_proc.poll() is not None:
                return False
            time.sleep(.5)
        return False


def comfy_online():
    try:
        data = http_json(COMFY + "/system_stats", timeout=2)
        return True, data
    except Exception as e:
        return False, str(e)

def object_info():
    now = time.time()
    if now - _comfy_info_cache["time"] < 20 and _comfy_info_cache["data"]:
        return _comfy_info_cache["data"]
    try:
        data = comfy_get("/object_info")
        _comfy_info_cache["time"] = now
        _comfy_info_cache["data"] = data
        return data
    except Exception:
        return {}

def scan_workflows():
    out = []
    # Bundled workflows and durable imports use distinct namespaces.
    for base, prefix in ((ROOT, ""), (IMPORTED, "imported/")):
        for p in base.glob("*.json"):
            if p.name in IGNORE_JSON:
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                workflows.validate_document(raw)
                out.append(workflow_card(prefix + p.name, raw))
            except (ValueError, OSError):
                continue
    info = object_info()
    for card in out:
        try:
            wf = load_workflow(card['id'])
            nodes = wf.values() if workflows.is_api(wf) else wf.get('nodes', [])
            models, missing = [], []
            for node in nodes:
                typ = node.get('class_type') or node.get('type')
                if typ in ('Note', 'MarkdownNote') or node.get('mode') in (2,4):
                    continue
                values = list(node.get('inputs', {}).values()) if workflows.is_api(wf) else node.get('widgets_values') or []
                names = [v for v in values if isinstance(v, str) and v.lower().endswith(('.safetensors','.gguf','.ckpt'))]
                models.extend(names)
                if info:
                    if typ not in info:
                        missing.append('Nœud : ' + str(typ))
                    else:
                        choices = []
                        for section in ('required','optional'):
                            for definition in info[typ].get('input', {}).get(section, {}).values():
                                if definition and isinstance(definition[0], list):
                                    choices.extend(definition[0])
                        missing.extend(n for n in names if n not in choices)
            if wf.get('definitions', {}).get('subgraphs'):
                missing.append('Exporter les sous-graphes au format API')
            card.update(models=models, missing=missing, ready=(not missing) if info else None)
        except Exception:
            card.update(models=[], missing=[], ready=None)
    return sorted(out, key=lambda x: x["name"].lower())


def workflow_card(rel, wf):
    name = Path(rel).stem
    low = name.lower()
    if "ltx" in low:
        kind, icon = "video-heavy", "🎞️"
    elif "motion" in low or "vace" in low or "video2video" in low or "video-to-video" in low:
        kind, icon = "motion", "↝"
    elif "video" in low or "wan" in low:
        kind, icon = "video", "🎬"
    elif "retouch" in low or "retouche" in low or "inpaint" in low or "img2img" in low:
        kind, icon = "retouch", "✨"
    else:
        kind, icon = "image", "🖼️"
    return {"id": rel, "name": name, "kind": kind, "icon": icon, "node_count": len(wf.get("nodes", wf)) if isinstance(wf, dict) else 0}

def load_workflow(rel):
    if not isinstance(rel, str):
        raise ValueError("Identifiant de workflow invalide")
    if rel.startswith("imported/"):
        base, name = IMPORTED.resolve(), rel[len("imported/"):]
    else:
        base, name = ROOT.resolve(), rel
    p = (base / name).resolve()
    if p.parent != base or p.suffix.lower() != ".json":
        raise ValueError("Chemin de workflow invalide")
    if not p.is_file():
        raise FileNotFoundError(rel)
    wf = json.loads(p.read_text(encoding="utf-8"))
    workflows.validate_document(wf)
    return wf


def convert_ui_to_api(wf):
    return workflows.to_api(wf, object_info())


def apply_user_inputs(api, prompt="", negative=None, image_ref=None, settings=None, mask_ref=None, video_ref=None):
    return workflows.apply_inputs(api, prompt, negative, image_ref, settings, mask_ref, video_ref)


def comfy_busy():
    state = comfy_get("/queue")
    return bool(state.get("queue_running") or state.get("queue_pending"))


def _free_comfy_if_idle():
    """Unload ComfyUI models only after every queued generation has finished."""
    try:
        state = comfy_get("/queue")
        if state.get("queue_running") or state.get("queue_pending"):
            return False
        comfy_post("/free", {"unload_models": True, "free_memory": True})
        return True
    except Exception:
        return False


def _prepare_chat(body):
    if comfy_online()[0]:
        if comfy_busy():
            raise RuntimeError("Une génération est en cours. Attends sa fin avant de lancer le chat, afin de préserver la mémoire GPU.")
        comfy_post("/free", {"unload_models": True, "free_memory": True})
    messages = body.get("messages") or []
    if not messages:
        raise ValueError("Aucun message à envoyer.")
    return messages


def _ensure_chat_components():
    """Install the local text engine lazily; media generation does not depend on it."""
    status = llm.status()
    if status.get("engine") and status.get("model"):
        return
    from local_app import bootstrap_windows
    previous_progress = bootstrap_windows.PROGRESS
    try:
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        STARTUP.update(state="running", message="Préparation du chat local…", error=None, started_at=time.time())
        if not status.get("engine"):
            bootstrap_windows.ensure_llama()
        if not status.get("model"):
            bootstrap_windows.ensure_model()
        STARTUP.update(state="ready", message="Chat local prêt.", error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state="error", message="Installation du chat à reprendre", error=str(exc), started_at=None)
        raise
    finally:
        bootstrap_windows.PROGRESS = previous_progress


def run_chat(body):
    with _engine_lock:
        _ensure_chat_components()
        messages = _prepare_chat(body)
        return llm.chat(messages, body.get("settings") or {})


def _web_llm_generate(system, context, prompt):
    with _engine_lock:
        _ensure_chat_components()
        return llm.chat([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': 'CURRENT PROJECT FILES:\n' + context + '\n\nREQUEST:\n' + prompt},
        ], {'temperature': 0.35, 'top_p': 0.9, 'max_tokens': 8192})


def _web_store():
    return web_builder.LocalAiWebStore(WEB_PROJECTS, _web_llm_generate)


def _web_preview_root(project_id):
    site = _web_store().project_dir(project_id) / "site"
    if (site / "package.json").is_file():
        for name in ("dist", "build", "out"):
            candidate = site / name
            if (candidate / "index.html").is_file():
                return candidate
    return site


def _web_site_ready(project_id):
    """Only expose external preview/export/inspector after real source is built."""
    store = _web_store()
    store.meta(project_id)
    site = store.project_dir(project_id) / "site"
    base = _web_preview_root(project_id)
    if (site / "package.json").is_file() and base.resolve() == site.resolve():
        return False
    index = base / "index.html"
    if not index.is_file():
        return False
    data = index.read_text(encoding="utf-8", errors="replace")
    return (len(data) >= 100 and
            "La prévisualisation devrait apparaitre ici." not in data)


def run_chat_stream(body):
    with _engine_lock:
        _ensure_chat_components()
        messages = _prepare_chat(body)
        yield from llm.chat_stream(messages, body.get("settings") or {})


def translate_visual_prompt_to_english(text):
    raw = (text or '').strip()
    if not raw:
        return raw
    translated = llm.chat([
        {'role': 'system', 'content': (
            'Translate the following image or video generation prompt faithfully into natural English. '
            'Preserve all requested details, negations, numbers, viewpoint, framing, pose, clothing, '
            'actions, adjectives and proper nouns. Do not add explanations or creative details. '
            'Return only the English translation. If already English, return it unchanged.'
        )},
        {'role': 'user', 'content': raw}
    ], {'temperature': 0.0, 'top_p': 0.1, 'max_tokens': 2048})
    value = (translated or '').strip()
    value = re.sub(r'^(?:translation|english|translated prompt)\\s*:\\s*', '', value, flags=re.I).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    if not value:
        raise RuntimeError("La traduction anglaise du prompt n'a renvoyé aucun texte.")
    return value


def _wait_for_setup(timeout=7200):
    deadline = time.monotonic() + timeout
    while _setup_lock.locked():
        if time.monotonic() >= deadline:
            raise RuntimeError("L’installation des modèles prend trop de temps. Consulte le journal puis réessaie.")
        time.sleep(.25)


def _stop_owned_comfyui():
    global _comfy_proc, _comfy_cwd
    proc = _comfy_proc
    if proc is None or proc.poll() is not None:
        _comfy_proc = None
        _comfy_cwd = None
        return False
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass
    _comfy_proc = None
    _comfy_cwd = None
    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    return True


def _restart_owned_comfyui():
    if not _stop_owned_comfyui():
        return False
    return ensure_comfyui(timeout=180)


OMNIWEAVING_REQUIRED_NODES = {
    'HYOmniWeavingTextEncoderLoader',
    'HYOmniWeavingUNetLoader',
    'HYOmniWeavingVAELoader',
    'HYOmniWeavingTextEncode',
    'HYOmniWeavingConditioning',
    'HYOmniWeavingImagePrep',
    'HYOmniWeavingI2VSemanticImages',
    'HYOmniWeavingReduxVisionEncode',
}


def omniweaving_nodes_loaded(info=None):
    info = object_info() if info is None else info
    return bool(info) and OMNIWEAVING_REQUIRED_NODES.issubset(set(info))


def _ensure_omni_runtime():
    """Load newly installed OmniWeaving custom nodes into the running ComfyUI."""
    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    if omniweaving_nodes_loaded():
        return True
    if _restart_owned_comfyui():
        _comfy_info_cache['time'] = 0
        _comfy_info_cache['data'] = {}
        if omniweaving_nodes_loaded():
            return True
    raise RuntimeError(
        "HY-OmniWeaving est installé sur disque mais le ComfyUI actuellement actif ne l'a pas chargé. "
        "Ferme toute autre instance de ComfyUI, puis relance LocalVisionAI une fois."
    )


def _media_component_for_workflow(current):
    values = ' '.join(str(v).lower() for n in current.values() for v in n.get('inputs', {}).values() if isinstance(v, str))
    if 'hunyuanimage2.1_distilled_fp8_e4m3fn.safetensors' in values:
        return 'isolated-image'
    profile = workflows.profile(current)
    if profile == 'omniweaving-i2v':
        return 'isolated-video-i2v'
    if profile == 'omniweaving-t2v':
        return 'isolated-video'
    if profile == 'sdxl':
        return 'image'
    if profile == 'wan':
        return 'video'
    if profile == 'hunyuanimage21':
        return 'isolated-image'
    if profile == 'hunyuan15-i2v-step':
        return 'isolated-video-i2v'
    return 'isolated-video' if profile == 'hunyuan15' else None


def _preflight_with_media_repair(current):
    try:
        workflows.preflight(current, object_info())
        return
    except ValueError as first_error:
        text = str(first_error)
        component = _media_component_for_workflow(current)
        # Only self-repair missing model/file choices. Structural workflow errors
        # must remain visible instead of triggering unrelated downloads.
        repairable = 'valeur ou fichier indisponible' in text
        if component in ('isolated-video', 'isolated-video-i2v') and 'nœud manquant : HYOmniWeaving' in text:
            repairable = True
        if component is None or not repairable:
            raise

    from local_app import bootstrap_windows
    if not _setup_lock.acquire(blocking=False):
        _wait_for_setup()
        _setup_lock.acquire()
    try:
        labels = {
            'image':'RealVisXL (photo)',
            'video':'Wan 2.1 1.3B (vidéo)',
            'isolated-image':'HunyuanImage 2.1 distilled FP8 (espace isolé)',
            'isolated-video':'HY-OmniWeaving T2V (espace isolé)',
            'isolated-video-i2v':'HY-OmniWeaving I2V (espace isolé)',
        }
        label = labels.get(component, component)
        STARTUP.update(state='running', message='Préparation automatique : ' + label, error=None, started_at=time.time())
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        # Safe to call even after another setup just finished: existing files are
        # detected immediately, while a genuinely missing file is downloaded.
        bootstrap_windows.ensure_media(component)
        _comfy_info_cache['time'] = 0
        _comfy_info_cache['data'] = {}
        if component in ('isolated-video', 'isolated-video-i2v'):
            _ensure_omni_runtime()
        STARTUP.update(state='ready', message='Modèles média prêts.', error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state='error', message='Installation à reprendre', error=str(exc), started_at=None)
        raise
    finally:
        _setup_lock.release()

    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    workflows.preflight(current, object_info())


def run_generation(body):
    # The first photo request can arrive while the automatic SDXL download is
    # still running. Wait for it instead of failing and forcing a second click.
    _wait_for_setup()
    with _engine_lock:
        if not ensure_comfyui(timeout=180):
            raise RuntimeError("ComfyUI n’est pas prêt. Consulte l’état d’installation et le journal comfy.log, puis utilise Réessayer.")
        wf = load_workflow(body.get("workflow"))
        api = convert_ui_to_api(wf)
        if not api:
            raise ValueError("Workflow vide ou non convertible")
        requires_image = any(n['class_type'] == 'LoadImage' for n in api.values())
        requires_mask = any(n['class_type'] == 'LoadImageMask' for n in api.values())
        requires_video = any(n['class_type'] == 'LoadVideo' for n in api.values())
        if requires_image and not body.get('image'):
            raise ValueError("Ajoute une image de référence avec le bouton +.")
        if requires_mask and not body.get('mask'):
            raise ValueError("Ouvre le masque et peins la zone à retoucher.")
        if requires_video and not body.get('video'):
            raise ValueError("Ajoute une vidéo de référence avec le bouton vidéo.")
        image_ref = mask_ref = video_ref = None
        if body.get('image'):
            data = base64.b64decode(body['image'].split(',', 1)[-1], validate=True)
            image_ref = upload_image('lva_' + uuid.uuid4().hex + '_' + Path(body.get('image_name') or 'input.png').name, data)
        if body.get('mask'):
            data = base64.b64decode(body['mask'].split(',', 1)[-1], validate=True)
            mask_ref = upload_image('lva_mask_' + uuid.uuid4().hex + '.png', data)
        if body.get('video'):
            data = base64.b64decode(body['video'].split(',', 1)[-1], validate=True)
            video_ref = store_comfy_input(Path(body.get('video_name') or 'reference.mp4').name, data)
        settings = body.get('settings') or {}
        source_prompt = (body.get('prompt') or '').strip()
        source_negative = body.get('negative')
        if settings.get('prompt_translation'):
            _ensure_chat_components()
            try:
                prepared_prompt = translate_visual_prompt_to_english(source_prompt)
                prepared_negative = translate_visual_prompt_to_english(source_negative) if isinstance(source_negative, str) and source_negative.strip() else source_negative
            finally:
                llm.stop_server()
        else:
            prepared_prompt = source_prompt
            prepared_negative = source_negative
        if settings.get('exact_prompt'):
            prompt = prepared_prompt
            negative = prepared_negative
            effective_style = None
        else:
            prompt, negative, effective_style = prepare_visual_request(
                prepared_prompt, settings.get('style'), prepared_negative, settings.get('reserved_profile'), settings.get('technical_quality', True))
        count = max(1, min(int(settings.get('count') or 1), 4))
        base_seed = settings.get('seed')
        prepared = []
        for index in range(count):
            current = json.loads(json.dumps(api))
            run_settings = dict(settings)
            if base_seed is None:
                run_settings['seed'] = uuid.uuid4().int % 2147483647
            else:
                run_settings['seed'] = int(base_seed) + (0 if settings.get('keepSeed') else index)
            current = apply_user_inputs(current, prompt, negative, image_ref, run_settings, mask_ref, video_ref)
            current = _apply_lora_stack(current, run_settings.get('loras') or [])
            _preflight_with_media_repair(current)
            prepared.append(current)
        # Only the subprocess created by this application may be stopped.
        llm.stop_server()
        results, warnings = [], []
        if llm.online()[0]:
            warnings.append("Un serveur texte externe reste actif ; sa mémoire GPU ne peut pas être libérée par cette application.")
        for current in prepared:
            try:
                result = queue_prompt(current)
                if not result.get('prompt_id'):
                    raise RuntimeError(json.dumps(result, ensure_ascii=False))
                results.append(result)
            except Exception as exc:
                if not results:
                    raise
                warnings.append("Seule une partie du lot a été acceptée : " + str(exc))
                break
        ids = [x['prompt_id'] for x in results]
        return {'ok': True, 'prompt_id': ids[0], 'prompt_ids': ids, 'warnings': warnings}



def _web_generate_image_asset(project_id, prompt):
    prompt = str(prompt or '').strip()
    if not prompt:
        raise ValueError("Décris l'image à générer.")
    preferred = os.getenv("LOCALAIWEB_IMAGE_WORKFLOW", "").strip()
    # An imported FLUX.2 Klein T2I workflow is discovered automatically, but
    # an explicitly chosen workflow takes priority. SDXL always remains fallback.
    if not preferred:
        for file in sorted(IMPORTED.glob("*.json")):
            label = file.stem.lower().replace("_", "").replace("-", "")
            if "flux" in label and "klein" in label and any(x in label for x in ("text", "t2i", "image")):
                preferred = "imported/" + file.name
                break
    workflows_to_try = [preferred, 'text to image sdxl.json'] if preferred else ['text to image sdxl.json']
    result = None
    first_error = None
    for workflow_name in workflows_to_try:
        try:
            result = run_generation({
                'workflow': workflow_name,
                'prompt': prompt,
        'settings': {
            'count': 1,
            'quality': 'quality',
            'technical_quality': True,
            'exact_prompt': False,
            'prompt_translation': False,
        }
            })
            break
        except Exception as exc:
            if first_error is None:
                first_error = str(exc)
    if result is None:
        raise RuntimeError("Aucun workflow photo disponible : " + str(first_error or "inconnu"))
    prompt_id = result.get('prompt_id')
    deadline = time.time() + 600
    info = None
    while time.time() < deadline:
        data = history(prompt_id)
        if prompt_id in data:
            info = data[prompt_id]
            break
        if data.get('_missing'):
            raise RuntimeError("La génération d'image a disparu de la file ComfyUI.")
        time.sleep(1.0)
    if info is None:
        raise RuntimeError("Délai dépassé pendant la génération de l'asset.")

    chosen = None
    for output in (info.get('outputs') or {}).values():
        for key in ('images','gifs'):
            rows = output.get(key) or []
            if rows:
                chosen = rows[0]
                break
        if chosen:
            break
    if not chosen:
        raise RuntimeError("ComfyUI n'a renvoyé aucun fichier image exploitable.")

    filename = chosen.get('filename','asset.png')
    subfolder = chosen.get('subfolder','')
    typ = chosen.get('type','output')
    params = f"?filename={quote(filename)}&subfolder={quote(subfolder)}&type={quote(typ)}"
    with urlopen(COMFY + "/view" + params, timeout=60) as response:
        raw = response.read()
        content_type = response.headers.get_content_type() or 'image/png'
    suffix = mimetypes.guess_extension(content_type) or Path(filename).suffix or '.png'
    safe_name = 'ai_' + time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6] + suffix
    store = _web_store()
    target = store.project_dir(project_id) / 'site' / 'assets' / safe_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    meta = store.meta(project_id); meta['updated_at'] = time.time(); store.write_meta(project_id, meta)
    return {'ok': True, 'path': 'assets/' + safe_name, 'size': len(raw), 'prompt_id': prompt_id}


def upload_image(filename, data):
    boundary = "----LocalVisionAI" + uuid.uuid4().hex
    body = bytearray()
    def add_field(name, value):
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode())
    body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode())
    body.extend(data)
    body.extend(f"\r\n".encode())
    add_field("type","input")
    add_field("overwrite","true")
    body.extend(f"--{boundary}--\r\n".encode())
    req = Request(COMFY + "/upload/image", data=bytes(body), headers={"Content-Type":f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def queue_prompt(api):
    return comfy_post("/prompt", {"prompt": api, "client_id": str(uuid.uuid4())})

def history(prompt_id):
    result = comfy_get("/history/" + quote(prompt_id))
    if prompt_id not in result:
        queue = comfy_get('/queue')
        active = queue.get('queue_running', []) + queue.get('queue_pending', [])
        result['_missing'] = not any(len(item)>1 and item[1]==prompt_id for item in active)
    else:
        # Outputs remain on disk; unloading the finished models gives the chat
        # or the next media engine the maximum available GPU memory.
        _free_comfy_if_idle()
    return result

class Handler(BaseHTTPRequestHandler):
    def _write_response(self, raw):
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # WebView/browser navigation can cancel an in-flight localhost
            # request. That is a normal client disconnect, not a server crash.
            return False
        return True

    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self._write_response(raw)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def send_bytes(self, data, content_type="application/octet-stream", status=200):
        try:
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(data)))
            self.end_headers()
            self._write_response(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/ping":
            self.send_json({"app": "LocalVisionAI", "version": VERSION,
                            "build_tag": build_info().get("build_tag")})
            return
        if u.path == "/api/health":
            online, detail = comfy_online()
            media = {'image': {'ready': False}, 'video': {'ready': False}, 'isolated-image': {'ready': False},
                     'isolated-video': {'ready': False}, 'isolated-video-i2v': {'ready': False}}
            try:
                from local_app import bootstrap_windows
                media = {
                    'image': bootstrap_windows.media_status('image'),
                    'video': bootstrap_windows.media_status('video'),
                    'isolated-image': bootstrap_windows.media_status('isolated-image'),
                    'isolated-video': bootstrap_windows.media_status('isolated-video'),
                    'isolated-video-i2v': bootstrap_windows.media_status('isolated-video-i2v')
                }
            except Exception:
                pass
            self.send_json({"online":online,"detail":detail,"url":COMFY,"llm":llm.status(), "startup": dict(STARTUP), "media": media, "version": VERSION})
            return
        if u.path == "/api/update/check":
            try:
                self.send_json(update_status())
            except Exception as e:
                self.send_json({"error": str(e)}, 502)
            return
        if u.path == "/api/update/diagnostics":
            try:
                self.send_json(update_diagnostics())
            except Exception as e:
                self.send_json({"error":str(e)},500)
            return
        if u.path == "/api/logs":
            parts = []
            for name in ("startup.log", "comfy.log", "llm.log"):
                path = DATA / "logs" / name
                if path.is_file():
                    with path.open("rb") as log:
                        log.seek(max(0, path.stat().st_size - 12000))
                        parts.append(name + "\n" + log.read().decode("utf-8", errors="replace"))
            self.send_json({"text": "\n\n".join(parts) or "Aucun journal disponible pour le moment."})
            return
        if u.path == "/api/llm":
            self.send_json(llm.status())
            return
        if u.path == "/api/workflows":
            self.send_json({"workflows":scan_workflows()})
            return
        if u.path == "/api/loras":
            self.send_json({"loras": _local_lora_metadata(), "catalog": _general_lora_catalog()})
            return
        if u.path == "/api/workflow":
            rel = parse_qs(u.query).get("id",[None])[0]
            try: self.send_json({"workflow":load_workflow(rel)})
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path.startswith("/api/history/"):
            pid = u.path.split("/",3)[3]
            try: self.send_json(history(pid))
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path == "/api/view":
            q = parse_qs(u.query)
            try:
                filename=q.get("filename",[""])[0]; sub=q.get("subfolder",[""])[0]; typ=q.get("type",["output"])[0]
                params=f"?filename={quote(filename)}&subfolder={quote(sub)}&type={quote(typ)}"
                with urlopen(COMFY+"/view"+params,timeout=60) as r:
                    self.send_bytes(r.read(),r.headers.get_content_type())
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path == "/api/web/capabilities":
            online, _detail = comfy_online()
            media = {}
            try:
                from local_app import bootstrap_windows
                for component in ("image", "video", "isolated-image", "isolated-video", "isolated-video-i2v"):
                    media[component] = bootstrap_windows.media_status(component)
            except Exception:
                media = {}
            self.send_json({
                "llm": llm.status(),
                "comfy": {"online": online, "url": COMFY},
                "media": media,
                "integrations": integrations_cli.status(),
                "shared_scope": "tools_and_models_only"
            })
            return
        if u.path == "/api/web/generation/status":
            try:
                project_id=parse_qs(u.query).get("id",[""])[0]
                self.send_json(_web_generation_status(project_id))
            except Exception as exc:
                self.send_json({"error":str(exc)},404)
            return
        if u.path == "/api/web/progress":
            project_id = parse_qs(u.query).get("id", [""])[0]
            try:
                _web_store().meta(project_id)
                with _web_progress_lock:
                    result = dict(_web_progress_rows.get(project_id, {"phase":"idle", "detail":"Prêt"}))
                self.send_json(result)
            except Exception as exc:
                self.send_json({"error":str(exc)}, 404)
            return
        if u.path == "/api/web/map/config":
            from local_app import web_google_maps
            self.send_json(web_google_maps.configuration())
            return
        if u.path == "/api/web/map/google/search":
            try:
                from local_app import web_google_maps
                q = parse_qs(u.query).get("q", [""])[0]
                self.send_json(web_google_maps.search(q))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/map/google/place":
            try:
                from local_app import web_google_maps
                place_id = parse_qs(u.query).get("place_id", [""])[0]
                self.send_json(web_google_maps.place_details(place_id))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/map/no-website/france":
            try:
                from local_app import web_map_no_website
                batch=parse_qs(u.query).get("batch",["0"])[0]
                self.send_json(web_map_no_website.france_overview(batch))
            except ValueError as exc:
                self.send_json({"error":str(exc)}, 400)
            except Exception as exc:
                self.send_json({"error":"Service OpenStreetMap indisponible : "+str(exc)}, 503)
            return
        if u.path == "/api/web/map/registry/city":
            try:
                from local_app import web_map_no_website
                params=parse_qs(u.query)
                self.send_json(web_map_no_website.registry_city(
                    params.get("lat",[""])[0],params.get("lon",[""])[0],
                    params.get("zoom",[""])[0]))
            except Exception as exc:
                self.send_json({"error":str(exc)},503)
            return
        if u.path == "/api/web/map/no-website/nearby":
            try:
                from local_app import web_map_no_website
                params=parse_qs(u.query)
                self.send_json(web_map_no_website.area_details(
                    params.get("lat", [""])[0],
                    params.get("lon", [""])[0],
                    params.get("zoom", [""])[0]))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 503)
            return
        if u.path == "/api/web/map/no-website/viewport":
            try:
                from local_app import web_map_no_website
                params=parse_qs(u.query)
                self.send_json(web_map_no_website.viewport_details(
                    params.get("south", [""])[0],
                    params.get("west", [""])[0],
                    params.get("north", [""])[0],
                    params.get("east", [""])[0],
                    params.get("zoom", [""])[0]))
            except ValueError as exc:
                self.send_json({"error":str(exc)}, 400)
            except Exception as exc:
                self.send_json({"error":str(exc)}, 503)
            return
        if u.path == "/api/web/map/categories":
            from local_app import web_business_categories
            self.send_json(web_business_categories.catalog())
            return
        if u.path == "/api/web/map/profile":
            try:
                from local_app import web_business_map, web_business_registry
                token=parse_qs(u.query).get("selection_token",[""])[0]
                business=web_business_map.selected_business(token)
                result=web_business_registry.professional_profile(business)
                if result.get("matched"):
                    web_business_map.attach_professional_profile(token,result)
                self.send_json({"profile":result})
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/map/search":
            try:
                from local_app import web_business_map
                q = parse_qs(u.query).get("q", [""])[0]
                self.send_json(web_business_map.location_or_business_search(q))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/map/nearby":
            try:
                from local_app import web_business_map
                args = parse_qs(u.query)
                self.send_json(web_business_map.nearby_businesses(
                    args.get("lat", [""])[0], args.get("lon", [""])[0],
                    args.get("radius", ["1500"])[0],
                    industry=args.get("industry",["all"])[0]))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/projects":
            self.send_json({"projects": _web_store().list_projects()})
            return
        if u.path == "/api/web/crm/overview":
            try:
                from local_app import web_crm
                self.send_json(web_crm.snapshot(LOCALAIWEB_DATA/"crm",_web_store()))
            except Exception as exc:
                self.send_json({"error":str(exc)},500)
            return
        if u.path == "/api/web/crm/quote/file":
            try:
                from local_app import web_crm
                number=parse_qs(u.query).get("number",[""])[0]
                path=web_crm.quote_file(LOCALAIWEB_DATA/"crm",number)
                self.send_bytes(path.read_bytes(),"application/pdf")
            except Exception as exc:
                self.send_json({"error":str(exc)},404)
            return
        if u.path == "/api/web/project/thumbnail":
            try:
                project_id = parse_qs(u.query).get("id", [""])[0]
                store = _web_store()
                store.meta(project_id)
                image = store.project_dir(project_id) / "site" / ".localaiweb-qa" / "ordinateur.png"
                if not image.is_file():
                    self.send_response(404); self.end_headers(); return
                self.send_bytes(image.read_bytes(), "image/png")
            except Exception as e:
                self.send_json({"error": str(e)}, 404)
            return
        if u.path == "/api/web/preview/status":
            try:
                project_id = parse_qs(u.query).get("id", [""])[0]
                ready = _web_site_ready(project_id)
                self.send_json({"ready": ready, "url": (
                    "/web-preview/" + web_builder.safe_id(project_id) + "/index.html" if ready else None)})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/sales/estimate":
            try:
                from local_app import web_sales_invoice
                pid=parse_qs(u.query).get("id",[""])[0]
                self.send_json(web_sales_invoice.estimate(_web_store(),pid))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/invoice/file":
            try:
                import re
                number=parse_qs(u.query).get("number",[""])[0]
                if not re.fullmatch(r"FORMA-\d{4}-\d{5}",number):
                    raise ValueError("Numéro de facture invalide.")
                path=LOCALAIWEB_DATA/"invoices"/(number+".pdf")
                if not path.is_file():raise FileNotFoundError("Facture introuvable.")
                self.send_bytes(path.read_bytes(),"application/pdf")
            except Exception as exc:
                self.send_json({"error":str(exc)},404)
            return
        if u.path == "/api/web/project":
            try:
                project_id = parse_qs(u.query).get("id", [""])[0]
                self.send_json(_web_store().payload(project_id))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/preflight":
            try:
                project_id = parse_qs(u.query).get("id", [""])[0]
                store = _web_store()
                report = store.preflight(project_id)
                syntax = integrations_cli.validate_site(store.project_dir(project_id) / "site")
                report["syntax"] = syntax
                if not syntax.get("ok"):
                    report["ok"] = False
                    report["score"] = min(int(report.get("score") or 0), 79)
                    report.setdefault("blockers", []).append({"id":"javascript_syntax","label":"Syntaxe JavaScript","ok":False,"weight":12})
                    report.setdefault("checks", []).append({"id":"javascript_syntax","label":"Syntaxe JavaScript","ok":False,"weight":12})
                elif syntax.get("node_available"):
                    report.setdefault("checks", []).append({"id":"javascript_syntax","label":"Syntaxe JavaScript","ok":True,"weight":12})
                self.send_json(report)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/export":
            try:
                project_id = parse_qs(u.query).get("id", [""])[0]
                raw = _web_store().export_zip(project_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="LocalAiWeb-' + web_builder.safe_id(project_id) + '.zip"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self._write_response(raw)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path.startswith("/web-preview/"):
            try:
                parts = u.path[len("/web-preview/"):].split("/", 1)
                project_id = web_builder.safe_id(parts[0])
                rel = parts[1] if len(parts) > 1 and parts[1] else "index.html"
                base = _web_preview_root(project_id).resolve()
                target = (base / web_builder.safe_rel(rel)).resolve()
                if not target.is_relative_to(base) or not target.is_file():
                    self.send_response(404); self.end_headers(); return
                self.send_bytes(target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path in ("/localaiweb", "/localaiweb/"):
            p = WEB / "localaiweb-projects.html"
            self.send_bytes(p.read_bytes(), "text/html; charset=utf-8")
            return
        if u.path == "/localaiweb/map":
            p = WEB / "localaiweb-map.html"
            self.send_bytes(p.read_bytes(), "text/html; charset=utf-8")
            return
        if u.path == "/localaiweb/vente":
            p = WEB / "localaiweb-sales.html"
            self.send_bytes(p.read_bytes(), "text/html; charset=utf-8")
            return
        if u.path == "/localaiweb/clients":
            p = WEB / "localaiweb-clients.html"
            self.send_bytes(p.read_bytes(), "text/html; charset=utf-8")
            return
        if u.path == "/localaiweb/editor":
            p = WEB / "localaiweb.html"
            self.send_bytes(p.read_bytes(), "text/html; charset=utf-8")
            return
        if u.path.startswith("/api/asset"):
            # Kept as a stable namespace for future local asset management.
            self.send_json({"ok":True})
            return
        if u.path == "/service-worker.js":
            p = WEB / "service-worker.js"
            self.send_bytes(p.read_bytes(), "application/javascript; charset=utf-8")
            return
        if u.path == "/" or u.path.startswith("/assets/"):
            rel = "index.html" if u.path=="/" else u.path[len("/assets/"):]
            p = (WEB / rel).resolve()
            if not p.is_relative_to(WEB.resolve()) or not p.exists() or not p.is_file():
                self.send_response(404); self.end_headers(); return
            data=p.read_bytes()
            c=mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            self.send_bytes(data,c)
            return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        u=urlparse(self.path)
        length=int(self.headers.get("Content-Length","0"))
        raw=self.rfile.read(length)
        try: body=json.loads(raw.decode())
        except Exception:
            self.send_json({"error":"JSON invalide"},400); return
        if u.path == "/api/web/open-browser":
            try:
                import webbrowser
                pid = body.get("id")
                if not _web_site_ready(pid):
                    raise ValueError("Le site doit être généré avant son ouverture.")
                url = "http://" + HOST + ":" + str(PORT) + (
                    "/web-preview/" + web_builder.safe_id(pid) + "/index.html")
                opened = webbrowser.open_new_tab(url)
                if not opened:
                    raise RuntimeError("Impossible d'ouvrir automatiquement le navigateur.")
                self.send_json({"ok": True, "url": url})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/rename":
            try:
                self.send_json(_web_store().rename_project(body.get("id"), body.get("name")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/duplicate":
            try:
                self.send_json(_web_store().duplicate_project(body.get("id"), body.get("name")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/delete":
            try:
                self.send_json(_web_store().delete_project(body.get("id")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/create-from-map":
            try:
                from local_app import web_business_map
                company = web_business_map.selected_business(body.get("selection_token"))
                store=_web_store()
                payload=store.create_business_project(company)
                # A project must not disappear because CRM indexing fails.
                try:
                    from local_app import web_crm
                    web_crm.attach_business_project(
                        LOCALAIWEB_DATA/"crm",store,payload["project"]["id"],company)
                except Exception as exc:
                    payload["crm_notice"]="Fiche commerciale non synchronisée : "+str(exc)
                self.send_json(payload)
            except Exception as exc:
                self.send_json({"error": str(exc)}, 400)
            return
        if u.path == "/api/web/asset/import-generation":
            try:
                from local_app import web_assets_bridge
                self.send_json(web_assets_bridge.import_generation(
                    _web_store(),_comfy_working_dir(),body.get("project_id"),
                    body.get("filename"),body.get("subfolder",""),
                    body.get("type","output")))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/crm/client/upsert":
            try:
                from local_app import web_crm
                self.send_json(web_crm.upsert_client(
                    LOCALAIWEB_DATA/"crm",_web_store(),body))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/crm/quote/create":
            try:
                from local_app import web_crm
                self.send_json(web_crm.create_quote(
                    LOCALAIWEB_DATA/"crm",_web_store(),body))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/project/pro/authorize":
            try:
                self.send_json(_web_store().authorize_pro_publication(
                    body.get("id"), confirmed=body.get("confirmed") is True))
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/project/auto-claim":
            try:
                result = _web_store().claim_initial_generation(
                    body.get("id"), retry=body.get("retry") is True)
                self.send_json(result)
            except Exception as exc:
                self.send_json({"error":str(exc)}, 400)
            return
        if u.path == "/api/web/invoice/issue":
            try:
                from local_app import web_sales_invoice
                result=web_sales_invoice.issue(
                    _web_store(),body.get("id"),
                    LOCALAIWEB_DATA/"invoices",
                    body.get("seller"),body.get("customer"),
                    body.get("items") or [],
                    accepted=body.get("accepted") is True,
                    service_date=body.get("service_date") or "",
                    due_days=body.get("due_days",30))
                try:
                    from local_app import web_crm
                    web_crm.register_invoice(LOCALAIWEB_DATA/"crm",_web_store(),result)
                    result["crm_indexed"]=True
                except Exception as crm_exc:
                    result["crm_indexed"]=False
                    result["crm_notice"]="Facture émise, mais registre commercial non synchronisé : "+str(crm_exc)
                self.send_json(result)
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/domain/attach":
            try:
                store=_web_store()
                pid=body.get("id")
                meta=store.meta(pid)
                if meta.get("project_kind")=="pro" and not meta.get("business_authorized"):
                    raise ValueError("Domaine officiel interdit avant autorisation de l'entreprise.")
                site=store.project_dir(pid)/"site"
                domain=integrations_cli.vercel_attach_purchased_domain(
                    site,body.get("domain"),body.get("vercel_project"))
                store.update_deployment(pid,{"custom_domain":domain["domain"],
                                            "vercel_target":domain["vercel_project"]})
                self.send_json(domain)
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/project/create":
            try:
                self.send_json(_web_store().create(body.get("name") or "Nouveau projet", body.get("template") or "default"))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/design-profile":
            try:
                from local_app import web_design_profile
                store=_web_store()
                project_id=body.get("id")
                meta=store.meta(project_id)
                if meta.get("project_kind")!="pro":
                    raise ValueError("Cette préparation graphique concerne les projets issus de la carte.")
                profile=web_design_profile.validate(body.get("profile"))
                meta["design_profile"]=profile
                meta["updated_at"]=time.time()
                store.write_meta(project_id,meta)
                self.send_json(store.payload(project_id))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/project/agent-settings":
            try:
                store=_web_store()
                project_id=body.get("id")
                requested=body.get("ai_provider")
                direction=body.get("art_direction")
                if requested is None and direction is None:
                    raise ValueError("Aucun réglage choisi.")
                patch={}
                if requested is not None:
                    if requested not in ("codex","claude"):
                        raise ValueError("Sélectionne Codex (ChatGPT) ou Claude Code.")
                    patch["ai_provider"]=requested
                if direction is not None:
                    if direction not in ("auto","professional","cinematic","spatial3d"):
                        raise ValueError("Direction artistique inconnue.")
                    patch["art_direction"]=direction
                response=store.update_settings(project_id,patch)
                if requested is not None:
                    # Existing projects defaulted silently to Claude before
                    # Codex was chosen. Only an explicit manual switch retains
                    # the alternative on later updates.
                    meta=store.meta(project_id)
                    meta["agent_selected_by_user"]=True
                    store.write_meta(project_id,meta)
                    response=store.payload(project_id)
                self.send_json(response)
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/brief/begin":
            try: self.send_json(_web_store().brief_begin(body.get("id"),body.get("prompt")))
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/web/brief/answer":
            try: self.send_json(_web_store().brief_answer(body.get("id"),body.get("answer")))
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/web/generate/start":
            try:
                self.send_json(_web_start_generation(body.get("id"),body.get("prompt")))
            except Exception as exc:
                self.send_json({"error":str(exc)},400)
            return
        if u.path == "/api/web/generate":
            try:
                from local_app import web_hybrid
                store = _web_store()
                project_id = body.get("id")
                request = str(body.get("prompt") or "").strip()
                if not request:
                    raise ValueError("Décris ton site.")
                _web_progress(project_id, "planning", "Analyse du projet et choix de l'agent…")
                meta = store.meta(project_id)
                settings = meta.get("settings") or {}
                # Codex is the default because the user has ChatGPT Plus.
                # Old projects with an automatically assigned Claude provider
                # migrate on first generation, unless Claude was explicitly
                # chosen afterwards. All project files remain untouched.
                provider = str(settings.get("ai_provider") or "codex")
                if provider == "claude" and not meta.get("agent_selected_by_user", False):
                    provider = "codex"
                    settings = dict(settings)
                    settings["ai_provider"] = provider
                    meta["settings"] = settings
                    store.write_meta(project_id,meta)
                # Starting a site must not synchronously probe unrelated
                # Vercel, Stripe, Supabase or GitHub credentials (minutes).
                available = integrations_cli.coding_agent_status(provider)
                agent_name = web_hybrid.select_coding_agent(
                    provider, available,
                    allow_local_fallback=(os.getenv("LOCALAIWEB_ALLOW_LOCAL_FALLBACK","")
                                          .strip().lower() in ("1","true","yes"))
                )
                # First mockup: do not wait for a 12-GB GPU to produce up to
                # three full-resolution photos before Codex even starts writing
                # the website. Real images can be added in the next iteration.
                from local_app import web_briefing
                first_draft = not _web_site_ready(project_id)
                if first_draft:
                    _web_progress(project_id, "images", "Première maquette rapide : réutilisation des ressources existantes…")
                    visuals = web_hybrid.make_visuals(
                        store, project_id, request, local_generate=None,
                        local_ready=False, defer_new_images=True)
                else:
                    try:
                        from local_app import bootstrap_windows
                        ready_image = (bool(bootstrap_windows.media_status("image").get("ready"))
                                       and comfy_online()[0])
                    except Exception:
                        ready_image = False
                    _web_progress(project_id, "images", "Création ou réutilisation des visuels produits…")
                    visuals = web_hybrid.make_visuals(
                        store, project_id, request, local_generate=_web_generate_image_asset,
                        local_ready=ready_image)
                if agent_name in ("claude", "codex"):
                    if agent_name == "codex" and first_draft:
                        # Single bounded Codex pass. No 15-minute read-only retry
                        # for the very first screen; tell the user if blocked.
                        coder = lambda site, instruction: integrations_cli.codex_apply(
                            site, instruction, timeout=420, allow_retry=False)
                    else:
                        coder = (integrations_cli.claude_apply if agent_name == "claude"
                                 else integrations_cli.codex_apply)
                    payload = web_hybrid.build_with_agent(
                        store, project_id, request, coder, integrations_cli, visuals,
                        progress=lambda phase, detail: _web_progress(project_id, phase, detail),
                        first_preview=first_draft)
                    payload["provider"] = agent_name
                else:
                    # Self-hosted fallback uses the same generated image inventory.
                    _web_progress(project_id, "building", "Génération locale des fichiers du site…")
                    payload = store.generate(
                        project_id, request,
                        agent_context=web_hybrid.developer_brief(request, visuals))
                    payload["provider"] = "local"
                    payload["visuals"] = visuals
                if meta.get("project_kind") == "pro":
                    store.settle_initial_generation(project_id, True)
                _web_progress(project_id, "done", "Création terminée ; site prêt dans l'aperçu.")
                self.send_json(payload)
            except Exception as e:
                _web_progress(body.get("id"), "error", str(e))
                try:
                    if body.get("id"):
                        _web_store().settle_initial_generation(body.get("id"), False, str(e))
                except Exception:
                    pass
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/build":
            try:
                store = _web_store()
                project_id = body.get("id")
                site = store.project_dir(project_id) / "site"
                result = integrations_cli.build_project(site)
                meta = store.meta(project_id)
                meta["updated_at"] = time.time()
                meta["last_build"] = {"time": time.time(), "kind": result.get("kind"), "message": result.get("message")}
                store.write_meta(project_id, meta)
                payload = store.payload(project_id)
                payload["build"] = result
                self.send_json(payload)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/integrations/install":
            try:
                self.send_json(integrations_cli.install_prerequisites())
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/integrations/connect":
            try:
                cwd = None
                if body.get("id"):
                    cwd = _web_store().project_dir(body.get("id")) / "site"
                self.send_json(integrations_cli.connect(body.get("provider"), cwd))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/integrations/status":
            try:
                self.send_json({"ok": True, "integrations": integrations_cli.status(bool(body.get("deep", False)))})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/github/publish":
            try:
                store = _web_store()
                if (store.meta(body.get("id")).get("project_kind") == "pro" and
                        not store.meta(body.get("id")).get("business_authorized")):
                    raise ValueError("Publication Pro interdite sans autorisation de l'entreprise confirmée.")
                site = store.project_dir(body.get("id")) / "site"
                result = integrations_cli.github_publish(site, body.get("repo"), body.get("branch") or "main", body.get("private", True))
                self.send_json(result)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/github/pull":
            try:
                store = _web_store()
                project_id = body.get("id")
                site = store.project_dir(project_id) / "site"
                store.snapshot(project_id, "Avant synchronisation GitHub")
                result = integrations_cli.github_pull(site, body.get("branch") or "main")
                meta = store.meta(project_id); meta["updated_at"] = time.time(); store.write_meta(project_id, meta)
                payload = store.payload(project_id); payload["git"] = result
                self.send_json(payload)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/codex/apply":
            try:
                store = _web_store()
                project_id = body.get("id")
                site = store.project_dir(project_id) / "site"
                store.append_chat(project_id, "user", body.get("prompt"))
                store.snapshot(project_id, "Avant modification Codex")
                result = integrations_cli.codex_apply(site, web_builder.generation_direction(store.meta(project_id).get("settings")) + "\n\nUser request: " + str(body.get("prompt") or ""))
                meta = store.meta(project_id); meta["updated_at"] = time.time(); meta["last_summary"] = result.get("summary","Codex")
                store.write_meta(project_id, meta)
                store.append_chat(project_id, "assistant", meta["last_summary"])
                payload = store.payload(project_id); payload["codex"] = result
                self.send_json(payload)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/vercel/publish":
            try:
                store = _web_store()
                project_id = body.get("id")
                if (store.meta(project_id).get("project_kind") == "pro" and
                        not store.meta(project_id).get("business_authorized")):
                    raise ValueError("Publication Pro interdite sans autorisation de l'entreprise confirmée.")
                qa = (store.meta(project_id).get("last_agent_quality") or {})
                if qa and (qa.get("ok") is False or qa.get("visual") == "failed"):
                    raise ValueError(
                        "Publication suspendue : la dernière génération contient encore "
                        "des défauts. Demande au chat de corriger le site avant de le publier.")
                site = store.project_dir(project_id) / "site"
                production = bool(body.get("production", True))
                result = integrations_cli.vercel_publish(site, production)
                if result.get("url"):
                    patch = {"last_deployed_at": time.time()}
                    patch["production_url" if production else "preview_url"] = result["url"]
                    store.update_deployment(project_id, patch)
                payload = store.payload(project_id)
                payload["deployment_result"] = result
                self.send_json(payload)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/vercel/env":
            try:
                store = _web_store()
                site = store.project_dir(body.get("id")) / "site"
                self.send_json(integrations_cli.vercel_add_env(site, body.get("name"), body.get("environment") or "production"))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/vercel/domain":
            try:
                store = _web_store()
                project_id = body.get("id")
                site = store.project_dir(project_id) / "site"
                result = integrations_cli.vercel_add_domain(site, body.get("domain"))
                store.update_deployment(project_id, {"custom_domain": body.get("domain") or ""})
                payload = store.payload(project_id); payload["domain_result"] = result
                self.send_json(payload)
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/supabase/link":
            try:
                store = _web_store()
                site = store.project_dir(body.get("id")) / "site"
                self.send_json(integrations_cli.supabase_link(site, body.get("project_ref")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/supabase/push":
            try:
                store = _web_store()
                site = store.project_dir(body.get("id")) / "site"
                self.send_json(integrations_cli.supabase_db_push(site))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/supabase/init":
            try:
                store = _web_store()
                site = store.project_dir(body.get("id")) / "site"
                self.send_json(integrations_cli.supabase_initialize(site))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/design":
            try:
                self.send_json(_web_store().apply_design(body.get("id"), body.get("design") or {}))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/deployment":
            try:
                self.send_json(_web_store().update_deployment(body.get("id"), body.get("deployment") or {}))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/settings":
            try:
                self.send_json(_web_store().update_settings(body.get("id"), body.get("settings") or {}))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/file/delete":
            try:
                self.send_json(_web_store().delete_file(body.get("id"), body.get("path")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/file/rename":
            try:
                self.send_json(_web_store().rename_file(body.get("id"), body.get("old_path"), body.get("new_path")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/file/save":
            try:
                store = _web_store(); pid = body.get("id"); path = web_builder.safe_rel(body.get("path"))
                if body.get("snapshot", True):
                    store.snapshot(pid, "Avant édition de " + str(path))
                files = store.write_files(pid, {path.as_posix(): body.get("content", "")}, replace=False)
                meta = store.meta(pid); meta["updated_at"] = time.time(); store.write_meta(pid, meta)
                self.send_json({"ok": True, "files": files, "versions": store.versions(pid)})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/project/replace":
            try:
                store = _web_store(); pid = body.get("id"); store.snapshot(pid, "Avant remplacement")
                files = store.write_files(pid, body.get("files") or {}, replace=True)
                meta = store.meta(pid); meta["updated_at"] = time.time(); store.write_meta(pid, meta)
                self.send_json({"ok": True, "files": files, "versions": store.versions(pid)})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/version/restore":
            try:
                self.send_json(_web_store().restore(body.get("id"), body.get("version_id")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/asset/generate":
            try:
                self.send_json(_web_generate_image_asset(body.get("id"), body.get("prompt")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/web/asset":
            try:
                self.send_json(_web_store().save_asset(body.get("id"), body.get("name"), body.get("data")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/setup":
            if body.get("component", "engines") not in ("engines", "image", "video", "isolated-image", "isolated-video", "isolated-video-i2v"):
                self.send_json({"error": "Composant inconnu"}, 400)
                return
            started = start_setup(body.get("component", "engines"))
            self.send_json({"ok": True, "started": started, "startup": dict(STARTUP)})
            return
        if u.path == "/api/import-workflow":
            try:
                workflows.validate_document(body.get("workflow"))
                name=Path(body.get("name","workflow.json").replace("\\", "/")).name
                name=re.sub(r'[^\w .()-]', '_', name).strip('. ') or 'workflow'
                if not name.lower().endswith(".json"): name += ".json"
                dest=IMPORTED / (uuid.uuid4().hex[:8] + "_" + name)
                dest.write_text(json.dumps(body["workflow"],ensure_ascii=False,indent=2),encoding="utf-8")
                self.send_json({"ok":True,"id":"imported/" + dest.name})
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/update/install":
            try:
                self.send_json(install_latest_update())
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/upload":
            try:
                b64=body["data"].split(",",1)[-1]
                result=upload_image(Path(body.get("name","input.png")).name,base64.b64decode(b64))
                self.send_json({"ok":True,"file":result})
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path == "/api/loras/install":
            try:
                self.send_json(_install_general_lora(body.get('lora_id')))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/delete-output":
            try:
                deleted = delete_comfy_output(body.get('filename',''), body.get('subfolder',''), body.get('type','output'))
                self.send_json({"ok": True, "deleted": deleted})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/chat/stop":
            llm.cancel_chat()
            self.send_json({"ok": True})
            return
        if u.path == "/api/chat/stream":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-transform")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                self.wfile.write(b'{"ready":true}\n')
                self.wfile.flush()
                for chunk in run_chat_stream(body):
                    self.wfile.write((json.dumps({"delta": chunk}, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b'{"done":true}\n')
                self.wfile.flush()
            except Exception as e:
                try:
                    self.wfile.write((json.dumps({"error": str(e)}, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass
            return
        if u.path == "/api/chat":
            try:
                answer = run_chat(body)
                self.send_json({"ok":True,"message":answer})
            except HTTPError as e:
                try: detail=e.read().decode()
                except: detail=str(e)
                self.send_json({"error":detail},502)
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/generate":
            try:
                self.send_json(run_generation(body))
            except HTTPError as e:
                try: detail=e.read().decode()
                except: detail=str(e)
                self.send_json({"error":detail},502)
            except Exception as e:
                self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/interrupt":
            try: self.send_json(comfy_post("/interrupt","{}" if False else {}))
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        self.send_response(404); self.end_headers()

def _setup_worker(component):
    try:
        from local_app import bootstrap_windows
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        STARTUP.update(state="running", message="Préparation des composants…", error=None, started_at=time.time())
        if component == "engines":
            # Attempt components independently: a text download must not prevent
            # an already installed image engine from working (or vice versa).
            errors = []
            for label, action in (("ComfyUI", bootstrap_windows.ensure_comfy),
                                  ("RealVisXL image", lambda: bootstrap_windows.ensure_media('image')),
                                  ("llama.cpp / Qwen chat", lambda: (
                                      bootstrap_windows.ensure_llama(),
                                      bootstrap_windows.ensure_model()))):
                STARTUP['message'] = "Installation / vérification : " + label
                try:
                    action()
                    if label == "ComfyUI" and not ensure_comfyui():
                        raise RuntimeError("ComfyUI ne démarre pas ; consulte logs/comfy.log.")
                    if label == "RealVisXL image":
                        _comfy_info_cache['time'] = 0
                        _comfy_info_cache['data'] = {}
                    if label == "llama.cpp / Qwen chat":
                        # The existing model is reused; no blind replacement.
                        # Starting the model is best effort and can take a while.
                        from local_app import llm
                        if not llm._ensure_server(timeout=120):
                            raise RuntimeError("Qwen n'a pas démarré. Consulte logs/llm.log.")
                except Exception as exc:
                    errors.append(label + " : " + str(exc))
            if errors:
                raise RuntimeError("\n".join(errors))
        else:
            STARTUP['message'] = "Téléchargement des modèles " + (
                "photo (RealVisXL)" if component == 'image'
                else "photo isolée (HunyuanImage 2.1)" if component == 'isolated-image'
                else "vidéo isolée T2V (HY-OmniWeaving)" if component == 'isolated-video'
                else "vidéo isolée I2V (HY-OmniWeaving)" if component == 'isolated-video-i2v'
                else "vidéo (Wan 2.1)")
            bootstrap_windows.ensure_media(component)
            _comfy_info_cache['time'] = 0
            _comfy_info_cache['data'] = {}
            if component in ('isolated-video', 'isolated-video-i2v'):
                if not ensure_comfyui():
                    raise RuntimeError("ComfyUI ne démarre pas ; consulte logs/comfy.log.")
                _ensure_omni_runtime()
        STARTUP.update(state="ready", message="Moteur média prêt. Le chat local sera préparé seulement à sa première utilisation.", error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state="error", message="Installation à reprendre", error=str(exc), started_at=None)
        print("[LocalVisionAI]", exc, flush=True)
    finally:
        _setup_lock.release()
        if component == "engines":
            try:
                bootstrap_windows.cleanup_obsolete_media()
            except Exception:
                pass


def start_setup(component="engines"):
    if not _setup_lock.acquire(blocking=False):
        return False
    STARTUP.update(state="running", message="Préparation…", error=None, started_at=time.time())
    threading.Thread(target=_setup_worker, args=(component,), daemon=True).start()
    return True


def stop_engines():
    llm.stop_server()
    proc = _comfy_proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    print(f"LocalVisionAI -> http://{HOST}:{PORT}", flush=True)
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    if os.environ.get('LOCALVISIONAI_SKIP_SETUP') != '1':
        start_setup()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        stop_engines()


if __name__=="__main__":
    main()
