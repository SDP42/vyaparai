import { Nav } from "@/components/landing/Nav";
import { Hero } from "@/components/landing/Hero";
import { Story } from "@/components/landing/Story";
import { ZoomReveal } from "@/components/landing/ZoomReveal";
import { Features } from "@/components/landing/Features";
import { Principles } from "@/components/landing/Principles";
import { Cta } from "@/components/landing/Cta";
import { SmoothScroll } from "@/components/landing/SmoothScroll";

export default function LandingPage() {
  return (
    <SmoothScroll>
      <div className="grain">
        <a href="#story" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded focus:bg-fg focus:px-3 focus:py-2 focus:text-canvas">
          Skip intro animation
        </a>
        <Nav />
        <main>
          <Hero />
          <Story />
          <ZoomReveal />
          <Features />
          <Principles />
          <Cta />
        </main>
      </div>
    </SmoothScroll>
  );
}
