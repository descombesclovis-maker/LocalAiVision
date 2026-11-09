import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { ArrowUpRight, Clapperboard, Code2, Globe2, ImagePlus, Layers3, Megaphone, Sparkles, Wand2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { TiltCard } from "@/components/TiltCard";
import { GlowDot } from "@/components/Aurora";
import { useMedia, useProjects } from "@/lib/hooks";
import { SITE_TYPES } from "@/lib/types";
import { cn } from "@/lib/utils";

const ease = [0.16, 1, 0.3, 1] as const;
const words = ["Créez", "l'exceptionnel,", "en", "un", "seul", "studio."];

function Universe({ tone }: { tone: "web" | "vision" }) {
  const web = tone === "web";
  const feats = web
    ? [{ i: Layers3, t: "6 étapes réelles, du brief au contrôle qualité" }, { i: Code2, t: "Sites multi-pages, interactifs, exportables" }, { i: Wand2, t: "Éditeur par chat et sélection d'éléments" }]
    : [{ i: ImagePlus, t: "Photos Nano Banana et Nano Banana Pro" }, { i: Clapperboard, t: "Vidéos Veo 3.1 Fast, Kling, MiniMax" }, { i: Megaphone, t: "Atelier publicité 9:16 · 1:1 · 16:9" }];
  return (
    <TiltCard className="rounded-[28px]" glare={web ? "rgba(167,139,250,0.28)" : "rgba(103,232,249,0.25)"} data-testid={`hub-universe-${tone}`}>
      <Link to={web ? "/web" : "/vision"} className={cn("group relative block h-full overflow-hidden rounded-[28px] p-7 md:p-9", web ? "glass-web" : "glass-vision")}>
        <div className={cn("absolute -right-24 -top-24 size-72 rounded-full blur-3xl transition-transform duration-700 group-hover:scale-125", web ? "bg-violet-500/30" : "bg-cyan-500/25")} />
        <div className="absolute right-8 top-8 size-28 animate-float">
          <div className={cn("absolute inset-0 rounded-full border animate-spin-slow [animation-duration:14s]", web ? "border-violet-300/30" : "border-cyan-300/30")} style={{ borderStyle: "dashed" }} />
          <div className={cn("absolute inset-5 rounded-2xl rotate-12 border backdrop-blur-md transition-transform duration-700 group-hover:rotate-45", web ? "border-violet-300/40 bg-violet-500/20" : "border-cyan-300/40 bg-cyan-500/20")} />
          <div className="absolute inset-0 flex items-center justify-center">
            {web ? <Globe2 className="size-9 text-violet-100" /> : <Clapperboard className="size-9 text-cyan-100" />}
          </div>
        </div>
        <p className={cn("eyebrow", web ? "text-violet-300" : "text-cyan-300")}>{web ? "Univers 01 · Sites" : "Univers 02 · Médias"}</p>
        <h2 className={cn("mt-4 text-4xl font-semibold md:text-5xl", web ? "text-gradient-web" : "text-gradient-vision")}>{web ? "LocalAiWeb" : "LocalAiVision"}</h2>
        <p className="mt-3 max-w-sm text-[15px] leading-relaxed text-slate-300">
          {web ? "Le générateur de sites premium : stratégie, direction artistique, images et code, orchestrés pour chaque métier." : "Le studio photo, vidéo et publicité : vos visuels de marque, prêts à rejoindre vos sites."}
        </p>
        <ul className="mt-8 space-y-3">
          {feats.map(({ i: Icon, t }, k) => (
            <motion.li key={t} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 + k * 0.08, ease }} className="flex items-center gap-3 text-sm text-slate-200">
              <span className={cn("flex size-8 items-center justify-center rounded-lg border", web ? "border-violet-400/30 bg-violet-500/15 text-violet-200" : "border-cyan-400/30 bg-cyan-500/15 text-cyan-200")}>
                <Icon className="size-4" />
              </span>
              {t}
            </motion.li>
          ))}
        </ul>
        <span className={cn("fx-btn mt-9", !web && "vision")} data-testid={web ? "hub-create-web-btn" : "hub-create-vision-btn"}>
          <span className="fx-shine" aria-hidden />
          <span className="relative z-10 inline-flex items-center gap-2">
            {web ? "Créer un site" : "Ouvrir le studio"} <ArrowUpRight className="size-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </span>
        </span>
      </Link>
    </TiltCard>
  );
}

export default function Home() {
  const { data: projects, isError } = useProjects("", "");
  const { data: media } = useMedia("");
  const thumbs = [
    ...(projects ?? []).filter((p) => p.thumbnail_url).map((p) => ({ id: p.id, url: p.thumbnail_url!, label: p.name, to: `/web/p/${p.id}`, video: false })),
    ...(media ?? []).filter((m) => m.status === "done" && m.source !== "site").map((m) => ({ id: m.id, url: m.url!, label: m.prompt, to: "/vision", video: m.kind === "video" })),
  ].slice(0, 14);

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] px-4 pb-10 pt-14 md:px-6 md:pt-20">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300 backdrop-blur">
          <GlowDot /> Moteurs IA en ligne · Claude, GPT, Gemini, Nano Banana, Veo, Kling, MiniMax
        </motion.div>
        <h1 className="mt-6 max-w-5xl text-[44px] font-semibold leading-[1.02] md:text-[88px]" data-testid="hub-title">
          {words.map((w, i) => (
            <motion.span
              key={w + i}
              className={cn("mr-[0.22em] inline-block", i === 1 && "text-gradient-duo")}
              initial={{ opacity: 0, y: 40, rotateX: -60, filter: "blur(10px)" }}
              animate={{ opacity: 1, y: 0, rotateX: 0, filter: "blur(0px)" }}
              transition={{ delay: 0.08 * i, duration: 0.8, ease }}
            >
              {w}
            </motion.span>
          ))}
        </h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="mt-6 max-w-xl text-lg leading-relaxed text-slate-400">
          LocalAiStudio réunit deux univers : des sites web originaux et interactifs, et des visuels de marque photo, vidéo et publicité.
        </motion.p>
      </section>

      <section className="mx-auto grid max-w-[1440px] gap-6 px-4 md:grid-cols-[1.08fr_1fr] md:px-6">
        <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.9, ease }}>
          <Universe tone="web" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.9, ease }} className="md:mt-14">
          <Universe tone="vision" />
        </motion.div>
      </section>

      <section className="mt-20 pb-24">
        <div className="mx-auto mb-6 flex max-w-[1440px] items-end justify-between px-4 md:px-6">
          <div>
            <p className="eyebrow text-slate-500">Dernières créations</p>
            <h3 className="mt-2 text-2xl font-semibold">L'atelier en mouvement</h3>
          </div>
          <Link to="/web" data-testid="hub-see-projects" className="text-sm text-violet-300 transition-colors hover:text-white">Tous les projets →</Link>
        </div>
        {thumbs.length === 0 ? (
          <div className="mx-auto max-w-[1440px] px-4 md:px-6">
            <div className="glass flex items-center gap-4 rounded-2xl p-6 text-slate-400" data-testid="hub-empty">
              <Sparkles className="size-5 text-violet-300" />
              {isError ? "Le studio est momentanément hors ligne." : "Vos sites et médias apparaîtront ici, en défilement continu."}
            </div>
          </div>
        ) : (
          <div className="relative overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_8%,black_92%,transparent)]">
            <div className="flex w-max animate-marquee gap-4 hover:[animation-play-state:paused]">
              {[...thumbs, ...thumbs].map((t, i) => (
                <Link key={t.id + i} to={t.to} data-testid={i < thumbs.length ? `hub-recent-${t.id}` : undefined} className="group relative h-56 w-80 shrink-0 overflow-hidden rounded-2xl border border-white/10">
                  {t.video ? <video src={t.url} muted loop autoPlay playsInline className="size-full object-cover" /> : <img src={t.url} alt={t.label} className="size-full object-cover transition-transform duration-700 group-hover:scale-110" />}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent" />
                  <p className="absolute bottom-3 left-4 right-4 truncate text-sm font-medium">{t.label}</p>
                </Link>
              ))}
            </div>
          </div>
        )}
        {projects && projects.length > 0 && (
          <div className="mx-auto mt-6 flex max-w-[1440px] flex-wrap gap-2 px-4 md:px-6">
            {projects.slice(0, 6).map((p) => (
              <Link key={p.id} to={`/web/p/${p.id}`} className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-violet-400/50 hover:text-white">
                {p.name || "Nouveau site"} · {SITE_TYPES[p.site_type] ?? p.site_type}
              </Link>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
