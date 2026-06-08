import React, { useCallback, useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { api } from './api/client';
import type { Dispatch, Gambit, HealthResponse, Order, Planet, War } from './api/types';
import { DispatchFeed } from './components/DispatchFeed';
import { OrderTracker } from './components/OrderTracker';
import { PlanetPanel } from './components/PlanetPanel';
import { WarStats } from './components/WarStats';
import { GalaxyMap } from './three/GalaxyMap';
import { useWarStream } from './hooks/useWarStream';
import './theme/crt.css';

function App(): JSX.Element {
  const [planets, setPlanets] = useState<Planet[]>([]);
  const [selected, setSelected] = useState<Planet | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [dispatches, setDispatches] = useState<Dispatch[]>([]);
  const [war, setWar] = useState<War | null>(null);
  const [gambits, setGambits] = useState<Gambit[]>([]);
  const [showGraphIntel, setShowGraphIntel] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applyPlanets = useCallback((response: { planets: Planet[] }) => {
    setPlanets(response.planets);
    setSelected((current) => current ? response.planets.find((planet) => planet.index === current.index) ?? current : response.planets[0] ?? null);
  }, []);

  const handleStreamError = useCallback((err: Error) => {
    setError(err.message);
  }, []);

  useWarStream({ onPlanets: applyPlanets, onError: handleStreamError });

  useEffect(() => {
    const refresh = async (): Promise<void> => {
      try {
        const [planetResponse, orderResponse, dispatchResponse, warResponse, graphResponse] = await Promise.all([
          api.planets(),
          api.orders(),
          api.dispatches(),
          api.war(),
          api.gambits()
        ]);
        applyPlanets(planetResponse);
        setOrders(orderResponse.orders);
        setDispatches(dispatchResponse.dispatches.slice().reverse());
        setWar(warResponse);
        setGambits(graphResponse.gambits);
        try {
          setHealth(await api.health());
        } catch {
          setHealth(null);
        }
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'WarDesk API unavailable');
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60_000);
    return () => window.clearInterval(timer);
  }, [applyPlanets]);

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <header className="flex flex-col justify-between gap-3 border-b border-cyan-500/20 pb-4 md:flex-row md:items-end">
        <div>
          <p className="text-xs uppercase tracking-[0.45em] text-terminal">Super Earth Tactical Console</p>
          <h1 className="text-4xl font-black uppercase tracking-[0.15em] text-cyan-100">WarDesk</h1>
        </div>
        <div className="space-y-2 text-sm text-slate-400 md:text-right">
          <p>Browser traffic terminates at WarDesk. Upstream APIs are polled only by the backend worker.</p>
          <SourceStatus health={health} />
        </div>
      </header>
      {error ? <div className="rounded border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-100">{error}</div> : null}
      <WarStats war={war} planetCount={planets.length} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-cyan-500/20 bg-black/40 px-4 py-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-cyan-400/80">Supply-line graph intelligence</p>
              <p className="text-sm text-slate-400">{gambits.length} gambit/siege/chokepoint detections cached by WarDesk.</p>
            </div>
            <button
              type="button"
              onClick={() => setShowGraphIntel((current) => !current)}
              className={`rounded border px-3 py-2 text-xs uppercase tracking-[0.2em] transition ${
                showGraphIntel ? 'border-terminal/60 bg-terminal/15 text-terminal' : 'border-slate-600 bg-slate-900/80 text-slate-300 hover:border-cyan-400/60'
              }`}
              aria-pressed={showGraphIntel}
            >
              {showGraphIntel ? 'Hide intel' : 'Show intel'}
            </button>
          </div>
          <GalaxyMap planets={planets} selected={selected} onSelect={setSelected} gambits={gambits} showGraphIntel={showGraphIntel} />
        </section>
        <div className="space-y-6">
          <PlanetPanel planet={selected} gambits={gambits} />
          <OrderTracker orders={orders} />
        </div>
      </div>
      <DispatchFeed dispatches={dispatches} />
    </main>
  );
}

function SourceStatus({ health }: { health: HealthResponse | null }): JSX.Element {
  const entries = Object.entries(health?.sources ?? {});
  const title = entries.length ? entries.map(([source, status]) => `${source}: ${status}`).join(' • ') : 'source health unavailable';
  const aggregate = entries.some(([, status]) => status === 'up') ? 'up' : entries.some(([, status]) => status === 'open') ? 'open' : 'down';
  const color = aggregate === 'up' ? 'bg-emerald-400 shadow-emerald-400/70' : aggregate === 'open' ? 'bg-amber-300 shadow-amber-300/70' : 'bg-red-500 shadow-red-500/70';
  return (
    <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500" title={title}>
      <span className={`h-2.5 w-2.5 rounded-full shadow ${color}`} aria-hidden="true" />
      <span>Sources</span>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
