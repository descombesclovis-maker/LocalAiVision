import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Ban, Download, Film, ImagePlus, Loader2, Megaphone, Sparkles, Trash2, Upload, Volume2, Wand2, Globe2 } from "lucide-react";
import { toast } from "sonner";
import { FxButton } from "@/components/FxButton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fileToDataUrl, useBrands, useMedia, useMediaActions, useProjects, useSmartMotionStatus, useVideoModels } from "@/lib/hooks";
import { apiPost } from "@/lib/api";
import { useComfy, useImageModels, useVideoEngineStatus } from "@/lib/companyHooks";
import type { ImageRequest, Media, VideoRequest } from "@/lib/types";
import { mediaFileUrl } from "@/lib/types";
import { cn } from "@/lib/utils";

const field = "w-full rounded-xl border border-white/10 bg-black/30 p-3.5 text-sm outline-none transition-[border-color,box-shadow] focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(6,182,212,0.15)] placeholder:text-slate-500";

function Chip({ active, onClick, children, testid }: { active: boolean; onClick: () => void; children: React.ReactNode; testid: string }) {
  return (
    <button type="button" data-testid={testid} onClick={onClick} className={cn("rounded-full border px-3.5 py-1.5 text-xs font-medium transition-[border-color,background-color,color,box-shadow] duration-200", active ? "border-cyan-300/70 bg-cyan-500/20 text-white shadow-[0_0_18px_-4px_rgba(6,182,212,0.9)]" : "border-white/10 text-slate-400 hover:border-white/25 hover:text-white")}>
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
            <p className="text-xs text-slate-300" data-testid={`media-progress-${m.id}`}>{busy ? m.progress_label || "En cours…" : m.error || "Échec"}</p>
            {busy && <div className="h-1 w-3/4 overflow-hidden rounded-full bg-white/10"><div className="shimmer-bar h-full w-full bg-cyan-400/40" /></div>}
            {busy && onCancel && <FxButton size="sm" tone="ghost" data-testid={`media-cancel-${m.id}`} onClick={onCancel}><Ban className="size-3.5" /> Annuler</FxButton>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 p-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs text-slate-200">{m.prompt}</p>
          <p className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{m.model}{m.duration ? ` · ${m.duration}` : ""}{m.aspect_ratio ? ` · ${m.aspect_ratio}` : ""}</p>
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
  const [ref, setRef] = useState<string | null>(null);
  const { data } = useMedia("image");
  const { image } = useMediaActions();
  const { data: models } = useImageModels();
  const { data: comfyCfg } = useComfy();
  const [comfyPreset, setComfyPreset] = useState<string | null>(null);
  // Only installed presets are selectable. A null state (ComfyUI cannot list models) is kept, not treated as missing.
  const candidates = (models ?? []).filter((m) => m.installed !== false);
  const noneInstalled = !!models && models.length > 0 && models.every((m) => m.installed === false);
  const savedKey = comfyCfg?.image_preset ?? null;
  const choice =
    (comfyPreset && candidates.some((m) => m.key === comfyPreset) ? comfyPreset : null) ??
    candidates.find((m) => m.key === savedKey)?.key ??
    candidates[0]?.key ??
    savedKey;
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
        <textarea data-testid="photo-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={5} placeholder="Ex. Flacon de parfum ambré sur pierre volcanique, lumière rasante dorée, macro éditoriale…" className={cn(field, "resize-none")} />
        <div className="flex flex-wrap gap-2">
          {(["1:1", "4:5", "16:9", "9:16"] as const).map((a) => <Chip key={a} testid={`photo-aspect-${a}`} active={aspect === a} onClick={() => setAspect(a)}>{a}</Chip>)}
        </div>
        <div>
          <Label className="mb-2 block text-xs text-slate-400">Transformer une image (facultatif)</Label>
          <RefPicker value={ref} onChange={setRef} testid="photo-ref" />
        </div>
        <FxButton tone="vision" size="lg" className="w-full" data-testid="generate-photo-btn" disabled={prompt.trim().length < 3 || image.isPending || (model === "comfy" && noneInstalled)} onClick={() => image.mutate({ prompt, model, aspect_ratio: aspect, ref_media_id: ref, comfy_preset: model === "comfy" ? choice : null }, { onSuccess: () => toast.success("Photo en cours de création") })}>
          <Sparkles className="size-4" /> {ref ? "Transformer l'image" : "Générer la photo"}
        </FxButton>
      </div>
      <div className="grid content-start gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="photo-results">
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

export function VideoStudio() {
  const { data: models } = useVideoModels();
  const { data: comfyCfg } = useComfy();
  const { data: engineStatus } = useVideoEngineStatus();
  const { data: smartMotionStatus } = useSmartMotionStatus();
  const [model, setModel] = useState<VideoRequest["model"] | "smartmotion">("comfy");
  const [mode, setMode] = useState<VideoRequest["mode"]>("text");
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState("3");
  const [aspect, setAspect] = useState("16:9");
  const [ref, setRef] = useState<string | null>(null);
  const [comfyPreset, setComfyPreset] = useState<NonNullable<VideoRequest["comfy_preset"]>>("wan22");
  const [cameraPose, setCameraPose] = useState("Static");
  const [smartMotionMove, setSmartMotionMove] = useState<"push_in" | "pan_left" | "pan_right" | "tilt_up" | "tilt_down" | "orbit_subtle" | "static">("push_in");
  const [smartMotionSize, setSmartMotionSize] = useState<"source" | "1280x720" | "1920x1080">("source");
  const [presetInitialized, setPresetInitialized] = useState(false);
  const cfg = models?.find((m) => m.key === model);
  const chosenPreset = engineStatus?.presets.find((p) => p.key === comfyPreset);
  const needsImage = model === "smartmotion" || (model === "comfy" && comfyPreset === "wan21_fun_camera");
  const comfyUnavailable = model === "comfy" && (!chosenPreset || chosenPreset.installed !== true);
  const smartMotionUnavailable = model === "smartmotion" && smartMotionStatus?.available !== true;
  const { data } = useMedia("video");
  const { video, smartmotion, cancel } = useMediaActions();
  useEffect(() => {
    if (comfyCfg && !presetInitialized) {
      setComfyPreset(comfyCfg.video_preset);
      setPresetInitialized(true);
    }
  }, [comfyCfg, presetInitialized]);
  useEffect(() => {
    if (needsImage) setMode("image");
  }, [needsImage]);
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
  };
  return (
    <div className="grid gap-6 lg:grid-cols-[440px_1fr]">
      <div className="glass-vision space-y-5 rounded-3xl p-5">
        <div className="grid gap-3">
          {(models ?? []).map((m) => (
            <ModelCard key={m.key} testid={`video-model-${m.key}`} active={model === m.key} onClick={() => setModel(m.key)} title={m.label} tagline={m.tagline} badge={`${m.durations.join(" / ")}${m.audio ? " · son" : ""}`} />
          ))}
        </div>
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
            <Chip testid="video-mode-image" active={mode === "image"} onClick={() => setMode("image")}>Image → vidéo</Chip>
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
        <textarea data-testid="video-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} placeholder="Ex. Travelling lent autour d'une table dressée, vapeur, lumière de bougie, ambiance gastronomique…" className={cn(field, "resize-none")} />
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
          <p data-testid="video-local-note" className="flex items-center gap-1.5 text-xs text-emerald-200/80"><Sparkles className="size-3.5" /> Gratuit : rendu sur votre GPU via ComfyUI (plusieurs minutes possibles, sans son).</p>
        ) : (
          <p className="flex items-center gap-1.5 text-xs text-amber-200/80"><Volume2 className="size-3.5" /> Moteur payant de secours : la vidéo coûte nettement plus qu'une photo sur le solde de la clé universelle.</p>
        )}
        <FxButton tone="vision" size="lg" className="w-full" data-testid="generate-video-btn" disabled={prompt.trim().length < 3 || video.isPending || smartmotion.isPending || (mode === "image" && !ref) || comfyUnavailable || smartMotionUnavailable} onClick={() => {
          if (model === "smartmotion") {
            if (!ref) return;
            smartmotion.mutate({ prompt, ref_media_id: ref, seconds: Number(duration), fps: 24, output_size: smartMotionSize, motion: smartMotionMove }, { onSuccess: () => toast.success("SmartMotion lancé localement — progression visible dans la bibliothèque") });
          } else {
            video.mutate({ prompt, model, mode, duration, aspect_ratio: aspect, ref_media_id: mode === "image" ? ref : null, comfy_preset: model === "comfy" ? comfyPreset : null, camera_pose: model === "comfy" ? cameraPose : "Static" }, { onSuccess: () => toast.success("Vidéo envoyée au moteur — elle continue même si vous changez d'écran") });
          }
        }}>
          <Film className="size-4" /> {model === "smartmotion" ? "Animer l'image" : "Générer la vidéo"}
        </FxButton>
      </div>
      <div className="grid content-start gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="video-results">
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
  const { data: brands } = useBrands();
  const { data: projects } = useProjects("", "");
  const { upload } = useMediaActions();
  const [base, setBase] = useState<string | null>(null);
  const [fmt, setFmt] = useState<Fmt>("1:1");
  const [brandId, setBrandId] = useState("");
  const [title, setTitle] = useState("L'art du goût");
  const [sub, setSub] = useState("Menu dégustation · réservez votre table");
  const [cta, setCta] = useState("Réserver");
  const [accent, setAccent] = useState("#06B6D4");
  const [pos, setPos] = useState<"bas" | "haut" | "centre">("bas");
  const [saved, setSaved] = useState<Media | null>(null);
  const [siteOpen, setSiteOpen] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const brand = brands?.find((b) => b.id === brandId);
  const choices = useMemo(() => (imgs ?? []).filter((m) => m.status === "done" && m.source !== "ad").slice(0, 24), [imgs]);

  useEffect(() => { if (brand?.colors[0]) setAccent(brand.colors[0]); }, [brand]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const c = canvas.current;
      if (!c) return;
      const [W, H] = FORMATS[fmt];
      c.width = W; c.height = H;
      const ctx = c.getContext("2d")!;
      ctx.fillStyle = "#0b0d14"; ctx.fillRect(0, 0, W, H);
      if (base) {
        const im = await loadImg(mediaFileUrl(base)).catch(() => null);
        if (!alive || !im) return;
        const s = Math.max(W / im.width, H / im.height);
        ctx.drawImage(im, (W - im.width * s) / 2, (H - im.height * s) / 2, im.width * s, im.height * s);
      }
      const g = pos === "haut" ? ctx.createLinearGradient(0, 0, 0, H * 0.6) : ctx.createLinearGradient(0, H, 0, H * 0.35);
      g.addColorStop(0, "rgba(0,0,0,0.78)"); g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = pos === "centre" ? "rgba(0,0,0,0.42)" : g; ctx.fillRect(0, 0, W, H);
      const pad = W * 0.07;
      const ts = Math.round(W * (fmt === "16:9" ? 0.052 : 0.082));
      const y0 = pos === "haut" ? pad + ts * 1.6 : pos === "centre" ? H / 2 - ts * 0.4 : H - pad - ts * 2.6;
      ctx.textAlign = pos === "centre" ? "center" : "left";
      const x = pos === "centre" ? W / 2 : pad;
      ctx.fillStyle = "#fff"; ctx.font = `600 ${ts}px 'Sora Variable', sans-serif`;
      ctx.fillText(title, x, y0, W - pad * 2);
      ctx.fillStyle = "rgba(255,255,255,0.82)"; ctx.font = `400 ${Math.round(ts * 0.42)}px 'DM Sans Variable', sans-serif`;
      ctx.fillText(sub, x, y0 + ts * 0.75, W - pad * 2);
      const bh = ts * 0.95;
      ctx.font = `600 ${Math.round(ts * 0.4)}px 'DM Sans Variable', sans-serif`;
      const bw = ctx.measureText(cta).width + bh * 1.2;
      const bx = pos === "centre" ? W / 2 - bw / 2 : pad;
      const by = y0 + ts * 1.15;
      ctx.fillStyle = accent; ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, bh / 2); ctx.fill();
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(cta, bx + bw / 2, by + bh / 2 + 1); ctx.textBaseline = "alphabetic";
      if (brand?.logo_media_id) {
        const logo = await loadImg(mediaFileUrl(brand.logo_media_id)).catch(() => null);
        if (alive && logo) {
          const lh = W * 0.09; const lw = (logo.width / logo.height) * lh;
          const ly = pos === "haut" ? H - pad - lh : pad;
          ctx.drawImage(logo, W - pad - lw, ly, lw, lh);
        }
      } else if (brand) {
        ctx.fillStyle = "#fff"; ctx.textAlign = "right"; ctx.font = `600 ${Math.round(ts * 0.38)}px 'Sora Variable', sans-serif`;
        ctx.fillText(brand.name, W - pad, pos === "haut" ? H - pad : pad + ts * 0.4);
      }
    })();
    return () => { alive = false; };
  }, [base, fmt, title, sub, cta, accent, pos, brand]);

  const save = () => {
    const url = canvas.current?.toDataURL("image/png");
    if (!url) return;
    upload.mutate({ data_url: url, source: "ad", prompt: `Publicité ${fmt} · ${title}` }, { onSuccess: (m) => { setSaved(m); toast.success("Visuel publicitaire enregistré"); } });
  };
  const addToSite = async (pid: string) => {
    if (!saved) return;
    try {
      await apiPost(`/projects/${pid}/chat`, { message: `Intègre ce visuel publicitaire (${fmt}) dans le site, dans une section promotionnelle soignée, avec un lien vers l'appel à l'action « ${cta} ».`, page: "index.html", selection: null, media_ids: [saved.id] });
      toast.success("Visuel envoyé au site — intégration en cours");
      setSiteOpen(false);
    } catch {
      toast.error("Ce site est occupé ou indisponible");
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[400px_1fr]">
      <div className="glass-vision space-y-4 rounded-3xl p-5">
        <div>
          <Label className="mb-2 block text-xs text-slate-400">Image de base</Label>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {choices.map((m) => (
              <button key={m.id} type="button" data-testid={`ad-base-${m.id}`} onClick={() => setBase(m.id)} className={cn("size-16 shrink-0 overflow-hidden rounded-xl border-2 transition-[border-color,transform] hover:scale-105", base === m.id ? "border-cyan-300" : "border-transparent")}>
                <img src={m.url!} alt="" className="size-full object-cover" />
              </button>
            ))}
            {!choices.length && <p className="text-xs text-slate-500">Générez d'abord une photo.</p>}
          </div>
        </div>
        <div className="flex gap-2">{(Object.keys(FORMATS) as Fmt[]).map((f) => <Chip key={f} testid={`ad-format-${f}`} active={fmt === f} onClick={() => setFmt(f)}>{f}</Chip>)}</div>
        <div className="space-y-1.5">
          <Label className="text-xs text-slate-400">Marque (logo réel)</Label>
          <select data-testid="ad-brand" value={brandId} onChange={(e) => setBrandId(e.target.value)} className={cn(field, "p-2.5")}>
            <option value="">Sans marque</option>
            {brands?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        <Input data-testid="ad-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre" className="border-white/10 bg-black/30" />
        <Input data-testid="ad-subtitle" value={sub} onChange={(e) => setSub(e.target.value)} placeholder="Sous-titre" className="border-white/10 bg-black/30" />
        <div className="flex gap-2">
          <Input data-testid="ad-cta" value={cta} onChange={(e) => setCta(e.target.value)} placeholder="Appel à l'action" className="border-white/10 bg-black/30" />
          <input data-testid="ad-accent" type="color" value={accent} onChange={(e) => setAccent(e.target.value)} className="h-9 w-12 cursor-pointer rounded-md border border-white/10 bg-transparent" aria-label="Couleur" />
        </div>
        <div className="flex gap-2">{(["haut", "centre", "bas"] as const).map((p) => <Chip key={p} testid={`ad-pos-${p}`} active={pos === p} onClick={() => setPos(p)}>{p}</Chip>)}</div>
        <div className="flex flex-wrap gap-2 pt-1">
          <FxButton tone="vision" data-testid="ad-save" disabled={upload.isPending} onClick={save}><Megaphone className="size-4" /> Enregistrer</FxButton>
          <FxButton tone="ghost" data-testid="ad-add-to-site" disabled={!saved} onClick={() => setSiteOpen(true)}><Globe2 className="size-4" /> Ajouter à un site</FxButton>
          {saved?.url && <a href={saved.url} download className="fx-btn ghost" data-testid="ad-download"><span className="fx-shine" /><span className="relative z-10 inline-flex items-center gap-2"><Download className="size-4" /> PNG</span></a>}
        </div>
      </div>
      <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-white/10 bg-black/40 p-6">
        <motion.canvas key={fmt} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} ref={canvas} data-testid="ad-canvas" className="max-h-[70dvh] max-w-full rounded-xl shadow-[0_30px_100px_-30px_rgba(6,182,212,0.7)]" />
      </div>
      <Dialog open={siteOpen} onOpenChange={setSiteOpen}>
        <DialogContent className="border-cyan-400/25 bg-panel/95 backdrop-blur-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Ajouter à un site</DialogTitle>
            <DialogDescription>Le moteur intégrera ce visuel dans une section promotionnelle, de façon ciblée.</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {projects?.filter((p) => p.status === "ready").map((p) => (
              <button key={p.id} type="button" data-testid={`ad-site-${p.id}`} onClick={() => addToSite(p.id)} className="flex w-full items-center gap-3 rounded-xl border border-white/10 p-3 text-left transition-colors hover:border-cyan-300/60 hover:bg-cyan-500/10">
                {p.thumbnail_url ? <img src={p.thumbnail_url} alt="" className="size-10 rounded-lg object-cover" /> : <Wand2 className="size-5" />}
                <span className="text-sm">{p.name}</span>
              </button>
            ))}
            {!projects?.some((p) => p.status === "ready") && <p className="text-sm text-slate-400">Aucun site prêt pour le moment.</p>}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
