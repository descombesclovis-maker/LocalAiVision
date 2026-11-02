"""Deterministic experiential checks for Codex / LocalAiWeb output.

The *rendered* browser remains authoritative for visual quality; this gate
catches missing implementation details the language-model prompt alone cannot.
It is deliberately request-aware: a restrained legal firm site need not animate.
"""
from __future__ import annotations
import re
import unicodedata

SOURCE_SUFFIXES=(".html",".css",".jsx",".tsx",".js",".mjs",".ts",".vue",".svelte")
ANIMATION=re.compile(r"\b(?:animations?|anim[ée]e?s?|mouvements?|transitions?|"
                     r"cin[ée]matographi\w*|spectaculair\w*|immersi\w*|"
                     r"parallaxe?|parallax|motion|3d|webgl|gsap)\b",re.I)
STATIC=re.compile(r"\b(?:sans animations?|no animation|aucun mouvement|"
                  r"r[ée]dui\w* animations?|statique seulement)\b",re.I)
REAL_MOTION=re.compile(r"@keyframes\b|\.animate\s*\(|\brequestAnimationFrame\s*\("
                      r"|\b(?:gsap|framer-motion|motion/react|@react-spring)\b",re.I)
ACCESSIBLE_MOTION=re.compile(r"prefers-reduced-motion|matchMedia\s*\(\s*['\"]"
                             r"\(prefers-reduced-motion",re.I)
INTERACTION=re.compile(r":focus-visible\b|:focus\b|onKeyDown\b|"
                       r"onkeydown\b|addEventListener\s*\(\s*['\"]keydown",re.I)


def _plain(value):
    raw=unicodedata.normalize("NFKD",str(value or "").lower())
    return "".join(ch for ch in raw if not unicodedata.combining(ch))


def check(files, request):
    """Find practical shortcomings, returning existing {id, fix} diagnostics."""
    if not isinstance(files,dict):
        return []
    prompt=_plain(request)
    if STATIC.search(prompt) or not ANIMATION.search(prompt):
        return []
    source="\n".join(str(content) for name,content in files.items()
                     if str(name).lower().endswith(SOURCE_SUFFIXES))
    if not source:
        return []
    issues=[]
    if not REAL_MOTION.search(source):
        issues.append({"id":"motion_missing","fix":
            "Le client demande des animations. Implémente une vraie chorégraphie "
            "dans les fichiers CSS/JS (keyframes ou Web Animations, GSAP si justifié), "
            "avec animations de révélation, feedback de clic et transitions discrètes. "
            "Ne te contente pas d'écrire « animé » dans le contenu."})
    if not ACCESSIBLE_MOTION.search(source):
        issues.append({"id":"motion_accessibility","fix":
            "Ajoute @media(prefers-reduced-motion: reduce) et une variante sans mouvement "
            "pour préserver l'accessibilité, l'autonomie et les performances."})
    if not INTERACTION.search(source):
        issues.append({"id":"keyboard_interaction","fix":
            "Les éléments interactifs doivent rester accessibles au clavier : styles "
            ":focus-visible ou équivalents, vrais boutons/liens et aucun piège de focus."})
    return issues
