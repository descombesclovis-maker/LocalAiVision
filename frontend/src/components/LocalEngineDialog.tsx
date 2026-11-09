import { useEffect, useState } from "react";
import { Cpu, PlugZap, CheckCircle2, AlertTriangle } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FxButton } from "@/components/FxButton";
import { useLocalEngine, useSaveLocalEngine, useTestLocalEngine } from "@/lib/companyHooks";
import type { LocalEngine } from "@/lib/companyTypes";
import { cn } from "@/lib/utils";

const PRESETS: Record<LocalEngine["kind"], { label: string; url: string; hint: string }> = {
  ollama: { label: "Ollama", url: "http://localhost:11434", hint: "ollama pull qwen2.5-coder:14b  (≈ 9 Go, tient dans les 12 Go d'une RTX 3060)" },
  openai: { label: "LM Studio / compatible OpenAI", url: "http://localhost:1234/v1", hint: "LM Studio → Developer → Start server, puis chargez un modèle" },
};

export function LocalEngineDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { data } = useLocalEngine();
  const save = useSaveLocalEngine();
  const test = useTestLocalEngine();
  const [cfg, setCfg] = useState<LocalEngine | null>(null);

  useEffect(() => {
    if (open && data) setCfg(data);
    if (!open) test.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, data]);

  if (!cfg) return null;
  const set = (patch: Partial<LocalEngine>) => setCfg({ ...cfg, ...patch });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="local-engine-dialog" className="max-w-lg border-white/10 bg-panel/95 backdrop-blur-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-heading"><Cpu className="size-5 text-violet-300" /> Moteur IA local</DialogTitle>
          <DialogDescription className="text-slate-400">
            100 % indépendant et gratuit : la génération tourne sur votre PC (RTX 3060) via Ollama ou LM Studio. Aucune image payante :
            le site mise sur la typographie et des compositions CSS.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-2">
          {(Object.keys(PRESETS) as LocalEngine["kind"][]).map((k) => (
            <button
              key={k}
              type="button"
              data-testid={`local-engine-kind-${k}`}
              onClick={() => set({ kind: k, base_url: PRESETS[k].url })}
              className={cn(
                "rounded-xl border px-3 py-3 text-left text-sm transition-[border-color,background-color] duration-200",
                cfg.kind === k ? "border-violet-400/60 bg-violet-500/15 text-white" : "border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/25",
              )}
            >
              {PRESETS[k].label}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="le-url">Adresse du serveur</Label>
            <Input id="le-url" data-testid="local-engine-url" value={cfg.base_url} onChange={(e) => set({ base_url: e.target.value })} className="border-white/10 bg-black/30 font-mono text-xs" />
          </div>
          <div className="grid grid-cols-[1fr_120px] gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="le-model">Modèle</Label>
              <Input id="le-model" data-testid="local-engine-model" value={cfg.model} onChange={(e) => set({ model: e.target.value })} className="border-white/10 bg-black/30 font-mono text-xs" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="le-ctx">Contexte</Label>
              <Input id="le-ctx" type="number" data-testid="local-engine-ctx" value={cfg.num_ctx} onChange={(e) => set({ num_ctx: Number(e.target.value) || 16384 })} className="border-white/10 bg-black/30 font-mono text-xs" />
            </div>
          </div>
          <p className="rounded-lg border border-white/[0.06] bg-black/30 px-3 py-2 font-mono text-[11px] text-slate-400" data-testid="local-engine-hint">{PRESETS[cfg.kind].hint}</p>
          {test.data?.models.length ? (
            <div className="flex flex-wrap gap-1.5" data-testid="local-engine-models">
              {test.data.models.map((m) => (
                <button key={m} type="button" onClick={() => set({ model: m })} className="rounded-full border border-white/10 px-2.5 py-0.5 font-mono text-[11px] text-slate-300 transition-colors hover:border-violet-400/50 hover:text-white">{m}</button>
              ))}
            </div>
          ) : null}
          {test.data && (
            <div
              data-testid="local-engine-test-result"
              className={cn("flex gap-2 rounded-lg border px-3 py-2 text-xs leading-relaxed", test.data.ok ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-amber-400/30 bg-amber-500/10 text-amber-100")}
            >
              {test.data.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0" />}
              {test.data.message}
            </div>
          )}
          <p className="text-[11px] leading-relaxed text-slate-500">
            Version en ligne : le serveur ne voit pas votre PC. Le moteur local fonctionne quand LocalAiStudio est lancé sur la même machine
            qu'Ollama (ou si vous exposez Ollama via une URL publique).
          </p>
        </div>

        <div className="flex justify-end gap-2">
          <FxButton tone="ghost" size="sm" data-testid="local-engine-test" disabled={test.isPending} onClick={() => test.mutate(cfg)}>
            <PlugZap className="size-4" /> {test.isPending ? "Test…" : "Tester la connexion"}
          </FxButton>
          <FxButton size="sm" data-testid="local-engine-save" disabled={save.isPending} onClick={() => save.mutate(cfg, { onSuccess: () => onOpenChange(false) })}>
            Enregistrer
          </FxButton>
        </div>
      </DialogContent>
    </Dialog>
  );
}
