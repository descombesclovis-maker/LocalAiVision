import { Link, NavLink, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { Clapperboard, Globe2, Image as ImageIcon, Loader2, Sparkles, Stamp } from "lucide-react";
import type { ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Toaster } from "@/components/ui/sonner";
import { Aurora, GlowDot } from "@/components/Aurora";
import { GpuQueuePill } from "@/components/GpuQueue";
import { useActivity } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Studio", end: true, tone: "duo" },
  { to: "/web", label: "LocalAiWeb", end: false, tone: "web" },
  { to: "/carte", label: "Carte", end: false, tone: "web" },
  { to: "/vision", label: "LocalAiVision", end: false, tone: "vision" },
  { to: "/marques", label: "Marques", end: false, tone: "duo" },
  { to: "/moteurs", label: "Moteurs", end: false, tone: "duo" },
];

export function ActivityPill() {
  const { data } = useActivity();
  const count = data?.count ?? 0;
  return (
    <Popover>
      <PopoverTrigger
        data-testid="activity-pill"
        className={cn(
          "group inline-flex h-9 items-center gap-2 rounded-full border px-3 text-xs font-medium transition-[border-color,background-color,box-shadow] duration-300",
          count ? "border-violet-400/40 bg-violet-500/10 text-violet-100 shadow-[0_0_24px_-6px_rgba(139,92,246,0.8)]" : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20",
        )}
      >
        {count ? <GlowDot /> : <span className="size-2 rounded-full bg-slate-600" />}
        <span data-testid="activity-count">{count ? `${count} en cours` : "Aucune génération"}</span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 border-white/10 bg-panel/95 backdrop-blur-xl">
        <p className="eyebrow mb-3 text-slate-400">Générations en cours</p>
        {!count && <p className="text-sm text-slate-400">Tout est calme. Lancez une création !</p>}
        <div className="space-y-2">
          {data?.items.map((it) => (
            <Link
              key={it.id}
              to={it.kind === "site" ? `/web/p/${it.id}` : "/vision"}
              data-testid={`activity-item-${it.id}`}
              className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.03] p-2.5 transition-colors hover:border-white/15"
            >
              <span className={cn("flex size-8 items-center justify-center rounded-md", it.kind === "site" ? "bg-violet-500/20 text-violet-300" : "bg-cyan-500/20 text-cyan-300")}>
                {it.kind === "site" ? <Globe2 className="size-4" /> : it.kind === "video" ? <Clapperboard className="size-4" /> : <ImageIcon className="size-4" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-white">{it.name}</span>
                <span className="block truncate text-xs text-slate-400">{it.label}</span>
              </span>
              <Loader2 className="size-4 animate-spin text-slate-400" />
            </Link>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

export function AppShell({ children, tone = "duo", full = false }: { children: ReactNode; tone?: "web" | "vision" | "duo"; full?: boolean }) {
  const loc = useLocation();
  return (
    <div className="grain relative min-h-dvh">
      <Aurora tone={tone} />
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-obsidian/60 backdrop-blur-2xl">
        <div className={cn("mx-auto flex h-16 items-center gap-4 px-4 md:px-6", !full && "max-w-[1440px]")}>
          <Link to="/" data-testid="nav-logo" className="group flex items-center gap-2.5">
            <span className="relative flex size-9 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-cyan-400 shadow-[0_0_30px_-6px_rgba(139,92,246,0.9)] transition-transform duration-500 group-hover:rotate-[18deg] group-hover:scale-105">
              <Sparkles className="size-4.5 text-white" />
            </span>
            <span className="hidden font-heading text-[15px] font-semibold tracking-tight sm:block">
              LocalAi<span className="text-gradient-duo">Studio</span>
              <span className="ml-1.5 rounded bg-white/10 px-1.5 py-0.5 align-middle font-mono text-[9px] tracking-widest text-slate-300">NEXTGEN</span>
            </span>
          </Link>
          <nav className="relative ml-2 hidden items-center gap-1 rounded-full border border-white/[0.07] bg-white/[0.02] p-1 md:flex">
            {NAV.map((n) => {
              const active = n.end ? loc.pathname === n.to : loc.pathname.startsWith(n.to);
              return (
                <NavLink key={n.to} to={n.to} end={n.end} data-testid={`nav-${n.to === "/" ? "home" : n.to.slice(1)}`} className="relative rounded-full px-4 py-1.5 text-sm">
                  {active && (
                    <motion.span
                      layoutId="nav-pill"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      className={cn(
                        "absolute inset-0 rounded-full",
                        n.tone === "web" ? "bg-violet-500/25 shadow-[0_0_20px_-4px_rgba(139,92,246,0.8)]" : n.tone === "vision" ? "bg-cyan-500/20 shadow-[0_0_20px_-4px_rgba(6,182,212,0.8)]" : "bg-white/10",
                      )}
                    />
                  )}
                  <span className={cn("relative transition-colors", active ? "text-white" : "text-slate-400 hover:text-white")}>{n.label}</span>
                </NavLink>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden sm:inline-flex"><GpuQueuePill /></span>
            <ActivityPill />
            <Link to="/marques" data-testid="nav-brands-icon" className="inline-flex size-9 items-center justify-center rounded-full border border-white/10 text-slate-300 transition-colors hover:text-white md:hidden">
              <Stamp className="size-4" />
            </Link>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2 md:hidden">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={`mnav-${n.to === "/" ? "home" : n.to.slice(1)}`} className={({ isActive }) => cn("shrink-0 rounded-full px-3 py-1 text-xs", isActive ? "bg-white/10 text-white" : "text-slate-400")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <AnimatePresence mode="wait">
        <motion.main
          key={loc.pathname}
          initial={{ opacity: 0, y: 14, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          {children}
        </motion.main>
      </AnimatePresence>
      <Toaster richColors theme="dark" />
    </div>
  );
}
