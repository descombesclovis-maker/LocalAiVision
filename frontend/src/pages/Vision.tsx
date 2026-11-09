import { useState } from "react";
import { motion } from "motion/react";
import { Clapperboard, ImagePlus, LibraryBig, Megaphone } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { AdWorkshop, Library, PhotoStudio, VideoStudio } from "@/components/vision";
import { cn } from "@/lib/utils";

const TABS = [
  { k: "photo", l: "Studio Photo IA", I: ImagePlus },
  { k: "video", l: "Vidéo", I: Clapperboard },
  { k: "ad", l: "Atelier Publicité", I: Megaphone },
  { k: "library", l: "Bibliothèque", I: LibraryBig },
] as const;
type TabKey = (typeof TABS)[number]["k"];

export default function Vision() {
  const [tab, setTab] = useState<TabKey>("photo");
  return (
    <AppShell tone="vision">
      <section className="mx-auto max-w-[1440px] px-4 pb-24 pt-12 md:px-6">
        <p className="eyebrow text-cyan-300">LocalAiVision · Studio médias</p>
        <h1 className="mt-3 text-4xl font-semibold md:text-6xl"><span className="text-gradient-vision">Images, vidéos,</span> publicités.</h1>
        <p className="mt-3 max-w-xl text-slate-400">Rendu gratuit sur votre GPU via ComfyUI par défaut (moteurs payants en secours). Chaque génération continue même si vous changez d'écran.</p>
        <div className="mt-8 flex gap-1 overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.03] p-1.5 md:inline-flex">
          {TABS.map(({ k, l, I }) => (
            <button key={k} type="button" data-testid={`vision-tab-${k}`} onClick={() => setTab(k)} className="relative shrink-0 rounded-xl px-4 py-2.5 text-sm">
              {tab === k && <motion.span layoutId="vision-tab" className="absolute inset-0 rounded-xl bg-cyan-500/20 shadow-[0_0_24px_-6px_rgba(6,182,212,0.9)]" transition={{ type: "spring", stiffness: 380, damping: 30 }} />}
              <span className={cn("relative inline-flex items-center gap-2", tab === k ? "text-white" : "text-slate-400 hover:text-white")}><I className="size-4" /> {l}</span>
            </button>
          ))}
        </div>
        <motion.div key={tab} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }} className="mt-8">
          {tab === "photo" && <PhotoStudio />}
          {tab === "video" && <VideoStudio />}
          {tab === "ad" && <AdWorkshop />}
          {tab === "library" && <Library />}
        </motion.div>
      </section>
    </AppShell>
  );
}
