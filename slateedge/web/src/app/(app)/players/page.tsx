import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { EmptyState } from '@/components/ui/callout';
import { PlayerPoolTable } from './player-pool-table';
import type { PlayerRow } from '@/lib/types';

export default async function PlayersPage() {
  await requireUser();
  const slate = await getActiveSlate();

  if (!slate) {
    return <EmptyState title="No active slate" description="Create a slate and import a salary CSV first." />;
  }

  const players = await prisma.player.findMany({
    where: { slateId: slate.id },
    include: { projection: true, tags: true },
    orderBy: { salary: 'desc' },
  });

  const rows: PlayerRow[] = players.map((p) => ({
    id: p.id,
    playerId: p.playerId,
    name: p.playerName,
    team: p.team,
    opponent: p.opponent,
    position: p.position,
    gameInfo: p.gameInfo || p.gameId,
    salary: p.salary,
    status: p.status,
    locked: p.locked,
    excluded: p.excluded,
    notes: p.notes ?? '',
    tags: p.tags.map((t) => ({ tag: t.tag, label: t.label })),
    projection: p.projection?.finalPoints ?? null,
    floor: p.projection?.floor ?? null,
    ceiling: p.projection?.ceiling ?? null,
    stdev: p.projection?.standardDeviation ?? null,
    ownership: p.projection?.projectedOwnership ?? null,
    leverage: p.projection?.leverageScore ?? null,
    value: p.projection?.value ?? null,
    ceilingValue: p.projection?.ceilingValue ?? null,
    chalkFlag: p.projection?.chalkFlag ?? false,
    contrarianFlag: p.projection?.contrarianFlag ?? false,
  }));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">Player Pool</h1>
        <p className="text-sm text-ink-400">{slate.slateName} — {rows.length} players.</p>
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No players yet" description="Import a salary CSV for this slate on the Slate Data Import page." />
      ) : (
        <PlayerPoolTable rows={rows} />
      )}
    </div>
  );
}
