import shutil, subprocess
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

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

def status():
    tools = {
        "git": _which("git", "git.exe"),
        "github": _which("gh", "gh.exe"),
        "node": _which("node", "node.exe"),
        "npm": _which("npm", "npm.cmd"),
        "vercel": _which("vercel", "vercel.cmd"),
        "supabase": _which("supabase", "supabase.exe"),
        "codex": _which("codex", "codex.cmd", "codex.exe"),
    }
    out = {k: {"installed": bool(v), "ready": False} for k,v in tools.items()}
    out["git"]["ready"] = out["git"]["installed"]
    out["node"]["ready"] = out["node"]["installed"]
    out["npm"]["ready"] = out["npm"]["installed"]
    if tools["github"]:
        out["github"]["ready"] = _run([tools["github"], "auth", "status"], timeout=20).returncode == 0
    if tools["vercel"]:
        out["vercel"]["ready"] = _run([tools["vercel"], "whoami"], timeout=30).returncode == 0
    if tools["supabase"]:
        out["supabase"]["ready"] = _run([tools["supabase"], "projects", "list", "--output", "json"], timeout=45).returncode == 0
    if tools["codex"]:
        probe = _run([tools["codex"], "--version"], timeout=20)
        out["codex"]["ready"] = probe.returncode == 0
    return out

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
    cli = _which("vercel", "vercel.cmd")
    if not cli:
        raise RuntimeError("Vercel CLI n'est pas installé.")
    args = [cli, "--yes"]
    if production:
        args.append("--prod")
    result = _run(args, cwd=site_dir, timeout=300)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "déploiement Vercel impossible").strip())
    lines = [x.strip() for x in (result.stdout or "").splitlines() if x.strip()]
    url = next((x for x in reversed(lines) if x.startswith("http")), "")
    return {"ok": True, "url": url}

def supabase_initialize(site_dir):
    cli = _which("supabase", "supabase.exe")
    if not cli:
        raise RuntimeError("Supabase CLI n'est pas installé.")
    site = Path(site_dir)
    if (site / "supabase" / "config.toml").exists():
        return {"ok": True, "already": True}
    result = _run([cli, "init"], cwd=site, timeout=120)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "initialisation Supabase impossible").strip())
    return {"ok": True, "already": False}


def codex_apply(site_dir, prompt):
    cli = _which("codex", "codex.cmd", "codex.exe")
    if not cli:
        raise RuntimeError("Codex CLI n'est pas installé.")
    text = str(prompt or "").strip()
    if not text:
        raise RuntimeError("Prompt Codex vide.")
    instruction = (
        "Work only inside this website project. Implement the request directly in the files. "
        "Preserve existing user assets and working features. Keep the result polished, responsive, accessible, "
        "semantic and production-ready. Verify obvious syntax problems before finishing. Request: " + text
    )
    result = _run([cli, "exec", "--full-auto", instruction], cwd=site_dir, timeout=900)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Codex n'a pas terminé.").strip()[:4000])
    return {"ok": True, "summary": (result.stdout or result.stderr or "Modification Codex terminée.").strip()[-3000:]}
