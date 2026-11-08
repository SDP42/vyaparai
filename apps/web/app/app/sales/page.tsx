"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { SalesExplorer } from "@/components/app/SalesExplorer";
import { loadSession } from "@/lib/session";

export default function SalesRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <SalesExplorer /> : null;
}
