import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { Clapperboard, Crown, Feather, Palette, Sparkles, Wand2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FxButton } from "@/components/FxButton";
import { useBrands, useCreateProject } from "@/lib/hooks";
import type { Llm, Mode, SiteEngine, StyleOptions } from "@/lib/types";
import { cn } from "@/lib/utils";

const LLM_LABELS: Record<Llm, string> = { local: "Moteur local gratuit (Ollama / LM Studio)", claude: "Claude Sonnet 4.5 (secours payant)", gpt: "GPT-5.2", gemini: "Gemini 3.1 Pro" };
const IDEAS = [
  "Boutique en ligne de bougies parfumées artisanales « Atelier Lueur », catalogue, variantes de parfums et panier.",
  "Agence immobilière premium sur la Côte d'Azur, biens d'exception filtrables, estimation et prise de rendez-vous.",
  "Studio de design d'intérieur à Bordeaux : galerie de réalisations et demande de devis.",
];

export function NewProjectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const nav = useNavigate();
  const create = useCreateProject();
  const { data: brands } = useBrands();
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<Mode>("libre");
  const [llm, setLlm] = useState<Llm>("local");
  const [engine, setEngine] = useState<SiteEngine>("premium");
  const [heroVideo, setHeroVideo] = useState(false);
  const [brand, setBrand] = useState("none");
  const [showStyle, setShowStyle] = useState(false);
  const [style, setStyle] = useState<StyleOptions>({ mood: "", colors: "", fonts: "", references: "" });

  const submit = () => {
    const hasStyle = Object.values(style).some(Boolean);
    create.mutate(
      { prompt, name, mode, llm, engine, hero_video: mode === "pro" && heroVideo, brand_id: brand === "none" ? null : brand, style: hasStyle ? style : null },
      { onSuccess: (p) => { onOpenChange(false); nav(`/web/p/${p.id}`); } },
    );
  };
  const brandLabel = (v: string) => (v === "none" ? "Aucune marque" : brands?.find((b) => b.id === v)?.name ?? "Marque");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92dvh] overflow-y-auto border-violet-400/25 bg-panel/95 backdrop-blur-2xl sm:max-w-2xl" data-testid="new-project-dialog">
        <DialogHeader>
          <p className="eyebrow text-violet-300">Nouveau projet LocalAiWeb</p>
          <DialogTitle className="font-heading text-2xl">Décrivez le site de vos rêves</DialogTitle>
          <DialogDescription>Le moteur analyse, conçoit, illustre, code et contrôle votre site. Une seule question vous sera posée si c'est vraiment nécessaire.</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div className="relative">
            <Textarea
              data-testid="new-project-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex. Restaurant bistronomique à Nantes, cuisine de saison, terrasse… je veux la carte et la réservation en ligne."
              className="min-h-36 resize-none rounded-xl border-white/10 bg-black/30 p-4 text-[15px] leading-relaxed focus-visible:border-violet-400/60 focus-visible:ring-violet-500/30"
            />
            <span className="pointer-events-none absolute bottom-3 right-3 font-mono text-[10px] text-slate-500">{prompt.length}/4000</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {IDEAS.map((i, k) => (
              <button key={k} type="button" data-testid={`idea-chip-${k}`} onClick={() => setPrompt(i)} className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-left text-xs text-slate-300 transition-[border-color,color,transform] duration-200 hover:-translate-y-0.5 hover:border-violet-400/50 hover:text-white">
                {i.slice(0, 46)}…
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            {([
              { v: "libre", t: "Libre", d: "4-5 pages · 3 images rapides", I: Feather },
              { v: "pro", t: "Pro", d: "5-7 pages · 5 images qualité max", I: Crown },
            ] as const).map(({ v, t, d, I }) => (
              <button
                key={v}
                type="button"
                data-testid={`mode-${v}`}
                onClick={() => setMode(v)}
                className={cn(
                  "relative overflow-hidden rounded-xl border p-4 text-left transition-[border-color,background-color,box-shadow] duration-300",
                  mode === v ? "border-violet-400/70 bg-violet-500/15 shadow-[0_0_30px_-8px_rgba(139,92,246,0.8)]" : "border-white/10 bg-white/[0.02] hover:border-white/25",
                )}
              >
                <I className={cn("mb-2 size-5", mode === v ? "text-violet-200" : "text-slate-400")} />
                <p className="font-heading font-semibold">{t}</p>
                <p className="text-xs text-slate-400">{d}</p>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-black/20 p-1" data-testid="new-project-engine">
            {([
              { v: "premium", t: "Moteur Premium", d: "Sections animées haut de gamme, unique à chaque site, idéal en local" },
              { v: "code", t: "Code libre", d: "L'IA écrit tout le code (meilleur avec Claude)" },
            ] as const).map((o) => (
              <button key={o.v} type="button" data-testid={`engine-${o.v}`} onClick={() => setEngine(o.v)} className={cn("rounded-lg px-3 py-2.5 text-left transition-[background-color,color] duration-300", engine === o.v ? "bg-gradient-to-br from-violet-500/30 to-cyan-500/20 text-white" : "text-slate-400 hover:text-slate-200")}>
                <p className="text-sm font-semibold">{o.t}</p>
                <p className="text-[11px] leading-snug opacity-80">{o.d}</p>
              </button>
            ))}
          </div>

          <label
            data-testid="hero-video-option"
            className={cn("flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-[border-color,opacity] duration-300", mode === "pro" ? "border-cyan-400/25 bg-cyan-500/[0.06]" : "border-white/10 opacity-50")}
          >
            <Clapperboard className="size-4 shrink-0 text-cyan-300" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-white">Vidéo d'en-tête</span>
              <span className="block text-[11px] leading-snug text-slate-400">
                {mode === "pro" ? "Boucle animée de 3 s créée à partir de l'image principale avec Wan 2.2 en local (environ 5 à 10 min de plus sur RTX 3060)" : "Disponible en mode Pro"}
              </span>
            </span>
            <Switch data-testid="hero-video-switch" checked={mode === "pro" && heroVideo} disabled={mode !== "pro"} onCheckedChange={(v: boolean) => setHeroVideo(v)} />
          </label>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-400">Nom (facultatif)</Label>
              <Input data-testid="new-project-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Déduit du brief" className="border-white/10 bg-black/30" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-400">Moteur IA</Label>
              <Select value={llm} onValueChange={(v: string) => setLlm(v as Llm)}>
                <SelectTrigger data-testid="new-project-llm" className="w-full border-white/10 bg-black/30"><SelectValue>{(v) => LLM_LABELS[v as Llm]}</SelectValue></SelectTrigger>
                <SelectContent>
                  {(Object.keys(LLM_LABELS) as Llm[]).map((k) => <SelectItem key={k} value={k}>{LLM_LABELS[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-400">Identité de marque</Label>
              <Select value={brand} onValueChange={(v: string) => setBrand(v)}>
                <SelectTrigger data-testid="new-project-brand" className="w-full border-white/10 bg-black/30"><SelectValue>{(v) => brandLabel(v as string)}</SelectValue></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucune marque</SelectItem>
                  {brands?.map((b) => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <button type="button" data-testid="toggle-style-window" onClick={() => setShowStyle((s) => !s)} className="flex items-center gap-2 text-sm text-violet-300 transition-colors hover:text-white">
            <Palette className="size-4" /> {showStyle ? "Masquer" : "Ajouter"} des préférences de style (facultatif)
          </button>
          <AnimatePresence>
            {showStyle && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="grid gap-3 rounded-xl border border-white/10 bg-black/20 p-4 sm:grid-cols-2">
                  {([
                    ["mood", "Ambiance", "Ex. éditorial, minéral, chaleureux"],
                    ["colors", "Couleurs", "Ex. noir charbon, or, crème"],
                    ["fonts", "Typographies", "Ex. serif élégante"],
                    ["references", "Références", "Ex. sites que vous aimez"],
                  ] as const).map(([k, l, ph]) => (
                    <div key={k} className="space-y-1.5">
                      <Label className="text-xs text-slate-400">{l}</Label>
                      <Input data-testid={`style-${k}`} value={style[k]} onChange={(e) => setStyle({ ...style, [k]: e.target.value })} placeholder={ph} className="border-white/10 bg-black/30" />
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex items-center justify-between gap-3 pt-1">
            <p className="flex items-center gap-1.5 text-xs text-slate-500"><Sparkles className="size-3.5" /> {llm === "local" ? "Gratuit : Ollama + ComfyUI sur votre PC" : "Moteur payant : déduit du solde de la clé universelle"}</p>
            <FxButton size="lg" data-testid="new-project-submit" disabled={prompt.trim().length < 8 || create.isPending} onClick={submit}>
              <Wand2 className="size-4" /> {create.isPending ? "Lancement…" : "Générer le site"}
            </FxButton>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
