import type { Dispatch } from '../api/types';

interface DispatchFeedProps {
  dispatches: Dispatch[];
}

export function DispatchFeed({ dispatches }: DispatchFeedProps): JSX.Element {
  return (
    <section className="rounded-2xl border border-terminal/30 bg-black/60 p-4 font-mono">
      <h2 className="mb-3 text-lg font-bold uppercase tracking-[0.3em] text-terminal">Dispatch Feed</h2>
      <div className="max-h-56 space-y-3 overflow-auto pr-2">
        {dispatches.length === 0 ? <p className="text-sm text-slate-500">Awaiting transmissions.</p> : null}
        {dispatches.map((dispatch) => (
          <article key={dispatch.id} className="border-l border-terminal/40 pl-3 text-sm text-green-100/90">
            <time className="text-xs text-terminal/60">{new Date(dispatch.published).toLocaleString()}</time>
            <p>{dispatch.message ?? '[redacted transmission]'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
