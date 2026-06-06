import { useEffect, useRef } from 'react';
import type { PlanetsResponse } from '../api/types';

interface UseWarStreamOptions {
  onPlanets: (response: PlanetsResponse) => void;
  onError?: (error: Error) => void;
}

export function useWarStream({ onPlanets, onError }: UseWarStreamOptions): void {
  const onPlanetsRef = useRef(onPlanets);
  const onErrorRef = useRef(onError);

  onPlanetsRef.current = onPlanets;
  onErrorRef.current = onError;

  useEffect(() => {
    let polling: number | undefined;
    const poll = async (): Promise<void> => {
      try {
        const response = await fetch('/api/v1/planets');
        onPlanetsRef.current((await response.json()) as PlanetsResponse);
      } catch (error) {
        onErrorRef.current?.(error instanceof Error ? error : new Error('polling failed'));
      }
    };

    const events = new EventSource('/sse');
    events.addEventListener('planets', (event) => {
      onPlanetsRef.current(JSON.parse((event as MessageEvent<string>).data) as PlanetsResponse);
    });
    events.onerror = () => {
      events.close();
      void poll();
      polling = window.setInterval(() => void poll(), 30_000);
    };

    return () => {
      events.close();
      if (polling !== undefined) {
        window.clearInterval(polling);
      }
    };
    // The EventSource is created once per mount; refs keep callbacks current so planet state updates do not reconnect SSE.
  }, []);
}
