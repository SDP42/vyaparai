"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { InventoryPage } from "@/components/app/InventoryPage";
import { loadSession } from "@/lib/session";

export default function InventoryRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <InventoryPage /> : null;
}
