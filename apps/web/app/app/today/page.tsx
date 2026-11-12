"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { TodayPage } from "@/components/app/TodayPage";
import { loadSession } from "@/lib/session";

export default function TodayPageRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <TodayPage /> : null;
}
