"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { DocumentsPage } from "@/components/app/DocumentsPage";
import { loadSession } from "@/lib/session";

export default function DocumentsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <DocumentsPage /> : null;
}
