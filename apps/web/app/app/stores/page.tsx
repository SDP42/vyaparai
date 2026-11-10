"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { StoresPage } from "@/components/app/StoresPage";
import { loadSession } from "@/lib/session";

export default function StoresRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <StoresPage /> : null;
}
