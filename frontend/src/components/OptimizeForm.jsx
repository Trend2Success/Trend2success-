import { useState } from "react";

const SPORTS = ["nfl", "nba", "mlb", "cfb"];
const CONTESTS = [
  { value: "cash", label: "Cash (50/50)" },
  { value: "gpp", label: "GPP (tournament)" },
  { value: "balanced", label: "Balanced" },
];

export default function OptimizeForm({ onSubmit, loading }) {
  const [sport, setSport] = useState("nfl");
  const [contestType, setContestType] = useState("gpp");
  const [numLineups, setNumLineups] = useState(20);
  const [alpha, setAlpha] = useState(0.5);
  const [stackMinSize, setStackMinSize] = useState(0);
  const [maxOverlap, setMaxOverlap] = useState(5);

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      sport,
      contest_type: contestType,
      num_lineups: Number(numLineups),
      alpha: Number(alpha),
      stack_min_size: Number(stackMinSize),
      max_overlap: Number(maxOverlap),
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid grid-cols-2 gap-4 rounded-xl border border-slate-800 bg-slate-900 p-5 md:grid-cols-3 lg:grid-cols-6"
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-400">Sport</span>
        <select
          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
          value={sport}
          onChange={(e) => setSport(e.target.value)}
        >
          {SPORTS.map((s) => (
            <option key={s} value={s}>
              {s.toUpperCase()}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-400">Contest</span>
        <select
          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
          value={contestType}
          onChange={(e) => setContestType(e.target.value)}
        >
          {CONTESTS.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </label>

      {contestType === "balanced" && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-400">Alpha (0=cash, 1=GPP)</span>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
            value={alpha}
            onChange={(e) => setAlpha(e.target.value)}
          />
        </label>
      )}

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-400"># Lineups</span>
        <input
          type="number"
          min="1"
          max="150"
          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
          value={numLineups}
          onChange={(e) => setNumLineups(e.target.value)}
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-400">Max overlap</span>
        <input
          type="number"
          min="0"
          max="9"
          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
          value={maxOverlap}
          onChange={(e) => setMaxOverlap(e.target.value)}
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-slate-400">QB stack size</span>
        <input
          type="number"
          min="0"
          max="3"
          className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5"
          value={stackMinSize}
          onChange={(e) => setStackMinSize(e.target.value)}
        />
      </label>

      <div className="col-span-2 flex items-end md:col-span-3 lg:col-span-6">
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-emerald-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Lineups"}
        </button>
      </div>
    </form>
  );
}
