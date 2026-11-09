import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Award, Building2, CalendarDays, Cpu, Euro, MapPin, Rocket, Users, X } from "lucide-react";
import { FxButton } from "@/components/FxButton";
import { useCompany, useCreateCompanySite, useLocalEngine, useLocalEngineStatus } from "@/lib/companyHooks";
import type { WebStatus, CompanyPoint, SiteEngine } from "@/lib/companyTypes";
import { cn } from "@/lib/utils";

const ENGINES: { k: SiteEngine; label: string; sub: string }[] = [
  { k: "local", label: "Moteur local", sub: "Gratuit · Ollama / LM Studio" },
  { k: "claude", label: "Claude Sonnet 4.5", sub: "En ligne · clé universelle" },
  { k: "gpt", label: "GPT-5.2", sub: "En ligne · clé universelle" },
  { k: "gemini", label: "Gemini 3.1 Pro", sub: "En ligne · clé universelle" },
];

const euro = (n: number) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", notation: n > 9_999_999 ? "compact" : "standard", maximumFractionDigits: 0 }).format(n);

function Fact({ icon: Icon, label, value, testid }: { icon: typeof MapPin; label: string; value: string; testid: string }) {
  if (!value) return null;
  return (
    <div className="flex gap-3 py-2">
      <Icon className="mt-0.5 size-4 shrink-0 text-violet-300/80" />
      <div className="min-w-0">
        <p className="eyebrow text-slate-500">{label}</p>
        <p data-testid={testid} className="text-sm text-slate-200">{value}</p>
      </div>
    </div>
  );
}

export function CompanyPanel({ point, web, onClose, onOpenEngine }: { point: CompanyPoint; web?: WebStatus; onClose: () => void; onOpenEngine: () => void }) {
  const nav = useNavigate();
  const { data: c, isLoading, error } = useCompany(point.siren);
  const create = useCreateCompanySite();
  const { data: engineCfg } = useLocalEngine();
  const status = useLocalEngineStatus(engineCfg);
  const [engine, setEngine] = useState<SiteEngine>("local");
  const [mode, setMode] = useState<"libre" | "pro">("pro");

  const launch = () =>
    create.mutate({ siren: point.siren, body: { llm: engine, mode } }, { onSuccess: (p) => nav(`/web/p/${p.id}`) });

  return (
    <motion.aside
      data-testid="company-panel"
      initial={{ opacity: 0, x: 40, scale: 0.98 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 40, scale: 0.98 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="absolute inset-x-2 bottom-2 z-[500] flex max-h-[78%] flex-col overflow-hidden rounded-3xl border border-white/10 bg-panel/90 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.9),0_0_60px_-30px_rgba(139,92,246,0.7)] backdrop-blur-2xl md:inset-x-auto md:bottom-4 md:right-4 md:top-4 md:max-h-none md:w-[420px]"
    >
      <div className="relative border-b border-white/[0.06] px-5 pb-4 pt-5">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_80%_at_0%_0%,rgba(139,92,246,0.25),transparent_60%)]" />
        <button type="button" data-testid="company-panel-close" onClick={onClose} className="absolute right-4 top-4 inline-flex size-8 items-center justify-center rounded-full border border-white/10 text-slate-400 transition-[color,transform] duration-200 hover:rotate-90 hover:text-white">
          <X className="size-4" />
        </button>
        <p className="eyebrow relative text-violet-300">{c?.section_label || point.naf || "Entreprise"}</p>
        <h2 data-testid="company-name" className="relative mt-1.5 pr-10 font-heading text-2xl font-semibold leading-tight text-white">{c?.name || point.name}</h2>
        {c && c.legal_name !== c.name && <p className="relative mt-0.5 text-xs text-slate-400" data-testid="company-legal-name">{c.legal_name}</p>}
        <p className="relative mt-2 font-mono text-[11px] text-slate-500" data-testid="company-siren">SIREN {point.siren} · NAF {c?.naf || point.naf}</p>
        {web && (
          <div data-testid="company-web-status" className={cn("relative mt-3 rounded-xl border px-3 py-2 text-xs", web.status === "none" ? "border-rose-400/40 bg-rose-500/10 text-rose-100" : web.status === "found" ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100" : "border-white/10 text-slate-400")}>
            {web.status === "none" && "Aucun site web détecté : prospect prioritaire"}
            {web.status === "pending" && "Vérification de la présence d'un site web…"}
            {web.status === "found" && web.url && (
              <>Site existant : <a href={web.url} target="_blank" rel="noreferrer" className="underline underline-offset-2" data-testid="company-web-url">{web.url.replace(/^https?:\/\//, "")}</a></>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-3">
        {isLoading && <div className="space-y-3 py-2">{[0, 1, 2, 3].map((i) => <div key={i} className="h-10 animate-pulse rounded-lg bg-white/[0.04]" />)}</div>}
        {error && <p className="py-4 text-sm text-amber-200" data-testid="company-error">Fiche indisponible pour le moment.</p>}
        {c && (
          <>
            <div className="divide-y divide-white/[0.05]">
              <Fact icon={MapPin} label="Adresse de l'établissement" value={point.address || c.address} testid="company-address" />
              <Fact icon={Building2} label="Forme · catégorie" value={[c.legal_form, c.category].filter(Boolean).join(" · ")} testid="company-legal-form" />
              <Fact icon={CalendarDays} label="Création" value={c.created ? new Date(c.created).toLocaleDateString("fr-FR", { year: "numeric", month: "long", day: "numeric" }) : ""} testid="company-created" />
              <Fact icon={Users} label="Effectif" value={[c.effectif, c.establishments > 1 ? `${c.establishments} établissements` : ""].filter(Boolean).join(" · ")} testid="company-effectif" />
              <Fact icon={Euro} label={`Chiffre d'affaires ${c.finance_year ?? ""}`} value={c.revenue ? `${euro(c.revenue)}${c.net_result != null ? ` · résultat ${euro(c.net_result)}` : ""}` : ""} testid="company-revenue" />
              <Fact icon={Users} label="Dirigeants" value={c.directors.slice(0, 3).join(" ; ")} testid="company-directors" />
            </div>
            {c.strengths.length > 0 && (
              <div className="mt-3">
                <p className="eyebrow mb-2 flex items-center gap-1.5 text-slate-400"><Award className="size-3.5" /> Atouts détectés</p>
                <div className="flex flex-wrap gap-1.5" data-testid="company-strengths">
                  {c.strengths.map((s, i) => (
                    <motion.span key={s} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * i }} className="rounded-full border border-violet-400/25 bg-violet-500/10 px-2.5 py-1 text-[11px] text-violet-100">{s}</motion.span>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5 rounded-2xl border border-white/[0.07] bg-black/25 p-3">
              <p className="eyebrow mb-2 text-slate-400">Moteur de génération</p>
              <div className="grid grid-cols-2 gap-1.5">
                {ENGINES.map((e) => (
                  <button
                    key={e.k}
                    type="button"
                    data-testid={`company-engine-${e.k}`}
                    onClick={() => setEngine(e.k)}
                    className={cn(
                      "rounded-xl border px-2.5 py-2 text-left transition-[border-color,background-color,transform] duration-200 active:scale-[0.97]",
                      engine === e.k ? "border-violet-400/60 bg-violet-500/15" : "border-white/[0.07] hover:border-white/20",
                    )}
                  >
                    <span className="block text-xs font-medium text-white">{e.label}</span>
                    <span className="block text-[10px] text-slate-500">{e.sub}</span>
                  </button>
                ))}
              </div>
              {engine === "local" && (
                <button type="button" data-testid="company-engine-status" onClick={onOpenEngine} className={cn("mt-2 flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[11px] transition-colors", status.data?.ok ? "bg-emerald-500/10 text-emerald-200" : "bg-amber-500/10 text-amber-100 hover:bg-amber-500/15")}>
                  <Cpu className="size-3.5 shrink-0" />
                  {status.isLoading ? "Vérification du moteur local…" : status.data?.ok ? status.data.message : "Moteur local non détecté — cliquez pour le configurer"}
                </button>
              )}
              <div className="mt-2 flex gap-1.5">
                {(["libre", "pro"] as const).map((m) => (
                  <button key={m} type="button" data-testid={`company-mode-${m}`} onClick={() => setMode(m)} className={cn("flex-1 rounded-lg border py-1.5 text-xs capitalize transition-colors", mode === m ? "border-white/30 bg-white/10 text-white" : "border-white/[0.07] text-slate-400")}>
                    {m === "pro" ? "Pro · 5-7 pages" : "Libre · 4-5 pages"}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      <div className="border-t border-white/[0.06] p-4">
        <FxButton size="lg" className="w-full" data-testid="company-create-site" disabled={!c || !c.active || create.isPending} onClick={launch}>
          <Rocket className="size-4" /> {create.isPending ? "Lancement…" : "Créer un site pour cette entreprise"}
        </FxButton>
        <p className="mt-2 text-center text-[10px] text-slate-500">L'IA identifie les meilleurs arguments de vente et construit le site automatiquement.</p>
      </div>
    </motion.aside>
  );
}
