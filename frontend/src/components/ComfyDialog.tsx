import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ImageIcon, PlugZap, Clapperboard } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FxButton } from "@/components/FxButton";
import { useComfy, useComfyPresets, useSaveComfy, useTestComfy } from "@/lib/companyHooks";
import type { ComfySettings } from "@/lib/companyTypes";
import { cn } from "@/lib/utils";

const mono = "border-white/10 bg-black/30 font-mono text-xs";

function PresetRow<K extends string>({ items, value, onPick, testid }: { items: { key: string; label: string }[]; value: K; onPick: (k: K) => void; testid: string }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((p) => (
        <button
          key={p.key}
          type="button"
          data-testid={`${testid}-${p.key}`}
          onClick={() => onPick(p.key as K)}
          className={cn("rounded-full border px-3 py-1 text-xs transition-[border-color,background-color,color] duration-200", value === p.key ? "border-cyan-300/60 bg-cyan-500/15 text-white" : "border-white/10 text-slate-400 hover:border-white/25 hover:text-white")}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

export function ComfyDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { data } = useComfy();
  const { data: presets } = useComfyPresets();
  const save = useSaveComfy();
  const test = useTestComfy();
  const [cfg, setCfg] = useState<ComfySettings | null>(null);
  const [advanced, setAdvanced] = useState(false);

  useEffect(() => {
    if (open && data) setCfg(data);
    if (!open) test.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, data]);

  if (!cfg || !presets) return null;
  const set = (patch: Partial<ComfySettings>) => setCfg({ ...cfg, ...patch });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="comfy-dialog" className="max-h-[90dvh] max-w-xl overflow-y-auto border-white/10 bg-panel/95 backdrop-blur-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading">ComfyUI · photos, retouches, pubs & vidéos</DialogTitle>
          <DialogDescription className="text-slate-400">Rendu 100 % local et gratuit sur votre carte graphique.</DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="cf-url">Adresse de ComfyUI</Label>
          <Input id="cf-url" data-testid="comfy-url" value={cfg.base_url} onChange={(e) => set({ base_url: e.target.value })} className={mono} />
          <p className="text-[11px] text-slate-500">ComfyUI portable : 8188 · ComfyUI Desktop : souvent 8000.</p>
        </div>

        <div className="space-y-2 rounded-2xl border border-white/[0.07] bg-black/20 p-3">
          <p className="eyebrow flex items-center gap-1.5 text-slate-400"><ImageIcon className="size-3.5" /> Photos</p>
          <PresetRow items={presets.image} value={cfg.image_preset} testid="comfy-image-preset" onPick={(k) => set({ image_preset: k, ...presets.image.find((p) => p.key === k)!.files })} />
          <Input data-testid="comfy-image-checkpoint" value={cfg.image_checkpoint} onChange={(e) => set({ image_checkpoint: e.target.value })} className={mono} />
        </div>

        <div className="space-y-2 rounded-2xl border border-white/[0.07] bg-black/20 p-3">
          <p className="eyebrow flex items-center gap-1.5 text-slate-400"><Clapperboard className="size-3.5" /> Vidéos</p>
          <PresetRow items={presets.video} value={cfg.video_preset} testid="comfy-video-preset" onPick={(k) => set({ video_preset: k, ...presets.video.find((p) => p.key === k)!.files })} />
          <Input data-testid="comfy-video-model" value={cfg.video_model} onChange={(e) => set({ video_model: e.target.value })} className={mono} />
          <div className="grid grid-cols-2 gap-2">
            <Input data-testid="comfy-video-te" value={cfg.video_text_encoder} onChange={(e) => set({ video_text_encoder: e.target.value })} className={mono} placeholder="encodeur texte" />
            <Input data-testid="comfy-video-vae" value={cfg.video_vae} onChange={(e) => set({ video_vae: e.target.value })} className={mono} placeholder="VAE (Wan uniquement)" disabled={cfg.video_preset === "ltxv"} />
          </div>
        </div>

        <button type="button" data-testid="comfy-advanced-toggle" onClick={() => setAdvanced((v) => !v)} className="text-left text-xs text-cyan-300 hover:text-cyan-200">
          {advanced ? "Masquer" : "Utiliser mes propres workflows ComfyUI (export API)"}
        </button>
        {advanced && (
          <div className="space-y-2">
            <p className="text-[11px] leading-relaxed text-slate-500">
              Placeholders : {"{{PROMPT}} {{NEGATIVE}} {{WIDTH}} {{HEIGHT}} {{SEED}} {{LENGTH}} {{IMAGE}}"}. Laissez vide pour les workflows intégrés.
            </p>
            <Textarea data-testid="comfy-custom-image" rows={4} value={cfg.custom_image_workflow} onChange={(e) => set({ custom_image_workflow: e.target.value })} placeholder="Workflow photo (JSON API)" className={mono} />
            <Textarea data-testid="comfy-custom-video" rows={4} value={cfg.custom_video_workflow} onChange={(e) => set({ custom_video_workflow: e.target.value })} placeholder="Workflow vidéo (JSON API)" className={mono} />
          </div>
        )}

        {test.data && (
          <div data-testid="comfy-test-result" className={cn("flex gap-2 rounded-lg border px-3 py-2 text-xs leading-relaxed", test.data.ok ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-amber-400/30 bg-amber-500/10 text-amber-100")}>
            {test.data.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0" />}
            {test.data.message}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <FxButton tone="ghost" size="sm" data-testid="comfy-test" disabled={test.isPending} onClick={() => test.mutate(cfg)}>
            <PlugZap className="size-4" /> {test.isPending ? "Test…" : "Tester"}
          </FxButton>
          <FxButton tone="vision" size="sm" data-testid="comfy-save" disabled={save.isPending} onClick={() => save.mutate(cfg, { onSuccess: () => onOpenChange(false) })}>
            Enregistrer
          </FxButton>
        </div>
      </DialogContent>
    </Dialog>
  );
}
