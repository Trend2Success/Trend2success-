export default function ResultsTable({ lineups, selectedRank, onSelect }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="bg-slate-900 text-left text-slate-400">
          <tr>
            <th className="px-3 py-2">#</th>
            <th className="px-3 py-2">EV</th>
            <th className="px-3 py-2">ITM%</th>
            <th className="px-3 py-2">Proj</th>
            <th className="px-3 py-2">Salary</th>
            <th className="px-3 py-2">Own Sum</th>
            <th className="px-3 py-2">Ceiling</th>
            <th className="px-3 py-2">Floor</th>
            <th className="px-3 py-2">Leverage</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {lineups.map((lu) => (
            <tr
              key={lu.rank}
              onClick={() => onSelect(lu.rank)}
              className={`cursor-pointer transition hover:bg-slate-800/60 ${
                selectedRank === lu.rank ? "bg-slate-800" : "bg-slate-950"
              }`}
            >
              <td className="px-3 py-2 font-medium text-slate-300">{lu.rank}</td>
              <td className="px-3 py-2 font-semibold text-emerald-400">
                ${lu.ev.toFixed(2)}
              </td>
              <td className="px-3 py-2">{(lu.itm_pct * 100).toFixed(1)}%</td>
              <td className="px-3 py-2">{lu.projected_points.toFixed(1)}</td>
              <td className="px-3 py-2">${lu.salary.toLocaleString()}</td>
              <td className="px-3 py-2">{lu.ownership_sum.toFixed(0)}%</td>
              <td className="px-3 py-2">{lu.ceiling.toFixed(1)}</td>
              <td className="px-3 py-2">{lu.floor.toFixed(1)}</td>
              <td className="px-3 py-2">{lu.avg_leverage.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
