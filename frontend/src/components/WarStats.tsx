import type { War } from '../api/types';

interface WarStatsProps {
  war: War | null;
  planetCount: number;
}

export function WarStats({ war, planetCount }: WarStatsProps): JSX.Element {
  return (
    <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className="rounded-xl border border-cyan-500/20 bg-black/40 p-3"><p className="text-xs text-slate-400">War ID</p><p className="text-lg text-cyan-100">{war?.warId ?? '—'}</p></div>
      <div className="rounded-xl border border-cyan-500/20 bg-black/40 p-3"><p className="text-xs text-slate-400">Planets</p><p className="text-lg text-cyan-100">{planetCount}</p></div>
      <div className="rounded-xl border border-cyan-500/20 bg-black/40 p-3"><p className="text-xs text-slate-400">Players</p><p className="text-lg text-cyan-100">{war?.statistics.playerCount.toLocaleString() ?? '—'}</p></div>
      <div className="rounded-xl border border-cyan-500/20 bg-black/40 p-3"><p className="text-xs text-slate-400">Accuracy</p><p className="text-lg text-cyan-100">{war?.statistics.accuracy ?? 0}%</p></div>
    </section>
  );
}
