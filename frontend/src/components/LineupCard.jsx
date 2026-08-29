export default function LineupCard({ lineup }) {
  const salaryPct = Math.min(100, (lineup.salary / 50000) * 100);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-300">
          Lineup #{lineup.rank}
        </span>
        <span className="text-sm font-bold text-emerald-400">
          EV ${lineup.ev.toFixed(2)}
        </span>
      </div>

      <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full bg-sky-500"
          style={{ width: `${salaryPct}%` }}
          title={`$${lineup.salary.toLocaleString()} / $50,000`}
        />
      </div>

      <ul className="mb-3 divide-y divide-slate-800 text-sm">
        {lineup.roster.map((p) => (
          <li key={`${lineup.rank}-${p.slot}-${p.player_id}`} className="flex justify-between py-1">
            <span className="text-slate-400">{p.slot}</span>
            <span className="text-slate-100">{p.name}</span>
            <span className="text-slate-500">${p.salary.toLocaleString()}</span>
          </li>
        ))}
      </ul>

      <div className="grid grid-cols-3 gap-2 text-center text-xs text-slate-400">
        <div>
          <div className="text-slate-200">{lineup.projected_points.toFixed(1)}</div>
          Proj
        </div>
        <div>
          <div className="text-slate-200">{(lineup.itm_pct * 100).toFixed(1)}%</div>
          ITM
        </div>
        <div>
          <div className="text-slate-200">{lineup.ownership_sum.toFixed(0)}%</div>
          Own Sum
        </div>
        <div>
          <div className="text-slate-200">{lineup.ceiling.toFixed(1)}</div>
          Ceiling
        </div>
        <div>
          <div className="text-slate-200">{lineup.floor.toFixed(1)}</div>
          Floor
        </div>
        <div>
          <div className="text-slate-200">{(lineup.top10_pct_rate * 100).toFixed(1)}%</div>
          Top 10%
        </div>
      </div>
    </div>
  );
}
