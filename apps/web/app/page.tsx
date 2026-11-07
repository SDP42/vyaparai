import { LandingPage } from "@/components/landing/LandingPage";

/**
 * Single route for this stage. The cinematic key-and-lock opening will be mounted
 * before <LandingPage/> in a later phase.
 */
export default function Home() {
  return <LandingPage />;
}
