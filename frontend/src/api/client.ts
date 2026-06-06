import type { DispatchesResponse, HealthResponse, OrdersResponse, Planet, PlanetsResponse, War } from './types';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`WarDesk API ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  war: () => getJson<War>('/api/v1/war'),
  planets: () => getJson<PlanetsResponse>('/api/v1/planets'),
  planet: (index: number) => getJson<Planet>(`/api/v1/planets/${index}`),
  orders: () => getJson<OrdersResponse>('/api/v1/orders/current'),
  dispatches: () => getJson<DispatchesResponse>('/api/v1/dispatches'),
  health: () => getJson<HealthResponse>('/healthz')
};
