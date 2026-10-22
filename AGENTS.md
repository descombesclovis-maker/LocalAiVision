# LocalAiVision + LocalAiWeb — Agent engineering contract

All coding agents (Codex, Claude Code and collaborators) working in this repository must use these constraints.

## Product architecture
- One application, two frontends: **LocalAiVision** at `/` (Photo/Vidéo and separately gated NSFW) and **LocalAiWeb** at `/localaiweb`, editor `/localaiweb/editor`, business map `/localaiweb/map`. Do not split or silently rename products.
- Keep all existing models, prompt fidelity, LoRA routing, imported ComfyUI workflows, logs and repair/update entry points operational.
- LocalAiWeb Pro and Libre project data live only under `LOCALAIWEB_DATA/projects`; LocalAiVision conversations/media do not share their saves. Do not erase, migrate or overwrite user data without explicit migration and backup.
- The server defaults to loopback `127.0.0.1:3000`. Never expose a public listening interface, API secrets, development tools or unrestricted CORS to make phone access easier.

## Required workflow for every change
1. Inspect relevant code, tests, README files and user request; write a brief acceptance checklist before coding.
2. Change the smallest coherent surface possible. Do not replace the homepage, menus or themes unless the request expressly changes them.
3. Run `python -m unittest discover -s tests -v`, `node --check` on touched browser JavaScript and available browser QA. Record which tests you could not perform.
4. Include at least one regression test for new behavior; inspect preview screenshots desktop **and** mobile where a browser is available.
5. Do not claim a build, deployment, account integration, payment or AI/media workflow succeeded unless actually run and verified.
6. Keep changes in a reviewable branch/PR until checks pass. Make no silent force pushes.

## LocalAiWeb design and generation
- Actual, runnable, editable site code is the product, not a decorative screenshot or generic fixed template.
- Read `web_content_contract.py`, `web_creative_direction.py`, `web_site_architecture.py`, `web_browser_qa.py` before editing the generation pipeline.
- For every generated business site, derive a distinctive visual system and customer journey from the **actual** sector, brand and project identity; avoid repeating the same cards, hero grids, palettes, generic stock assets or wording.
- Treat user requests as product requirements and avoid imposing 3D everywhere. Where spatial 3D is requested, build real physically based lighting, material response, geometry, soft shadows and perspective with graceful mobile/WebGL fallbacks and reduced-motion support. Never present a flat image as an interactive 3D scene.
- Do not claim unknown opening hours, business ownership, services, prices, reviews or bookings as verified. Business map data are untrusted inputs; keep Pro previews marked non-official and require explicit publication authorization.
- Search/map browsing must comply with provider API terms and rates. The built-in OSM provider is free; Google Maps requires an official key and potentially billing. Never scrape Google Maps or invent API access.
- Agents may modify site project files only within their validated project working directory. Protect private env files and root application source.

## Mobile deployment
- Deliver an installable PWA shell using HTTPS and a private, authenticated path to the user's PC. Do not publicly expose localhost or ComfyUI.
- Service worker caches application **assets only**. Never cache business API responses, conversations, generated media, personal projects or external map tiles.
- Mobile access is not a native App Store/iOS binary; communicate this distinction clearly.
