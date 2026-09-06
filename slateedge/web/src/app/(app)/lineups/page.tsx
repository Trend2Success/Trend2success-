import Link from 'next/link';
import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { EmptyState } from '@/components/ui/callout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LineupBuilderForm } from './lineup-builder-form';
import { DEFAULT_SALARY_CAP } from '@/lib/optimizer/types';

export default async function LineupsPage() {
  const user = await requireUser();
  const slate = await getActiveSlate();
  if (!slate) return <EmptyState title="No active slate" description="Create a slate and import players first." />;

  const [players, settings, runs, presets] = await Promise.all([
    prisma.player.findMany({ where: { slateId: slate.id }, orderBy: { salary: 'desc' } }),
    prisma.settings.findUnique({ where: { userId: user.id } }),
    prisma.lineupRun.findMany({ where: { slateId: slate.id }, include: { lineups: true }, orderBy: { createdAt: 'desc' }, take: 10 }),
    prisma.lineupPreset.findMany({ where: { userId: user.id }, orderBy: { updatedAt: 'desc' } }),
  ]);

  if (players.length === 0) {
    return <EmptyState title="No players in this slate" description="Import a salary CSV before building lineups." />;
  }

  const playerOptions = players.map((p) => ({ id: p.playerId, label: `${p.playerName} (${p.position}, ${p.team})` }));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Lineup Builder</h1>
        <p className="text-sm text-ink-400">
          {slate.slateName} — outputs are <strong>model-ranked lineups</strong>, estimates only, never guaranteed
          winners.
        </p>
      </div>

      <LineupBuilderForm
        slateId={slate.id}
        salaryCapDefault={settings?.defaultSalaryCap ?? DEFAULT_SALARY_CAP}
        playerOptions={playerOptions}
        savedPresets={presets.map((p) => ({ id: p.id, name: p.name, settingsJson: p.settingsJson }))}
      />

      <Card>
        <CardHeader>
          <CardTitle>Recent optimizer runs</CardTitle>
          <CardDescription>Full settings and seed are saved with each run for comparison.</CardDescription>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-xs text-ink-400">No runs yet.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-graphite-700">
              {runs.map((r) => (
                <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p>
                      {r.presetName} <Badge variant="outline" className="ml-1">{r.lineups.length} lineups</Badge>
                    </p>
                    <p className="text-xs text-ink-400">
                      {new Date(r.createdAt).toLocaleString()} · seed {r.seedUsed ?? 'random'}
                    </p>
                  </div>
                  <Button asChild size="sm" variant="secondary">
                    <Link href={`/portfolio?runId=${r.id}`}>Review in Portfolio</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
