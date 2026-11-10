"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { AnalyticsProvider, WorkspaceProvider } from "@/components/app/AppContext";
import { AppShell } from "@/components/app/AppShell";
import { loadSession, signOut as endSession, type Session } from "@/lib/session";

/**
 * Gate for everything under /app.
 *  - no session        → /login
 *  - persona (demo)    → the page renders alone (illustrative data)
 *  - real account      → workspace + analytics providers and the app shell
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    const s = loadSession();
    if (!s) router.replace("/login");
    setSession(s);
  }, [router]);

  if (!session) return <div className="min-h-dvh bg-canvas" aria-busy="true" />;
  if (session.kind === "persona") return <>{children}</>;

  const signOut = () => {
    void endSession().finally(() => router.push("/login"));
  };
  return (
    <WorkspaceProvider>
      <AnalyticsProvider>
        <AppShell name={session.name} onSignOut={signOut}>
          {children}
        </AppShell>
      </AnalyticsProvider>
    </WorkspaceProvider>
  );
}
