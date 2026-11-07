import { SmoothScroll } from "./SmoothScroll";
import { Navigation } from "./Navigation";
import { HeroSection } from "./HeroSection";
import { ProblemSection } from "./ProblemSection";
import { IntelligenceSection } from "./IntelligenceSection";
import { HowItWorksSection } from "./HowItWorksSection";
import { ProductPreviewSection } from "./ProductPreviewSection";
import { ShowcaseSection } from "./ShowcaseSection";
import { CopilotPreviewSection } from "./CopilotPreviewSection";
import { TrustSection } from "./TrustSection";
import { FinalCta, Footer } from "./FinalCta";
import { CinematicOpening } from "@/components/opening/CinematicOpening";

export function LandingPage() {
  return (
    <SmoothScroll>
      <div className="grain">
        <a
          href="#platform"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded focus:bg-fg focus:px-3 focus:py-2 focus:text-canvas"
        >
          Skip to content
        </a>
        <CinematicOpening />
        <Navigation />
        <main>
          <HeroSection />
          <ProblemSection />
          <IntelligenceSection />
          <HowItWorksSection />
          <ProductPreviewSection />
          <ShowcaseSection />
          <CopilotPreviewSection />
          <TrustSection />
          <FinalCta />
        </main>
        <Footer />
      </div>
    </SmoothScroll>
  );
}
