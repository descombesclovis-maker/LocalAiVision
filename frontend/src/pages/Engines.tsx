import { useState } from "react";
import { motion } from "motion/react";
import { CheckCircle2, Cable, Copy, Cpu, Download, HardDrive, Image as ImageIcon, Loader2, Settings2, AlertTriangle, Terminal } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { FxButton } from "@/components/FxButton";
import { LocalEngineDialog } from "@/components/LocalEngineDialog";
import { ComfyDialog } from "@/components/ComfyDialog";
import { GpuQueueList } from "@/components/GpuQueue";
import { DiagnosticPanel } from "@/components/DiagnosticPanel";
import { useSearchParams } from "react-router-dom";
import { useKitInfo } from "@/lib/companyHooks";
import { useComfy, useComfyStatus, useLocalEngine, useLocalEngineStatus } from "@/lib/companyHooks";
import { cn } from "@/lib/utils";

function Status({ loading, ok, message, testid }: { loading: boolean; ok?: boolean; message?: string; testid: string }) {
  return (
    <div data-testid={testid} className={cn("flex gap-2 rounded-xl border px-3 py-2 text-xs leading-relaxed", loading ? "border-white/10 text-slate-400" : ok ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" : "border-amber-400/30 bg-amber-500/10 text-amber-100")}>
      {loading ? <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" /> : ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0" /> : <AlertTriangle className="mt-0.5 size-4 shrink-0" />}
      <span>{loading ? "Vérification…" : message}</span>
    </div>
  );
}

const TUNNELS = [
  { k: "ollama", label: "Ollama", cmd: "cloudflared tunnel --url http://localhost:11434 --http-host-header localhost:11434" },
  { k: "comfy", label: "ComfyUI", cmd: "cloudflared tunnel --url http://localhost:8188" },
];

const STEPS = [
  { t: "Téléchargez le kit", d: "Code complet de LocalAiStudio + scripts Windows." },
  { t: "Lancez install.ps1", d: "Python, Node, MongoDB, Ollama et le modèle qwen2.5-coder:14b, installés automatiquement." },
  { t: "Installez ComfyUI + modèles", d: "ComfyUI Desktop, puis download-models.ps1 (FLUX dev, Wan 2.2)." },
  { t: "start-localaistudio.bat", d: "Ouvre http://localhost:3000 : tout est gratuit et local." },
];

export default function Engines() {
  const [ollamaOpen, setOllamaOpen] = useState(false);
  const [comfyOpen, setComfyOpen] = useState(false);
  const { data: ollama } = useLocalEngine();
  const ollamaStatus = useLocalEngineStatus(ollama);
  const { data: comfy } = useComfy();
  const comfyStatus = useComfyStatus(comfy);

  const cards = [
    {
      key: "ollama", icon: Cpu, tone: "web" as const, title: "Ollama · sites web", sub: ollama ? `${ollama.model} · ${ollama.base_url}` : "",
      text: "Analyse, architecture, direction artistique, code des pages et corrections. Remplace Claude, GPT et Gemini.",
      status: ollamaStatus, open: () => setOllamaOpen(true),
    },
    {
      key: "comfy", icon: ImageIcon, tone: "vision" as const, title: "ComfyUI · photos, pubs & vidéos", sub: comfy ? `${comfy.image_preset} · ${comfy.video_preset} · ${comfy.base_url}` : "",
      text: "Photos FLUX/SDXL, retouches image→image, visuels de site et de pub, vidéos Wan 2.2 / LTX. Remplace Nano Banana, Veo et Kling.",
      status: comfyStatus, open: () => setComfyOpen(true),
    },
  ];

  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "diagnostic" ? "diagnostic" : "engines";
  const kit = useKitInfo();

  return (
    <AppShell tone="duo">
      <div className="mx-auto max-w-[1200px] px-4 py-10 md:px-6 md:py-14">
        <p className="eyebrow text-violet-300">Indépendance totale</p>
        <h1 className="mt-2 max-w-3xl font-heading text-4xl font-semibold leading-[1.05] text-white md:text-5xl" data-testid="engines-title">
          Moteurs 100 % locaux, <span className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-transparent">zéro frais</span> de génération.
        </h1>
        <p className="mt-4 max-w-2xl text-slate-400">
          Par défaut, LocalAiStudio génère tout sur votre PC (RTX 3060). Les moteurs payants restent disponibles en secours, au cas par cas.
        </p>

        <div className="mt-8 inline-flex rounded-full border border-white/10 bg-black/30 p-1" role="tablist" data-testid="engines-tabs">
          {([["engines", "Moteurs"], ["diagnostic", "Diagnostic"]] as const).map(([k, l]) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              data-testid={`engines-tab-${k}`}
              onClick={() => setParams(k === "engines" ? {} : { tab: k }, { replace: true })}
              className={cn("rounded-full px-5 py-2 text-sm transition-[background-color,color] duration-300", tab === k ? "bg-gradient-to-r from-violet-500/40 to-cyan-500/30 text-white" : "text-slate-400 hover:text-white")}
            >
              {l}
            </button>
          ))}
        </div>

        {tab === "diagnostic" ? <DiagnosticPanel /> : (<>
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          {cards.map((c, i) => (
            <motion.div
              key={c.key}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * i, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              data-testid={`engine-card-${c.key}`}
              className={cn("relative overflow-hidden rounded-3xl border border-white/10 bg-panel/70 p-6 backdrop-blur-xl", c.tone === "web" ? "shadow-[0_0_60px_-30px_rgba(139,92,246,0.9)]" : "shadow-[0_0_60px_-30px_rgba(6,182,212,0.9)]")}
            >
              <div className={cn("pointer-events-none absolute -right-16 -top-16 size-48 rounded-full blur-3xl", c.tone === "web" ? "bg-violet-500/20" : "bg-cyan-500/20")} />
              <div className="relative flex items-start gap-4">
                <span className={cn("inline-flex size-11 shrink-0 items-center justify-center rounded-2xl border", c.tone === "web" ? "border-violet-400/30 bg-violet-500/15 text-violet-200" : "border-cyan-400/30 bg-cyan-500/15 text-cyan-200")}>
                  <c.icon className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="font-heading text-xl font-semibold text-white">{c.title}</h2>
                  <p className="truncate font-mono text-[11px] text-slate-500" data-testid={`engine-${c.key}-config`}>{c.sub}</p>
                </div>
              </div>
              <p className="relative mt-4 text-sm leading-relaxed text-slate-300">{c.text}</p>
              <div className="relative mt-4">
                <Status testid={`engine-${c.key}-status`} loading={c.status.isLoading} ok={c.status.data?.ok} message={c.status.data?.message} />
              </div>
              <div className="relative mt-4 flex gap-2">
                <FxButton tone={c.tone} size="sm" data-testid={`engine-${c.key}-configure`} onClick={c.open}><Settings2 className="size-4" /> Configurer</FxButton>
                <FxButton tone="ghost" size="sm" data-testid={`engine-${c.key}-retest`} onClick={() => c.status.refetch()}>Re-tester</FxButton>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-[1.25fr_1fr]">
          <section data-testid="tunnel-section" className="rounded-3xl border border-white/10 bg-panel/70 p-6 backdrop-blur-xl">
            <p className="eyebrow flex items-center gap-1.5 text-violet-300"><Cable className="size-3.5" /> Brancher cette preview sur votre PC</p>
            <h2 className="mt-2 font-heading text-xl font-semibold text-white">Pourquoi « non connecté » ?</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              Cette preview tourne sur un serveur en ligne : « localhost » désigne ce serveur, pas votre PC. Pour utiliser votre RTX depuis ici, ouvrez un tunnel gratuit
              (Cloudflare, sans compte) sur votre PC, puis collez l'adresse <span className="font-mono text-slate-200">https://….trycloudflare.com</span> affichée dans « Configurer ».
              En local avec le kit, rien à faire : tout se connecte seul.
            </p>
            <div className="mt-4 space-y-2">
              {TUNNELS.map((t) => (
                <div key={t.k} className="flex items-center gap-2 rounded-xl border border-white/[0.06] bg-black/40 p-2 pl-3">
                  <span className="w-16 shrink-0 text-[11px] text-slate-400">{t.label}</span>
                  <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-cyan-200" data-testid={`tunnel-cmd-${t.k}`}>{t.cmd}</code>
                  <button type="button" title="Copier" data-testid={`tunnel-copy-${t.k}`} onClick={() => navigator.clipboard?.writeText(t.cmd)} className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white">
                    <Copy className="size-3.5" />
                  </button>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-slate-500">Le kit contient aussi <span className="font-mono">tunnel-preview.bat</span>, qui lance les deux tunnels d'un double-clic (winget install Cloudflare.cloudflared).</p>
          </section>
          <section data-testid="gpu-queue-section" className="rounded-3xl border border-white/10 bg-panel/70 p-6 backdrop-blur-xl">
            <p className="eyebrow text-cyan-300">File d'attente GPU</p>
            <h2 className="mt-2 mb-4 font-heading text-xl font-semibold text-white">Rendus en cours</h2>
            <GpuQueueList />
          </section>
        </div>

        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mt-8 grid gap-6 rounded-3xl border border-white/10 bg-gradient-to-br from-violet-500/10 via-panel/70 to-cyan-500/10 p-6 backdrop-blur-xl lg:grid-cols-[1fr_1.2fr]"
          data-testid="kit-section"
        >
          <div>
            <p className="eyebrow flex items-center gap-1.5 text-cyan-300"><HardDrive className="size-3.5" /> Kit Windows</p>
            <h2 className="mt-2 font-heading text-2xl font-semibold text-white">Installer LocalAiStudio sur votre PC</h2>
            <p className="mt-2 text-sm text-slate-400">
              Cette version en ligne ne peut pas joindre votre carte graphique. Le kit lance l'application chez vous, sur la même machine qu'Ollama et ComfyUI.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {kit.data?.installer_available && (
                <FxButton size="lg" data-testid="installer-download" onClick={() => window.location.assign("/api/kit/installer")}>
                  <Download className="size-4" /> Installateur Windows (.exe · {kit.data.installer_size_mb} Mo)
                </FxButton>
              )}
              <FxButton size="lg" tone={kit.data?.installer_available ? "ghost" : "web"} data-testid="kit-download" onClick={() => window.location.assign("/api/kit/download")}>
                <Download className="size-4" /> Kit complet (.zip)
              </FxButton>
            </div>
            <p className="mt-2 text-[11px] text-slate-500">L'installateur télécharge Python, Node.js, MongoDB, Ollama et les modèles IA avec une barre de progression, puis crée le raccourci sur le Bureau.</p>
          </div>
          <ol className="space-y-3">
            {STEPS.map((s, i) => (
              <li key={s.t} className="flex gap-3 rounded-2xl border border-white/[0.06] bg-black/25 p-3" data-testid={`kit-step-${i + 1}`}>
                <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10 font-mono text-xs text-white">{i + 1}</span>
                <div>
                  <p className="flex items-center gap-1.5 text-sm font-medium text-white">{i === 3 && <Terminal className="size-3.5 text-cyan-300" />}{s.t}</p>
                  <p className="text-xs text-slate-400">{s.d}</p>
                </div>
              </li>
            ))}
          </ol>
        </motion.section>

        <p className="mt-6 max-w-3xl text-xs leading-relaxed text-slate-500" data-testid="engines-quality-note">
          Qualité sur RTX 3060 : les photos FLUX dev sont très proches de Nano Banana. Les sites utilisent le moteur Premium : l'IA locale écrit la direction artistique et les textes, et une bibliothèque de sections animées assure un rendu haut de gamme, différent à chaque génération.
          Les vidéos Wan 2.2 (832×480, 3 à 5 s, sans son) restent en dessous de Veo et Kling.
        </p>
        </>)}
      </div>
      <LocalEngineDialog open={ollamaOpen} onOpenChange={setOllamaOpen} />
      <ComfyDialog open={comfyOpen} onOpenChange={setComfyOpen} />
    </AppShell>
  );
}
