import { useEffect, useState } from "react";
import OptimizeForm from "./components/OptimizeForm.jsx";
import ResultsTable from "./components/ResultsTable.jsx";
import LineupCard from "./components/LineupCard.jsx";
import PastRuns from "./components/PastRuns.jsx";
import { optimize, downloadCsv, listRuns, getRun } from "./api.js";

export default function App() {
  const [response, setResponse] = useState(null);
  const [selectedRank, setSelectedRank] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState([]);

  async function refreshRuns() {
    try {
      setRuns(await listRuns());
    } catch {
      // past-runs list is a convenience; a failed fetch shouldn't block the page
    }
  }

  useEffect(() => {
    refreshRuns();
  }, []);

  async function handleGenerate(payload) {
    setLoading(true);
    setError(null);
    try {
      const result = await optimize(payload);
      setResponse(result);
      setSelectedRank(result.lineups[0]?.rank ?? null);
      refreshRuns();
    } catch (err) {
      setError(err.message);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectRun(runId) {
    setError(null);
    try {
      const result = await getRun(runId);
      setResponse(result);
      setSelectedRank(result.lineups[0]?.rank ?? null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleExport() {
    if (!response) return;
    try {
      await downloadCsv(response.run_id);
    } catch (err) {
      setError(err.message);
    }
  }

  const selectedLineup = response?.lineups.find((lu) => lu.rank === selectedRank);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">DK EV Optimizer</h1>
        <p className="text-sm text-slate-400">
          True Expected Value lineup generation for DraftKings Cash &amp; GPP contests.
        </p>
      </header>

      <OptimizeForm onSubmit={handleGenerate} loading={loading} />

      <div className="mt-6">
        <PastRuns runs={runs} activeRunId={response?.run_id} onSelect={handleSelectRun} />
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-red-700 bg-red-950 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {response && (
        <div className="mt-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-200">
              {response.lineups.length} lineup(s) — run #{response.run_id}
            </h2>
            <button
              onClick={handleExport}
              className="rounded-md bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400"
            >
              Export to DraftKings CSV
            </button>
          </div>

          <ResultsTable
            lineups={response.lineups}
            selectedRank={selectedRank}
            onSelect={setSelectedRank}
          />

          {selectedLineup && (
            <div className="max-w-md">
              <LineupCard lineup={selectedLineup} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
