"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { BillsPage } from "@/components/app/BillsPage";
import { loadSession } from "@/lib/session";

export default function BillsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <BillsPage /> : null;
}
