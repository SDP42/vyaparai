"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { GallaPage } from "@/components/app/GallaPage";
import { loadSession } from "@/lib/session";

export default function GallaPageRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <GallaPage /> : null;
}
