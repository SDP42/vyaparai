"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { PricingPage } from "@/components/app/PricingPage";
import { loadSession } from "@/lib/session";

export default function PricingRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <PricingPage /> : null;
}
