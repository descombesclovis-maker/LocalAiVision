# V2-AF — LoRA marketing catalogue

## Candidate review

### Shoaibism / SDXL Product Photography

- HF card metadata and pinned revision `304e968eceee596bff14e7f0979868169dac5c08` declare `stabilityai/stable-diffusion-xl-base-1.0`, `apache-2.0`, and SDXL LoRA. README says it was DreamBooth-trained on 20 studio sneaker images and specifies trigger `PRDCT`; its example uses 1024², 25 steps, CFG 7.5. These are author-reported examples, not independent recommendations. No separate LICENSE file was present in the repo; the HF card declares Apache-2.0, so we preserve the attribution/source and do not bundle the weight in the application installer or Git.
- Weight: `pytorch_lora_weights.safetensors`, downloaded only to the user's shared ComfyUI LoRA folder (not the repo); 93,065,304 bytes, SHA-256 `772797c56b396c60e246e3329609c091ba88ea764a7709f31dfce5461da180ba`. Safetensors inspection found 1,120 Diffusers `unet.*` tensors; the installed ComfyUI's LoRA mapper explicitly supports Diffusers UNet keys. Runtime visibility confirmed through `/models/loras`.
- Catalog entry only for SDXL 1.0 image workflow. Trigger is added once to the prompt when selected. Starting strength 1.0; not visually calibrated. It is appropriate to trial for sneaker/product packshots only. It is not evidence for people, other product domains, or video.
- License: Apache-2.0 declared in HF metadata (commercial use and redistribution are generally permitted under its conditions); there is no separately supplied license file. The application does not redistribute this weight.
- No controlled render was made in this sprint: game processes `Windrose` and `RocketLeague` were present on the GPU during resource checks. Do not interpret the author's sample images as our visual proof. Catalog preview remains explicitly pending.

### martintomov / SDXL Advertisement LoRA

- HF metadata/README identify SDXL 1.0 and Diffusers LoRA, a 23.4 MB `pytorch_lora_weights.safetensors`, `openrail`, and instance prompt `advertisement product photography, photorealistic`.
- Not added to active catalogue. The repo had no separate LICENSE file and its OpenRAIL variant/redistribution terms for this exact artifact could not be independently confirmed from the available card/artifact, so commercial-use and weight redistribution clearance are insufficient for this product catalogue. No weight downloaded, no preview used, no generation made. The card's sample prompt is not a LoRA-quality test.

Neither candidate has evidence about person anatomy, hands, faces, or video generation; no people-oriented LoRA was installed. The user's two prioritized candidates were reviewed, but the second is not activated rather than filling the catalogue with unverified weights.

## Comparison mechanism and visual evidence

`backend/lib/lora_comparison.py` provides deterministic cache keys (prompt, model/checkpoint hash, seed, dimensions, steps, CFG, sampler/scheduler, LoRA identity/hash/strength), a manifest contract, and a workflow-pair builder that asserts the sampler inputs are equal and only the treatment graph inserts `LoraLoader`. Frontend cards support paired local comparison assets labelled **SANS LoRA / AVEC LoRA**, but render no placeholder/third-party illustration as a comparison. The cache stays under the caller-provided run directory, not in source control.

There are no V2-AF comparison images yet. The two GPU games found running are left untouched. A proper paired render and visual assessment are therefore pending; quality claims are deliberately withheld.

## Catalog organization and safety

The backend declares two extensible taxonomies: `vision-marketing` (products, luxury, architecture, real estate, food, hospitality, automotive, fashion, cosmetics, websites, headers, professional photography) and `advertising` (product ads, luxury campaigns, people, models, commercial portraits, presenters, automotive, beauty, social, cinematic ads). These are empty category slots, not fictitious LoRA listings. Current verified records use only real jewelry/product entries. Each record has `media_type=image`; future video adapters can be distinguished without allowing this SDXL photo graph to consume them.

No changes to video engines, paid fallbacks, SmartMotion, SANA, Wan, projects, or the V2-Q stash. The weight is user-local and is excluded from Git and distribution.

## Validation

Targeted tests and frontend build results are recorded in `PROGRESS.md` for V2-AF. Chrome validation checks only the catalogue display/selection readiness and pending-comparison label; it does not claim a generated visual result.
