import { OptimizeRequest, OptimizeResponse, SimulateRequest, SimulateResponse } from './types';

function serviceUrl(path: string): string {
  const base = process.env.OPTIMIZER_SERVICE_URL ?? 'http://localhost:8000';
  return `${base.replace(/\/$/, '')}${path}`;
}

export async function runOptimizer(request: OptimizeRequest): Promise<OptimizeResponse> {
  const res = await fetch(serviceUrl('/optimize'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    cache: 'no-store',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Optimizer service error (${res.status}): ${text}`);
  }
  return res.json();
}

export async function runSimulation(request: SimulateRequest): Promise<SimulateResponse> {
  const res = await fetch(serviceUrl('/simulate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    cache: 'no-store',
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Simulation service error (${res.status}): ${text}`);
  }
  return res.json();
}

export async function checkOptimizerHealth(): Promise<boolean> {
  try {
    const res = await fetch(serviceUrl('/health'), { cache: 'no-store' });
    return res.ok;
  } catch {
    return false;
  }
}
