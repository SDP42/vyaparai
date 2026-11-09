"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EventsPage } from "@/components/app/EventsPage";
import { loadSession } from "@/lib/session";

export default function FestivalsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <EventsPage /> : null;
}
