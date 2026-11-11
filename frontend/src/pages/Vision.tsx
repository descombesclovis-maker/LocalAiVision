import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { Clapperboard, ImagePlus, LibraryBig, Settings2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Library, PhotoStudio, VideoStudio } from "@/components/vision";
import { cn } from "@/lib/utils";

const MODES = [
  { k: "photo", l: "Photo", detail: "T2I · I2I", I: ImagePlus },
  { k: "video", l: "Vidéo", detail: "T2V · I2V", I: Clapperboard },
] as const;
type StudioTab = (typeof MODES)[number]["k"] | "library";

export default function Vision() {
  const [tab, setTab] = useState<StudioTab>("photo");
  return (
    <AppShell tone="vision">
      <section className="mx-auto max-w-[1560px] px-4 pb-24 pt-8 md:px-6 md:pt-12">
        <motion.header initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }} className="mb-8 flex flex-col gap-5 border-b border-white/[0.07] pb-7 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="eyebrow text-cyan-300">LocalAiVision · Studio de création</p>
            <h1 className="mt-3 text-4xl font-semibold md:text-6xl"><span className="text-gradient-vision">Donnez vie</span> à vos idées.</h1>
            <p className="mt-3 max-w-xl text-sm text-slate-400">Créez des images et vidéos avec les moteurs disponibles, puis retrouvez vos créations dans votre bibliothèque.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative inline-flex rounded-2xl border border-white/10 bg-black/30 p-1.5" role="tablist" aria-label="Mode de création" data-testid="vision-mode-switch">
              {MODES.map(({ k, l, detail, I }) => (
                <button key={k} type="button" role="tab" aria-selected={tab === k} data-testid={`vision-tab-${k}`} onClick={() => setTab(k)} className="relative min-w-32 rounded-xl px-4 py-2.5 text-left">
                  {tab === k && <motion.span layoutId="vision-mode-active" className="absolute inset-0 rounded-xl bg-cyan-500/20 shadow-[0_0_24px_-6px_rgba(6,182,212,0.7)]" transition={{ type: "spring", stiffness: 380, damping: 30 }} />}
                  <span className={cn("relative flex items-center gap-2 font-medium", tab === k ? "text-white" : "text-slate-400 hover:text-white")}><I className="size-4" />{l}</span>
                  <span className={cn("relative ml-6 block text-[10px] tracking-wide", tab === k ? "text-cyan-100/75" : "text-slate-500")}>{detail}</span>
                </button>
              ))}
            </div>
            <button type="button" data-testid="vision-tab-library" aria-pressed={tab === "library"} onClick={() => setTab("library")} className={cn("inline-flex h-11 items-center gap-2 rounded-xl border px-3.5 text-sm transition-[border-color,background-color,color] duration-200", tab === "library" ? "border-cyan-300/50 bg-cyan-400/10 text-white" : "border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-white")}>
              <LibraryBig className="size-4" /> Bibliothèque
            </button>
            <Link to="/moteurs" data-testid="vision-advanced-settings" className="inline-flex h-11 items-center gap-2 rounded-xl border border-white/10 px-3.5 text-sm text-slate-400 transition-colors hover:border-white/20 hover:text-white">
              <Settings2 className="size-4" /> Réglages avancés
            </Link>
          </div>
        </motion.header>
        <motion.div key={tab} initial={{ opacity: 0, y: 14, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }} data-testid="vision-studio-content">
          {tab === "photo" && <PhotoStudio />}
          {tab === "video" && <VideoStudio />}
          {tab === "library" && <Library />}
        </motion.div>
      </section>
    </AppShell>
  );
}
