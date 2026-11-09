import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const PALETTES = {
  web: ["rgba(139,92,246,0.32)", "rgba(192,132,252,0.18)", "rgba(76,29,149,0.35)"],
  vision: ["rgba(6,182,212,0.28)", "rgba(103,232,249,0.14)", "rgba(14,116,144,0.32)"],
  duo: ["rgba(139,92,246,0.30)", "rgba(6,182,212,0.24)", "rgba(91,33,182,0.28)"],
};

// Fixed animated aurora + grid + cursor spotlight behind every screen.
export function Aurora({ tone = "duo" }: { tone?: keyof typeof PALETTES }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.setProperty("--mx", `${e.clientX}px`);
        el.style.setProperty("--my", `${e.clientY}px`);
      });
    };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, []);
  const [a, b, c] = PALETTES[tone];
  return (
    <div ref={ref} aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-obsidian">
      <div className="absolute -left-[15%] -top-[20%] size-[70vmax] rounded-full blur-[120px] animate-aurora transition-[background] duration-1000" style={{ background: a }} />
      <div className="absolute -right-[20%] top-[10%] size-[60vmax] rounded-full blur-[130px] animate-aurora [animation-delay:-6s] transition-[background] duration-1000" style={{ background: b }} />
      <div className="absolute bottom-[-30%] left-[20%] size-[55vmax] rounded-full blur-[140px] animate-aurora [animation-delay:-11s] transition-[background] duration-1000" style={{ background: c }} />
      <div className="grid-lines absolute inset-0" />
      <div className="spotlight absolute inset-0" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,#090A0F_100%)]" />
    </div>
  );
}

export function GlowDot({ tone = "web", className }: { tone?: "web" | "vision"; className?: string }) {
  const c = tone === "web" ? "bg-violet-400" : "bg-cyan-400";
  return (
    <span className={cn("relative inline-flex size-2.5", className)}>
      <span className={cn("absolute inset-0 rounded-full animate-pulse-ring", c)} />
      <span className={cn("relative inline-flex size-2.5 rounded-full", c)} />
    </span>
  );
}
