import Link from 'next/link';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { EmptyState, Callout } from '@/components/ui/callout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DeleteLineupButton, DeleteRunButton } from './delete-buttons';

export default async function PortfolioPage({ searchParams }: { searchParams: { runId?: string } }) {
  const user = await requireUser();
  const slate = await getActiveSlate();
  if (!slate) return <EmptyState title="No active slate" description="Create a slate first." />;

  const runs = await prisma.lineupRun.findMany({
    where: { slateId: slate.id },
    orderBy: { createdAt: 'desc' },
  });
  const activeRun = searchParams.runId
    ? runs.find((r) => r.id === searchParams.runId) ?? runs[0]
    : runs[0];

  if (!activeRun) {
    return <EmptyState title="No lineups yet" description="Generate lineups on the Lineup Builder page first." />;
  }

  const lineups = await prisma.lineup.findMany({
    where: { runId: activeRun.id },
    include: { players: { include: { player: true } } },
    orderBy: { modelScore: 'desc' },
  });

  const totalLineups = lineups.length;

  // Player exposure
  const playerCounts = new Map<string, { name: string; team: string; count: number }>();
  const teamCounts = new Map<string, number>();
  const gameCounts = new Map<string, number>();
  const stackCounts = new Map<string, number>();
  const pairCounts = new Map<string, { names: [string, string]; count: number }>();
  const lineupKeySets = new Map<string, string[]>();

  for (const lineup of lineups) {
    const playerIds = lineup.players.map((lp) => lp.playerId).sort();
    lineupKeySets.set(lineup.id, playerIds);

    const teamsInLineup = new Set<string>();
    const gamesInLineup = new Set<string>();

    for (const lp of lineup.players) {
      const entry = playerCounts.get(lp.playerId) ?? { name: lp.player.playerName, team: lp.player.team, count: 0 };
      entry.count += 1;
      playerCounts.set(lp.playerId, entry);
      teamsInLineup.add(lp.player.team);
      gamesInLineup.add(lp.player.gameId);
    }
    for (const t of teamsInLineup) teamCounts.set(t, (teamCounts.get(t) ?? 0) + 1);
    for (const g of gamesInLineup) gameCounts.set(g, (gameCounts.get(g) ?? 0) + 1);

    stackCounts.set(lineup.stackSummary, (stackCounts.get(lineup.stackSummary) ?? 0) + 1);

    const names = lineup.players.map((lp) => ({ id: lp.playerId, name: lp.player.playerName }));
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const key = [names[i]!.id, names[j]!.id].sort().join('|');
        const entry = pairCounts.get(key) ?? { names: [names[i]!.name, names[j]!.name], count: 0 };
        entry.count += 1;
        pairCounts.set(key, entry);
      }
    }
  }

  // Duplicate lineup detection (identical player sets)
  const seenSets = new Map<string, string[]>();
  for (const [lineupId, ids] of lineupKeySets.entries()) {
    const key = ids.join(',');
    seenSets.set(key, [...(seenSets.get(key) ?? []), lineupId]);
  }
  const duplicateGroups = [...seenSets.values()].filter((ids) => ids.length > 1);

  const exposureWarnings: string[] = [];
  for (const [, e] of playerCounts) {
    const pct = (e.count / totalLineups) * 100;
    if (pct >= 50 && totalLineups >= 4) exposureWarnings.push(`You have ${pct.toFixed(0)}% exposure to ${e.name} across ${totalLineups} lineups.`);
  }
  for (const [gameId, count] of gameCounts) {
    const pct = (count / totalLineups) * 100;
    if (pct >= 60 && totalLineups >= 4) exposureWarnings.push(`Your lineup pool has ${pct.toFixed(0)}% exposure to one game (${gameId}).`);
  }
  for (const [signature, count] of stackCounts) {
    const pct = (count / totalLineups) * 100;
    if (pct >= 60 && totalLineups >= 4) exposureWarnings.push(`${count} lineups (${pct.toFixed(0)}%) share nearly identical construction: "${signature}".`);
  }
  if (duplicateGroups.length > 0) {
    exposureWarnings.push(`${duplicateGroups.length} set(s) of fully duplicate lineups detected — consider deleting and regenerating.`);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Portfolio Review</h1>
          <p className="text-sm text-ink-400">
            {slate.slateName} · Run: {activeRun.presetName} · {new Date(activeRun.createdAt).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="secondary" size="sm">
            <a href={`/api/export/lineups?runId=${activeRun.id}&field=name`}>Export CSV (names)</a>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <a href={`/api/export/lineups?runId=${activeRun.id}&field=id`}>Export CSV (ids)</a>
          </Button>
          <DeleteRunButton runId={activeRun.id} />
        </div>
      </div>

      {runs.length > 1 ? (
        <div className="flex flex-wrap gap-2">
          {runs.map((r) => (
            <Button key={r.id} asChild size="sm" variant={r.id === activeRun.id ? 'default' : 'outline'}>
              <Link href={`/portfolio?runId=${r.id}`}>
                {r.presetName} ({new Date(r.createdAt).toLocaleDateString()})
              </Link>
            </Button>
          ))}
        </div>
      ) : null}

      {exposureWarnings.length > 0 ? (
        <div className="flex flex-col gap-2">
          {exposureWarnings.map((w, i) => (
            <Callout key={i} variant="warning">
              {w}
            </Callout>
          ))}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Lineups ({totalLineups})</CardTitle>
          <CardDescription>Model-ranked lineups — estimates, not guaranteed winners.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Salary</TableHead>
                <TableHead>Projection</TableHead>
                <TableHead>Ceiling</TableHead>
                <TableHead>Ownership</TableHead>
                <TableHead>Leverage</TableHead>
                <TableHead>Model score</TableHead>
                <TableHead>Stack</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {lineups.map((l, i) => (
                <TableRow key={l.id}>
                  <TableCell>{i + 1}</TableCell>
                  <TableCell>${l.salaryUsed.toLocaleString()}</TableCell>
                  <TableCell>{l.totalProjection.toFixed(1)}</TableCell>
                  <TableCell>{l.totalCeiling.toFixed(1)}</TableCell>
                  <TableCell>{l.totalOwnership.toFixed(1)}%</TableCell>
                  <TableCell>{l.leverageScore.toFixed(2)}</TableCell>
                  <TableCell>{l.modelScore.toFixed(1)}</TableCell>
                  <TableCell className="max-w-xs whitespace-normal text-xs text-ink-300">{l.stackSummary}</TableCell>
                  <TableCell>
                    <DeleteLineupButton lineupId={l.id} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Player exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <ExposureList
              items={[...playerCounts.values()]
                .sort((a, b) => b.count - a.count)
                .map((e) => ({ label: `${e.name} (${e.team})`, pct: (e.count / totalLineups) * 100 }))}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Team & game exposure</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <p className="mb-1 text-xs font-medium text-ink-400">Team (share of lineups using ≥1 player)</p>
              <ExposureList items={[...teamCounts.entries()].sort((a, b) => b[1] - a[1]).map(([t, c]) => ({ label: t, pct: (c / totalLineups) * 100 }))} />
            </div>
            <div>
              <p className="mb-1 text-xs font-medium text-ink-400">Game (share of lineups using ≥1 player)</p>
              <ExposureList items={[...gameCounts.entries()].sort((a, b) => b[1] - a[1]).map(([g, c]) => ({ label: g, pct: (c / totalLineups) * 100 }))} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Stack-type exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <ExposureList items={[...stackCounts.entries()].sort((a, b) => b[1] - a[1]).map(([s, c]) => ({ label: s, pct: (c / totalLineups) * 100 }))} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top pairwise player exposure</CardTitle>
            <CardDescription>Player pairs appearing together most often.</CardDescription>
          </CardHeader>
          <CardContent>
            <ExposureList
              items={[...pairCounts.values()]
                .sort((a, b) => b.count - a.count)
                .slice(0, 10)
                .map((p) => ({ label: `${p.names[0]} + ${p.names[1]}`, pct: (p.count / totalLineups) * 100 }))}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ExposureList({ items }: { items: { label: string; pct: number }[] }) {
  if (items.length === 0) return <p className="text-xs text-ink-400">No data.</p>;
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2 text-xs">
          <span className="w-40 shrink-0 truncate text-ink-200">{item.label}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-graphite-800">
            <div
              className={item.pct >= 50 ? 'h-full bg-amber-500' : 'h-full bg-teal-500'}
              style={{ width: `${Math.min(100, item.pct)}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right text-ink-400">{item.pct.toFixed(0)}%</span>
        </li>
      ))}
    </ul>
  );
}
