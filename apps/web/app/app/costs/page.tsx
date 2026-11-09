"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CostsPage } from "@/components/app/CostsPage";
import { loadSession } from "@/lib/session";

export default function CostsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <CostsPage /> : null;
}
