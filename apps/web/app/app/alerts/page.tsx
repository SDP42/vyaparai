"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AlertsPage } from "@/components/app/AlertsPage";
import { loadSession } from "@/lib/session";

export default function AlertsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <AlertsPage /> : null;
}
