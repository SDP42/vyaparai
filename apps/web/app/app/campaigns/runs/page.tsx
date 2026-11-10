"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CampaignRunsPage } from "@/components/app/CampaignRunsPage";
import { loadSession } from "@/lib/session";

export default function CampaignRunsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <CampaignRunsPage /> : null;
}
