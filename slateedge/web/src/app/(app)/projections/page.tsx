import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout, EmptyState } from '@/components/ui/callout';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { BlendForm } from './blend-form';
import { ManualAdjustRow } from './manual-adjust-row';

export default async function ProjectionsPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();
  if (!slate) return <EmptyState title="No active slate" description="Create a slate first." />;

  const [sources, players, adjustments] = await Promise.all([
    prisma.projectionSource.findMany({ where: { slateId: slate.id } }),
    prisma.player.findMany({ where: { slateId: slate.id }, include: { projection: true }, orderBy: { salary: 'desc' } }),
    prisma.projectionAdjustment.findMany({
      where: { player: { slateId: slate.id } },
      include: { editor: true, player: true },
      orderBy: { createdAt: 'desc' },
      take: 50,
    }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Projection Lab</h1>
        <p className="text-sm text-ink-400">{slate.slateName} — transparent, editable projections. Nothing here is a guarantee.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Why this changed</CardTitle>
          <CardDescription>Plain-language explanation of every calculation on this page.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-xs text-ink-200">
          <p><strong>Base projection</strong> = an equal-weighted average of every imported projection source for that player, unless you set custom weights below.</p>
          <p><strong>Final projection</strong> = base projection plus any manual point or percent adjustments you apply, most recent first.</p>
          <p><strong>Value</strong> = final projection ÷ (salary ÷ 1000). <strong>Ceiling value</strong> = ceiling ÷ (salary ÷ 1000).</p>
          <p><strong>Leverage score</strong> = the player's ceiling percentile rank on this slate minus their ownership percentile rank, roughly -1 to 1. It is a description of where a player sits relative to the field, not a recommendation.</p>
        </CardContent>
      </Card>

      {sources.length > 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>Blend weights</CardTitle>
            <CardDescription>Recomputes base and final projections for every player using these weights. Resets manual adjustments.</CardDescription>
          </CardHeader>
          <CardContent>
            <BlendForm slateId={slate.id} sources={sources.map((s) => ({ id: s.id, sourceLabel: s.sourceLabel }))} />
          </CardContent>
        </Card>
      ) : sources.length === 0 ? (
        <Callout variant="warning">No projection sources imported yet. Import a projection CSV on the Slate Data Import page.</Callout>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Player projections</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player</TableHead>
                <TableHead>Base</TableHead>
                <TableHead>Final</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Ceiling Value</TableHead>
                <TableHead>Manual adjustment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {players.filter((p) => p.projection).map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    {p.playerName} <span className="text-ink-400">({p.position})</span>
                  </TableCell>
                  <TableCell>{p.projection!.basePoints.toFixed(2)}</TableCell>
                  <TableCell className="font-medium text-teal-300">{p.projection!.finalPoints.toFixed(2)}</TableCell>
                  <TableCell>{p.projection!.value?.toFixed(2) ?? '—'}</TableCell>
                  <TableCell>{p.projection!.ceilingValue?.toFixed(2) ?? '—'}</TableCell>
                  <TableCell>
                    <ManualAdjustRow playerId={p.id} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audit trail</CardTitle>
          <CardDescription>Every adjustment, who made it, and when.</CardDescription>
        </CardHeader>
        <CardContent>
          {adjustments.length === 0 ? (
            <p className="text-xs text-ink-400">No adjustments yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Player</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Before</TableHead>
                  <TableHead>After</TableHead>
                  <TableHead>Editor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {adjustments.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{new Date(a.createdAt).toLocaleString()}</TableCell>
                    <TableCell>{a.player.playerName}</TableCell>
                    <TableCell>{a.kind}</TableCell>
                    <TableCell>{a.beforeValue.toFixed(2)}</TableCell>
                    <TableCell>{a.afterValue.toFixed(2)}</TableCell>
                    <TableCell>{a.editor.displayName || a.editor.email}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
