import Link from 'next/link';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout, EmptyState } from '@/components/ui/callout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { ceilingToOwnershipRatio } from '@/lib/calculations';

export default async function OwnershipPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();
  if (!slate) return <EmptyState title="No active slate" description="Create a slate first." />;

  const [players, settings] = await Promise.all([
    prisma.player.findMany({ where: { slateId: slate.id }, include: { projection: true }, orderBy: { salary: 'desc' } }),
    prisma.settings.findUnique({ where: { userId: user.id } }),
  ]);

  const withProjection = players.filter((p) => p.projection);
  const sorted = [...withProjection].sort((a, b) => (b.projection!.leverageScore ?? 0) - (a.projection!.leverageScore ?? 0));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Ownership & Leverage</h1>
        <p className="text-sm text-ink-400">{slate.slateName}</p>
      </div>

      <Callout variant="info">
        Leverage describes where a player's ceiling ranks relative to their ownership on this slate — it is not a
        recommendation. Low ownership alone does not make a player a good tournament play; a low-owned player can
        still have a low ceiling. No player here is ever called a "lock."
      </Callout>

      <Card>
        <CardHeader>
          <CardTitle>Thresholds</CardTitle>
          <CardDescription>
            Chalk flag at ≥ {settings?.chalkThresholdPct ?? 25}% ownership. Contrarian flag at ≤{' '}
            {settings?.contrarianOwnershipPct ?? 8}% ownership and ≥ {settings?.contrarianCeilingPctile ?? 70}th ceiling
            percentile. Adjust these in{' '}
            <Link href="/settings" className="text-teal-400 hover:underline">
              Settings
            </Link>
            .
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Players ranked by leverage</CardTitle>
        </CardHeader>
        <CardContent>
          {sorted.length === 0 ? (
            <p className="text-xs text-ink-400">Import projections with ownership data to see leverage.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Player</TableHead>
                  <TableHead>Ownership %</TableHead>
                  <TableHead>Ceiling</TableHead>
                  <TableHead>Ceiling / Own Ratio</TableHead>
                  <TableHead>Leverage</TableHead>
                  <TableHead>Flags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((p) => {
                  const own = p.projection!.projectedOwnership ?? 0;
                  const ceiling = p.projection!.ceiling ?? p.projection!.finalPoints;
                  const ratio = ceilingToOwnershipRatio(ceiling, own);
                  return (
                    <TableRow key={p.id}>
                      <TableCell>
                        {p.playerName} <span className="text-ink-400">({p.position})</span>
                      </TableCell>
                      <TableCell>{own.toFixed(1)}%</TableCell>
                      <TableCell>{ceiling.toFixed(1)}</TableCell>
                      <TableCell>{ratio ?? '—'}</TableCell>
                      <TableCell>{(p.projection!.leverageScore ?? 0).toFixed(2)}</TableCell>
                      <TableCell className="flex gap-1">
                        {p.projection!.chalkFlag ? <Badge variant="amber">Chalk</Badge> : null}
                        {p.projection!.contrarianFlag ? <Badge variant="teal">Contrarian</Badge> : null}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
