# Build 315 — acceptance checklist and audit baseline

## Scope guard

- Start from `fix/studio-314-completion-motion-ui` at `742e34e40e91af0734ed28bfa4842ac3c582c3fc`.
- Keep the Build 314 logos, interface changes, user data formats, workflows and update path.
- Leave the isolated NSFW generation implementation untouched: prompts, samplers, workflow settings, model routing and saved configuration are outside this change. Only shared presentation or resource handling may change when it is explicitly scoped away from `body.nsfw-active`.
- Do not run a generation against the user's models or modify user projects, histories, LoRAs, workflows, credentials or backups.
- Keep the Build 315 branch and pull request in draft for review. Do not merge, release or deploy.

## Acceptance checklist

- [x] Audit the LocalAiWeb brief, direction, architecture, generation, preview, build and recovery path before changing it.
- [ ] Keep changes narrow, preserve project boundaries and the exact original user brief.
- [x] Add regression coverage for preview throttling and scope boundaries.
- [x] Run the full Python suite and Node tests available locally.
- [ ] Complete Chromium/Edge browser QA in Windows CI.
- [ ] Visually inspect real browser captures on desktop and mobile before claiming a visual pass.
- [ ] Compile, start and visually confirm non-blank WebView2 content in the Windows executable CI before claiming Windows validation.
- [ ] Run GPU or ComfyUI benchmarks only where the named hardware and installed models are actually available; report unavailable checks clearly.
- [ ] Compare all derivative graphics with immutable originals and describe any approximation.

## Initial audit, 4 November 2026

- GitHub PR #63 is open and in draft. Its head is `742e34e40e91af0734ed28bfa4842ac3c582c3fc`, with `codex/studio-314-brand-polish` as its base.
- A separate Build 315 branch was created locally from that exact commit. The changes keep their draft pull request targeted at the PR #63 base branch.
- Baseline Python suite: 308 tests, all passing; one Windows-only test skipped on this Linux host.
- The cinematic 3D quality helper tests pass (6 tests), including the 8 FPS media-busy cap.
- Final local baseline after the change: 311 Python tests pass, with one Windows-only skip; 10 Node tests pass. Two touched browser JavaScript files pass `node --check`; `git diff --check` is clean.
- This host reports 9.7 GiB RAM, no `nvidia-smi`, no local ComfyUI at `127.0.0.1:8188`, and no LocalAiStudio server at `127.0.0.1:3000`. It cannot provide an RTX 3060 generation benchmark or a live model-generation example.
- The reference Windows executable run `41740621667` succeeded on the Build 314 commit. That is a reference artifact, not a Build 315 compilation.
- Playwright is available but its Chromium binary is not. Browser QA must be performed in CI or reported unavailable; source-level tests are not a visual pass.

## Known baseline boundary

The existing code already includes project-specific creative direction, multi-page checks, compiled-site checks, optional browser review, persistent generation-status records and recovery messaging, and adaptive 3D quality helpers. Those were present in the audited base; they are not new Build 315 improvements. The new preview cadence gate is limited to the LocalAiWeb editor and cinematic template.
