const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function optimize(payload) {
  const res = await fetch(`${API_BASE}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Optimize failed (${res.status})`);
  }
  return res.json();
}

export async function listRuns() {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) throw new Error(`Listing runs failed (${res.status})`);
  return res.json();
}

export async function getRun(runId) {
  const res = await fetch(`${API_BASE}/lineups/${runId}`);
  if (!res.ok) throw new Error(`Loading run failed (${res.status})`);
  return res.json();
}

export function exportCsvUrl(runId) {
  return `${API_BASE}/export/csv/${runId}`;
}

export async function downloadCsv(runId, filename) {
  const res = await fetch(exportCsvUrl(runId));
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `dk_upload_run_${runId}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
