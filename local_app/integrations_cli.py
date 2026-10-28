import os
import re
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

def _run(args, cwd=None, timeout=120, input_text=None):
    kwargs = {"cwd": str(cwd) if cwd else None, "text": True, "capture_output": True, "timeout": timeout, "check": False}
    if input_text is not None:
        # Keep long Codex prompts out of the Windows command line (CreateProcess
        # has a ~32K-character limit). A stdin pipe also preserves Unicode.
        kwargs["input"] = str(input_text)
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
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


def _claude_cmd():
    # Use an explicitly installed Claude Code CLI. Never npm-install it
    # implicitly during a generation run.
    direct = _which("claude", "claude.cmd", "claude.exe")
    return [direct] if direct else None


def status(deep=False):
    gh = _which("gh", "gh.exe")
    git = _which("git", "git.exe")
    node = _which("node", "node.exe")
    npm = _which("npm", "npm.cmd")
    npx = _which("npx", "npx.cmd")
    vercel_direct = _which("vercel", "vercel.cmd")
    supabase_direct = _which("supabase", "supabase.exe")
    codex_direct = _which("codex", "codex.cmd", "codex.exe")
    claude_direct = _claude_cmd()
    stripe_direct = _which("stripe", "stripe.exe")
    out = {
        "git": {"installed": bool(git), "ready": bool(git)},
        "github": {"installed": bool(gh), "ready": False},
        "node": {"installed": bool(node), "ready": bool(node)},
        "npm": {"installed": bool(npm), "ready": bool(npm)},
        "vercel": {"installed": bool(vercel_direct or npx), "ready": False, "via_npx": bool(not vercel_direct and npx)},
        "supabase": {"installed": bool(supabase_direct or npx), "ready": False, "via_npx": bool(not supabase_direct and npx)},
        "codex": {"installed": bool(codex_direct or npx), "ready": False, "via_npx": bool(not codex_direct and npx)},
        "claude": {"installed": bool(claude_direct), "ready": False},
        "stripe": {"installed": bool(stripe_direct), "ready": False},
    }
    if gh:
        out["github"]["ready"] = _run([gh, "auth", "status"], timeout=20).returncode == 0

    vercel_cmd = [vercel_direct] if vercel_direct else (_vercel_cmd() if deep else None)
    supabase_cmd = [supabase_direct] if supabase_direct else (_supabase_cmd() if deep else None)
    codex_cmd = [codex_direct] if codex_direct else (_codex_cmd() if deep else None)
    if vercel_cmd:
        try:
            out["vercel"]["ready"] = _run(vercel_cmd + ["whoami"], timeout=60 if deep else 20).returncode == 0
        except Exception:
            pass
    if supabase_cmd:
        try:
            out["supabase"]["ready"] = _run(supabase_cmd + ["projects", "list", "--output", "json"], timeout=90 if deep else 30).returncode == 0
        except Exception:
            pass
    if codex_cmd:
        try:
            out["codex"]["ready"] = _run(codex_cmd + ["login", "status"], timeout=60 if deep else 20).returncode == 0
        except Exception:
            pass
    if claude_direct:
        try:
            out["claude"]["ready"] = _run(claude_direct + ["auth", "status"], timeout=20).returncode == 0
        except Exception:
            pass
    if stripe_direct:
        out["stripe"]["ready"] = _run([stripe_direct, "config", "--list"], timeout=20).returncode == 0
    return out

def install_prerequisites():
    if os.name != "nt":
        raise RuntimeError("L'installation automatique des prérequis est prévue pour Windows.")
    winget = _which("winget", "winget.exe")
    if not winget:
        raise RuntimeError("WinGet n'est pas disponible sur ce Windows.")
    packages = []
    if not _which("git", "git.exe"):
        packages.append("Git.Git")
    if not _which("gh", "gh.exe"):
        packages.append("GitHub.cli")
    if not _which("node", "node.exe") or not _which("npx", "npx.cmd"):
        packages.append("OpenJS.NodeJS.LTS")
    if not packages:
        return {"ok": True, "started": False, "message": "Les prérequis principaux sont déjà installés."}
    commands = []
    for package in packages:
        commands.append('"' + winget + '" install --id ' + package + ' --exact --accept-package-agreements --accept-source-agreements')
    command = " && ".join(commands) + " && echo. && echo Installation terminee. Redemarre LocalAiVision si les nouveaux outils ne sont pas encore detectes. && pause"
    subprocess.Popen(["cmd.exe", "/c", command], creationflags=CREATE_NEW_CONSOLE)
    return {"ok": True, "started": True, "packages": packages,
            "message": "Installation des prérequis ouverte dans une fenêtre Windows."}

def build_project(site_dir):
    site = Path(site_dir)
    package = site / "package.json"
    if not package.is_file():
        return {"ok": True, "kind": "static", "output_dir": str(site), "message": "Projet statique : aucun build requis."}
    npm = _which("npm", "npm.cmd")
    if not npm:
        raise RuntimeError("Node.js/npm est requis pour construire ce projet.")
    try:
        config = json.loads(package.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("package.json invalide : " + str(exc)) from None
    scripts = config.get("scripts") or {}
    if "build" not in scripts:
        raise RuntimeError("Ce projet possède package.json mais aucun script npm build.")
    install_args = [npm, "ci"] if (site / "package-lock.json").is_file() else [npm, "install"]
    installed = _run(install_args, cwd=site, timeout=900)
    if installed.returncode != 0:
        raise RuntimeError((installed.stderr or installed.stdout or "npm install impossible").strip()[-5000:])
    build_args = [npm, "run", "build"]
    # Preview is hosted at /web-preview/<project>/; absolute /assets would
    # incorrectly point at the editor's own bundled files.
    if "vite build" in str(scripts.get("build", "")) and "--base" not in str(scripts.get("build", "")):
        build_args += ["--", "--base=./"]
    built = _run(build_args, cwd=site, timeout=900)
    if built.returncode != 0:
        raise RuntimeError((built.stderr or built.stdout or "npm run build impossible").strip()[-5000:])
    candidates = [site / "dist", site / "build", site / "out", site / ".next" / "static"]
    output = next((p for p in candidates if (p / "index.html").is_file()), None)
    if output is None:
        # Some frameworks build server-rendered output. Vercel can still deploy them,
        # but the built-in static preview cannot safely emulate their server runtime.
        return {"ok": True, "kind": "framework", "output_dir": "", "message": "Build réussi. Aperçu statique indisponible pour ce framework.",
                "output": (built.stdout or built.stderr or "")[-4000:]}
    return {"ok": True, "kind": "static-build", "output_dir": str(output),
            "message": "Build terminé.", "output": (built.stdout or built.stderr or "")[-4000:]}

def validate_site(site_dir):
    site = Path(site_dir)
    node = _which("node", "node.exe")
    issues = []
    checked = 0
    if node:
        for path in sorted(site.rglob("*")):
            if checked >= 80:
                break
            if any(part in ("node_modules", ".git", ".next", ".cache") for part in path.relative_to(site).parts):
                continue
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
    elif provider == "stripe":
        stripe = _which("stripe", "stripe.exe")
        if not stripe:
            raise RuntimeError("Stripe CLI n'est pas installé.")
        args = [stripe, "login"]
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

def vercel_add_env(site_dir, name, environment="production"):
    cmd = _vercel_cmd()
    if not cmd:
        raise RuntimeError("Vercel CLI n'est pas disponible.")
    name = str(name or "").strip().upper()
    environment = str(environment or "production").strip().lower()
    if not re.fullmatch(r'[A-Z_][A-Z0-9_]{1,80}', name):
        raise RuntimeError("Nom de variable invalide.")
    if environment not in ("production", "preview", "development"):
        raise RuntimeError("Environnement Vercel invalide.")
    args = cmd + ["env", "add", name, environment]
    subprocess.Popen([str(x) for x in args], cwd=str(site_dir),
                     creationflags=CREATE_NEW_CONSOLE if os.name == "nt" else 0)
    return {"ok": True, "name": name, "environment": environment,
            "message": "Vercel va demander la valeur dans une fenêtre séparée. LocalAiWeb ne lit pas le secret."}

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

def vercel_attach_purchased_domain(site_dir, domain, project_name):
    """Assign an already purchased domain to an explicit linked Vercel project.

    Never buy a domain, change DNS or claim SSL is ready without confirmation.
    """
    cmd = _vercel_cmd()
    if not cmd:
        raise RuntimeError("Vercel CLI indisponible. Connecte-toi à Vercel avant de rattacher le domaine.")
    domain = str(domain or "").lower().strip().rstrip(".")
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        raise ValueError("Nom de domaine non valide.") from None
    import re
    if (len(domain)>253 or not re.fullmatch(
        r"(?=.{4,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",domain)):
        raise ValueError("Utilise un vrai domaine acheté, par exemple exemple.fr.")
    project = str(project_name or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?",project):
        raise ValueError("Indique le nom du projet Vercel auquel rattacher le domaine.")
    result=_run(cmd+["domains","add",domain,project],cwd=site_dir,timeout=180)
    if result.returncode!=0:
        raise RuntimeError((result.stderr or result.stdout or "Ajout impossible")[-1600:])
    inspect=_run(cmd+["domains","inspect",domain],cwd=site_dir,timeout=70)
    return {
        "ok":True,"domain":domain,"vercel_project":project,
        "verification_pending":True,
        "notice":"Le domaine est ajouté à Vercel ; configure les DNS chez le fournisseur du domaine et vérifie HTTPS avant publication officielle.",
        "dns_instructions":(inspect.stdout or inspect.stderr or "")[-2900:],
        "dashboard":"https://vercel.com/dashboard"
    }


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
    """Apply verified Codex edits; recover safely if native Windows sandbox is read-only."""
    import tempfile
    from local_app import web_codex_writeback as writeback

    cmd = _codex_cmd()
    if not cmd:
        raise RuntimeError("Codex CLI n'est pas installé.")
    text = str(prompt or "").strip()
    if not text:
        raise RuntimeError("Prompt Codex vide.")
    site = Path(site_dir).resolve()
    instruction = (
        "Work ONLY inside this website project. Actually create or change website files, "
        "not just describe your ideas. Preserve user assets and existing working features. "
        "Honor brand, design and requested functionality. Build polished production-ready "
        "responsive web pages. Avoid exposing secrets. Request:\n" + text
    )
    before = writeback.snapshot(site)
    # Codex may exit 0 while its Windows workspace is effectively read-only.
    result = _run(cmd + ["exec", "--sandbox", "workspace-write",
                         "--skip-git-repo-check", "-"], cwd=site, timeout=900,
                  input_text=instruction)
    after = writeback.snapshot(site)
    if writeback.changed_app(before, after) and not writeback.placeholder(site):
        if result.returncode != 0:
            raise RuntimeError("Codex a modifié des fichiers mais a signalé une erreur : " +
                               (result.stderr or result.stdout or "")[-1500:])
        return {"ok": True, "summary": "Codex a enregistré les fichiers du site.",
                "files_written": writeback.changed(before, after), "method": "workspace-write"}

    # No actual website was created. Ask for bounded JSON source only, and
    # write it ourselves after validating every destination. Never lift sandbox.
    with tempfile.TemporaryDirectory(prefix="localaiweb-codex-") as folder:
        final = Path(folder) / "files.json"
        request = writeback.structured_prompt(instruction, site)
        retry = _run(cmd + ["exec", "--sandbox", "read-only",
                            "--skip-git-repo-check",
                            "--output-last-message", str(final), "-"],
                     cwd=site, timeout=900, input_text=request)
        if retry.returncode != 0:
            raise RuntimeError(
                "Codex n'a écrit aucun fichier et son second essai a échoué : " +
                (retry.stderr or retry.stdout or "")[-1800:])
        if not final.is_file():
            raise RuntimeError("Codex n'a écrit aucun fichier et n'a pas transmis de projet de secours.")
        written = writeback.apply_bundle(site, final.read_text(encoding="utf-8"))
    if not writeback.changed_app(before, writeback.snapshot(site)) or writeback.placeholder(site):
        raise RuntimeError("Codex a terminé, mais la prévisualisation reste vide. Aucun site complet n'a été créé.")
    return {"ok": True, "summary": "Codex a créé les fichiers du site via l'écriture sécurisée.",
            "files_written": written, "method": "validated-writeback"}

def claude_apply(site_dir, prompt):
    """Claude Code non-interactive authenticated editing, with bounded tool grants."""
    cmd = _claude_cmd()
    if not cmd:
        raise RuntimeError("Claude Code n'est pas installé ou est introuvable dans PATH.")
    text = str(prompt or "").strip()
    if not text:
        raise RuntimeError("La demande Claude est vide.")
    instruction = (
        "You are an expert full-stack developer and visual art director. "
        "Edit ONLY this website project; never alter sibling projects or the application. "
        "Act as a senior creative director, UX architect and full-stack engineer. "
        "First derive a distinct visual concept from the real business, its sector, "
        "audience, products and verified identity; avoid generic Shopify, dashboard "
        "and repetitive hero/card layouts. Respect the user's exact brand colors. "
        "Produce complete real pages, refined typography, cinematic but purposeful "
        "motion, tactile details, polished navigation and responsive interactions. "
        "In the site project document the design intent and meaningful page architecture. "
        "Use legitimate supplied images and assets only; never invent a product photograph "
        "or impersonate official branding. For genuinely appropriate immersive 3D, implement "
        "real Three.js or React Three Fiber geometry, lighting, materials, camera and "
        "WebGL/mobile/reduced-motion fallbacks, not a flat simulated 3D screenshot. "
        "Keep every interaction functional; never fake connected booking, payments or authentication. "
        "Write user-visible content in natural French. After editing, run the available "
        "production build and tests, fix errors and inspect desktop/mobile output where possible. "
        "Never print keys or write secrets to client code. Preserve existing working site features. "
        "Original request:\n" + text
    )
    result = _run(cmd + [
        "-p", "--model", "sonnet", "--permission-mode", "acceptEdits",
        "--allowedTools", "Read", "Edit", "Write", "Bash(npm *)",
        "Bash(npx *)", "Bash(node *)",
        instruction,
    ], cwd=site_dir, timeout=900)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Claude Code n'a pas terminé.").strip()[:4000])
    return {"ok": True, "summary": (result.stdout or "Site modifié par Claude Code.")[-3000:]}
