"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { OrdersPage } from "@/components/app/OrdersPage";
import { loadSession } from "@/lib/session";

export default function OrdersPageRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <OrdersPage /> : null;
}
