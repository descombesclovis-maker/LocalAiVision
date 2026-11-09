import { motion } from "motion/react";
import { AlertTriangle, CheckCircle2, Copy, Info, Loader2, RefreshCw, XCircle } from "lucide-react";
import { toast } from "sonner";
import { FxButton } from "@/components/FxButton";
import { useDiagnostic } from "@/lib/companyHooks";
import type { DiagCheck } from "@/lib/companyTypes";
import { cn } from "@/lib/utils";

const STYLE = {
  ok: { icon: CheckCircle2, ring: "border-emerald-400/25", text: "text-emerald-300", label: "OK" },
  warn: { icon: AlertTriangle, ring: "border-amber-400/30", text: "text-amber-300", label: "À vérifier" },
  error: { icon: XCircle, ring: "border-rose-400/35", text: "text-rose-300", label: "À corriger" },
  info: { icon: Info, ring: "border-cyan-400/30", text: "text-cyan-300", label: "Info" },
} as const;

function Row({ c, i }: { c: DiagCheck; i: number }) {
  const s = STYLE[c.status];
  return (
    <motion.li
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.04 * i, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      data-testid={`diag-check-${c.key}`}
      className={cn("rounded-2xl border bg-panel/70 p-4 backdrop-blur-xl", s.ring)}
    >
      <div className="flex items-start gap-3">
        <s.icon className={cn("mt-0.5 size-5 shrink-0", s.text)} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-white">{c.label}</p>
            <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider", s.ring, s.text)} data-testid={`diag-check-${c.key}-status`}>{s.label}</span>
          </div>
          <p className="mt-1 text-sm text-slate-400" data-testid={`diag-check-${c.key}-detail`}>{c.detail}</p>
          {c.fix && c.status !== "ok" && (
            <p className="mt-2 text-sm text-slate-200" data-testid={`diag-check-${c.key}-fix`}><span className={cn("font-semibold", s.text)}>Solution : </span>{c.fix}</p>
          )}
          {c.cmd && c.status !== "ok" && (
            <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/[0.06] bg-black/40 p-1.5 pl-3">
              <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-cyan-200">{c.cmd}</code>
              <button
                type="button"
                title="Copier"
                data-testid={`diag-check-${c.key}-copy`}
                onClick={() => { navigator.clipboard?.writeText(c.cmd); toast.success("Commande copiée"); }}
                className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              >
                <Copy className="size-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.li>
  );
}

export function DiagnosticPanel() {
  const { data, isFetching, refetch } = useDiagnostic();
  const total = data ? data.ok + data.warn + data.error : 0;
  const score = total ? Math.round((data!.ok / total) * 100) : 0;
  return (
    <section className="mt-8" data-testid="diagnostic-panel">
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-violet-500/10 via-panel/70 to-cyan-500/10 p-6 backdrop-blur-xl">
        <div>
          <p className="eyebrow text-cyan-300">Vérification de l'installation</p>
          <h2 className="mt-2 font-heading text-2xl font-semibold text-white" data-testid="diag-summary">
            {!data ? "Analyse en cours…" : data.error ? `${data.error} point(s) à corriger` : data.warn ? `Presque prêt : ${data.warn} point(s) à vérifier` : "Tout est prêt, 100 % local"}
          </h2>
          {data && (
            <p className="mt-1 font-mono text-[11px] text-slate-400" data-testid="diag-counts">
              {data.ok} OK · {data.warn} à vérifier · {data.error} à corriger · {new Date(data.checked_at).toLocaleTimeString("fr-FR")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          {data && (
            <div className="relative size-16" data-testid="diag-score">
              <svg viewBox="0 0 36 36" className="size-16 -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="url(#dg)" strokeWidth="3" strokeLinecap="round" strokeDasharray={`${score * 0.974} 100`} className="transition-[stroke-dasharray] duration-700" />
                <defs><linearGradient id="dg"><stop offset="0" stopColor="#a78bfa" /><stop offset="1" stopColor="#67e8f9" /></linearGradient></defs>
              </svg>
              <span className="absolute inset-0 grid place-items-center font-mono text-xs text-white">{score}%</span>
            </div>
          )}
          <FxButton tone="ghost" size="sm" data-testid="diag-rerun" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />} Relancer
          </FxButton>
        </div>
      </div>
      <ul className="mt-5 grid gap-3 lg:grid-cols-2">
        {data?.checks.map((c, i) => <Row key={c.key} c={c} i={i} />)}
      </ul>
    </section>
  );
}
