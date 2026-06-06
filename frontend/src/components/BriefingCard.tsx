export function BriefingCard(): JSX.Element {
  return (
    <section className="rounded-2xl border border-cyan-500/30 bg-cyan-950/10 p-4">
      <h2 className="mb-2 text-lg font-bold uppercase tracking-[0.3em] text-cyan-200">War Briefing</h2>
      <p className="text-sm text-slate-300">M1 plain-mode briefing is served by the backend from the cached dispatch feed.</p>
    </section>
  );
}
