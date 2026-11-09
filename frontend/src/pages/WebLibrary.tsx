import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { Crown, Feather, Globe2, Loader2, Plus, Search, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { FxButton } from "@/components/FxButton";
import { NewProjectDialog } from "@/components/NewProjectDialog";
import { TiltCard } from "@/components/TiltCard";
import { useDeleteProject, useProjects } from "@/lib/hooks";
import { SITE_TYPES, STATUS_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";

const FILTERS = [
  { v: "", l: "Tous" },
  { v: "libre", l: "Libres" },
  { v: "pro", l: "Pro" },
];

export default function WebLibrary() {
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("");
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useProjects(q, mode);
  const del = useDeleteProject();

  return (
    <AppShell tone="web">
      <section className="mx-auto max-w-[1440px] px-4 pb-24 pt-12 md:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="eyebrow text-violet-300">LocalAiWeb · Bibliothèque</p>
            <h1 className="mt-3 text-4xl font-semibold md:text-6xl"><span className="text-gradient-web">Vos sites</span>, prêts à briller.</h1>
            <p className="mt-3 max-w-lg text-slate-400">Chaque génération continue en arrière-plan : vous pouvez quitter l'éditeur et revenir quand vous voulez.</p>
          </div>
          <FxButton size="lg" data-testid="library-new-project" onClick={() => setOpen(true)}>
            <Plus className="size-4" /> Nouveau site
          </FxButton>
        </div>

        <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="glass flex h-11 flex-1 items-center gap-2 rounded-full px-4 focus-within:border-violet-400/50">
            <Search className="size-4 text-slate-500" />
            <input data-testid="library-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un projet…" className="h-full flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500" />
          </div>
          <div className="relative flex rounded-full border border-white/10 bg-white/[0.03] p-1">
            {FILTERS.map((f) => (
              <button key={f.v} type="button" data-testid={`library-filter-${f.v || "all"}`} onClick={() => setMode(f.v)} className="relative rounded-full px-4 py-1.5 text-sm">
                {mode === f.v && <motion.span layoutId="lib-filter" className="absolute inset-0 rounded-full bg-violet-500/30" transition={{ type: "spring", stiffness: 400, damping: 30 }} />}
                <span className={cn("relative", mode === f.v ? "text-white" : "text-slate-400")}>{f.l}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-8 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          <motion.button
            type="button"
            data-testid="library-new-card"
            onClick={() => setOpen(true)}
            whileHover={{ y: -4 }}
            className="group relative flex min-h-72 flex-col items-center justify-center gap-4 overflow-hidden rounded-3xl border border-dashed border-violet-400/30 bg-violet-500/[0.04] text-violet-200 transition-[border-color,background-color] duration-300 hover:border-violet-300/70 hover:bg-violet-500/10"
          >
            <span className="relative flex size-16 items-center justify-center rounded-2xl bg-violet-500/20 transition-transform duration-500 group-hover:rotate-90 group-hover:scale-110">
              <Plus className="size-7" />
            </span>
            <span className="font-heading text-lg">Lancer un nouveau site</span>
            <span className="text-xs text-slate-400">Restaurant, boutique, services, immobilier…</span>
          </motion.button>

          {isLoading && Array.from({ length: 2 }).map((_, i) => <div key={i} className="glass min-h-72 animate-pulse rounded-3xl" />)}
          {isError && <div className="glass flex min-h-72 items-center justify-center rounded-3xl p-6 text-center text-slate-400" data-testid="library-offline">Bibliothèque momentanément indisponible.</div>}

          <AnimatePresence>
            {data?.map((p, i) => {
              const busy = ["queued", "generating", "editing"].includes(p.status);
              return (
                <motion.div key={p.id} layout initial={{ opacity: 0, y: 30, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ delay: i * 0.04, ease: [0.16, 1, 0.3, 1], duration: 0.6 }}>
                  <TiltCard className="rounded-3xl" data-testid={`project-card-${p.id}`}>
                    <Link to={`/web/p/${p.id}`} className="group glass block overflow-hidden rounded-3xl transition-[border-color,box-shadow] duration-300 hover:border-violet-400/40 hover:shadow-[0_20px_60px_-20px_rgba(139,92,246,0.6)]">
                      <div className="relative aspect-[16/10] overflow-hidden bg-panel-2">
                        {p.thumbnail_url ? (
                          <img src={p.thumbnail_url} alt={p.name} className="size-full object-cover transition-transform duration-[1.2s] ease-out group-hover:scale-110" />
                        ) : (
                          <div className="flex size-full items-center justify-center bg-[radial-gradient(circle_at_30%_30%,rgba(139,92,246,0.35),transparent_60%)]">
                            {busy ? <Loader2 className="size-8 animate-spin text-violet-300" /> : <Globe2 className="size-10 text-violet-300/60" />}
                          </div>
                        )}
                        {busy && <div className="absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-violet-400/30 to-transparent animate-scan" />}
                        <div className="absolute inset-0 bg-gradient-to-t from-panel via-transparent to-transparent" />
                        <div className="absolute left-3 top-3 flex gap-2">
                          <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium backdrop-blur-md", p.mode === "pro" ? "bg-amber-400/20 text-amber-200" : "bg-white/10 text-slate-200")}>
                            {p.mode === "pro" ? <Crown className="size-3" /> : <Feather className="size-3" />} {p.mode === "pro" ? "Pro" : "Libre"}
                          </span>
                          <span data-testid={`project-status-${p.id}`} className={cn("rounded-full px-2.5 py-1 text-[11px] font-medium backdrop-blur-md", p.status === "ready" ? "bg-emerald-500/20 text-emerald-200" : p.status === "error" ? "bg-red-500/20 text-red-200" : "bg-violet-500/30 text-violet-100")}>
                            {STATUS_LABELS[p.status]}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-start gap-3 p-5">
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate font-heading text-lg font-semibold">{p.name || "Nouveau site"}</h3>
                          <p className="mt-1 line-clamp-2 text-sm text-slate-400">{p.prompt}</p>
                          <p className="mt-3 font-mono text-[11px] uppercase tracking-widest text-slate-500">{SITE_TYPES[p.site_type] ?? p.site_type} · v{p.version}</p>
                        </div>
                        <button
                          type="button"
                          data-testid={`project-delete-${p.id}`}
                          onClick={(e) => { e.preventDefault(); if (window.confirm(`Supprimer « ${p.name} » ?`)) del.mutate(p.id); }}
                          className="rounded-lg p-2 text-slate-500 opacity-0 transition-[opacity,color,background-color] group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-300"
                          aria-label="Supprimer"
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </div>
                    </Link>
                  </TiltCard>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </section>
      <NewProjectDialog open={open} onOpenChange={setOpen} />
    </AppShell>
  );
}
