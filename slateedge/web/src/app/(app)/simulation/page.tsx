import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { EmptyState, Callout } from '@/components/ui/callout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { RunSimulationForm } from './run-form';
import { PlayerSimChart, LineupSimChart } from './simulation-charts';
import type { SimulateResponse } from '@/lib/optimizer/types';

export default async function SimulationPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();
  if (!slate) return <EmptyState title="No active slate" description="Create a slate first." />;

  const [players, lineupRuns, latestSim] = await Promise.all([
    prisma.player.findMany({ where: { slateId: slate.id } }),
    prisma.lineupRun.findMany({ where: { slateId: slate.id }, orderBy: { createdAt: 'desc' }, take: 10 }),
    prisma.simulationRun.findFirst({ where: { slateId: slate.id }, orderBy: { createdAt: 'desc' } }),
  ]);

  const names = Object.fromEntries(players.map((p) => [p.playerId, p.playerName]));
  const results = latestSim?.resultsJson as unknown as SimulateResponse | undefined;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Simulation Lab</h1>
        <p className="text-sm text-ink-400">{slate.slateName} — Monte Carlo estimates from your inputs, not predictions of real outcomes.</p>
      </div>

      <Callout variant="warning" title="Estimates only">
        These figures never imply expected profit, ROI, or a probability of winning a tournament. Correlation
        assumptions are simple, editable rules — not a model of real football outcomes.
      </Callout>

      <Card>
        <CardHeader>
          <CardTitle>Run a simulation</CardTitle>
          <CardDescription>Samples player outcomes from your imported mean/standard deviation using the chosen distribution.</CardDescription>
        </CardHeader>
        <CardContent>
          <RunSimulationForm
            slateId={slate.id}
            runs={lineupRuns.map((r) => ({ id: r.id, label: `${r.presetName} — ${new Date(r.createdAt).toLocaleString()}` }))}
          />
        </CardContent>
      </Card>

      {!latestSim || !results ? (
        <EmptyState title="No simulations run yet for this slate" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Latest run</CardTitle>
              <CardDescription>
                {latestSim.numSimulations.toLocaleString()} simulations · {latestSim.distribution} · seed{' '}
                {latestSim.seedUsed ?? 'random'} · {new Date(latestSim.createdAt).toLocaleString()}
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Player outcome distributions</CardTitle>
              <CardDescription>Top 15 players by mean simulated points. Median vs. 90th percentile shown.</CardDescription>
            </CardHeader>
            <CardContent>
              <PlayerSimChart stats={results.player_stats} names={names} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Player outcome table</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Player</TableHead>
                    <TableHead>Mean</TableHead>
                    <TableHead>Median</TableHead>
                    <TableHead>P75</TableHead>
                    <TableHead>P90</TableHead>
                    <TableHead>P(exceed threshold)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.player_stats.map((s) => (
                    <TableRow key={s.player_id}>
                      <TableCell>{names[s.player_id] ?? s.player_id}</TableCell>
                      <TableCell>{s.mean.toFixed(1)}</TableCell>
                      <TableCell>{s.median.toFixed(1)}</TableCell>
                      <TableCell>{s.p75.toFixed(1)}</TableCell>
                      <TableCell>{s.p90.toFixed(1)}</TableCell>
                      <TableCell>{s.prob_exceeds_threshold !== null ? `${(s.prob_exceeds_threshold * 100).toFixed(1)}%` : '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {results.lineup_stats.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Lineup outcome distributions & duplication-risk proxy</CardTitle>
                <CardDescription>
                  Duplication risk is a heuristic proxy combining ownership and portfolio overlap — not a real field
                  model.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <LineupSimChart stats={results.lineup_stats} />
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
