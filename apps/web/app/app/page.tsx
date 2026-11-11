"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CommandCenter } from "@/components/app/CommandCenter";
import { allowedPath, usePersona } from "@/components/app/PersonaContext";

export default function AppHome() {
  const router = useRouter();
  const { persona, ready } = usePersona();
  const away = ready && !allowedPath(persona, "/app");
  useEffect(() => {
    if (away && persona) router.replace(persona.home);
  }, [away, persona, router]);
  if (!ready || away) return <div aria-busy="true" className="min-h-[50vh]" />;
  return <CommandCenter />;
}
