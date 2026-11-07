"use client";

import { useEffect, useRef, useState, type ReactNode, type PointerEvent } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";

export const EASE = [0.16, 1, 0.3, 1] as const;

/** Eyebrow label that "decodes" from random glyphs when it enters the viewport. */
export function Eyebrow({ children, className = "" }: { children: string; className?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const reduce = useReducedMotion();
  const [text, setText] = useState(children);

  useEffect(() => {
    if (!inView || reduce) return;
    const glyphs = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/·—";
    let frame = 0;
    const total = 22;
    const id = window.setInterval(() => {
      frame++;
      const revealed = Math.floor((frame / total) * children.length);
      setText(
        children
          .split("")
          .map((ch, i) => (i < revealed || ch === " " ? ch : glyphs[Math.floor(Math.random() * glyphs.length)]))
          .join(""),
      );
      if (frame >= total) {
        window.clearInterval(id);
        setText(children);
      }
    }, 32);
    return () => window.clearInterval(id);
  }, [inView, reduce, children]);

  return (
    <p ref={ref} className={`font-mono text-[11px] uppercase tracking-[0.24em] text-blue-soft ${className}`} aria-label={children}>
      <span aria-hidden>{text}</span>
    </p>
  );
}

/** Headline whose words rise out of a mask, one after another. */
export function SplitHeading({
  text,
  as: Tag = "h2",
  className = "",
  accent,
  id,
}: {
  id?: string;
  text: string;
  as?: "h1" | "h2" | "h3";
  className?: string;
  accent?: string[];
}) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <Tag id={id} className={className} aria-label={text}>
      {words.map((w, i) => {
        const isAccent = accent?.some((a) => w.toLowerCase().startsWith(a.toLowerCase()));
        return (
          <span key={i} aria-hidden className="inline-block overflow-hidden pb-[0.12em] align-top">
            <motion.span
              className={`inline-block ${isAccent ? "bg-gradient-to-r from-violet-soft to-blue-soft bg-clip-text text-transparent" : ""}`}
              initial={reduce ? false : { y: "110%", rotate: 4 }}
              whileInView={{ y: "0%", rotate: 0 }}
              viewport={{ once: true, margin: "-8% 0px" }}
              transition={{ duration: 0.9, ease: EASE, delay: i * 0.045 }}
            >
              {w}
              {i < words.length - 1 ? " " : ""}
            </motion.span>
          </span>
        );
      })}
    </Tag>
  );
}

export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 28, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.8, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

/** Button that leans toward the pointer. */
export function MagneticLink({
  href,
  children,
  variant = "primary",
  onClick,
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "ghost";
  onClick?: () => void;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const move = (e: PointerEvent<HTMLAnchorElement>) => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = el.getBoundingClientRect();
    el.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.25}px)`;
  };
  const leave = () => {
    if (ref.current) ref.current.style.transform = "";
  };
  const styles =
    variant === "primary"
      ? "bg-fg text-white hover:bg-violet shadow-[0_14px_40px_-14px_rgba(115,87,232,0.8)]"
      : "border border-line-strong text-fg hover:border-fg/40 hover:bg-surface";
  return (
    <a
      ref={ref}
      href={href}
      onClick={onClick}
      onPointerMove={move}
      onPointerLeave={leave}
      className={`group inline-flex h-12 items-center gap-2 rounded-full px-6 text-sm font-medium transition-[background,border-color,transform] duration-300 ease-out ${styles}`}
    >
      {children}
      <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-0.5">
        →
      </span>
    </a>
  );
}

/** Card with a cursor-following spotlight + animated gradient border on hover. */
export function SpotlightCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  const move = (e: PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return (
    <div
      onPointerMove={move}
      className={`ring-sweep group relative overflow-hidden rounded-3xl border border-line bg-surface ${className}`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(520px circle at var(--mx) var(--my), color-mix(in oklab, var(--color-violet) 14%, transparent), transparent 60%)",
        }}
      />
      <div className="relative h-full">{children}</div>
    </div>
  );
}

/** Animated count-up for figures (formatter supplied by caller). */
export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [v, setV] = useState(reduce ? value : 0);
  useEffect(() => {
    if (!inView || reduce) {
      setV(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 1400);
      setV(value * (1 - Math.pow(1 - k, 4)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, reduce, value]);
  return (
    <span ref={ref} className="tabular">
      {format(v)}
    </span>
  );
}

export function DemoBadge({ label = "Demo data" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-brass/40 bg-brass/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-brass">
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-brass" />
      {label}
    </span>
  );
}

export function Delta({ v }: { v: number }) {
  const up = v >= 0;
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-xs ${up ? "text-success" : "text-danger"}`}>
      <span aria-hidden>{up ? "▲" : "▼"}</span>
      {Math.abs(v).toFixed(1)}%<span className="sr-only">{up ? " increase" : " decrease"}</span>
    </span>
  );
}
