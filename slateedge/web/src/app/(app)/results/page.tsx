import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout, EmptyState } from '@/components/ui/callout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CsvUploadCard } from '@/components/csv-upload-card';
import { previewResultsCsvAction, commitResultsCsvAction } from '@/server/actions/imports';
import { formatCents, formatPct } from '@/lib/utils';
import { BankrollTrendChart, RoiByContestTypeChart, EntriesVsResultsChart } from './charts';

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

export default async function ResultsPage() {
  const user = await requireUser();
  const results = await prisma.contestResult.findMany({
    where: { slate: { userId: user.id } },
    include: { slate: true },
    orderBy: { createdAt: 'asc' },
  });

  const totalEntries = results.reduce((s, r) => s + r.numberOfEntries, 0);
  const totalFees = results.reduce((s, r) => s + r.totalEntryFeesCents, 0);
  const totalWinnings = results.reduce((s, r) => s + r.totalWinningsCents, 0);
  const netPnl = results.reduce((s, r) => s + r.netProfitLossCents, 0);
  const roi = totalFees > 0 ? (netPnl / totalFees) * 100 : null;
  const distinctSlates = new Set(results.map((r) => r.slateId)).size;

  function breakdown<K extends string>(keyFn: (r: (typeof results)[number]) => K) {
    const map = new Map<K, { fees: number; winnings: number; net: number; entries: number; count: number }>();
    for (const r of results) {
      const key = keyFn(r);
      const entry = map.get(key) ?? { fees: 0, winnings: 0, net: 0, entries: 0, count: 0 };
      entry.fees += r.totalEntryFeesCents;
      entry.winnings += r.totalWinningsCents;
      entry.net += r.netProfitLossCents;
      entry.entries += r.numberOfEntries;
      entry.count += 1;
      map.set(key, entry);
    }
    return [...map.entries()].map(([key, v]) => ({
      key,
      ...v,
      roi: v.fees > 0 ? (v.net / v.fees) * 100 : null,
    }));
  }

  const byContestType = breakdown((r) => r.contestType);
  const byBuyIn = breakdown((r) => buyInTier(r.entryFeeCents));
  const byEntrySize = breakdown((r) => entrySizeTier(r.fieldSize));
  const bySlate = breakdown((r) => r.slate.slateName);

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

          <BreakdownTable title="By contest type" rows={byContestType} />
          <BreakdownTable title="By buy-in level" rows={byBuyIn} />
          <BreakdownTable title="By entry-size tier" rows={byEntrySize} />
          <BreakdownTable title="By slate" rows={bySlate} />
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
                <TableCell>{r.key}</TableCell>
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
