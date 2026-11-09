import { useRef, type ReactNode, type PointerEvent } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { cn } from "@/lib/utils";

// 3D tilt card with a light glare that follows the cursor.
export function TiltCard({ children, className, glare = "rgba(167,139,250,0.25)", ...rest }: { children: ReactNode; className?: string; glare?: string; "data-testid"?: string; onClick?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const rx = useSpring(useTransform(y, [0, 1], [7, -7]), { stiffness: 200, damping: 20 });
  const ry = useSpring(useTransform(x, [0, 1], [-9, 9]), { stiffness: 200, damping: 20 });
  const gx = useTransform(x, (v) => `${v * 100}%`);
  const gy = useTransform(y, (v) => `${v * 100}%`);
  const bg = useTransform([gx, gy], ([a, b]) => `radial-gradient(500px circle at ${a} ${b}, ${glare}, transparent 45%)`);
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    x.set((e.clientX - r.left) / r.width);
    y.set((e.clientY - r.top) / r.height);
  };
  const leave = () => { x.set(0.5); y.set(0.5); };
  return (
    <motion.div
      ref={ref}
      onPointerMove={move}
      onPointerLeave={leave}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 1100 }}
      className={cn("relative will-change-transform", className)}
      {...rest}
    >
      {children}
      <motion.div aria-hidden className="pointer-events-none absolute inset-0 rounded-[inherit]" style={{ background: bg }} />
    </motion.div>
  );
}
