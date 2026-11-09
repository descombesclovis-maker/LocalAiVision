import { forwardRef, useState, type ButtonHTMLAttributes, type MouseEvent } from "react";
import { cn } from "@/lib/utils";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "web" | "vision" | "ghost";
  size?: "sm" | "md" | "lg";
};

interface Ripple { id: number; x: number; y: number }

// Signature button: conic animated border on hover, light sweep, click ripple.
export const FxButton = forwardRef<HTMLButtonElement, Props>(function FxButton(
  { tone = "web", size = "md", className, children, onClick, ...rest },
  ref,
) {
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const handle = (e: MouseEvent<HTMLButtonElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const id = Date.now();
    setRipples((p) => [...p, { id, x: e.clientX - r.left, y: e.clientY - r.top }]);
    window.setTimeout(() => setRipples((p) => p.filter((x) => x.id !== id)), 650);
    onClick?.(e);
  };
  return (
    <button
      ref={ref}
      type="button"
      {...rest}
      onClick={handle}
      className={cn("fx-btn", tone === "vision" && "vision", tone === "ghost" && "ghost", size === "sm" && "sm", size === "lg" && "lg", className)}
    >
      <span className="fx-shine" aria-hidden />
      {ripples.map((r) => (
        <span
          key={r.id}
          aria-hidden
          className="pointer-events-none absolute size-6 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/50 animate-[pulse-ring_0.65s_ease-out_forwards]"
          style={{ left: r.x, top: r.y }}
        />
      ))}
      <span className="relative z-10 inline-flex items-center gap-2">{children}</span>
    </button>
  );
});

export function IconBtn({ active, className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        "inline-flex size-9 items-center justify-center rounded-lg border text-slate-300 transition-[background-color,color,border-color,transform] duration-200 hover:-translate-y-0.5 hover:text-white active:scale-95 disabled:opacity-40",
        active ? "border-violet-400/60 bg-violet-500/20 text-white shadow-[0_0_20px_-4px_rgba(139,92,246,0.7)]" : "border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.07]",
        className,
      )}
    />
  );
}
