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
    npx = _which("npx", "npx.cmd")
    vercel_direct = _which("vercel", "vercel.cmd")
    supabase_direct = _which("supabase", "supabase.exe")
    codex_direct = _which("codex", "codex.cmd", "codex.exe")
    out = {
        "git": {"installed": bool(git), "ready": bool(git)},
        "github": {"installed": bool(gh), "ready": False},
        "node": {"installed": bool(node), "ready": bool(node)},
        "npm": {"installed": bool(npm), "ready": bool(npm)},
        "vercel": {"installed": bool(vercel_direct or npx), "ready": False, "via_npx": bool(not vercel_direct and npx)},
        "supabase": {"installed": bool(supabase_direct or npx), "ready": False, "via_npx": bool(not supabase_direct and npx)},
        "codex": {"installed": bool(codex_direct or npx), "ready": False, "via_npx": bool(not codex_direct and npx)},
    }
    if gh:
        out["github"]["ready"] = _run([gh, "auth", "status"], timeout=20).returncode == 0
    if vercel_direct:
        out["vercel"]["ready"] = _run([vercel_direct, "whoami"], timeout=20).returncode == 0
    if supabase_direct:
        out["supabase"]["ready"] = _run([supabase_direct, "projects", "list", "--output", "json"], timeout=30).returncode == 0
    if codex_direct:
        out["codex"]["ready"] = _run([codex_direct, "login", "status"], timeout=20).returncode == 0
    return out

def validate_site(site_dir):
    site = Path(site_dir)
    node = _which("node", "node.exe")
    issues = []
    checked = 0
    if node:
        for path in sorted(site.rglob("*")):
            if checked >= 80:
                break
            if path.is_file() and path.suffix.lower() in (".js", ".mjs", ".cjs"):
                checked += 1
                result = _run([node, "--check", str(path)], cwd=site, timeout=30)
                if result.returncode != 0:
                    issues.append({"file": path.relative_to(site).as_posix(),
                                   "message": (result.stderr or result.stdout or "JavaScript invalide").strip()[:1200]})
    return {"ok": not issues, "checked": checked, "issues": issues, "node_available": bool(node)}

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
        added = _run([git, "remote", "add", "origin", target], cwd=site, timeout=20)
        if added.returncode != 0:
            raise RuntimeError((added.stderr or added.stdout or "remote GitHub impossible").strip())
    elif (remote.stdout or "").strip() != target:
        changed = _run([git, "remote", "set-url", "origin", target], cwd=site, timeout=20)
        if changed.returncode != 0:
            raise RuntimeError((changed.stderr or changed.stdout or "mise à jour du remote impossible").strip())

    exists = _run([gh, "repo", "view", repo, "--json", "nameWithOwner"], cwd=site, timeout=30)
    if exists.returncode != 0:
        create = [gh, "repo", "create", repo, "--private" if private else "--public"]
        made = _run(create, cwd=site, timeout=120)
        if made.returncode != 0:
            raise RuntimeError((made.stderr or made.stdout or "création GitHub impossible").strip())

    _run([git, "add", "-A"], cwd=site, timeout=30)
    state = _run([git, "status", "--porcelain"], cwd=site, timeout=30)
    if (state.stdout or "").strip():
        commit = _run([git, "commit", "-m", "LocalAiWeb: publish project"], cwd=site, timeout=60)
        if commit.returncode != 0:
            raise RuntimeError((commit.stderr or commit.stdout or "commit impossible").strip())
    _run([git, "branch", "-M", branch], cwd=site, timeout=20)
    push = _run([git, "push", "-u", "origin", branch], cwd=site, timeout=180)
    if push.returncode != 0:
        raise RuntimeError((push.stderr or push.stdout or "push impossible").strip())
    return {"ok": True, "repo": repo, "branch": branch, "url": "https://github.com/" + repo}

def github_pull(site_dir, branch="main"):
    git = _which("git", "git.exe")
    if not git:
        raise RuntimeError("Git n'est pas installé.")
    site = Path(site_dir)
    if not (site / ".git").exists():
        raise RuntimeError("Ce projet n'est pas encore relié à GitHub.")
    dirty = _run([git, "status", "--porcelain"], cwd=site, timeout=30)
    if (dirty.stdout or "").strip():
        raise RuntimeError("Le projet contient des modifications locales. Synchronise-les d'abord vers GitHub avant de récupérer les changements distants.")
    result = _run([git, "pull", "--rebase", "origin", str(branch or "main")], cwd=site, timeout=180)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git pull impossible").strip())
    return {"ok": True, "output": (result.stdout or "")[-2000:]}

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

def vercel_add_domain(site_dir, domain):
    cmd = _vercel_cmd()
    if not cmd:
        raise RuntimeError("Vercel CLI n'est pas disponible.")
    domain = str(domain or "").strip().lower()
    if not domain or "." not in domain or any(ch.isspace() for ch in domain):
        raise RuntimeError("Nom de domaine invalide.")
    result = _run(cmd + ["domains", "add", domain], cwd=site_dir, timeout=180)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Ajout du domaine impossible").strip())
    return {"ok": True, "domain": domain, "output": (result.stdout or "")[-2000:]}

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
