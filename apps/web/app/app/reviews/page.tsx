"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ReviewsPage } from "@/components/app/ReviewsPage";
import { loadSession } from "@/lib/session";

export default function ReviewsRoute() {
  const router = useRouter();
  const isAccount = typeof window !== "undefined" && loadSession()?.kind === "account";
  useEffect(() => {
    if (!isAccount) router.replace("/app");
  }, [isAccount, router]);
  return isAccount ? <ReviewsPage /> : null;
}
