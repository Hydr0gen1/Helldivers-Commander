import type { Planet } from '../api/types';

interface PlanetPanelProps {
  planet: Planet | null;
}

export function PlanetPanel({ planet }: PlanetPanelProps): JSX.Element {
  if (planet === null) {
    return (
      <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4 text-slate-400">
        Select a planet on the tactical map.
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-cyan-100">{planet.name}</h2>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400/80">{planet.sector}</p>
        </div>
        <span className="rounded bg-cyan-400/10 px-2 py-1 text-xs text-cyan-100">{planet.currentOwner}</span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Liberation</dt><dd className="text-lg text-terminal">{planet.liberationPct.toFixed(2)}%</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Helldivers</dt><dd className="text-lg text-terminal">{planet.players.toLocaleString()}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Health</dt><dd>{planet.health.toLocaleString()}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Decay/sec</dt><dd>{planet.regenPerSecond.toFixed(2)}</dd></div>
      </dl>
    </section>
  );
}
