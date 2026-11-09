"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { DigestPage } from "@/components/app/DigestPage";
import { loadSession } from "@/lib/session";

export default function DigestRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <DigestPage /> : null;
}
