"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { StaffPage } from "@/components/app/StaffPage";
import { loadSession } from "@/lib/session";

export default function StaffRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <StaffPage /> : null;
}
