import { useEffect, useMemo, useState } from 'react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/client';
import type { Gambit, Planet, PlanetHistoryPoint } from '../api/types';

interface PlanetPanelProps {
  planet: Planet | null;
  gambits?: Gambit[];
}

function formatHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) {
    return '—';
  }
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`;
  }
  return `${hours.toFixed(1)}h`;
}

function formatRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) {
    return '—';
  }
  return `${rate > 0 ? '+' : ''}${rate.toFixed(2)}%/hr`;
}

export function PlanetPanel({ planet, gambits = [] }: PlanetPanelProps): JSX.Element {
  const [details, setDetails] = useState<Planet | null>(planet);
  const [history, setHistory] = useState<PlanetHistoryPoint[]>([]);

  useEffect(() => {
    setDetails(planet);
    setHistory([]);
    if (planet === null) {
      return;
    }
    let cancelled = false;
    const loadHistory = async (): Promise<void> => {
      try {
        const [freshPlanet, planetHistory] = await Promise.all([api.planet(planet.index), api.planetHistory(planet.index)]);
        if (!cancelled) {
          setDetails(freshPlanet);
          setHistory(planetHistory.history);
        }
      } catch {
        if (!cancelled) {
          setDetails(planet);
          setHistory([]);
        }
      }
    };
    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [planet]);

  const chartData = useMemo(
    () => history.map((point) => ({ ...point, label: new Date(point.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) })),
    [history]
  );

  const displayPlanet = details ?? planet;
  const planetGambits = displayPlanet === null ? [] : gambits.filter((gambit) => gambit.targetIndex === displayPlanet.index || gambit.sourceIndex === displayPlanet.index);

  if (displayPlanet === null) {
    return (
      <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4 text-slate-400">
        Select a planet on the tactical map.
      </section>
    );
  }

  const netRate = displayPlanet.derived?.libRatePctPerHr ?? null;
  const barColor = netRate !== null && netRate < 0 ? 'bg-red-500' : 'bg-emerald-400';
  const barWidth = `${Math.max(2, Math.min(100, displayPlanet.liberationPct))}%`;

  return (
    <section className="rounded-2xl border border-cyan-500/30 bg-black/50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-cyan-100">{displayPlanet.name}</h2>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400/80">{displayPlanet.sector}</p>
        </div>
        <span className="rounded bg-cyan-400/10 px-2 py-1 text-xs text-cyan-100">{displayPlanet.currentOwner}</span>
      </div>
      <div className="mt-4 h-2 rounded-full bg-slate-900">
        <div className={`h-2 rounded-full ${barColor}`} style={{ width: barWidth }} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Liberation</dt><dd className="text-lg text-terminal">{displayPlanet.liberationPct.toFixed(2)}%</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Helldivers</dt><dd className="text-lg text-terminal">{displayPlanet.players.toLocaleString()}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Net rate</dt><dd className={netRate !== null && netRate < 0 ? 'text-red-300' : 'text-emerald-300'}>{formatRate(netRate)}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">ETA</dt><dd>{formatHours(displayPlanet.derived?.etaHours)}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Decay rate</dt><dd className="text-orange-200">{formatRate(displayPlanet.derived?.decayPctPerHr ?? 0)}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Trend</dt><dd className="capitalize">{displayPlanet.derived?.trend ?? '—'}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Health</dt><dd>{displayPlanet.health.toLocaleString()}</dd></div>
        <div className="rounded bg-slate-900/80 p-3"><dt className="text-slate-400">Decay/sec</dt><dd>{displayPlanet.regenPerSecond.toFixed(2)}</dd></div>
      </dl>
      {planetGambits.length ? (
        <div className="mt-4 rounded border border-amber-300/30 bg-amber-950/20 p-3">
          <div className="mb-2 text-xs uppercase tracking-[0.18em] text-amber-200">Graph intel</div>
          <ul className="space-y-2 text-sm text-amber-50/90">
            {planetGambits.map((gambit) => (
              <li key={`${gambit.kind}-${gambit.sourceIndex}-${gambit.targetIndex}`} className="rounded bg-black/30 p-2">
                <span className="mr-2 rounded bg-amber-300/15 px-2 py-0.5 text-xs font-bold text-amber-200">{gambit.kind}</span>
                {gambit.note}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="mt-4 rounded bg-slate-950/80 p-3">
        <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.18em] text-slate-400">
          <span>Liberation history</span>
          <span>{history.length ? `${history.length} points` : 'Awaiting DB snapshots'}</span>
        </div>
        <div className="h-28">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis dataKey="label" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip
                contentStyle={{ background: '#020617', border: '1px solid rgba(34,211,238,0.35)', color: '#e0f2fe' }}
                formatter={(value: number) => [`${Number(value).toFixed(2)}%`, 'Liberation']}
                labelFormatter={(label) => `Time ${label}`}
              />
              <Line type="monotone" dataKey="liberationPct" stroke={netRate !== null && netRate < 0 ? '#f87171' : '#34d399'} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
