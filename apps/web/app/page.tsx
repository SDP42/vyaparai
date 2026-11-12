import { Nav } from "@/components/landing/Nav";
import { SmoothScroll } from "@/components/landing/SmoothScroll";
import { ShopOpening } from "@/components/opening/ShopOpening";
import { FinalCta, Jobs, Showcase, Trust, Voice } from "@/components/landing/v2/Bottom";
import { Hero, HowItWorks, Proof } from "@/components/landing/v2/Top";

export default function LandingPage() {
  return (
    <SmoothScroll>
      <a
        href="#top"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded focus:bg-fg focus:px-3 focus:py-2 focus:text-canvas"
      >
        Skip to content
      </a>
      <ShopOpening />
      <Nav />
      <main>
        <Hero />
        <Proof />
        <HowItWorks />
        <Showcase />
        <Jobs />
        <Voice />
        <Trust />
      </main>
      <FinalCta />
    </SmoothScroll>
  );
}
