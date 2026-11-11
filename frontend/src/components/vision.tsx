import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Ban, Download, Film, ImagePlus, Loader2, Megaphone, Sparkles, Trash2, Upload, Volume2, Globe2 } from "lucide-react";
import { toast } from "sonner";
import { FxButton } from "@/components/FxButton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fileToDataUrl, useBrands, useMedia, useMediaActions, useProjects, useHuggingFaceVideoStatus, usePrivateSanaStatus, useSmartMotionStatus, useVideoModels } from "@/lib/hooks";
import { apiPost } from "@/lib/api";
import { useComfy, useImageModels, useImageLoras, useVideoEngineStatus } from "@/lib/companyHooks";
import type { ImageRequest, Media, SmartMotionRequest, VideoRequest } from "@/lib/types";
import { mediaFileUrl } from "@/lib/types";
import { cn } from "@/lib/utils";

const field = "w-full rounded-xl border border-white/10 bg-black/30 p-3.5 text-sm outline-none transition-[border-color,box-shadow] focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] placeholder:text-slate-500";

const PHOTO_STYLES = [
  { id: "none", name: "Sans style", tone: "from-slate-600/30 to-slate-900/70", guidance: "" },
  { id: "product", name: "Produit éditorial", tone: "from-amber-300/25 via-stone-500/10 to-slate-900", guidance: "photographie publicitaire de produit, matières fidèles, composition éditoriale, éclairage studio maîtrisé" },
  { id: "cinematic", name: "Cinéma", tone: "from-indigo-400/30 via-violet-500/15 to-slate-950", guidance: "photographie cinématographique, éclairage motivé, profondeur atmosphérique, cadrage de film" },
  { id: "architecture", name: "Architecture", tone: "from-cyan-300/25 via-blue-500/10 to-slate-950", guidance: "photographie d'architecture, lignes structurées, perspective naturelle, lumière ambiante réaliste" },
  { id: "illustration", name: "Illustration manga", tone: "from-fuchsia-400/25 via-rose-500/10 to-slate-950", guidance: "illustration manga, contours dessinés, aplats cel-shading, composition dynamique" },
] as const;

const VIDEO_STYLES = [
  { id: "none", name: "Sans style", tone: "from-slate-600/30 to-slate-900/70", guidance: "" },
  { id: "cinematic", name: "Cinéma naturel", tone: "from-indigo-400/30 via-violet-500/15 to-slate-950", guidance: "mouvement cinématographique naturel, gestes physiquement plausibles, anatomie cohérente, scène stable, lumière de cinéma" },
  { id: "product", name: "Produit premium", tone: "from-amber-300/25 via-stone-500/10 to-slate-900", guidance: "film publicitaire produit premium, matières réalistes, mouvement de caméra maîtrisé, éclairage studio raffiné" },
  { id: "documentary", name: "Documentaire", tone: "from-emerald-300/25 via-teal-500/10 to-slate-950", guidance: "esthétique documentaire d'observation, lumière naturelle, mouvement crédible, caméra sobre" },
  { id: "fashion", name: "Mode éditoriale", tone: "from-fuchsia-400/25 via-rose-500/10 to-slate-950", guidance: "film de mode éditorial, mouvement expressif mais naturel, composition raffinée, lumière cinématographique" },
] as const;

function StyleCards({ styles, value, onChange, testid }: { styles: readonly { id: string; name: string; tone: string; guidance: string }[]; value: string; onChange: (id: string) => void; testid: string }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid={testid}>
      {styles.map((style) => (
        <motion.button key={style.id} type="button" whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }} aria-pressed={value === style.id} data-testid={`${testid}-${style.id}`} onClick={() => onChange(style.id)} className={cn("overflow-hidden rounded-xl border text-left transition-[border-color,box-shadow]", value === style.id ? "border-cyan-300/60 shadow-[0_0_20px_-8px_rgba(6,182,212,0.9)]" : "border-white/10 hover:border-white/25")}>
          <span aria-hidden="true" className={cn("block h-12 bg-gradient-to-br", style.tone)} />
          <span className="block px-2.5 py-2 text-xs font-medium text-slate-200">{style.name}</span>
          <span className="block px-2.5 pb-2 text-[9px] uppercase tracking-wider text-slate-500">Consigne textuelle · sans aperçu</span>
        </motion.button>
      ))}
    </div>
  );
}

function SetupPreview({ mode, model, format, style, prompt, testid }: { mode: string; model: string; format: string; style: string; prompt: string; testid: string }) {
  return (
    <section data-testid={testid} className="col-span-full overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.045] to-transparent p-4">
      <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-widest text-slate-400">
        {[mode, model, format, style].filter(Boolean).map((item) => <span key={item} className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1">{item}</span>)}
      </div>
      <p className="mt-3 line-clamp-2 text-sm text-slate-300">{prompt.trim() || "Votre description apparaîtra ici. Le résultat final sera affiché après une génération réelle."}</p>
      <p className="mt-2 text-[10px] text-slate-500">Aperçu de configuration — pas une image générée</p>
    </section>
  );
}

function Chip({ active, onClick, children, testid, disabled = false }: { active: boolean; onClick: () => void; children: React.ReactNode; testid: string; disabled?: boolean }) {
  return (
    <button type="button" data-testid={testid} disabled={disabled} onClick={onClick} className={cn("rounded-full border px-3.5 py-1.5 text-xs font-medium transition-[border-color,background-color,color,box-shadow] duration-200", active ? "border-cyan-300/70 bg-cyan-500/20 text-white shadow-[0_0_18px_-4px_rgba(6,182,212,0.9)]" : "border-white/10 text-slate-400 hover:border-white/25 hover:text-white", disabled && "cursor-not-allowed opacity-40 hover:border-white/10 hover:text-slate-400")}>
      {children}
    </button>
  );
}

function ModelCard({ active, onClick, title, tagline, badge, testid }: { active: boolean; onClick: () => void; title: string; tagline: string; badge?: string; testid: string }) {
  return (
    <motion.button whileHover={{ y: -3 }} whileTap={{ scale: 0.98 }} type="button" data-testid={testid} onClick={onClick} className={cn("relative w-full overflow-hidden rounded-2xl border p-4 text-left transition-[border-color,background-color,box-shadow] duration-300", active ? "border-cyan-300/60 bg-cyan-500/[0.12] shadow-[0_0_40px_-12px_rgba(6,182,212,0.9)]" : "border-white/10 bg-white/[0.02] hover:border-white/25")}>
      {active && <motion.span layoutId={`${testid.split("-")[0]}-model-glow`} className="absolute -right-10 -top-10 size-28 rounded-full bg-cyan-400/25 blur-2xl" />}
      <p className="relative font-heading font-semibold">{title}</p>
      <p className="relative mt-1 text-xs leading-snug text-slate-400">{tagline}</p>
      {badge && <span className="relative mt-3 inline-block rounded-full bg-white/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan-200">{badge}</span>}
    </motion.button>
  );
}

function RefPicker({ value, onChange, testid }: { value: string | null; onChange: (id: string | null) => void; testid: string }) {
  const { data } = useMedia("image");
  const { upload } = useMediaActions();
  const imgs = (data ?? []).filter((m) => m.status === "done").slice(0, 18);
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className="space-y-2">
      <div className="flex gap-2 overflow-x-auto pb-1">
        <button type="button" data-testid={`${testid}-upload`} onClick={() => inputRef.current?.click()} className="flex size-16 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/20 text-[10px] text-slate-400 transition-colors hover:border-cyan-300 hover:text-white">
          {upload.isPending ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />} Importer
        </button>
        <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          upload.mutate({ data_url: await fileToDataUrl(f), source: "upload", prompt: f.name }, { onSuccess: (m) => onChange(m.id) });
        }} />
        {imgs.map((m) => (
          <button key={m.id} type="button" data-testid={`${testid}-${m.id}`} onClick={() => onChange(value === m.id ? null : m.id)} className={cn("size-16 shrink-0 overflow-hidden rounded-xl border-2 transition-[border-color,transform] duration-200 hover:scale-105", value === m.id ? "border-cyan-300 shadow-[0_0_16px_rgba(6,182,212,0.8)]" : "border-transparent")}>
            <img src={m.url!} alt="" className="size-full object-cover" />
          </button>
        ))}
      </div>
    </div>
  );
}

function userVisibleProviderText(value: string) {
  return value.replace(/ZeroGPU/gi, "calcul distant");
}

function MediaTile({ m, onCancel }: { m: Media; onCancel?: () => void }) {
  const busy = m.status === "pending" || m.status === "running";
  const perf = m.generation_metrics as { timing_seconds?: { comfy_total?: number }; gpu_memory_mib?: { peak_used?: number }; total_wall_seconds_including_depth?: number; vram_peak_sampled_mib?: number } | null | undefined;
  const perfSeconds = perf?.timing_seconds?.comfy_total ?? perf?.total_wall_seconds_including_depth;
  const perfVram = perf?.gpu_memory_mib?.peak_used ?? perf?.vram_peak_sampled_mib;
  const { remove } = useMediaActions();
  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-panel" data-testid={`media-tile-${m.id}`}>
      <div className="relative aspect-square">
        {m.status === "done" && m.url ? (
          m.kind === "video" ? <video src={m.url} controls loop playsInline className="size-full object-cover" /> : <img src={m.url} alt={m.prompt} className="size-full object-cover transition-transform duration-700 group-hover:scale-105" />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-3 bg-[radial-gradient(circle_at_50%_40%,rgba(6,182,212,0.25),transparent_60%)] p-4 text-center">
            {busy ? <Loader2 className="size-7 animate-spin text-cyan-300" /> : <Ban className="size-7 text-red-300" />}
            <p className="text-xs text-slate-300" data-testid={`media-progress-${m.id}`}>{busy ? userVisibleProviderText(m.progress_label || "En cours…") : userVisibleProviderText(m.error || "Échec")}</p>
            {busy && <div className="h-1 w-3/4 overflow-hidden rounded-full bg-white/10"><div className="shimmer-bar h-full w-full bg-cyan-400/40" /></div>}
            {busy && onCancel && <FxButton size="sm" tone="ghost" data-testid={`media-cancel-${m.id}`} onClick={onCancel}><Ban className="size-3.5" /> Annuler</FxButton>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 p-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs text-slate-200">{m.prompt}</p>
          <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{userVisibleProviderText(m.model)}{m.duration ? ` · ${m.duration}` : ""}{m.aspect_ratio ? ` · ${m.aspect_ratio}` : ""}</p>
          {perf && <p data-testid={`video-metrics-${m.id}`} className="mt-1 text-[10px] text-slate-400">{perfSeconds != null ? `${Number(perfSeconds).toFixed(1)} s` : "durée inconnue"}{perfVram != null ? ` · VRAM pic ${(perfVram / 1024).toFixed(1)} Gio` : ""}</p>}
        </div>
        {m.url && <a href={m.url} download data-testid={`media-download-${m.id}`} className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-white" aria-label="Télécharger"><Download className="size-3.5" /></a>}
        {!busy && <button type="button" data-testid={`media-delete-${m.id}`} onClick={() => remove.mutate(m.id)} className="rounded-md p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-300" aria-label="Supprimer"><Trash2 className="size-3.5" /></button>}
      </div>
    </motion.div>
  );
}

export function PhotoStudio() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState<ImageRequest["model"]>("comfy");
  const [aspect, setAspect] = useState<ImageRequest["aspect_ratio"]>("1:1");
  const [mode, setMode] = useState<"text" | "image">("text");
  const [styleId, setStyleId] = useState<(typeof PHOTO_STYLES)[number]["id"]>("none");
  const [ref, setRef] = useState<string | null>(null);
  const { data } = useMedia("image");
  const { image } = useMediaActions();
  const { data: models } = useImageModels();
  const { data: comfyCfg } = useComfy();
  const [comfyPreset, setComfyPreset] = useState<string | null>(null);
  const [loraName, setLoraName] = useState<string | null>(null);
  const [loraStrength, setLoraStrength] = useState(0.8);
  // Only installed presets are selectable. A null state (ComfyUI cannot list models) is kept, not treated as missing.
  const candidates = (models ?? []).filter((m) => m.installed !== false);
  const noneInstalled = !!models && models.length > 0 && models.every((m) => m.installed === false);
  const savedKey = comfyCfg?.image_preset ?? null;
  const choice =
    (comfyPreset && candidates.some((m) => m.key === comfyPreset) ? comfyPreset : null) ??
    candidates.find((m) => m.key === savedKey)?.key ??
    candidates[0]?.key ??
    savedKey;
  const { data: loras } = useImageLoras(choice);
  useEffect(() => { if (choice !== "sdxl") setLoraName(null); }, [choice]);
  const mine = (data ?? []).filter((m) => m.source === "photo").slice(0, 12);
  return (
    <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
      <div className="glass-vision space-y-5 rounded-3xl p-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <ModelCard testid="photo-model-comfy" active={model === "comfy"} onClick={() => setModel("comfy")} title="Local · ComfyUI (FLUX / SDXL)" tagline="100 % gratuit, rendu sur votre RTX 3060" badge="Par défaut · gratuit" />
          </div>
          <ModelCard testid="photo-model-nano-banana" active={model === "nano-banana"} onClick={() => setModel("nano-banana")} title="Nano Banana" tagline="Secours en ligne, rapide" badge="Payant" />
          <ModelCard testid="photo-model-nano-banana-pro" active={model === "nano-banana-pro"} onClick={() => setModel("nano-banana-pro")} title="Nano Banana Pro" tagline="Secours en ligne, qualité max" badge="Payant" />
        </div>
        {model === "comfy" && (
          <div data-testid="photo-preset-picker" className="space-y-2">
            <Label className="block text-xs text-slate-400">Modèle ComfyUI</Label>
            {(models ?? []).map((m) => {
              const missing = m.installed === false;
              const active = choice === m.key;
              return (
                <button
                  key={m.key}
                  type="button"
                  data-testid={`photo-preset-${m.key}`}
                  aria-pressed={active}
                  disabled={missing}
                  onClick={() => setComfyPreset(m.key)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition",
                    active ? "border-violet-400 bg-violet-500/15 text-white" : "border-white/10 text-slate-300 hover:bg-white/5",
                    missing && "cursor-not-allowed opacity-40",
                  )}
                >
                  <span>{m.label}</span>
                  <span className="text-[11px] text-slate-400">
                    {m.installed === true ? "installé" : m.installed === false ? "non installé" : "vérification…"}
                  </span>
                </button>
              );
            })}
            {!models && <p className="text-xs text-slate-400">Chargement des modèles…</p>}
            {noneInstalled && (
              <p data-testid="photo-no-model" className="text-xs text-amber-300">
                Aucun modèle image installé dans ComfyUI. Lancez download-models.ps1, puis redémarrez ComfyUI.
              </p>
            )}
          </div>
        )}
        {model === "comfy" && (loras ?? []).map((l) => (
          <article key={l.id} data-testid={`lora-card-${l.id}`} className="overflow-hidden rounded-2xl border border-amber-200/20 bg-black/20">
            <div className="space-y-2 p-3"><div className="flex items-center justify-between gap-2"><strong className="text-sm">{l.name}</strong><span className="text-[10px] text-amber-200">{l.category}</span></div>
              {l.comparison_preview ? <div className="grid grid-cols-2 gap-2" data-testid={`lora-comparison-${l.id}`}><figure><img className="aspect-square w-full rounded-lg object-cover" src={l.comparison_preview.without_lora} alt="Même génération sans LoRA" /><figcaption className="mt-1 text-center text-[10px] text-slate-300">SANS LoRA</figcaption></figure><figure><img className="aspect-square w-full rounded-lg object-cover" src={l.comparison_preview.with_lora} alt="Même génération avec LoRA" /><figcaption className="mt-1 text-center text-[10px] text-slate-300">AVEC LoRA</figcaption></figure><a className="col-span-2 text-[10px] text-cyan-200 underline" href={l.comparison_preview.metadata}>Paramètres et métadonnées de comparaison</a></div> : <p data-testid={`lora-comparison-pending-${l.id}`} className="rounded-lg border border-dashed border-white/15 px-2 py-2 text-[10px] text-slate-400">Comparaison visuelle contrôlée SANS / AVEC LoRA pas encore générée.</p>}
              <p className="text-xs text-slate-300">{l.description}</p><p className="text-[10px] text-slate-400">Base : {l.base_model} · {l.engine} · {l.resolution} · intensité conseillée {l.strength} · type {l.media_type ?? "image"}</p>
              <p className="text-[10px] text-amber-200">{l.installed === true ? "Installé localement" : l.installed === false ? "Fichier absent" : "Disponibilité inconnue"} · {l.compatible ? "Compatible avec le modèle sélectionné" : l.reason}</p>
              <p className="text-[10px] text-slate-400">{l.license} {l.restrictions}</p>
              <div className="flex items-center justify-between gap-2"><a href={l.source_url} target="_blank" rel="noreferrer" className="text-[10px] text-cyan-200 underline">Voir la source (aperçu non intégré)</a><button type="button" data-testid={`lora-toggle-${l.id}`} disabled={!l.selectable} aria-pressed={loraName === l.filename} onClick={() => { setLoraName(loraName === l.filename ? null : l.filename); setLoraStrength(l.strength); }} className={cn("rounded-lg border px-3 py-1.5 text-xs", loraName === l.filename ? "border-amber-200 bg-amber-200/15 text-white" : "border-white/15 text-slate-300", !l.selectable && "cursor-not-allowed opacity-40")}>{loraName === l.filename ? "Désactiver" : "Sélectionner"}</button></div>
              {loraName === l.filename && <label className="block text-xs text-slate-300">Intensité {loraStrength.toFixed(2)}<input aria-label="Intensité LoRA" data-testid="lora-strength" type="range" min="0" max="1.5" step="0.05" value={loraStrength} onChange={(e) => setLoraStrength(Number(e.target.value))} className="ml-2 align-middle" /></label>}
            </div>
          </article>
        ))}
        <div className="flex gap-2" role="group" aria-label="Mode de génération photo">
          <Chip testid="photo-mode-text" active={mode === "text"} onClick={() => setMode("text")}>Texte → image</Chip>
          <Chip testid="photo-mode-image" active={mode === "image"} onClick={() => setMode("image")}>Image → image</Chip>
        </div>
        <textarea data-testid="photo-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} placeholder={mode === "image" ? "Décrivez la transformation souhaitée : ambiance, décor, lumière, style…" : "Ex. Flacon de parfum ambré sur pierre volcanique, lumière rasante dorée, macro éditoriale…"} className={cn(field, "resize-none")} />
        <div className="space-y-2">
          <div><Label className="block text-xs text-slate-300">Direction artistique</Label><p className="mt-1 text-[10px] text-slate-500">Préréglages textuels transmis au prompt — pas de LoRA, aperçu indisponible.</p></div>
          <StyleCards styles={PHOTO_STYLES} value={styleId} onChange={(id) => setStyleId(id as typeof styleId)} testid="photo-styles" />
        </div>
        <div className="flex flex-wrap gap-2">
          {(["1:1", "4:5", "16:9", "9:16"] as const).map((a) => <Chip key={a} testid={`photo-aspect-${a}`} active={aspect === a} onClick={() => setAspect(a)}>{a}</Chip>)}
        </div>
        {mode === "image" && <div>
          <Label className="mb-2 block text-xs text-slate-400">Image source à transformer · importez ou choisissez un média</Label>
          <RefPicker value={ref} onChange={setRef} testid="photo-ref" />
        </div>}
        <FxButton tone="vision" size="lg" className="w-full" data-testid="generate-photo-btn" disabled={prompt.trim().length < 3 || image.isPending || (model === "comfy" && noneInstalled) || (mode === "image" && !ref)} onClick={() => {
          const style = PHOTO_STYLES.find((item) => item.id === styleId);
          const styledPrompt = style?.guidance ? `${prompt.trim()}, ${style.guidance}` : prompt.trim();
          image.mutate({ prompt: styledPrompt, model, aspect_ratio: aspect, ref_media_id: mode === "image" ? ref : null, comfy_preset: model === "comfy" ? choice : null, lora_name: model === "comfy" && choice === "sdxl" ? loraName : null, lora_strength: loraStrength }, { onSuccess: () => toast.success("Photo en cours de création") });
        }}>
          <Sparkles className="size-4" /> {mode === "image" ? "Transformer l'image" : "Générer la photo"}
        </FxButton>
      </div>
      <div className="grid content-start gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="photo-results">
        <SetupPreview testid="photo-setup-preview" mode={mode === "image" ? "Image → image" : "Texte → image"} model={model === "comfy" ? choice ?? "ComfyUI" : model} format={aspect} style={PHOTO_STYLES.find((item) => item.id === styleId)?.name ?? "Sans style"} prompt={prompt} />
        <AnimatePresence>{mine.map((m) => <MediaTile key={m.id} m={m} />)}</AnimatePresence>
        {!mine.length && <EmptyState icon={ImagePlus} text="Vos photos générées apparaîtront ici." />}
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, text }: { icon: typeof ImagePlus; text: string }) {
  return (
    <div className="glass col-span-full flex min-h-60 flex-col items-center justify-center gap-3 rounded-3xl text-sm text-slate-400">
      <Icon className="size-8 text-cyan-300/70 animate-float" /> {text}
    </div>
  );
}

const SMARTMOTION_MOVE_LABEL: Record<"push_in" | "pan_left" | "pan_right" | "tilt_up" | "tilt_down" | "orbit_subtle" | "static", string> = {
  push_in: "travelling avant doux", pan_left: "panoramique gauche", pan_right: "panoramique droite",
  tilt_up: "inclinaison haut", tilt_down: "inclinaison bas", orbit_subtle: "arc latéral subtil", static: "caméra fixe",
};

export function VideoStudio() {
  const { data: models } = useVideoModels();
  const { data: hfStatus } = useHuggingFaceVideoStatus();
  const { data: sanaStatus } = usePrivateSanaStatus();
  const { data: comfyCfg } = useComfy();
  const { data: engineStatus } = useVideoEngineStatus();
  const { data: smartMotionStatus } = useSmartMotionStatus();
  const [model, setModel] = useState<VideoRequest["model"] | "smartmotion">("hf_ltx");
  const [mode, setMode] = useState<VideoRequest["mode"]>("text");
  const [prompt, setPrompt] = useState("");
  const [styleId, setStyleId] = useState<(typeof VIDEO_STYLES)[number]["id"]>("none");
  const [duration, setDuration] = useState("3");
  const [aspect, setAspect] = useState("16:9");
  const [ref, setRef] = useState<string | null>(null);
  const [comfyPreset, setComfyPreset] = useState<NonNullable<VideoRequest["comfy_preset"]>>("wan21_t2v");
  const [cameraPose, setCameraPose] = useState("Static");
  const [smartMotionMove, setSmartMotionMove] = useState<"push_in" | "pan_left" | "pan_right" | "tilt_up" | "tilt_down" | "orbit_subtle" | "static">("push_in");
  const [smartMotionSize, setSmartMotionSize] = useState<"source" | "1280x720" | "1920x1080">("source");
  const [presetInitialized, setPresetInitialized] = useState(false);
  const cfg = models?.find((m) => m.key === model);
  const chosenPreset = engineStatus?.presets.find((p) => p.key === comfyPreset);
  const needsImage = model === "smartmotion" || (model === "comfy" && comfyPreset === "wan21_fun_camera");
  const t2vOnly = model === "hf_ltx" || model === "hf_sana" || (model === "comfy" && comfyPreset === "wan21_t2v");
  const paidModel = model === "veo" || model === "kling" || model === "minimax";
  const paidUnitCost = model === "veo" ? 0.15 : model === "kling" ? 0.07 : 0.045;
  const paidEstimatedCost = paidModel ? (Number.parseFloat(duration.replace(/s$/i, "")) * paidUnitCost).toFixed(2) : "0.00";
  const comfyUnavailable = model === "comfy" && (!chosenPreset || chosenPreset.installed !== true);
  const smartMotionUnavailable = model === "smartmotion" && smartMotionStatus?.available !== true;
  const cloudUnavailable = (model === "hf_ltx" && hfStatus?.available !== true) || (model === "hf_sana" && sanaStatus?.available !== true);
  const { data } = useMedia("video");
  const { video, smartmotion, cancel } = useMediaActions();
  useEffect(() => {
    if (comfyCfg && engineStatus && !presetInitialized) {
      const saved = engineStatus.presets.find((p) => p.key === comfyCfg.video_preset && p.installed === true)?.key;
      const firstInstalled = engineStatus.presets.find((p) => p.installed === true)?.key;
      setComfyPreset(saved ?? firstInstalled ?? comfyCfg.video_preset);
      setPresetInitialized(true);
    }
  }, [comfyCfg, engineStatus, presetInitialized]);
  useEffect(() => {
    if (needsImage) setMode("image");
    else if (t2vOnly) setMode("text");
  }, [needsImage, t2vOnly]);
  useEffect(() => {
    if (!cfg) return;
    if (!cfg.durations.includes(duration)) setDuration(model === "smartmotion" ? cfg.durations[0] : cfg.durations[cfg.durations.length - 1]);
    if (!cfg.aspects.includes(aspect)) setAspect(cfg.aspects[0]);
  }, [cfg, duration, aspect, model]);
  const showAspect = cfg && !(mode === "image" && model !== "veo" && model !== "comfy") && cfg.aspects.length > 1;
  const cameraOptions = engineStatus?.camera_poses ?? [];
  const pickPreset = (value: NonNullable<VideoRequest["comfy_preset"]>) => {
    setComfyPreset(value);
    if (value === "wan21_fun_camera") setMode("image");
    if (value === "wan21_t2v") setMode("text");
  };
  return (
    <div className="grid gap-6 lg:grid-cols-[440px_1fr]">
      <div className="glass-vision space-y-5 rounded-3xl p-5">
        <div className="grid gap-3">
          {(models ?? []).map((m) => (
            <ModelCard key={m.key} testid={`video-model-${m.key}`} active={model === m.key} onClick={() => setModel(m.key as VideoRequest["model"] | "smartmotion")} title={m.key === "comfy" ? "LocalAi Video Engine — Gratuit" : m.key === "hf_ltx" ? "Cloud vidéo · LTX (gratuit, limité)" : m.key === "hf_sana" ? "SANA · calcul distant privé" : m.label} tagline={m.key === "comfy" ? "Local · Wan génératif via ComfyUI · T2V et I2V selon le modèle installé" : m.key === "hf_ltx" ? "Calcul sur serveur distant · quota quotidien limité · T2V uniquement validé" : m.key === "hf_sana" ? "T2V · profils 5/8 s · 1280×736 · jeton HF privé requis · quota restant non consultable" : userVisibleProviderText(m.tagline)} badge={`${m.durations.join(" / ")}${m.audio ? " · son" : ""}`} />
          ))}
        </div>
        {model === "hf_ltx" && (
          <div className="space-y-2 text-xs text-slate-300" data-testid="hf-ltx-status">
            <p>Génération sur serveur distant, pas sur votre PC. Modèle : {hfStatus?.model ?? "LTX Video 0.9.8"}. {hfStatus?.available ? "Le service répond actuellement." : "Le service est actuellement indisponible; aucune requête ne sera envoyée."}</p>
            <p className="text-amber-200">Quota limité et restant non consultable; seul le T2V 2 s, 256×256 a été validé avec ce connecteur. Qualité et disponibilité variables.</p>
          </div>
        )}
        {model === "hf_sana" && (
          <div className="space-y-2 rounded-2xl border border-cyan-300/15 bg-cyan-400/[0.04] p-3 text-xs" data-testid="sana-status">
            <p className="text-slate-200">{sanaStatus?.available ? "Space privé SANA prêt." : sanaStatus?.reason ?? "Vérification du Space privé…"}</p>
            <p className="text-slate-400">T2V uniquement · {sanaStatus?.resolution ?? "1280×736"} · profils {sanaStatus?.durations_seconds?.join(" / ") ?? "5 / 8"} s · I2V non pris en charge.</p>
            <p className="text-amber-200">{sanaStatus?.credential_configured ? "Jeton privé configuré; aucun calcul avant votre clic Générer." : "Jeton HF privé absent. Configurez-le dans les réglages avancés. Aucun rendu ne sera soumis."} Quota restant non exposé par le service; aucun secours payant.</p>
          </div>
        )}
        {model === "comfy" && (
          <div className="space-y-3 rounded-2xl border border-white/[0.07] bg-black/20 p-3">
            <Label htmlFor="video-comfy-preset">Modèle vidéo ComfyUI</Label>
            <select id="video-comfy-preset" data-testid="video-comfy-preset" value={comfyPreset} onChange={(e) => pickPreset(e.target.value as NonNullable<VideoRequest["comfy_preset"]>)} className={field}>
              {(engineStatus?.presets ?? []).map((p) => <option key={p.key} value={p.key} disabled={p.installed !== true}>{p.label} · {p.installed === true ? "installé" : p.installed === false ? "non installé" : "état inconnu"}</option>)}
            </select>
            {chosenPreset?.installed !== true && <p role="status" className="text-xs text-amber-200">{chosenPreset?.installed === false ? `Composants absents : ${chosenPreset.files.join(", ")}` : "ComfyUI n'a pas confirmé les modèles installés."}</p>}
          </div>
        )}
        {needsImage ? (
          <div className="space-y-2"><p className="text-xs text-slate-300">{model === "smartmotion" ? "SmartMotion anime uniquement la caméra à partir d'une image fixe; les objets ne sont pas générés ni animés." : "Wan Fun Camera est un modèle Image → vidéo uniquement. Choisissez une image de départ."}</p><RefPicker value={ref} onChange={setRef} testid="video-ref" /></div>
        ) : (
          <div className="flex gap-2">
            <Chip testid="video-mode-text" active={mode === "text"} onClick={() => setMode("text")}>Texte → vidéo</Chip>
            <Chip testid="video-mode-image" active={mode === "image"} disabled={t2vOnly} onClick={() => setMode("image")}>Image → vidéo</Chip>
          </div>
        )}
        {mode === "image" && !needsImage && <RefPicker value={ref} onChange={setRef} testid="video-ref" />}
        {model === "comfy" && needsImage && cameraOptions.length > 0 && (
          <div className="space-y-1.5">
            <Label htmlFor="video-camera-pose">Mouvement de caméra Wan</Label>
            <select id="video-camera-pose" data-testid="video-camera-pose" value={cameraPose} onChange={(e) => setCameraPose(e.target.value)} className={field}>
              {cameraOptions.map((pose) => <option key={pose} value={pose}>{pose === "Pan Up" ? "Tilt vers le haut · Pan Up" : pose === "Pan Down" ? "Tilt vers le bas · Pan Down" : pose === "ClockWise (CW)" ? "Rotation horaire" : pose === "Anti Clockwise (ACW)" ? "Rotation antihoraire" : pose}</option>)}
            </select>
          </div>
        )}
        {model === "smartmotion" && (
          <div className="space-y-3 rounded-xl border border-cyan-300/15 bg-cyan-400/[0.04] p-3">
            <div className="space-y-1.5"><Label htmlFor="smartmotion-move">Mouvement caméra 2.5D</Label>
              <select id="smartmotion-move" data-testid="smartmotion-move" value={smartMotionMove} onChange={(e) => setSmartMotionMove(e.target.value as typeof smartMotionMove)} className={field}>
                <option value="push_in">Travelling avant doux</option><option value="pan_left">Panoramique vers la gauche</option><option value="pan_right">Panoramique vers la droite</option><option value="tilt_up">Inclinaison vers le haut</option><option value="tilt_down">Inclinaison vers le bas</option><option value="orbit_subtle">Arc latéral subtil (pseudo-3D)</option><option value="static">Caméra fixe</option>
              </select>
            </div>
            <div className="space-y-1.5"><Label htmlFor="smartmotion-size">Sortie</Label>
              <select id="smartmotion-size" data-testid="smartmotion-size" value={smartMotionSize} onChange={(e) => setSmartMotionSize(e.target.value as typeof smartMotionSize)} className={field}>
                <option value="source">Dimensions source (sans recadrage)</option><option value="1280x720">720p paysage (recadrage si nécessaire)</option><option value="1920x1080">1080p paysage (upscale/recadrage si nécessaire)</option>
              </select>
            </div>
            <p className="text-xs text-slate-400">Le prompt n'est pas interprété dans ce mode : choisissez le mouvement caméra ci-dessus. Pour générer un mouvement réel des personnages/objets, sélectionnez Local · ComfyUI (modèle vidéo requis).</p>
            {smartMotionStatus?.available === false && <p role="status" className="text-xs text-amber-200">SmartMotion indisponible : {smartMotionStatus.reason}</p>}
          </div>
        )}
        {model === "smartmotion" ? (
          <p data-testid="smartmotion-no-prompt-required" className="rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-slate-300">
            Aucun prompt requis : SmartMotion applique uniquement le mouvement caméra sélectionné à l'image de départ.
          </p>
        ) : (
          <textarea data-testid="video-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} placeholder="Ex. Travelling lent autour d'une table dressée, vapeur, lumière de bougie, ambiance gastronomique…" className={cn(field, "resize-none")} />
        )}
        {model !== "smartmotion" && <div className="space-y-2">
          <div><Label className="block text-xs text-slate-300">Direction artistique vidéo</Label><p className="mt-1 text-[10px] text-slate-500">Consigne textuelle ajoutée au prompt. Aucun LoRA vidéo n'est activé par ces styles.</p></div>
          <StyleCards styles={VIDEO_STYLES} value={styleId} onChange={(id) => setStyleId(id as typeof styleId)} testid="video-styles" />
        </div>}
        <div className="space-y-2">
          <p className="text-xs text-slate-400">{model === "smartmotion" ? "Durée SmartMotion (maximum 30 s)" : "Durée acceptée par ce modèle"}</p>
          <div className="flex flex-wrap gap-2">{cfg?.durations.map((d) => <Chip key={d} testid={`video-duration-${d}`} active={duration === d} onClick={() => setDuration(d)}>{d.replace("s", "")} s</Chip>)}</div>
        </div>
        {showAspect && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400">Format</p>
            <div className="flex flex-wrap gap-2">{cfg.aspects.map((a) => <Chip key={a} testid={`video-aspect-${a}`} active={aspect === a} onClick={() => setAspect(a)}>{a}</Chip>)}</div>
          </div>
        )}
        {cfg && !showAspect && <p className="text-xs text-slate-500">Format : {model === "smartmotion" ? (smartMotionSize === "source" ? "celui de l'image de départ" : smartMotionSize) : mode === "image" ? "celui de l'image de départ" : cfg.aspects[0]} (selon la sortie choisie)</p>}
        {model === "smartmotion" ? (
          <p data-testid="smartmotion-local-note" className="flex items-center gap-1.5 text-xs text-emerald-200/80"><Sparkles className="size-3.5" /> Traitement local · caméra 2.5D uniquement · 24 FPS · aucun modèle vidéo génératif.</p>
        ) : model === "comfy" ? (
          <p data-testid="video-local-note" className="flex items-center gap-1.5 text-xs text-emerald-200/80"><Sparkles className="size-3.5" /> Local · rendu sur votre GPU via ComfyUI (plusieurs minutes possibles, sans son).</p>
        ) : model === "hf_ltx" ? (
          <p data-testid="video-cloud-note" className="flex items-center gap-1.5 text-xs text-cyan-200/90"><Sparkles className="size-3.5" /> Calcul vidéo sur serveur distant (ce n’est pas local). Le prompt français est envoyé au fournisseur; son code ajoute des indications anglaises de vitesse. Quota restant non consultable; seul un clip de 2 s / 256×256 est validé.</p>
        ) : paidModel ? (
          <p className="flex items-center gap-1.5 text-xs text-amber-200/80"><Volume2 className="size-3.5" /> Moteur payant facultatif · estimation actuelle : {paidEstimatedCost} USD pour ce clip. Une confirmation explicite du coût sera demandée avant tout appel; aucun coût n'est testé automatiquement.</p>
        ) : null}
        <FxButton tone="vision" size="lg" className="w-full" data-testid="generate-video-btn" disabled={(model !== "smartmotion" && prompt.trim().length < 3) || video.isPending || smartmotion.isPending || (mode === "image" && !ref) || comfyUnavailable || smartMotionUnavailable || cloudUnavailable} onClick={() => {
          if (model === "smartmotion") {
            if (!ref) return;
            smartmotion.mutate({ prompt: `SmartMotion · ${SMARTMOTION_MOVE_LABEL[smartMotionMove]}`, ref_media_id: ref, seconds: Number(duration), fps: 24, output_size: smartMotionSize, motion: smartMotionMove }, { onSuccess: () => toast.success("SmartMotion lancé localement — progression visible dans la bibliothèque") });
          } else {
            const paidCostAcknowledged = paidModel && window.confirm(`Génération payante via ${cfg?.label ?? model}. Estimation actuelle : ${paidEstimatedCost} USD pour ${duration} s. Le tarif réel du fournisseur/proxy peut varier. Aucun appel ne sera effectué si vous annulez. Confirmez-vous explicitement ce coût ?`);
            if (paidModel && !paidCostAcknowledged) return;
            const selectedStyle = VIDEO_STYLES.find((item) => item.id === styleId);
            const styledPrompt = selectedStyle?.guidance ? `${prompt.trim()}, ${selectedStyle.guidance}` : prompt.trim();
            video.mutate({ prompt: styledPrompt, model, mode, duration, aspect_ratio: aspect, ref_media_id: mode === "image" ? ref : null, comfy_preset: model === "comfy" ? comfyPreset : null, camera_pose: model === "comfy" ? cameraPose : "Static", paid_cost_acknowledged: paidModel ? paidCostAcknowledged : false }, { onSuccess: () => toast.success("Vidéo envoyée au moteur — elle continue même si vous changez d'écran") });
          }
        }}>
          <Film className="size-4" /> {model === "smartmotion" ? "Animer l'image" : "Générer la vidéo"}
        </FxButton>
      </div>
      <div className="grid content-start gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="video-results">
        <SetupPreview testid="video-setup-preview" mode={model === "smartmotion" ? "SmartMotion · caméra 2.5D" : mode === "image" ? "Image → vidéo" : "Texte → vidéo"} model={model === "comfy" ? chosenPreset?.label ?? "ComfyUI" : cfg?.label ?? model} format={`${duration} s · ${aspect}`} style={model === "smartmotion" ? "Style non appliqué" : VIDEO_STYLES.find((item) => item.id === styleId)?.name ?? "Sans style"} prompt={prompt} />
        <AnimatePresence>{(data ?? []).map((m) => <MediaTile key={m.id} m={m} onCancel={() => cancel.mutate(m.id)} />)}</AnimatePresence>
        {!data?.length && <EmptyState icon={Film} text="Vos vidéos apparaîtront ici avec leur progression réelle." />}
      </div>
    </div>
  );
}

export function Library() {
  const [kind, setKind] = useState("");
  const { data, isError } = useMedia(kind);
  const { cancel } = useMediaActions();
  return (
    <div>
      <div className="mb-5 flex gap-2">
        {[["", "Tout"], ["image", "Images"], ["video", "Vidéos"]].map(([k, l]) => <Chip key={k} testid={`library-kind-${k || "all"}`} active={kind === k} onClick={() => setKind(k)}>{l}</Chip>)}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="media-library-grid">
        <AnimatePresence>{data?.map((m) => <MediaTile key={m.id} m={m} onCancel={() => cancel.mutate(m.id)} />)}</AnimatePresence>
        {!data?.length && <EmptyState icon={ImagePlus} text={isError ? "Bibliothèque momentanément indisponible." : "Aucun média pour l'instant."} />}
      </div>
    </div>
  );
}

const FORMATS = { "9:16": [1080, 1920], "1:1": [1080, 1080], "16:9": [1920, 1080] } as const;
type Fmt = keyof typeof FORMATS;

function loadImg(src: string) {
  return new Promise<HTMLImageElement>((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
}

export function AdWorkshop() {
  const { data: imgs } = useMedia("image");
  const { data: videos } = useMedia("video");
  const { data: brands } = useBrands();
  const { data: projects } = useProjects("", "");
  const { data: comfyCfg } = useComfy();
  const { data: imageModels } = useImageModels();
  const [adLoraName, setAdLoraName] = useState<string | null>(null);
  const [adLoraStrength, setAdLoraStrength] = useState(0.8);
  const { data: videoStatus } = useVideoEngineStatus();
  const { data: smStatus } = useSmartMotionStatus();
  const { upload, image, smartmotion, video, cancel } = useMediaActions();
  const [base, setBase] = useState<string | null>(null);
  const [generated, setGenerated] = useState<string | null>(null);
  const [fmt, setFmt] = useState<Fmt>("1:1");
  const [brandId, setBrandId] = useState("");
  const [photoPrompt, setPhotoPrompt] = useState("");
  const [adKind, setAdKind] = useState("Produit");
  const [imagePreset, setImagePreset] = useState<"flux-dev" | "flux-schnell" | "sdxl">("sdxl");
  const { data: adLoras } = useImageLoras(imagePreset);
  useEffect(() => { if (imagePreset !== "sdxl") setAdLoraName(null); }, [imagePreset]);
  const [videoEngine, setVideoEngine] = useState<"smartmotion" | "wan" | "wan-t2v">("smartmotion");
  const [videoPreset, setVideoPreset] = useState<"wan22" | "wan21_fun_camera" | "ltxv">("wan21_fun_camera");
  const [t2vPreset, setT2vPreset] = useState<"wan22" | "wan21_t2v" | "ltxv" | "wan21_fun_camera">("wan21_t2v");
  const [duration, setDuration] = useState(5);
  const [wanDuration, setWanDuration] = useState("3");
  const [cameraMotion, setCameraMotion] = useState<SmartMotionRequest["motion"]>("push_in");
  const [title, setTitle] = useState("Une expérience inoubliable");
  const [sub, setSub] = useState("Découvrez notre sélection, imaginée pour vous.");
  const [cta, setCta] = useState("Découvrir");
  const [accent, setAccent] = useState("#d5a85b");
  const [pos, setPos] = useState<"bas" | "haut" | "centre">("bas");
  const [posterId, setPosterId] = useState<string | null>(null);
  const [selectedClips, setSelectedClips] = useState<string[]>([]);
  const [exportId, setExportId] = useState<string | null>(null);
  const [siteOpen, setSiteOpen] = useState(false);
  const [canvasReady, setCanvasReady] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlayCanvas = useRef<HTMLCanvasElement>(null);
  const brand = brands?.find((b) => b.id === brandId);
  const choices = useMemo(() => (imgs ?? []).filter((m) => m.status === "done").slice(0, 36), [imgs]);
  const completeClips = useMemo(() => (videos ?? []).filter((m) => m.status === "done" && m.kind === "video"), [videos]);
  const baseMedia = imgs?.find((m) => m.id === base);
  const adMedia = useMemo(() => {
    const ids = [...(generated ? [generated] : []), ...selectedClips, ...(exportId ? [exportId] : [])];
    const all = [...(imgs ?? []), ...(videos ?? [])];
    return [...new Set(ids)].map((id) => all.find((m) => m.id === id)).filter((m): m is Media => !!m);
  }, [generated, selectedClips, exportId, imgs, videos]);
  const availablePhotoModels = imageModels?.filter((m) => m.installed === true) ?? [];

  useEffect(() => { if (brand?.colors[0]) setAccent(brand.colors[0]); }, [brand]);
  useEffect(() => {
    if (comfyCfg?.image_preset) setImagePreset(comfyCfg.image_preset);
  }, [comfyCfg?.image_preset]);
  useEffect(() => {
    const preferred = imageModels?.find((m) => m.key === comfyCfg?.image_preset && m.installed === true) ?? imageModels?.find((m) => m.installed === true);
    if (preferred) setImagePreset(preferred.key as typeof imagePreset);
  }, [imageModels, comfyCfg?.image_preset]);
  useEffect(() => {
    if (videoStatus?.presets.some((p) => p.key === videoPreset && p.installed === true)) return;
    const installed = videoStatus?.presets.find((p) => p.key === "wan21_fun_camera" && p.installed === true);
    if (installed) setVideoPreset("wan21_fun_camera");
  }, [videoStatus, videoPreset]);
  useEffect(() => {
    if (videoStatus?.presets.some((p) => p.key === t2vPreset && p.installed === true)) return;
    const installed = videoStatus?.presets.find((p) => p.key === "wan21_t2v" && p.installed === true)
      ?? videoStatus?.presets.find((p) => p.key === "wan22" && p.installed === true)
      ?? videoStatus?.presets.find((p) => p.key === "ltxv" && p.installed === true);
    if (installed) setT2vPreset(installed.key as typeof t2vPreset);
  }, [videoStatus, t2vPreset]);

  useEffect(() => {
    let alive = true;
    setCanvasReady(false);
    (async () => {
      const c = canvas.current;
      const layer = overlayCanvas.current;
      if (!c || !layer) return;
      const [W, H] = FORMATS[fmt];
      c.width = W; c.height = H; layer.width = W; layer.height = H;
      const ctx = c.getContext("2d");
      const overlayCtx = layer.getContext("2d");
      if (!ctx || !overlayCtx) return;
      ctx.fillStyle = "#101219"; ctx.fillRect(0, 0, W, H);
      if (base && baseMedia?.status !== "done") return;
      if (base) {
        const im = await loadImg(mediaFileUrl(base)).catch(() => null);
        if (!alive) return;
        if (im) {
          const scale = Math.max(W / im.width, H / im.height);
          ctx.drawImage(im, (W - im.width * scale) / 2, (H - im.height * scale) / 2, im.width * scale, im.height * scale);
        }
      }
      overlayCtx.clearRect(0, 0, W, H);
      const pad = W * 0.07;
      for (const target of [ctx, overlayCtx]) {
        if (pos !== "centre") {
          const gradient = pos === "haut" ? target.createLinearGradient(0, 0, 0, H * 0.62) : target.createLinearGradient(0, H, 0, H * 0.52);
          gradient.addColorStop(0, pos === "haut" ? "rgba(0,0,0,0.78)" : "rgba(0,0,0,0.82)");
          gradient.addColorStop(1, "rgba(0,0,0,0)");
          target.fillStyle = gradient; target.fillRect(0, 0, W, H);
        } else {
          target.fillStyle = "rgba(0,0,0,0.40)"; target.fillRect(W * 0.06, H * 0.34, W * 0.88, H * 0.32);
        }
      }
      const ts = Math.round(W * (fmt === "16:9" ? 0.052 : 0.075));
      const y0 = pos === "haut" ? pad + ts * 1.5 : pos === "centre" ? H / 2 - ts * 0.62 : H - pad - ts * 2.8;
      const x = pos === "centre" ? W / 2 : pad;
      const align = pos === "centre" ? "center" : "left";
      const paintText = (target: CanvasRenderingContext2D) => {
        target.textAlign = align; target.textBaseline = "alphabetic";
        target.fillStyle = "#fff"; target.font = `700 ${ts}px 'Sora Variable', sans-serif`;
        target.shadowColor = "rgba(0,0,0,.3)"; target.shadowBlur = ts * 0.08;
        target.fillText(title, x, y0, W - pad * 2);
        target.shadowBlur = 0;
        target.fillStyle = "rgba(255,255,255,.90)"; target.font = `400 ${Math.round(ts * 0.43)}px 'DM Sans Variable', sans-serif`;
        target.fillText(sub, x, y0 + ts * 0.75, W - pad * 2);
        const bh = ts * 0.92;
        target.font = `700 ${Math.round(ts * 0.38)}px 'DM Sans Variable', sans-serif`;
        const bw = Math.min(W - pad * 2, target.measureText(cta).width + bh * 1.4);
        const bx = pos === "centre" ? W / 2 - bw / 2 : pad;
        const by = y0 + ts * 1.18;
        target.fillStyle = accent; target.beginPath(); target.roundRect(bx, by, bw, bh, bh / 2); target.fill();
        target.fillStyle = "#101219"; target.textAlign = "center"; target.textBaseline = "middle";
        target.fillText(cta, bx + bw / 2, by + bh / 2, bw - bh * 0.4);
        target.textBaseline = "alphabetic"; target.shadowBlur = 0;
      };
      paintText(ctx); paintText(overlayCtx);
      if (brand?.logo_media_id) {
        const logo = await loadImg(mediaFileUrl(brand.logo_media_id)).catch(() => null);
        if (alive && logo) {
          const lh = W * 0.09; const lw = Math.min(W * 0.28, logo.width / logo.height * lh);
          const lx = W - pad - lw;
          const ly = pos === "haut" ? H - pad - lh : pad;
          // A translucent brand plate preserves contrast over both bright and dark source footage.
          // It is included in the transparent overlay too, so the exported MP4 matches the preview.
          for (const target of [ctx, overlayCtx]) {
            const bx = lx - pad * 0.22; const by = ly - pad * 0.16;
            const bw = lw + pad * 0.44; const bh = lh + pad * 0.32;
            target.fillStyle = "rgba(9,14,20,.76)";
            target.beginPath(); target.roundRect(bx, by, bw, bh, Math.min(bh * 0.22, pad * 0.18)); target.fill();
            target.strokeStyle = "rgba(213,168,91,.48)"; target.lineWidth = Math.max(1, W * 0.0015);
            target.stroke();
            target.drawImage(logo, lx, ly, lw, lh);
          }
        }
      } else if (brand) {
        for (const target of [ctx, overlayCtx]) {
          target.fillStyle = "#fff"; target.textAlign = "right"; target.font = `700 ${Math.round(ts * 0.38)}px 'Sora Variable', sans-serif`;
          target.fillText(brand.name, W - pad, pos === "haut" ? H - pad : pad + ts * 0.4, W * 0.35);
        }
      }
      if (alive) setCanvasReady(true);
    })().catch(() => { if (alive) setCanvasReady(false); });
    return () => { alive = false; };
  }, [base, baseMedia?.status, fmt, title, sub, cta, accent, pos, brand]);

  const changeFormat = (next: Fmt) => {
    if (next !== fmt && base) {
      setBase(null); setGenerated(null); setPosterId(null); setSelectedClips([]);
      toast.info("Format modifié : choisissez une nouvelle référence ou générez une photo dans ce format.");
    }
    setFmt(next);
  };
  const generatePhoto = () => {
    const selectedRef = base && !generated ? base : null;
    const brandContext = brand ? ` Identité de marque : ${brand.name}${brand.slogan ? `, slogan « ${brand.slogan} »` : ""}.` : "";
    const fullPrompt = `Photographie publicitaire ${adKind.toLowerCase()}. ${photoPrompt.trim()}${brandContext} Composition professionnelle, sans texte ni logo intégré dans l'image.`;
    image.mutate({ prompt: fullPrompt, model: "comfy", aspect_ratio: fmt, ref_media_id: selectedRef, comfy_preset: imagePreset, lora_name: imagePreset === "sdxl" ? adLoraName : null, lora_strength: adLoraStrength }, {
      onSuccess: (m) => { setBase(m.id); setGenerated(m.id); setPosterId(null); toast.success("Photo publicitaire envoyée à ComfyUI"); },
    });
  };
  const savePoster = () => {
    const url = canvas.current?.toDataURL("image/png");
    if (!url || !base || !canvasReady) return;
    upload.mutate({ data_url: url, source: "ad", prompt: `Affiche publicitaire ${fmt} · ${title}` }, { onSuccess: (m) => { setPosterId(m.id); toast.success("Affiche enregistrée dans la bibliothèque"); } });
  };
  const animateAd = () => {
    if (videoEngine !== "wan-t2v" && !base) return;
    const onSuccess = (m: Media) => {
      setSelectedClips((prev) => prev.includes(m.id) ? prev : [...prev, m.id]);
      toast.success("Plan publicitaire prêt · sélectionné pour le montage");
    };
    if (videoEngine === "smartmotion") {
      if (!base || !smStatus?.available) return;
      smartmotion.mutate({ prompt: `Publicité ${adKind.toLowerCase()} · ${title}`, ref_media_id: base, seconds: duration, fps: 24, output_size: "source", motion: cameraMotion }, { onSuccess });
      return;
    }
    if (videoEngine === "wan-t2v") {
      video.mutate({ prompt: photoPrompt.trim(), model: "comfy", mode: "text", duration: wanDuration, aspect_ratio: fmt, ref_media_id: null, comfy_preset: t2vPreset, camera_pose: "Static" }, { onSuccess });
      return;
    }
    if (!base) return;
    video.mutate({ prompt: photoPrompt.trim(), model: "comfy", mode: "image", duration: wanDuration, aspect_ratio: fmt, ref_media_id: base, comfy_preset: videoPreset, camera_pose: "Static" }, { onSuccess });
  };
  const composeAd = async () => {
    const overlay = overlayCanvas.current?.toDataURL("image/png");
    if (!overlay || !selectedClips.length) return;
    try {
      const output = await apiPost<Media>("/media/ads/compose", { clip_media_ids: selectedClips, overlay_data_url: overlay, title: title || "Publicité locale" });
      setExportId(output.id);
      toast.success("Assemblage local lancé · progression dans la bibliothèque");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Impossible de lancer l'export MP4");
    }
  };
  const addToSite = async (pid: string) => {
    if (!posterId) return;
    try {
      await apiPost(`/projects/${pid}/chat`, { message: `Intègre ce visuel publicitaire (${fmt}) dans le site, avec le titre « ${title} » et l'appel à l'action « ${cta} ».`, page: "index.html", selection: null, media_ids: [posterId] });
      toast.success("Visuel envoyé au site — intégration en cours"); setSiteOpen(false);
    } catch { toast.error("Ce site est occupé ou indisponible"); }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]" data-testid="ad-workshop">
      <section className="glass-vision space-y-5 rounded-3xl p-5">
        <header><p className="text-[10px] uppercase tracking-[.24em] text-amber-200">Studio de campagne</p><h2 className="mt-1 font-heading text-xl font-semibold">Du concept au spot</h2><p className="mt-1 text-xs text-slate-400">Photo locale → mouvement caméra → habillage graphique stable → MP4.</p></header>
        <div className="space-y-2"><Label htmlFor="ad-kind">Type de publicité</Label><select id="ad-kind" data-testid="ad-kind" value={adKind} onChange={(e) => setAdKind(e.target.value)} className={field}><option>Produit</option><option>Entreprise</option><option>Service</option><option>Réseaux sociaux</option><option>Campagne promotionnelle</option><option>Présentation de produit</option></select></div>
        <div className="space-y-2"><Label htmlFor="ad-prompt">Votre idée en français</Label><textarea id="ad-prompt" data-testid="ad-prompt" value={photoPrompt} onChange={(e) => setPhotoPrompt(e.target.value)} rows={4} placeholder="Ex. Un flacon de parfum bleu cobalt posé sur du marbre blanc, lumière dorée du soir, composition élégante et minimaliste…" className={cn(field, "resize-y")} /></div>
        <div className="space-y-2"><Label className="text-xs text-slate-400">Référence visuelle (facultatif)</Label><div className="flex gap-2 overflow-x-auto pb-1">{choices.slice(0, 18).map((m) => <button key={m.id} type="button" data-testid={`ad-reference-${m.id}`} onClick={() => { setBase(m.id); setGenerated(null); setPosterId(null); }} className={cn("size-14 shrink-0 overflow-hidden rounded-xl border-2", base === m.id ? "border-amber-300" : "border-transparent")}><img src={m.url!} alt={m.prompt} className="size-full object-cover" /></button>)}</div></div>
        <div className="space-y-2"><Label htmlFor="ad-format">Format de campagne</Label><div className="flex gap-2">{(Object.keys(FORMATS) as Fmt[]).map((f) => <Chip key={f} testid={`ad-format-${f}`} active={fmt === f} onClick={() => changeFormat(f)}>{f}</Chip>)}</div></div>
        <div className="grid gap-3 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="ad-brand">Identité de marque</Label><select id="ad-brand" data-testid="ad-brand" value={brandId} onChange={(e) => setBrandId(e.target.value)} className={field}><option value="">Sans marque</option>{brands?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div><div className="space-y-2"><Label htmlFor="ad-image-model">Moteur photo local</Label><select id="ad-image-model" data-testid="ad-image-model" value={imagePreset} onChange={(e) => setImagePreset(e.target.value as typeof imagePreset)} className={field}>{(imageModels ?? []).map((m) => <option key={m.key} value={m.key} disabled={m.installed !== true}>{m.label} · {m.installed === true ? "installé" : m.installed === false ? "absent" : "inconnu"}</option>)}</select></div></div>
        {adLoras?.map((l) => <article key={l.id} data-testid={`ad-lora-card-${l.id}`} className="rounded-xl border border-amber-200/20 p-3"><div className="space-y-1"><strong className="text-xs">{l.name}</strong><p className="text-[10px] text-slate-400">{l.category} · {l.description}</p>{l.comparison_preview ? <div className="grid grid-cols-2 gap-2" data-testid={`ad-lora-comparison-${l.id}`}><figure><img className="aspect-square w-full rounded-lg object-cover" src={l.comparison_preview.without_lora} alt="Même génération sans LoRA" /><figcaption className="text-center text-[10px]">SANS LoRA</figcaption></figure><figure><img className="aspect-square w-full rounded-lg object-cover" src={l.comparison_preview.with_lora} alt="Même génération avec LoRA" /><figcaption className="text-center text-[10px]">AVEC LoRA</figcaption></figure><a className="col-span-2 text-[10px] text-cyan-200 underline" href={l.comparison_preview.metadata}>Paramètres comparatifs</a></div> : <p data-testid={`ad-lora-comparison-pending-${l.id}`} className="text-[10px] text-slate-400">Comparaison contrôlée SANS / AVEC LoRA pas encore générée.</p>}<p className="text-[10px] text-amber-200">{l.selectable ? "Disponible · SDXL uniquement" : l.reason || (l.installed === false ? "LoRA absent" : "Non compatible / indisponible")} · {l.installed === true ? "installé" : l.installed === false ? "absent" : "état inconnu"} · intensité conseillée {l.strength} · {l.base_model}</p><p className="text-[10px] text-slate-500">{l.license} {l.restrictions}</p><div className="flex items-center gap-2"><a href={l.source_url} target="_blank" rel="noreferrer" className="text-[10px] text-cyan-200 underline">Source (aperçu non intégré)</a><button type="button" data-testid={`ad-lora-toggle-${l.id}`} disabled={!l.selectable} aria-pressed={adLoraName === l.filename} onClick={() => { setAdLoraName(adLoraName === l.filename ? null : l.filename); setAdLoraStrength(l.strength); }} className="rounded border border-white/15 px-2 py-1 text-[10px] disabled:opacity-40">{adLoraName === l.filename ? "Désactiver" : "Appliquer à la photo"}</button>{adLoraName === l.filename && <input aria-label="Intensité LoRA publicité" type="range" min="0" max="1.5" step="0.05" value={adLoraStrength} onChange={(e) => setAdLoraStrength(Number(e.target.value))} />}</div></div></article>)}
        <FxButton tone="vision" data-testid="ad-generate-photo" disabled={photoPrompt.trim().length < 3 || image.isPending || !availablePhotoModels.some((m) => m.key === imagePreset)} onClick={generatePhoto}><ImagePlus className="size-4" />{image.isPending ? "Photo en cours…" : "Générer la photo publicitaire"}</FxButton>
        <div className="space-y-3 rounded-2xl border border-white/10 bg-black/20 p-3"><div className="space-y-2"><Label htmlFor="ad-video-engine">Animation</Label><select id="ad-video-engine" data-testid="ad-video-engine" value={videoEngine} onChange={(e) => setVideoEngine(e.target.value as typeof videoEngine)} className={field}><option value="smartmotion" disabled={!base}>SmartMotion · caméra 2.5D (local)</option><option value="wan" disabled={!base || !videoStatus?.presets.some((p) => p.key === "wan21_fun_camera" && p.installed === true)}>Wan Fun Camera · génération I2V</option><option value="wan-t2v" disabled={!videoStatus?.presets.some((p) => (p.key === "wan21_t2v" || p.key === "wan22" || p.key === "ltxv") && p.installed === true)}>Wan · génération T2V</option></select></div>
          {videoEngine === "wan" ? <div className="space-y-2"><Label htmlFor="ad-wan-preset">Modèle vidéo réel</Label><select id="ad-wan-preset" data-testid="ad-wan-preset" value={videoPreset} onChange={(e) => setVideoPreset(e.target.value as typeof videoPreset)} className={field}>{(videoStatus?.presets ?? []).filter((p) => p.key === "wan21_fun_camera" || p.key === "wan22" || p.key === "ltxv").map((p) => <option key={p.key} value={p.key} disabled={p.installed !== true}>{p.label} · {p.installed === true ? "installé" : "absent"}</option>)}</select><div className="mt-2 space-y-2"><Label htmlFor="ad-wan-duration">Durée du plan Wan</Label><select id="ad-wan-duration" data-testid="ad-wan-duration" value={wanDuration} onChange={(e) => setWanDuration(e.target.value)} className={field}><option value="3">3 secondes</option><option value="5">5 secondes</option></select></div><p className="text-[11px] text-amber-200">Wan génère le mouvement des pixels; les textes/logo sont appliqués ensuite et restent nets. Cette génération est lente.</p></div> : videoEngine === "wan-t2v" ? <div className="space-y-2"><Label htmlFor="ad-t2v-preset">Modèle T2V</Label><select id="ad-t2v-preset" data-testid="ad-t2v-preset" value={t2vPreset} onChange={(e) => setT2vPreset(e.target.value as typeof t2vPreset)} className={field}>{(videoStatus?.presets ?? []).filter((p) => p.key === "wan21_t2v" || p.key === "wan22" || p.key === "ltxv").map((p) => <option key={p.key} value={p.key} disabled={p.installed !== true}>{p.label} · {p.installed === true ? "installé" : "absent"}</option>)}</select><div className="space-y-2"><Label htmlFor="ad-wan-duration">Durée du plan</Label><select id="ad-wan-duration" data-testid="ad-wan-duration" value={wanDuration} onChange={(e) => setWanDuration(e.target.value)} className={field}><option value="3">3 secondes</option><option value="5">5 secondes</option></select></div><p className="text-[11px] text-amber-200">Texte → vidéo génératif. Le prompt français est transmis tel quel. Le titre, logo et CTA sont composités après génération.</p></div> : <><div className="space-y-2"><Label htmlFor="ad-duration">Durée SmartMotion</Label><select id="ad-duration" data-testid="ad-duration" value={duration} onChange={(e) => setDuration(Number(e.target.value))} className={field}>{[5, 10, 15, 20, 30].map((d) => <option key={d} value={d}>{d} secondes</option>)}</select></div><div className="space-y-2"><Label htmlFor="ad-motion">Mouvement caméra</Label><select id="ad-motion" data-testid="ad-motion" value={cameraMotion} onChange={(e) => setCameraMotion(e.target.value as typeof cameraMotion)} className={field}><option value="push_in">Travelling avant doux</option><option value="pan_left">Panoramique gauche</option><option value="pan_right">Panoramique droite</option><option value="tilt_up">Inclinaison haut</option><option value="tilt_down">Inclinaison bas</option><option value="orbit_subtle">Arc latéral subtil</option><option value="static">Caméra fixe</option></select></div><p className="text-[11px] text-slate-400">SmartMotion déplace la caméra uniquement. Aucun mouvement d'objet n'est généré.</p></>}
          <FxButton tone="ghost" data-testid="ad-generate-video" disabled={smartmotion.isPending || video.isPending || (videoEngine === "smartmotion" && (smStatus?.available !== true || !base)) || (videoEngine === "wan" && !base) || (videoEngine === "wan-t2v" && (photoPrompt.trim().length < 3 || !videoStatus?.presets.some((p) => p.key === t2vPreset && p.installed === true)))} onClick={animateAd}><Film className="size-4" />{smartmotion.isPending || video.isPending ? "Plan en cours…" : videoEngine === "smartmotion" ? "Créer un plan animé" : videoEngine === "wan-t2v" ? "Générer le clip publicitaire T2V" : "Générer un plan Wan"}</FxButton>
        </div>
      </section>
      <section className="space-y-5">
        <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex min-h-[420px] items-center justify-center overflow-hidden rounded-3xl border border-white/10 bg-[#090b10] p-4"><motion.canvas key={fmt} initial={{ opacity: 0 }} animate={{ opacity: 1 }} ref={canvas} data-testid="ad-canvas" className="max-h-[72dvh] max-w-full rounded-xl shadow-[0_24px_90px_-28px_rgba(213,168,91,.38)]" /></div>
          <div className="glass-vision space-y-3 rounded-3xl p-5"><p className="text-[10px] uppercase tracking-[.2em] text-slate-400">Habillage graphique · aperçu en direct</p><Input data-testid="ad-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre commercial" className="border-white/10 bg-black/30" /><Input data-testid="ad-subtitle" value={sub} onChange={(e) => setSub(e.target.value)} placeholder="Promesse / sous-titre" className="border-white/10 bg-black/30" /><div className="flex gap-2"><Input data-testid="ad-cta" value={cta} onChange={(e) => setCta(e.target.value)} placeholder="Appel à l'action" className="border-white/10 bg-black/30" /><input data-testid="ad-accent" type="color" value={accent} onChange={(e) => setAccent(e.target.value)} aria-label="Couleur accent" className="h-10 w-12 rounded-lg border border-white/10 bg-transparent" /></div><div className="flex gap-2">{(["haut", "centre", "bas"] as const).map((p) => <Chip key={p} testid={`ad-pos-${p}`} active={pos === p} onClick={() => setPos(p)}>{p}</Chip>)}</div><p className="text-xs text-slate-400">Le calque typographique est ajouté après le mouvement vidéo pour préserver la lisibilité.</p>
            <div className="flex flex-wrap gap-2"><FxButton tone="vision" data-testid="ad-save-poster" disabled={!base || !canvasReady || upload.isPending} onClick={savePoster}><Megaphone className="size-4" />Enregistrer l'affiche PNG</FxButton>{posterId && <a href={mediaFileUrl(posterId)} download data-testid="ad-download-poster" className="fx-btn ghost"><Download className="size-4" />PNG</a>}<FxButton tone="ghost" data-testid="ad-add-to-site" disabled={!posterId} onClick={() => setSiteOpen(true)}><Globe2 className="size-4" />Ajouter au site</FxButton></div>
          </div>
        </div>
        <div className="glass-vision space-y-3 rounded-2xl p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-heading font-semibold">Montage vidéo</h3><p className="text-xs text-slate-400">Sélectionnez 1 à 8 plans terminés. Coupe franche, texte/logo net au-dessus du mouvement.</p></div><FxButton tone="vision" data-testid="ad-export-mp4" disabled={!selectedClips.length || selectedClips.some((id) => !completeClips.some((m) => m.id === id)) || !canvasReady} onClick={composeAd}><Download className="size-4" />Exporter le MP4 publicitaire</FxButton></div>
          <div className="flex flex-wrap gap-2">{completeClips.slice(0, 20).map((m) => <button key={m.id} type="button" data-testid={`ad-clip-${m.id}`} aria-pressed={selectedClips.includes(m.id)} onClick={() => setSelectedClips((prev) => prev.includes(m.id) ? prev.filter((id) => id !== m.id) : prev.length < 8 ? [...prev, m.id] : prev)} className={cn("rounded-xl border px-3 py-2 text-left text-xs", selectedClips.includes(m.id) ? "border-amber-300 bg-amber-300/10 text-white" : "border-white/10 text-slate-400")}>{m.prompt.slice(0, 48)} · {m.duration || "vidéo"}</button>)}{!completeClips.length && <p className="text-xs text-slate-500">Le plan généré apparaîtra ici lorsqu'il sera terminé.</p>}</div>{exportId && <p className="text-xs text-cyan-200" data-testid="ad-export-status">Export demandé · média {exportId} suivi dans la bibliothèque.</p>}</div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="ad-media-results"><AnimatePresence>{adMedia.map((m) => <MediaTile key={m.id} m={m} onCancel={() => cancel.mutate(m.id)} />)}</AnimatePresence>{!adMedia.length && <p className="text-xs text-slate-500">Les rendus de cette campagne apparaîtront ici.</p>}</div>
      </section>
      <canvas ref={overlayCanvas} className="hidden" aria-hidden="true" />
      <Dialog open={siteOpen} onOpenChange={setSiteOpen}><DialogContent className="border-cyan-400/25 bg-panel/95 backdrop-blur-2xl"><DialogHeader><DialogTitle className="font-heading">Ajouter l'affiche à un site</DialogTitle><DialogDescription>L'affiche PNG est intégrée à la section promotionnelle.</DialogDescription></DialogHeader><div className="max-h-80 space-y-2 overflow-y-auto">{projects?.filter((p) => p.status === "ready").map((p) => <button key={p.id} type="button" data-testid={`ad-site-${p.id}`} onClick={() => addToSite(p.id)} className="flex w-full items-center gap-3 rounded-xl border border-white/10 p-3 text-left hover:border-cyan-300/60">{p.thumbnail_url && <img src={p.thumbnail_url} alt="" className="size-10 rounded-lg object-cover" />}<span className="text-sm">{p.name}</span></button>)}{!projects?.some((p) => p.status === "ready") && <p className="text-sm text-slate-400">Aucun site prêt pour le moment.</p>}</div></DialogContent></Dialog>
    </div>
  );
}
