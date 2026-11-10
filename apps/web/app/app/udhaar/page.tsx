"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { UdhaarPage } from "@/components/app/UdhaarPage";
import { loadSession } from "@/lib/session";

export default function UdhaarRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <UdhaarPage /> : null;
}
