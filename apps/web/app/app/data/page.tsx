"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { DataPage } from "@/components/app/DataPage";
import { loadSession } from "@/lib/session";

export default function DataRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <DataPage /> : null;
}
