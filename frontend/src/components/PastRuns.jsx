export default function PastRuns({ runs, activeRunId, onSelect }) {
  if (runs.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-300">Past Runs</h2>
      <ul className="divide-y divide-slate-800 text-sm">
        {runs.map((run) => (
          <li key={run.run_id}>
            <button
              onClick={() => onSelect(run.run_id)}
              className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left transition hover:bg-slate-800/60 ${
                run.run_id === activeRunId ? "bg-slate-800" : ""
              }`}
            >
              <span className="text-slate-200">
                #{run.run_id} · {run.sport.toUpperCase()} · {run.contest_type}
              </span>
              <span className="text-slate-500">
                {run.num_lineups} lineups · {new Date(run.created_at).toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
