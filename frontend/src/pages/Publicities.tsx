import { motion } from "motion/react";
import { ArrowUpRight, Megaphone } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { AdWorkshop } from "@/components/vision";

/** Dedicated route reusing the existing ad workshop without changing its workflow. */
export default function Publicities() {
  return (
    <AppShell tone="vision">
      <section className="mx-auto max-w-[1440px] px-4 pb-24 pt-10 md:px-6">
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="mb-8 flex flex-col gap-4 border-b border-white/[0.07] pb-7 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <p className="eyebrow flex items-center gap-2 text-cyan-300"><Megaphone className="size-3.5" /> Forma · création de campagnes</p>
            <h1 className="mt-3 text-4xl font-semibold md:text-6xl"><span className="text-gradient-vision">Publicités</span></h1>
            <p className="mt-3 max-w-xl text-sm text-slate-400">Créez, animez et exportez vos créations de marque depuis les moteurs disponibles.</p>
          </div>
          <a href="#ad-workshop" className="inline-flex h-10 items-center gap-2 self-start rounded-full border border-cyan-300/20 bg-cyan-400/[0.06] px-4 text-sm text-cyan-100 transition-colors hover:border-cyan-300/50 hover:bg-cyan-400/10 sm:self-auto">
            Ouvrir l’atelier <ArrowUpRight className="size-4" />
          </a>
        </motion.header>
        <div id="ad-workshop" className="scroll-mt-28">
          <AdWorkshop />
        </div>
      </section>
    </AppShell>
  );
}
