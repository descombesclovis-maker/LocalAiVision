# V2-AD — SANA French prompt fidelity experiment

## Decision

No cloud comparison render was submitted. The original V2-AB run settings and seed are recoverable, but the official ZeroGPU interface does not expose the account's remaining quota. A five-second SANA call reserves up to 75 seconds (`@spaces.GPU(duration=_estimate_duration)`); with the remaining free balance unknown, an additional GPU allocation could not be confirmed quota-safe. No GPU endpoint was called in V2-AD.

## Recovered baseline

Archived artifact: `backend/bench_runs/v2ab/sana_fox_t2v.mp4` (gitignored), SHA-256 `e6fe839931c27248c6ee898a6807568c3f09e6ad2cae6b34170fdac9a893c7a1`.

- French source prompt, verbatim: `Un renard roux court de gauche à droite dans une forêt verte, saute par-dessus une branche tombée, caméra fixe, plan cinématographique large.`
- Model: SANA-Video 2.0 5B 4-step; Space revision at the time and current read-only query both report `488f3c65e771054b0601b20b359b14c434a609ec`.
- Duration profile: 5 seconds, 81 frames, 16 FPS; output 1280x736.
- Seed returned by the Space: `420042`, randomize false.
- RL LoRA scale 0.7; motion score 20; CFG 1.0; four DMD steps; `sana_shift6_dpm` sigma profile.
- V2-AB wall time 17.594 s; engine-reported processing 12.95 s (including scale 4.01 s, prompt encoding 0.36 s, DiT 5.65 s, VAE 1.53 s, GPU→CPU 0.31 s and MP4 encoding 1.07 s). These are the archived measurements, not remeasured in V2-AD.

Current authenticated, non-GPU `engine_status` reports the model ready, T2V only, on the 48-GB (`large`) Space. It does not expose remaining quota. Official ZeroGPU documentation currently lists 5 minutes/day for Free accounts; the account's remaining balance is not queryable through this Space/API. No inference or quota-consuming diagnostic was made.

The archived MP4 was checked structurally in V2-AD: 8,615,216 bytes, MP4 boxes consistent, duration 5.063 s, video track 1280x736. FFmpeg/ffprobe, PyAV and imageio video decoder are unavailable in the current local Python environment, so full frame-by-frame decoding was not repeated. The archived contact sheet contains ten time samples.

## A/B prompt candidates

A — original (unchanged):

> Un renard roux court de gauche à droite dans une forêt verte, saute par-dessus une branche tombée, caméra fixe, plan cinématographique large.

B — experimental clause-level English translation:

> A red fox runs from left to right through a green forest, jumps over a fallen branch, fixed camera, cinematic wide shot.

The translation preserves in order: singular red fox, run, left-to-right direction, green forest, jump over fallen branch, fixed camera, cinematic wide shot. It does **not** add landing, which is not stated in the archived prompt. The mapping is deterministic and phrase-reviewed; it does not use an LLM or add a negative prompt. The original French is retained exactly.

## Implementation and safety

`backend/lib/sana_prompt_preparation.py` provides an experimental, pure parser/translator for the archived reference clauses. Unknown clauses disable the English candidate entirely; the original is always returned verbatim. It is intentionally not wired into `hf_sana.generate`, the Space, or any UI. Thus the production prompt remains French and the English prompt is not automatically selected.

Tests assert the extracted semantic slots and exact clause order, prevent invented landing/objects, and assert fail-closed behavior for unsupported text. These tests demonstrate code-level preservation for the reviewed example only, not that SANA understands either language better.

## Archived visual assessment (not an A/B result)

The ten-sample contact sheet shows an orange tabby cat-like animal, not a fox. The animal stays mostly around/on the fallen trunk; a clear jump, landing, or left-to-right traversal is not demonstrated. The green forest, trunk, fixed composition and cinematic lighting are visible. The frames look detailed, but detail/photorealism does not compensate for the incorrect subject and action. No V2-AD translated-prompt MP4 exists, so no improvement or regression can be claimed.

## Sources

- Official ZeroGPU quotas, GPU sizes, and `@spaces.GPU(duration=...)`: https://huggingface.co/docs/hub/spaces-zerogpu
- Private Space API status and archived V2-AB response: local authenticated `engine_status` plus `backend/bench_runs/v2ab/space_response.json` (no GPU allocation).
- SANA inference settings and prompt conditioning: `spaces/LocalAiStudio-VideoEngine/sana_runtime.py` at the unchanged Space revision above.

## Limitations / next safe experiment

- No translated-prompt GPU render: no A/B visual conclusion.
- Quota balance unknown; do not retry until the user confirms sufficient free quota or Hugging Face exposes a reliable remaining-balance value. Keep the exact seed and inference settings above for a single paired-condition experiment.
- The parser intentionally supports only the archived reference prompt. Any unmatched clause blocks the candidate. It is not a general-purpose French translator.
- A single-seed A/B can reveal an obvious change but cannot establish broad model superiority.
- I2V, prompt translation benefit, and a production-ready fidelity solution remain unvalidated. If the controlled English candidate still misses species/action, investigate a model with stronger semantic/video control rather than layering unvalidated rewrites.
