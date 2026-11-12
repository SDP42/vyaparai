"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ExpiryPage } from "@/components/app/ExpiryPage";
import { loadSession } from "@/lib/session";

export default function ExpiryPageRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <ExpiryPage /> : null;
}
