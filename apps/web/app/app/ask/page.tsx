"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AskPage } from "@/components/app/AskPage";
import { loadSession } from "@/lib/session";

export default function AskRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <AskPage /> : null;
}
