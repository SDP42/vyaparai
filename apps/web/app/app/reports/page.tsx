"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ReportsPage } from "@/components/app/ReportsPage";
import { loadSession } from "@/lib/session";

export default function ReportsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <ReportsPage /> : null;
}
