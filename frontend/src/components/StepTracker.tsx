import { motion } from "motion/react";
import { AlertTriangle, Check, CircleHelp, Loader2 } from "lucide-react";
import type { Step } from "@/lib/types";
import { cn } from "@/lib/utils";

export function StepTracker({ steps, compact = false }: { steps: Step[]; compact?: boolean }) {
  const done = steps.filter((s) => s.status === "done").length;
  const pct = Math.round((done / Math.max(steps.length, 1)) * 100);
  return (
    <div data-testid="step-tracker" className="glass-web relative overflow-hidden rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="eyebrow text-violet-300">Moteur LocalAiWeb</p>
        <span className="font-mono text-xs text-violet-100" data-testid="step-progress">{pct}%</span>
      </div>
      <div className="relative mb-4 h-1.5 overflow-hidden rounded-full bg-white/10">
        <motion.div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-violet-500 via-fuchsia-400 to-cyan-400" animate={{ width: `${Math.max(pct, 4)}%` }} transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }} />
        <div className="shimmer-bar absolute inset-0" />
      </div>
      <ol className="space-y-1.5">
        {steps.map((s, i) => (
          <motion.li
            key={s.key}
            data-testid={`step-${s.key}`}
            data-status={s.status}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={cn("relative flex gap-3 rounded-xl px-2.5 py-2 transition-colors", s.status === "running" && "bg-violet-500/15")}
          >
            <span
              className={cn(
                "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-mono",
                s.status === "done" && "border-emerald-400/50 bg-emerald-500/20 text-emerald-300",
                s.status === "running" && "border-violet-300 bg-violet-500/30 text-white shadow-[0_0_16px_rgba(139,92,246,0.8)]",
                s.status === "error" && "border-red-400/60 bg-red-500/20 text-red-300",
                s.status === "waiting" && "border-amber-400/60 bg-amber-500/20 text-amber-300",
                s.status === "pending" && "border-white/15 text-slate-500",
              )}
            >
              {s.status === "done" ? <Check className="size-3.5" /> : s.status === "running" ? <Loader2 className="size-3.5 animate-spin" /> : s.status === "error" ? <AlertTriangle className="size-3.5" /> : s.status === "waiting" ? <CircleHelp className="size-3.5" /> : i + 1}
            </span>
            <span className="min-w-0">
              <span className={cn("block text-sm", s.status === "pending" ? "text-slate-500" : "text-white")}>{s.label}</span>
              {!compact && s.detail && <span className="block text-xs leading-snug text-slate-400 line-clamp-2">{s.detail}</span>}
            </span>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
