import Link from 'next/link';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Callout, EmptyState } from '@/components/ui/callout';
import { formatCents, formatPct } from '@/lib/utils';

export default async function DashboardPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();

  if (!slate) {
    return (
      <div className="mx-auto max-w-2xl">
        <EmptyState
          title="No slates yet"
          description="Start by creating a slate and importing your salary CSV. The onboarding wizard walks through every step."
          action={
            <Button asChild>
              <Link href="/onboarding">Start onboarding</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const [players, lastImport, runs, results, allSlatesCount, settings] = await Promise.all([
    prisma.player.findMany({ where: { slateId: slate.id }, include: { projection: true } }),
    prisma.importBatch.findFirst({ where: { slateId: slate.id }, orderBy: { createdAt: 'desc' } }),
    prisma.lineupRun.findMany({ where: { slateId: slate.id }, include: { lineups: { include: { players: { include: { player: true } } } } } }),
    prisma.contestResult.findMany({ where: { slate: { userId: user.id } } }),
    prisma.slate.count({ where: { userId: user.id, results: { some: {} } } }),
    prisma.settings.findUnique({ where: { userId: user.id } }),
  ]);

  const excludedCount = players.filter((p) => p.excluded).length;
  const withOwnership = players.filter((p) => p.projection?.projectedOwnership != null);
  const avgOwnership =
    withOwnership.length > 0
      ? withOwnership.reduce((sum, p) => sum + (p.projection?.projectedOwnership ?? 0), 0) / withOwnership.length
      : null;

  const gameMap = new Map<string, { gameInfo: string; total: number; players: number }>();
  for (const p of players) {
    if (!p.projection) continue;
    const entry = gameMap.get(p.gameId) ?? { gameInfo: p.gameInfo || p.gameId, total: 0, players: 0 };
    entry.total += p.projection.finalPoints;
    entry.players += 1;
    gameMap.set(p.gameId, entry);
  }
  const topGames = [...gameMap.entries()]
    .map(([gameId, v]) => ({ gameId, ...v }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 5);

  const allLineups = runs.flatMap((r) => r.lineups);
  const totalLineups = allLineups.length;

  const exposureCounts = new Map<string, { name: string; count: number }>();
  for (const lineup of allLineups) {
    for (const lp of lineup.players) {
      const entry = exposureCounts.get(lp.playerId) ?? { name: lp.player.playerName, count: 0 };
      entry.count += 1;
      exposureCounts.set(lp.playerId, entry);
    }
  }
  const exposureWarnings = [...exposureCounts.values()]
    .map((e) => ({ ...e, pct: totalLineups > 0 ? (e.count / totalLineups) * 100 : 0 }))
    .filter((e) => e.pct >= 50 && totalLineups >= 4)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 5);

  const totalEntries = results.reduce((s, r) => s + r.numberOfEntries, 0);
  const totalFees = results.reduce((s, r) => s + r.totalEntryFeesCents, 0);
  const totalWinnings = results.reduce((s, r) => s + r.totalWinningsCents, 0);
  const netPnl = results.reduce((s, r) => s + r.netProfitLossCents, 0);
  const roi = totalFees > 0 ? (netPnl / totalFees) * 100 : null;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-ink-400">
          {slate.slateName} · {slate.sport} · {new Date(slate.contestDate).toLocaleString()}
          {slate.isDemo ? (
            <Badge variant="amber" className="ml-2">
              Demo Data — Not Real Players or Projections
            </Badge>
          ) : null}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Player pool" value={String(players.length)} sub={`${excludedCount} excluded`} />
        <StatCard
          label="Avg projected ownership"
          value={avgOwnership !== null ? formatPct(avgOwnership) : '—'}
          sub="Across players with ownership data"
        />
        <StatCard label="Lineups generated" value={String(totalLineups)} sub={`${runs.length} optimizer runs`} />
        <StatCard
          label="Last data update"
          value={lastImport ? new Date(lastImport.createdAt).toLocaleString() : 'Never'}
          sub={lastImport ? `${lastImport.kind} import` : 'No imports yet'}
        />
      </div>

      <Callout variant="info" title="Session budget reminder">
        Budget: {formatCents(settings?.sessionBudgetCents ?? 10000)} · Stop-loss:{' '}
        {formatCents(settings?.stopLossCents ?? 5000)}. Adjust these in Settings & Responsible Play.
      </Callout>

      {allSlatesCount < 10 ? (
        <Callout variant="warning" title="Small sample">
          You have tracked results for {allSlatesCount} slate{allSlatesCount === 1 ? '' : 's'}. Do not treat results as
          proof of a strategy until you have a larger sample.
        </Callout>
      ) : null}

      {exposureWarnings.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Exposure warnings</CardTitle>
            <CardDescription>Based on all lineups generated for this slate.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {exposureWarnings.map((w) => (
              <Callout key={w.name} variant="warning">
                You have {formatPct(w.pct)} exposure to {w.name} across {totalLineups} lineups.
              </Callout>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top projected game environments</CardTitle>
            <CardDescription>Sum of final projections for all rostered-eligible players in the game, from your imported data only.</CardDescription>
          </CardHeader>
          <CardContent>
            {topGames.length === 0 ? (
              <p className="text-xs text-ink-400">Import projections to see game environments.</p>
            ) : (
              <ul className="flex flex-col gap-2 text-sm">
                {topGames.map((g) => (
                  <li key={g.gameId} className="flex items-center justify-between">
                    <span>{g.gameInfo}</span>
                    <span className="text-ink-400">{g.total.toFixed(1)} pts · {g.players} players</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent results summary</CardTitle>
            <CardDescription>All tracked contests across every slate.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <Metric label="Entries" value={String(totalEntries)} />
            <Metric label="Total fees" value={formatCents(totalFees)} />
            <Metric label="Total winnings" value={formatCents(totalWinnings)} />
            <Metric label="Net P/L" value={formatCents(netPnl)} highlight={netPnl >= 0 ? 'positive' : 'negative'} />
            <Metric label="ROI" value={roi !== null ? formatPct(roi) : '—'} />
            <Metric label="Sample size" value={`${results.length} contests`} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-ink-400">{label}</p>
        <p className="mt-1 text-lg font-semibold text-ink-50">{value}</p>
        {sub ? <p className="text-[11px] text-ink-600">{sub}</p> : null}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: 'positive' | 'negative' }) {
  return (
    <div>
      <p className="text-[11px] text-ink-400">{label}</p>
      <p
        className={
          highlight === 'positive'
            ? 'font-semibold text-teal-300'
            : highlight === 'negative'
              ? 'font-semibold text-rose-400'
              : 'font-semibold text-ink-50'
        }
      >
        {value}
      </p>
    </div>
  );
}
