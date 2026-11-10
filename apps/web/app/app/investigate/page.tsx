"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { InvestigatePage } from "@/components/app/InvestigatePage";
import { loadSession } from "@/lib/session";

export default function InvestigateRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <InvestigatePage /> : null;
}
