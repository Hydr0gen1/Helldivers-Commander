import React, { useCallback, useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { api } from './api/client';
import type { Dispatch, Order, Planet, War } from './api/types';
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
  const [error, setError] = useState<string | null>(null);

  const applyPlanets = useCallback((response: { planets: Planet[] }) => {
    setPlanets(response.planets);
    setSelected((current) => current ? response.planets.find((planet) => planet.index === current.index) ?? current : response.planets[0] ?? null);
  }, []);

  useWarStream({ onPlanets: applyPlanets, onError: (err) => setError(err.message) });

  useEffect(() => {
    const refresh = async (): Promise<void> => {
      try {
        const [planetResponse, orderResponse, dispatchResponse, warResponse] = await Promise.all([
          api.planets(),
          api.orders(),
          api.dispatches(),
          api.war()
        ]);
        applyPlanets(planetResponse);
        setOrders(orderResponse.orders);
        setDispatches(dispatchResponse.dispatches.slice().reverse());
        setWar(warResponse);
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
        <p className="text-sm text-slate-400">Browser traffic terminates at WarDesk. Upstream APIs are polled only by the backend worker.</p>
      </header>
      {error ? <div className="rounded border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-100">{error}</div> : null}
      <WarStats war={war} planetCount={planets.length} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <GalaxyMap planets={planets} selected={selected} onSelect={setSelected} />
        <div className="space-y-6">
          <PlanetPanel planet={selected} />
          <OrderTracker orders={orders} />
        </div>
      </div>
      <DispatchFeed dispatches={dispatches} />
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
