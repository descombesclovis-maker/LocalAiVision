# LocalAiStudio NextGen — SPEC

Web app (French UI) with two universes, single workspace, no user accounts.

## LocalAiWeb (violet) — AI website generator
- `/web` project library (search, filter Libre/Pro, thumbnails, delete). `/web/p/:id` editor.
- Create: POST /api/projects {prompt, name?, mode libre|pro, llm claude|gpt|gemini, brand_id?, style?} → background pipeline (lib/pipeline.py):
  1 analyse (JSON brief; may pause with status `needs_input` + one question → answered via chat)
  2 architecture (pages + legal pages mentions-legales.html, confidentialite.html)
  3 direction artistique (fonts, palette, image briefs, use_three)
  4 images (Nano Banana libre ×3 / Nano Banana Pro ×5, stored as media source=site)
  5 generation: shared `_head.html`, `_header.html`, `_footer.html`, `styles.css`, `app.js`, `_guide.md`, then each page in parallel. Pages contain `<!--HEAD-->`, `<!--HEADER-->`, `<!--FOOTER-->` placeholders substituted at render.
  6 QA (links, missing pages, node --check JS, missing images, viewport, @media, footer credit "Site web créé par Forma", fonts URL) + targeted LLM SEARCH/REPLACE fix.
- Statuses: queued, generating, editing, ready, error, needs_input. On backend restart in-flight jobs → error, "Reprendre" (POST /retry) resumes from first non-done step.
- Editor: chat (POST /chat — targeted SEARCH/REPLACE edits, new files, deletes; optional selection {page, selector, html} from iframe click; media_ids to embed), preview iframe `/api/preview/{id}/{path}?v=` (same-origin), devices desktop/tablet/mobile, tabs Pages/Ressources/Code (autosave PUT /files → new version)/Versions (restore, undo), ZIP export GET /projects/{id}/export (media rewritten to assets/).
- Every edit/restore/save creates a version snapshot (collection `versions`).

## LocalAiVision (cyan)
- Photos: POST /api/media/images {prompt, model nano-banana|nano-banana-pro, aspect_ratio, ref_media_id?} (background).
- Videos via fal.ai universal key proxy (lib/fal.py): models veo (Veo 3.1 Fast, 4s/6s/8s, 16:9/9:16, audio), kling (2.5 Turbo Pro, 5/10, 16:9/9:16/1:1), minimax (Hailuo 02 standard, 6/10, 16:9). text or image mode (image passed as data URL). Poll status, cancel POST /media/{id}/cancel. 402 → insufficient credits message.
- Library GET /media?kind=; file GET /media/{id}/file (GridFS bucket `mediafs`); upload POST /media/upload {data_url, source upload|ad|logo}.
- Ad workshop: client-side canvas composition (image + brand logo + title + subtitle + CTA, formats 9:16/1:1/16:9) → upload source=ad → "Ajouter à un site" sends chat to project with media_ids.

## Brands
- /marques CRUD /api/brands {name, slogan, colors[], logo_media_id}. Brand injected in pipeline prompts.

## Other
- GET /api/activity → running sites + media (header pill).
- Collections: projects, versions, media, brands, mediafs (GridFS).
- No auth. No real payments/emails in generated sites (demo notices).

## Carte des entreprises (/carte)
- Source: official free API "Recherche d'entreprises" (recherche-entreprises.api.gouv.fr, no key) + API Adresse (geocoding). Proxied by backend (`/api/companies/*`).
- National view: ~25-40 real active companies sampled around each of the 96 metropolitan préfectures (`company_overview` collection, refreshed weekly, built in background). Zoom ≥ 13 → `/api/companies/near` loads all active establishments of the visible area (up to 4×25 companies/page). Leaflet + markercluster on OSM tiles (CSS dark filter).
- Click a dot → CompanyPanel: SIRENE facts (address, legal form, creation, staff, revenue, directors) + computed strengths → "Créer un site pour cette entreprise" → `POST /api/companies/{siren}/site {llm, mode}` builds a sales-argument-oriented prompt and starts the normal pipeline (project gets `company` field).

## Local engines (/moteurs) — default, free
- Text/sites: `llm="local"` (default) → Ollama native `/api/chat` (num_ctx) or OpenAI-compatible server (LM Studio). Settings `settings{id:"local_engine"}`; `/api/settings/local-engine` GET/PUT, `/test`.
- Images/video: ComfyUI (`lib/comfy.py`), settings `settings{id:"comfyui"}`; `/api/settings/comfyui` GET/PUT, `/test`, `/presets`. Built-in workflows (validated against ComfyUI graph validation): FLUX dev/schnell fp8 & SDXL txt2img + img2img; Wan 2.2 TI2V 5B & LTX-Video 2B t2v/i2v (CreateVideo+SaveVideo mp4). Custom API-format workflows with {{PROMPT}} {{NEGATIVE}} {{WIDTH}} {{HEIGHT}} {{SEED}} {{LENGTH}} {{IMAGE}}.
- Image model `comfy` (default) / video model `comfy` (default, durations 3/5 s, 16:9/9:16/1:1). Site pipeline uses ComfyUI images when llm=local (skipped silently if ComfyUI is unreachable).
- Paid engines (Claude/GPT/Gemini, Nano Banana, Veo/Kling/MiniMax) kept as fallback options; emergentintegrations import is optional.
- In the cloud preview the user's PC is unreachable → local engines report "injoignable" clearly. Windows kit: `GET /api/kit/download` zips backend+frontend+`/app/local-kit` (install.ps1, download-models.ps1, start-localaistudio.bat, INSTALLATION.md, requirements-local.txt, .env template).

## Website-presence filter (carte)
- At zoom >= 13 the 120 companies nearest the map centre are POSTed to `/api/companies/web-status`; backend/lib/webcheck.py tests probable domains (nom.fr/.com, nom-ville.fr) and accepts a site only if the page mentions the business name. Status pending → found | none (cached in Mongo).
- Map: rose dots = no website (prospects, drawn on top), faded green = has a site, violet pulse = checking. Switch "Seulement les entreprises sans site web", counters, quick list of 5 prospects. CompanyPanel shows the status / existing URL.

## GPU queue
- backend/lib/gpu_queue.py serialises local renders (ComfyUI photo/video, local LLM site/edit) on the single GPU; ETA learned from `render_stats`. `/api/queue` (GET), `/api/queue/{id}/prioritize`, `/api/queue/{id}/cancel`.
- UI: header pill "GPU · n · ETA" (popover list) + "Rendus en cours" card on /moteurs.

## Premium site engine (default, `engine: "premium"`; legacy `"code"` = LLM writes all code)
- backend/lib/premium/: `themes.py` (7 moods × palettes × font pairs + random switches: hero variant, radius, cursor, header/footer layout, labels, grain, loader), `runtime.css` + `runtime.js` (hand-written, dependency-free animation runtime: split text, reveals, pinned story, horizontal scroll, statement word reveal, counters, configurator, tabs, testimonials, 3D canvas network, custom cursor, magnetic buttons, tilt, page curtain, preloader), `__init__.py` (section renderers + prompts).
- Pipeline: direction step asks the LLM only for concept/mood/photo_style/image_briefs, theme drawn with seed `project id`; generation step asks per page for JSON `{title, description, sections:[{type,...}]}` from an 18-type catalogue (hero, marquee, story, statement, features, hscroll, stats, configurator, network, gallery, testimonials, pricing, process, textimage, faq, logos, cta, contact) and renders HTML. Output keeps the usual file layout (_head/_header/_footer/styles.css/app.js + pages) so QA, chat edits, versions and ZIP export work unchanged.
- Preview "non connecté" for local engines is expected online; /moteurs explains that public unauthenticated tunnels have been disabled for security (V1-B). Remote access requires an authenticated reverse proxy.
