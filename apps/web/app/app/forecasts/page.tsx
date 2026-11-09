"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ForecastsPage } from "@/components/app/ForecastsPage";
import { loadSession } from "@/lib/session";

export default function ForecastsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <ForecastsPage /> : null;
}
