"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ProductsPage } from "@/components/app/ProductsPage";
import { loadSession } from "@/lib/session";

export default function ProductsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <ProductsPage /> : null;
}
