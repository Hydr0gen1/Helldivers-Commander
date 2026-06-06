import type { Order, Task } from '../api/types';

const TARGET_VALUE_TYPE_IDS = new Set([3]);

function countdown(expiration: string): string {
  const ms = new Date(expiration).getTime() - Date.now();
  if (ms <= 0) return 'expired';
  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.floor((ms % 3_600_000) / 60_000);
  return `${hours}h ${minutes}m`;
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function targetForTask(task: Task): number | null {
  const targetIndex = task.valueTypes.findIndex((valueType) => TARGET_VALUE_TYPE_IDS.has(valueType));
  if (targetIndex >= 0) {
    const target = task.values[targetIndex];
    return Number.isFinite(target) && target > 0 ? target : null;
  }

  const explicitPercentTarget = task.values.find((value) => value === 100);
  return explicitPercentTarget ?? null;
}

function taskPercent(progress: number, task: Task): number {
  const target = targetForTask(task);
  if (target !== null) {
    return clampPercent((progress / target) * 100);
  }

  return clampPercent(progress);
}

function progressLabel(progress: number, task: Task): string {
  const target = targetForTask(task);
  if (target === null || target === 100) {
    return `${taskPercent(progress, task).toFixed(0)}%`;
  }
  return `${progress.toLocaleString()} / ${target.toLocaleString()}`;
}

interface OrderTrackerProps {
  orders: Order[];
}

export function OrderTracker({ orders }: OrderTrackerProps): JSX.Element {
  return (
    <section className="rounded-2xl border border-yellow-400/30 bg-black/50 p-4 shadow-lg shadow-yellow-950/20">
      <h2 className="mb-3 text-lg font-bold uppercase tracking-[0.3em] text-yellow-300">Major Orders</h2>
      {orders.length === 0 ? <p className="text-sm text-slate-400">No order data cached yet.</p> : null}
      <div className="space-y-4">
        {orders.map((order) => (
          <article key={order.id} className="rounded-lg border border-yellow-500/20 bg-yellow-950/10 p-3">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold text-yellow-100">{order.title || `Order ${order.id}`}</h3>
              <span className="shrink-0 rounded bg-yellow-400/10 px-2 py-1 text-xs text-yellow-200">{countdown(order.expiration)}</span>
            </div>
            <p className="mt-2 line-clamp-4 text-sm text-slate-300">{order.description || order.briefing}</p>
            <div className="mt-3 space-y-2">
              {order.tasks.map((task, index) => {
                // Major Order task structures vary by order; valueTypes identifies which value is the target/goal.
                const progress = order.progress[index] ?? 0;
                const percent = taskPercent(progress, task);
                return (
                  <div key={`${order.id}-${index}`}>
                    <div className="mb-1 flex justify-between text-xs text-slate-400">
                      <span>Task {index + 1}</span>
                      <span>{progressLabel(progress, task)}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                      <div className="h-full rounded-full bg-yellow-300" style={{ width: `${percent}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
