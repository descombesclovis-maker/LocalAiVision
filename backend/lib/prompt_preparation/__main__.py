"""Read-only JSON diagnostics/comparison: python -m lib.prompt_preparation --help.

No generation or automatic activation. The legacy text must be supplied explicitly.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys

from . import (
    COMFY_IMAGE, COMFY_VIDEO, FidelityMode, LocalAnalyzer, LocalLLMConfig,
    PromptTask, compare_preparations,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="V2-A : comparaison textuelle locale, sans rendu ni activation automatique.")
    parser.add_argument("--prompt-file", type=Path, required=True, help="Prompt utilisateur original (UTF-8).")
    parser.add_argument("--legacy-file", type=Path, required=True, help="Prompt réellement préparé par l'ancien chemin (UTF-8).")
    parser.add_argument("--task", choices=[item.value for item in PromptTask], default="photo")
    parser.add_argument("--mode", choices=[item.value for item in FidelityMode], default="balanced")
    parser.add_argument("--enable", action="store_true", help="Autoriser une analyse LLM locale ; désactivée par défaut.")
    parser.add_argument("--profile", choices=["undeclared", "comfy-image", "comfy-video"], default="undeclared")
    parser.add_argument("--reference", action="store_true", help="Une référence sera fournie au générateur (aucune image n'est lue ici).")
    parser.add_argument("--mask", action="store_true", help="Un masque sera fourni ; rejeté si le profil ne le prend pas en charge.")
    parser.add_argument("--local-kind", choices=["ollama", "openai"], default="ollama")
    parser.add_argument("--local-url", help="Racine loopback du serveur local (Ollama : sans /api/chat ; LM Studio : /v1) ; nécessite --local-model.")
    parser.add_argument("--local-model", help="Modèle DÉJÀ installé ; nécessite --local-url. Aucun téléchargement.")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    if bool(args.local_url) != bool(args.local_model):
        parser.error("--local-url et --local-model doivent être fournis ensemble")
    try:
        # Preserve CRLF, spaces and Unicode exactly, unlike universal-newline read_text().
        original = args.prompt_file.read_bytes().decode("utf-8")
        legacy = args.legacy_file.read_bytes().decode("utf-8")
        analyzer = LocalAnalyzer(LocalLLMConfig(args.local_kind, args.local_url, args.local_model)) if args.local_url else None
        result = asyncio.run(compare_preparations(
            original, legacy, task=args.task, mode=args.mode, enabled=args.enable,
            capabilities={"undeclared": None, "comfy-image": COMFY_IMAGE, "comfy-video": COMFY_VIDEO}[args.profile],
            reference_provided=args.reference, mask_provided=args.mask,
            analyzer=analyzer, timeout=args.timeout,
        ))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
