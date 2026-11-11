"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useWorkspace } from "./AppContext";

/** What the signed-in person's job in the shop (persona) allows: pages, questions, data. */
export type PersonaView = {
  key: string;
  label: string;
  about: string;
  home: string;
  nav: string[];
  capabilities: string[];
  suggestions: string[];
};
type Ctx = { persona: PersonaView | null; ready: boolean };
const PersonaCtx = createContext<Ctx>({ persona: null, ready: false });
export const usePersona = () => useContext(PersonaCtx);

/** Whether a page is part of this persona's view (no persona means every page). */
export function allowedPath(persona: PersonaView | null, path: string): boolean {
  if (!persona || persona.key === "owner") return true;
  return persona.nav.some((n) => (n === "/app" ? path === "/app" : path === n || path.startsWith(`${n}/`)));
}

export function PersonaProvider({ children }: { children: ReactNode }) {
  const { workspace } = useWorkspace();
  const { lang } = useT();
  const [state, setState] = useState<Ctx>({ persona: null, ready: false });
  useEffect(() => {
    let live = true;
    api<{ persona: PersonaView | null }>(`/workspaces/${workspace.id}/me?lang=${lang}`)
      .then((d) => live && setState({ persona: d.persona, ready: true }))
      .catch(() => live && setState({ persona: null, ready: true }));
    return () => {
      live = false;
    };
  }, [workspace.id, lang]);
  return <PersonaCtx.Provider value={state}>{children}</PersonaCtx.Provider>;
}
