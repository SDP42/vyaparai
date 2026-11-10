export const metadata = { title: "Offline — Vyapar AI" };

export default function Offline() {
  return (
    <main className="grid min-h-dvh place-items-center bg-canvas p-6">
      <div className="max-w-md text-center">
        <p className="font-serif text-4xl">No connection</p>
        <p className="mt-3 text-fg/75">Numbers you looked at recently are saved on this phone and open when you go back to the app. Anything new needs a connection.</p>
        <a href="/app" className="mt-6 inline-block rounded-full bg-fg px-6 py-2.5 font-semibold text-canvas">Open the app</a>
      </div>
    </main>
  );
}
