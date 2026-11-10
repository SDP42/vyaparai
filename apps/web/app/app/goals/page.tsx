"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { GoalsPage } from "@/components/app/GoalsPage";
import { loadSession } from "@/lib/session";

export default function GoalsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <GoalsPage /> : null;
}
