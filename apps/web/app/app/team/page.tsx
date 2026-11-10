"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { TeamPage } from "@/components/app/TeamPage";
import { loadSession } from "@/lib/session";

export default function TeamRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <TeamPage /> : null;
}
