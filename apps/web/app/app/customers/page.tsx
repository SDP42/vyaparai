"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { CustomersPage } from "@/components/app/CustomersPage";
import { loadSession } from "@/lib/session";

export default function CustomersRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <CustomersPage /> : null;
}
