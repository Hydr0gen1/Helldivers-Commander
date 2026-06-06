import { useEffect, useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/client';
import type { HistoryPoint, Planet } from '../api/types';

interface PlanetPanelProps {
  planet: Planet | null;
}

function formatEta(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return 'No ETA';
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  return `${hours.toFixed(1)}h`;
}

export function PlanetPanel({ planet }: PlanetPanelProps): JSX.Element {
  const [detail, setDetail] = useState<Planet | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);

  useEffect(() => {
    if (planet === null) {
      setDetail(null);
      setHistory([]);
      return;
    }
    let cancelled = false;
    const load = async (): Promise<void> => {
      try {
        const [planetDetail, historyResponse] = await Promise.all([api.planet(planet.index), api.history(planet.index)]);
        if (!cancelled) {
          setDetail(planetDetail);
          setHistory(historyResponse.history);
        }
      } catch {
        if (!cancelled) {
          setDetail(planet);
          setHistory([]);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [planet]);

  const current = detail ?? planet;
  if (current === null) {
    return (
      <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4 text-slate-400">
        Select a planet on the tactical map.
      </section>
    );
  }

  const derived = current.derived;
  const netRate = derived?.libRatePctPerHr ?? null;
  const netRateClass = netRate !== null && netRate > 0 ? 'text-green-300' : 'text-red-300';
  const chartData = history.map((point) => ({
    ...point,
    time: new Date(point.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }));

  return (
    <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-cyan-100">{current.name}</h2>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400/80">{current.sector}</p>
        </div>
        <span className="rounded bg-cyan-400/10 px-2 py-1 text-xs text-cyan-100">{current.currentOwner}</span>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Liberation</dt><dd className="text-lg text-terminal">{current.liberationPct.toFixed(2)}%</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Helldivers</dt><dd className="text-lg text-terminal">{current.players.toLocaleString()}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Net rate</dt><dd className={`text-lg ${netRateClass}`}>{netRate === null ? '—' : `${netRate.toFixed(2)}%/hr`}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">ETA</dt><dd>{formatEta(derived?.etaHours)}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Decay rate</dt><dd>{derived ? `${derived.decayPctPerHr.toFixed(2)}%/hr` : `${current.regenPerSecond.toFixed(2)}/sec`}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Trend</dt><dd className="capitalize">{derived?.trend ?? 'unknown'}</dd></div>
      </dl>
      <div className="mt-4 h-32 rounded bg-slate-950/80 p-2">
        {chartData.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(34,211,238,0.35)', color: '#e2e8f0' }} />
              <Line type="monotone" dataKey="liberationPct" stroke="#67e8f9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-slate-500">No history snapshots yet.</div>
        )}
      </div>
    </section>
  );
}
