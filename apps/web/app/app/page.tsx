"use client";

import { useRouter } from "next/navigation";
import { CommandCenter } from "@/components/app/CommandCenter";
import { DemoDashboard } from "@/components/app/DemoDashboard";
import { clearSession, loadSession } from "@/lib/session";

export default function AppHome() {
  const router = useRouter();
  const session = loadSession();
  if (session?.kind === "persona") {
    return (
      <DemoDashboard
        personaId={session.personaId}
        onSignOut={() => {
          clearSession();
          router.push("/login");
        }}
      />
    );
  }
  return <CommandCenter />;
}
