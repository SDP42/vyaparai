"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CampaignsPage } from "@/components/app/CampaignsPage";
import { loadSession } from "@/lib/session";

export default function CampaignsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <CampaignsPage /> : null;
}
