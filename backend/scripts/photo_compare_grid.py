"""Galerie comparative locale d'un ou plusieurs runs lib.prompt_bench (photo).

Produit, dans --out :
  grid_<label>.png : grille lignes = seeds, colonnes = approches (rendus identiques par seed) ;
  summary.md       : mesures par run et par approche (durée, VRAM, longueur du prompt) ;
  index.html       : page locale reliant grilles, tableau et rendus.

Aucune mesure n'est inventée : seules les valeurs du manifest sont reprises.
Dépendance : Pillow (non présent dans backend/.venv ; utiliser un Python qui l'a,
par ex. le venv de ComfyUI). Usage :
  <python-avec-Pillow> backend/scripts/photo_compare_grid.py \
      --run backend/bench_runs/<run_sdxl> --label sdxl \
      --run backend/bench_runs/<run_flux> --label flux_schnell --out backend/bench_runs/photo_spatial_compare
"""
from __future__ import annotations

import argparse
import html
import json
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

APPROACHES = ["A0_raw", "A_legacy", "B_v2a_balanced", "C_constraint_first"]
CELL = 360
PAD = 40
BOILERPLATE = "Still-image instructions"


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_run(run: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    renders = [r for r in manifest["renders"] if r.get("file") and not r.get("error")]
    return manifest, renders


def build_grid(run: Path, renders: list[dict], out: Path, label: str) -> Path:
    seeds = sorted({int(r["seed"]) for r in renders})
    by_key = {(r["approach"], int(r["seed"])): r for r in renders}
    font = _font(18)
    width = PAD + len(APPROACHES) * CELL
    height = PAD + len(seeds) * (CELL + PAD)
    canvas = Image.new("RGB", (width, height), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    for c, appr in enumerate(APPROACHES):
        draw.text((PAD + c * CELL + 8, 10), appr, fill=(230, 230, 230), font=font)
    for rI, seed in enumerate(seeds):
        y = PAD + rI * (CELL + PAD)
        draw.text((4, y + CELL // 2), f"s{seed}", fill=(230, 230, 230), font=font)
        for c, appr in enumerate(APPROACHES):
            r = by_key.get((appr, seed))
            x = PAD + c * CELL
            if r is None:
                draw.rectangle([x, y, x + CELL - 4, y + CELL - 4], outline=(180, 0, 0), width=3)
                continue
            img = Image.open(run / r["file"]).convert("RGB")
            img.thumbnail((CELL - 4, CELL - 4))
            canvas.paste(img, (x, y))
            draw.text((x + 4, y + CELL - 4 + 2), f"{r.get('duration_s', '?')} s", fill=(200, 200, 200), font=_font(14))
    path = out / f"grid_{label}.png"
    canvas.save(path)
    return path


def metrics(renders: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for appr in APPROACHES:
        rows = [r for r in renders if r["approach"] == appr]
        if not rows:
            continue
        durations = [float(r["duration_s"]) for r in rows if r.get("duration_s") not in (None, "")]
        prompts = [r.get("prompt_sent", "") for r in rows]
        result[appr] = {
            "n": len(rows),
            "duration_mean_s": round(statistics.mean(durations), 1) if durations else None,
            "duration_min_s": min(durations) if durations else None,
            "duration_max_s": max(durations) if durations else None,
            "vram_delta_mib_first": next((r.get("vram_peak_delta_mib") for r in rows if r.get("may_include_model_load")), None),
            "prompt_chars_mean": round(statistics.mean(len(p) for p in prompts)),
            "has_boilerplate": any(BOILERPLATE in p for p in prompts),
            "checkpoint": next(iter(rows[0].get("params", {}).get("CheckpointLoaderSimple", {}).values()), None),
            "steps": rows[0].get("params", {}).get("KSampler", {}).get("steps"),
            "cfg": rows[0].get("params", {}).get("KSampler", {}).get("cfg"),
            "sampler": rows[0].get("params", {}).get("KSampler", {}).get("sampler_name"),
            "resolution": rows[0].get("resolution"),
        }
    return result


def write_summary(runs: list[tuple[str, Path, dict, dict]], out: Path) -> None:
    lines = ["# Comparaison photo — mesures brutes (aucune note subjective)", ""]
    for label, run, manifest, met in runs:
        lines += [f"## {label} — `{run.name}`", "",
                  "| Approche | n | Durée moy. (s) | Min–max (s) | VRAM 1er rendu (MiB) | Prompt (car.) | Boilerplate | Checkpoint | Steps | CFG | Sampler | Résolution |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for appr, m in met.items():
            lines.append(f"| {appr} | {m['n']} | {m['duration_mean_s']} | {m['duration_min_s']}–{m['duration_max_s']} | "
                         f"{m['vram_delta_mib_first']} | {m['prompt_chars_mean']} | {'oui' if m['has_boilerplate'] else 'non'} | "
                         f"{m['checkpoint']} | {m['steps']} | {m['cfg']} | {m['sampler']} | {m['resolution']} |")
        lines += ["", "Note : la 1re génération de chaque run inclut le chargement du modèle ; les durées des autres approches "
                  "ne sont comparables que si elles ne subissent pas de déchargement.", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_index(runs: list[tuple[str, Path, dict, dict]], grids: dict[str, Path], out: Path) -> None:
    parts = ["<!doctype html><meta charset='utf-8'><title>Comparaison photo</title>",
             "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:16px}img{max-width:100%}</style>",
             "<h1>Comparaison photo — cas spatial</h1>",
             "<p>Lignes : seeds identiques entre approches. Colonnes : A0 brut, A historique, B préparation V2-A, C contraintes d'abord.</p>"]
    for label, run, _, _ in runs:
        parts.append(f"<h2>{html.escape(label)}</h2><img src='{html.escape(grids[label].name)}' alt='grille {html.escape(label)}'>")
        parts.append(f"<p>Run : <code>{html.escape(str(run))}</code></p>")
    parts.append("<p>Mesures : <a href='summary.md'>summary.md</a></p>")
    (out / "index.html").write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, type=Path)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    if len(args.run) != len(args.label):
        raise SystemExit("--run et --label doivent être appariés")
    args.out.mkdir(parents=True, exist_ok=True)
    runs, grids = [], {}
    for run, label in zip(args.run, args.label):
        manifest, renders = load_run(run)
        grids[label] = build_grid(run, renders, args.out, label)
        runs.append((label, run, manifest, metrics(renders)))
        print(f"grille {label}: {grids[label]} ({len(renders)} rendus)")
    write_summary(runs, args.out)
    write_index(runs, grids, args.out)
    print(f"summary: {args.out / 'summary.md'}\nindex: {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
