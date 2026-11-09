import { ArrowUpToLine, Clapperboard, Globe2, Image as ImageIcon, Loader2, PenLine, X } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useGpuQueue, useQueueAction } from "@/lib/companyHooks";
import type { QueueItem } from "@/lib/companyTypes";
import { cn } from "@/lib/utils";

export const fmtDuration = (s: number) => {
  if (s < 60) return `${Math.max(0, Math.round(s))} s`;
  const m = Math.floor(s / 60);
  return m < 60 ? `${m} min ${String(Math.round(s % 60)).padStart(2, "0")}` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}`;
};

const ICON = { photo: ImageIcon, video: Clapperboard, site: Globe2, edit: PenLine } as const;

function Row({ it }: { it: QueueItem }) {
  const act = useQueueAction();
  const Icon = ICON[it.kind];
  const pct = it.status === "running" ? Math.min(97, Math.round((it.elapsed_s / Math.max(1, it.elapsed_s + it.eta_s)) * 100)) : 0;
  return (
    <div data-testid={`gpu-job-${it.id}`} className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2.5">
      <div className="flex items-center gap-2.5">
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-lg", it.kind === "site" || it.kind === "edit" ? "bg-violet-500/20 text-violet-300" : "bg-cyan-500/20 text-cyan-300")}>
          <Icon className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-white">{it.label}</p>
          <p className="truncate font-mono text-[10px] text-slate-400" data-testid={`gpu-job-${it.id}-eta`}>
            {it.status === "running" ? `En cours · reste ~${fmtDuration(it.eta_s)}` : `#${it.position} · démarre dans ~${fmtDuration(it.start_in_s)}`} · {it.engine}
          </p>
        </div>
        {it.status === "waiting" && it.position > 1 && (
          <button type="button" title="Passer en premier" data-testid={`gpu-job-${it.id}-prioritize`} onClick={() => act.mutate({ id: it.id, action: "prioritize" })} className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white">
            <ArrowUpToLine className="size-3.5" />
          </button>
        )}
        <button type="button" title="Annuler" data-testid={`gpu-job-${it.id}-cancel`} onClick={() => act.mutate({ id: it.id, action: "cancel" })} className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-rose-500/15 hover:text-rose-300">
          <X className="size-3.5" />
        </button>
      </div>
      {it.status === "running" && (
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-gradient-to-r from-violet-400 to-cyan-300 transition-[width] duration-700" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

export function GpuQueueList({ className }: { className?: string }) {
  const { data } = useGpuQueue();
  const items = data?.items ?? [];
  return (
    <div className={cn("space-y-2", className)} data-testid="gpu-queue-list">
      {items.length === 0 ? (
        <p className="text-sm text-slate-400" data-testid="gpu-queue-empty">Aucun rendu local en attente. La carte graphique est libre.</p>
      ) : (
        <>
          <p className="font-mono text-[11px] text-slate-400" data-testid="gpu-queue-total">{items.length} rendu(s) · tout terminé dans ~{fmtDuration(data?.total_eta_s ?? 0)}</p>
          {items.map((it) => <Row key={it.id} it={it} />)}
        </>
      )}
    </div>
  );
}

export function GpuQueuePill() {
  const { data } = useGpuQueue();
  const n = data?.items.length ?? 0;
  return (
    <Popover>
      <PopoverTrigger
        data-testid="gpu-queue-pill"
        className={cn(
          "inline-flex h-9 items-center gap-2 rounded-full border px-3 font-mono text-[11px] transition-[border-color,background-color] duration-300",
          n ? "border-cyan-400/40 bg-cyan-500/10 text-cyan-100" : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20",
        )}
      >
        {n ? <Loader2 className="size-3.5 animate-spin" /> : <span className="size-2 rounded-full bg-slate-600" />}
        GPU{n ? ` · ${n} · ${fmtDuration(data?.total_eta_s ?? 0)}` : ""}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 border-white/10 bg-panel/95 backdrop-blur-xl">
        <p className="eyebrow mb-3 text-cyan-300">File d'attente GPU (RTX locale)</p>
        <GpuQueueList />
      </PopoverContent>
    </Popover>
  );
}
