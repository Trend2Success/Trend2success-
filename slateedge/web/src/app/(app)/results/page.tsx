import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout, EmptyState } from '@/components/ui/callout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CsvUploadCard } from '@/components/csv-upload-card';
import { previewResultsCsvAction, commitResultsCsvAction } from '@/server/actions/imports';
import { formatCents, formatPct } from '@/lib/utils';
import { BankrollTrendChart, RoiByContestTypeChart, EntriesVsResultsChart } from './charts';
import { LinkLineupSelect } from './link-lineup-select';
import { DeleteResultButton } from './delete-result-button';

function buyInTier(cents: number): string {
  const dollars = cents / 100;
  if (dollars <= 1) return '$0-1';
  if (dollars <= 5) return '$1-5';
  if (dollars <= 20) return '$5-20';
  if (dollars <= 100) return '$20-100';
  return '$100+';
}

function entrySizeTier(field: number | null): string {
  if (field === null) return 'Unknown';
  if (field <= 2) return 'Head-to-head / small';
  if (field <= 100) return 'Small field';
  if (field <= 5000) return 'Mid field';
  return 'Large field (5,000+)';
}

function lineupCountTier(n: number): string {
  if (n <= 1) return '1 lineup';
  if (n <= 5) return '2-5 lineups';
  if (n <= 20) return '6-20 lineups';
  return '21+ lineups';
}

function salaryRemainingTier(salaryUsed: number, cap = 50000): string {
  const remaining = cap - salaryUsed;
  if (remaining <= 200) return '$0-200 remaining';
  if (remaining <= 1000) return '$200-1,000 remaining';
  return '$1,000+ remaining';
}

function ownershipRangeTier(totalOwnership: number): string {
  if (totalOwnership <= 60) return 'Low (≤60%)';
  if (totalOwnership <= 100) return 'Medium (60-100%)';
  return 'High (100%+)';
}

export default async function ResultsPage() {
  const user = await requireUser();
  const results = await prisma.contestResult.findMany({
    where: { slate: { userId: user.id } },
    include: { slate: true, linkedLineup: true },
    orderBy: { createdAt: 'asc' },
  });

  const slateIds = [...new Set(results.map((r) => r.slateId))];
  const lineupsBySlate = new Map<string, { id: string; label: string }[]>();
  if (slateIds.length > 0) {
    const lineups = await prisma.lineup.findMany({
      where: { run: { slateId: { in: slateIds }, userId: user.id } },
      include: { run: true },
      orderBy: { createdAt: 'desc' },
    });
    for (const l of lineups) {
      const list = lineupsBySlate.get(l.run.slateId) ?? [];
      list.push({ id: l.id, label: `${l.run.presetName} · $${l.salaryUsed.toLocaleString()} · ${new Date(l.createdAt).toLocaleDateString()}` });
      lineupsBySlate.set(l.run.slateId, list);
    }
  }

  const totalEntries = results.reduce((s, r) => s + r.numberOfEntries, 0);
  const totalFees = results.reduce((s, r) => s + r.totalEntryFeesCents, 0);
  const totalWinnings = results.reduce((s, r) => s + r.totalWinningsCents, 0);
  const netPnl = results.reduce((s, r) => s + r.netProfitLossCents, 0);
  const roi = totalFees > 0 ? (netPnl / totalFees) * 100 : null;
  const distinctSlates = new Set(results.map((r) => r.slateId)).size;
  const linkedResults = results.filter((r) => r.linkedLineup);

  function breakdown<T, K extends string>(source: T[], keyFn: (r: T) => K, metricsFn: (r: T) => { fees: number; winnings: number; net: number; entries: number }) {
    const map = new Map<K, { fees: number; winnings: number; net: number; entries: number; count: number }>();
    for (const r of source) {
      const key = keyFn(r);
      const m = metricsFn(r);
      const entry = map.get(key) ?? { fees: 0, winnings: 0, net: 0, entries: 0, count: 0 };
      entry.fees += m.fees;
      entry.winnings += m.winnings;
      entry.net += m.net;
      entry.entries += m.entries;
      entry.count += 1;
      map.set(key, entry);
    }
    return [...map.entries()].map(([key, v]) => ({ key, ...v, roi: v.fees > 0 ? (v.net / v.fees) * 100 : null }));
  }

  const metrics = (r: (typeof results)[number]) => ({
    fees: r.totalEntryFeesCents,
    winnings: r.totalWinningsCents,
    net: r.netProfitLossCents,
    entries: r.numberOfEntries,
  });

  const byContestType = breakdown(results, (r) => r.contestType, metrics);
  const byBuyIn = breakdown(results, (r) => buyInTier(r.entryFeeCents), metrics);
  const byEntrySize = breakdown(results, (r) => entrySizeTier(r.fieldSize), metrics);
  const bySlate = breakdown(results, (r) => r.slate.slateName, metrics);
  const bySport = breakdown(results, (r) => r.slate.sport, metrics);
  const byLineupCount = breakdown(results, (r) => lineupCountTier(r.numberOfEntries), metrics);
  const byStack = breakdown(linkedResults, (r) => r.linkedLineup!.stackSummary, metrics);
  const bySalaryRemaining = breakdown(linkedResults, (r) => salaryRemainingTier(r.linkedLineup!.salaryUsed), metrics);
  const byOwnershipRange = breakdown(linkedResults, (r) => ownershipRangeTier(r.linkedLineup!.totalOwnership), metrics);

  let cumulative = 0;
  const bankrollTrend = results.map((r) => {
    cumulative += r.netProfitLossCents / 100;
    return { date: new Date(r.createdAt).toLocaleDateString(), cumulative: Number(cumulative.toFixed(2)) };
  });
  const roiChartData = byContestType.map((b) => ({ type: b.key, roi: b.roi ?? 0 }));
  const entriesChartData = byEntrySize.map((b) => ({ date: b.key, entries: b.entries, netCents: b.net }));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Contest & Results Tracker</h1>
        <p className="text-sm text-ink-400">Import your own results CSV to build a track record over time.</p>
      </div>

      <CsvUploadCard
        title="Results CSV"
        description="Import contest results for slates you've already imported salary data for."
        templateHref="/api/templates/results"
        previewAction={previewResultsCsvAction}
        commitAction={commitResultsCsvAction}
      />

      {distinctSlates < 10 ? (
        <Callout variant="warning" title="Small sample">
          You have tracked results for {distinctSlates} slate{distinctSlates === 1 ? '' : 's'}. Do not treat results
          as proof of a strategy until you have a larger sample. Never chase losses or raise stakes based on a small
          sample — review, consider, and track instead.
        </Callout>
      ) : null}

      {results.length === 0 ? (
        <EmptyState title="No results tracked yet" />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <Metric label="Contests" value={String(results.length)} />
            <Metric label="Entries" value={String(totalEntries)} />
            <Metric label="Total fees" value={formatCents(totalFees)} />
            <Metric label="Total winnings" value={formatCents(totalWinnings)} />
            <Metric label="Net P/L" value={formatCents(netPnl)} highlight={netPnl >= 0} />
            <Metric label="ROI" value={roi !== null ? formatPct(roi) : '—'} highlight={(roi ?? 0) >= 0} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Bankroll trend</CardTitle>
              <CardDescription>Cumulative net profit/loss over time, in the order results were imported.</CardDescription>
            </CardHeader>
            <CardContent>
              <BankrollTrendChart data={bankrollTrend} />
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>ROI by contest type</CardTitle>
              </CardHeader>
              <CardContent>
                <RoiByContestTypeChart data={roiChartData} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Entries by field-size tier</CardTitle>
              </CardHeader>
              <CardContent>
                <EntriesVsResultsChart data={entriesChartData} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>All tracked results</CardTitle>
              <CardDescription>
                Link a result to a SlateEdge-generated lineup to unlock stack/salary/ownership breakdowns below.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Contest</TableHead>
                    <TableHead>Slate</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Entries</TableHead>
                    <TableHead>Net</TableHead>
                    <TableHead>Linked lineup</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{r.contestName}</TableCell>
                      <TableCell className="text-xs text-ink-400">{r.slate.slateName}</TableCell>
                      <TableCell>{r.contestType}</TableCell>
                      <TableCell>{r.numberOfEntries}</TableCell>
                      <TableCell className={r.netProfitLossCents >= 0 ? 'text-teal-300' : 'text-rose-400'}>
                        {formatCents(r.netProfitLossCents)}
                      </TableCell>
                      <TableCell>
                        <LinkLineupSelect
                          resultId={r.id}
                          linkedLineupId={r.linkedLineupId}
                          options={lineupsBySlate.get(r.slateId) ?? []}
                        />
                      </TableCell>
                      <TableCell>
                        <DeleteResultButton resultId={r.id} contestName={r.contestName} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <BreakdownTable title="By sport" rows={bySport} />
          <BreakdownTable title="By contest type" rows={byContestType} />
          <BreakdownTable title="By buy-in level" rows={byBuyIn} />
          <BreakdownTable title="By entry-size tier" rows={byEntrySize} />
          <BreakdownTable title="By lineup count" rows={byLineupCount} />
          <BreakdownTable title="By slate" rows={bySlate} />

          {linkedResults.length === 0 ? (
            <Callout variant="info" title="Stack, salary, and ownership breakdowns">
              Link at least one result above to a SlateEdge-generated lineup to see breakdowns by stack construction,
              salary remaining, and total lineup ownership.
            </Callout>
          ) : (
            <>
              <BreakdownTable title="By stack construction" rows={byStack} />
              <BreakdownTable title="By salary remaining" rows={bySalaryRemaining} />
              <BreakdownTable title="By ownership range" rows={byOwnershipRange} />
            </>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <Card>
      <CardContent className="p-3">
        <p className="text-[11px] text-ink-400">{label}</p>
        <p className={highlight === undefined ? 'font-semibold text-ink-50' : highlight ? 'font-semibold text-teal-300' : 'font-semibold text-rose-400'}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function BreakdownTable({
  title,
  rows,
}: {
  title: string;
  rows: { key: string; count: number; entries: number; fees: number; winnings: number; net: number; roi: number | null }[];
}) {
  if (rows.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{title.replace('By ', '')}</TableHead>
              <TableHead>Contests</TableHead>
              <TableHead>Entries</TableHead>
              <TableHead>Fees</TableHead>
              <TableHead>Winnings</TableHead>
              <TableHead>Net</TableHead>
              <TableHead>ROI</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.key}>
                <TableCell className="max-w-xs whitespace-normal text-xs">{r.key}</TableCell>
                <TableCell>{r.count}</TableCell>
                <TableCell>{r.entries}</TableCell>
                <TableCell>{formatCents(r.fees)}</TableCell>
                <TableCell>{formatCents(r.winnings)}</TableCell>
                <TableCell className={r.net >= 0 ? 'text-teal-300' : 'text-rose-400'}>{formatCents(r.net)}</TableCell>
                <TableCell>{r.roi !== null ? formatPct(r.roi) : '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
