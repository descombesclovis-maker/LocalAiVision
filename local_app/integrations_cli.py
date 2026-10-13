import os
import shutil, subprocess
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

def _which(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None

def _run(args, cwd=None, timeout=120):
    kwargs = {"cwd": str(cwd) if cwd else None, "text": True, "capture_output": True, "timeout": timeout, "check": False}
    if CREATE_NO_WINDOW:
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return subprocess.run([str(x) for x in args], **kwargs)

def _vercel_cmd():
    direct = _which("vercel", "vercel.cmd")
    if direct:
        return [direct]
    npx = _which("npx", "npx.cmd")
    return [npx, "--yes", "vercel@latest"] if npx else None

def _supabase_cmd():
    direct = _which("supabase", "supabase.exe")
    if direct:
        return [direct]
    npx = _which("npx", "npx.cmd")
    return [npx, "--yes", "supabase"] if npx else None

def _codex_cmd():
    direct = _which("codex", "codex.cmd", "codex.exe")
    if direct:
        return [direct]
    npx = _which("npx", "npx.cmd")
    return [npx, "--yes", "@openai/codex"] if npx else None


def status():
    gh = _which("gh", "gh.exe")
    git = _which("git", "git.exe")
    node = _which("node", "node.exe")
    npm = _which("npm", "npm.cmd")
    vercel = _vercel_cmd()
    supabase = _supabase_cmd()
    codex = _codex_cmd()
    out = {
        "git": {"installed": bool(git), "ready": bool(git)},
        "github": {"installed": bool(gh), "ready": False},
        "node": {"installed": bool(node), "ready": bool(node)},
        "npm": {"installed": bool(npm), "ready": bool(npm)},
        "vercel": {"installed": bool(vercel), "ready": False},
        "supabase": {"installed": bool(supabase), "ready": False},
        "codex": {"installed": bool(codex), "ready": False},
    }
    if gh:
        out["github"]["ready"] = _run([gh, "auth", "status"], timeout=20).returncode == 0
    if vercel:
        out["vercel"]["ready"] = _run(vercel + ["whoami"], timeout=45).returncode == 0
    if supabase:
        out["supabase"]["ready"] = _run(supabase + ["projects", "list", "--output", "json"], timeout=60).returncode == 0
    if codex:
        probe = _run(codex + ["login", "status"], timeout=45)
        out["codex"]["ready"] = probe.returncode == 0
    return out

def connect(provider, cwd=None):
    if provider == "github":
        gh = _which("gh", "gh.exe")
        if not gh:
            raise RuntimeError("GitHub CLI n'est pas installé.")
        args = [gh, "auth", "login", "--hostname", "github.com", "--web"]
    elif provider == "vercel":
        cmd = _vercel_cmd()
        if not cmd:
            raise RuntimeError("Vercel CLI n'est pas disponible.")
        args = cmd + ["login"]
    elif provider == "supabase":
        cmd = _supabase_cmd()
        if not cmd:
            raise RuntimeError("Supabase CLI n'est pas disponible.")
        args = cmd + ["login"]
    elif provider == "codex":
        cmd = _codex_cmd()
        if not cmd:
            raise RuntimeError("Codex CLI n'est pas disponible.")
        args = cmd
    else:
        raise ValueError("Intégration inconnue.")
    subprocess.Popen([str(x) for x in args], cwd=str(cwd) if cwd else None,
                     creationflags=CREATE_NEW_CONSOLE if os.name == "nt" else 0)
    return {"ok": True, "provider": provider, "message": "Connexion ouverte dans une fenêtre séparée."}

def github_publish(site_dir, repo, branch="main", private=True):
    gh = _which("gh", "gh.exe")
    git = _which("git", "git.exe")
    if not gh or not git:
        raise RuntimeError("Git et GitHub CLI sont requis.")
    site = Path(site_dir)
    repo = str(repo or "").strip().strip("/")
    if "/" not in repo:
        raise RuntimeError("Dépôt GitHub invalide. Utilise propriétaire/dépôt.")
    branch = str(branch or "main").strip() or "main"
    if not (site / ".git").exists():
        result = _run([git, "init", "-b", branch], cwd=site, timeout=30)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "git init impossible").strip())
    _run([git, "config", "user.name", "LocalAiWeb"], cwd=site, timeout=20)
    _run([git, "config", "user.email", "localaiweb@localhost"], cwd=site, timeout=20)
    remote = _run([git, "remote", "get-url", "origin"], cwd=site, timeout=20)
    target = "https://github.com/" + repo + ".git"
    if remote.returncode != 0:
        _run([git, "remote", "add", "origin", target], cwd=site, timeout=20)
    _run([git, "add", "-A"], cwd=site, timeout=30)
    state = _run([git, "status", "--porcelain"], cwd=site, timeout=30)
    if (state.stdout or "").strip():
        commit = _run([git, "commit", "-m", "LocalAiWeb: publish project"], cwd=site, timeout=60)
        if commit.returncode != 0:
            raise RuntimeError((commit.stderr or commit.stdout or "commit impossible").strip())
    exists = _run([gh, "repo", "view", repo, "--json", "nameWithOwner"], cwd=site, timeout=30)
    if exists.returncode != 0:
        create = [gh, "repo", "create", repo, "--source", ".", "--remote", "origin", "--private" if private else "--public"]
        made = _run(create, cwd=site, timeout=120)
        if made.returncode != 0:
            raise RuntimeError((made.stderr or made.stdout or "création GitHub impossible").strip())
    push = _run([git, "push", "-u", "origin", branch], cwd=site, timeout=180)
    if push.returncode != 0:
        raise RuntimeError((push.stderr or push.stdout or "push impossible").strip())
    return {"ok": True, "repo": repo, "branch": branch, "url": "https://github.com/" + repo}

def vercel_publish(site_dir, production=True):
    cmd = _vercel_cmd()
    if not cmd:
        raise RuntimeError("Vercel CLI n'est pas installé.")
    args = cmd + ["--yes"]
    if production:
        args.append("--prod")
    result = _run(args, cwd=site_dir, timeout=300)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "déploiement Vercel impossible").strip())
    lines = [x.strip() for x in (result.stdout or "").splitlines() if x.strip()]
    url = next((x for x in reversed(lines) if x.startswith("http")), "")
    return {"ok": True, "url": url}

def supabase_initialize(site_dir):
    cmd = _supabase_cmd()
    if not cmd:
        raise RuntimeError("Supabase CLI n'est pas installé.")
    site = Path(site_dir)
    if (site / "supabase" / "config.toml").exists():
        return {"ok": True, "already": True}
    result = _run(cmd + ["init"], cwd=site, timeout=180)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "initialisation Supabase impossible").strip())
    return {"ok": True, "already": False}


def supabase_link(site_dir, project_ref):
    cmd = _supabase_cmd()
    if not cmd:
        raise RuntimeError("Supabase CLI n'est pas disponible.")
    project_ref = str(project_ref or "").strip()
    if not project_ref:
        raise RuntimeError("Référence de projet Supabase manquante.")
    site = Path(site_dir)
    if not (site / "supabase" / "config.toml").exists():
        init = _run(cmd + ["init"], cwd=site, timeout=180)
        if init.returncode != 0:
            raise RuntimeError((init.stderr or init.stdout or "initialisation Supabase impossible").strip())
    result = _run(cmd + ["link", "--project-ref", project_ref], cwd=site, timeout=180)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "liaison Supabase impossible").strip())
    return {"ok": True, "project_ref": project_ref}

def supabase_db_push(site_dir):
    cmd = _supabase_cmd()
    if not cmd:
        raise RuntimeError("Supabase CLI n'est pas disponible.")
    result = _run(cmd + ["db", "push"], cwd=site_dir, timeout=300)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "migration Supabase impossible").strip())
    return {"ok": True, "output": (result.stdout or "")[-2000:]}

def codex_apply(site_dir, prompt):
    cmd = _codex_cmd()
    if not cmd:
        raise RuntimeError("Codex CLI n'est pas installé.")
    text = str(prompt or "").strip()
    if not text:
        raise RuntimeError("Prompt Codex vide.")
    instruction = (
        "Work only inside this website project. Implement the request directly in the files. "
        "Preserve existing user assets and working features. Keep the result polished, responsive, accessible, "
        "semantic and production-ready. Verify obvious syntax problems before finishing. Request: " + text
    )
    result = _run(cmd + ["exec", "--full-auto", instruction], cwd=site_dir, timeout=900)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Codex n'a pas terminé.").strip()[:4000])
    return {"ok": True, "summary": (result.stdout or result.stderr or "Modification Codex terminée.").strip()[-3000:]}
