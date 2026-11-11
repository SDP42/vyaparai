"use client";

import { useEffect, useState } from "react";

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

/** Registers the service worker (production only), and offers "install" and an offline notice. */
export function PwaRegister() {
  const [offline, setOffline] = useState(false);
  const [saved, setSaved] = useState(false);
  const [install, setInstall] = useState<InstallEvent | null>(null);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
    const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as unknown as { standalone?: boolean }).standalone;
    setIos(/iphone|ipad|ipod/i.test(navigator.userAgent) && !standalone);
    const onBip = (e: Event) => { e.preventDefault(); setInstall(e as InstallEvent); };
    const off = () => setOffline(true);
    const on = () => { setOffline(false); setSaved(false); };
    const fromCache = () => setSaved(true);
    setOffline(!navigator.onLine);
    window.addEventListener("beforeinstallprompt", onBip);
    window.addEventListener("offline", off);
    window.addEventListener("online", on);
    window.addEventListener("vyapar:offline-data", fromCache);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBip);
      window.removeEventListener("offline", off);
      window.removeEventListener("online", on);
      window.removeEventListener("vyapar:offline-data", fromCache);
    };
  }, []);

  return (
    <>
      {(offline || saved) && (
        <div role="status" className="fixed inset-x-0 bottom-16 z-40 bg-fg px-4 py-2 text-center text-sm text-canvas md:bottom-0">
          {saved ? "You are offline. These are the numbers saved on this phone." : "You are offline. Saved numbers will open; new data needs a connection."}
        </div>
      )}
      {install && (
        <button type="button" onClick={async () => { await install.prompt(); setInstall(null); }} className="fixed bottom-20 right-4 z-40 md:bottom-4 rounded-full bg-fg px-5 py-3 text-sm font-semibold text-canvas shadow-lg hover:bg-sindoor">
          Install the app
        </button>
      )}
      {ios && !install && (
        <p className="sr-only">To install on iPhone, tap Share, then Add to Home Screen.</p>
      )}
    </>
  );
}
