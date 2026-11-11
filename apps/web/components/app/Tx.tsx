"use client";

import { useT, type Key } from "@/lib/i18n";

/** A translated string in place, so server-light page files need no hook of their own. */
export function Tx({ k }: { k: Key }) {
  const { t } = useT();
  return <>{t(k)}</>;
}
