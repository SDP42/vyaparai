"use client";

import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { DashboardPreview } from "./DashboardPreview";

gsap.registerPlugin(ScrollTrigger);

/** Zoom-through: the headline flies past the camera while the product scales up to fill the screen. */
export function ZoomReveal() {
  const root = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: { trigger: el, start: "top top", end: "+=180%", pin: true, scrub: 0.7 },
      });
      tl.to("[data-zoom='word']", { scale: 9, opacity: 0, duration: 0.55, ease: "power2.in" }, 0)
        .fromTo(
          "[data-zoom='frame']",
          { scale: 0.32, borderRadius: "48px", rotateX: 22, y: 140 },
          { scale: 1, borderRadius: "18px", rotateX: 0, y: 0, duration: 0.7, ease: "power2.out" },
          0.12,
        )
        .fromTo("[data-zoom='caption']", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.15 }, 0.75);
    });
    return () => mm.revert();
  }, []);

  return (
    <section
      ref={root}
      id="product"
      className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-canvas py-20 [perspective:1400px]"
      aria-labelledby="zoom-title"
    >
      <h2
        id="zoom-title"
        data-zoom="word"
        className="pointer-events-none absolute z-20 text-center text-[13vw] font-extrabold leading-[0.85] tracking-tighter"
      >
        <span className="block">Every rupee,</span>
        <span className="block font-serif font-normal italic text-haldi-deep">explained.</span>
      </h2>
      <div data-zoom="frame" className="relative z-10 w-[min(1180px,94vw)] overflow-hidden border border-line bg-surface shadow-[0_40px_120px_-30px_rgba(217,54,43,0.35)] will-change-transform">
        <DashboardPreview />
      </div>
      <p data-zoom="caption" className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
        Command center · demo data
      </p>
    </section>
  );
}
