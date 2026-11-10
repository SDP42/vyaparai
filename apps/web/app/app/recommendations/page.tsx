"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { RecommendationsPage } from "@/components/app/RecommendationsPage";
import { loadSession } from "@/lib/session";

export default function RecommendationsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <RecommendationsPage /> : null;
}
