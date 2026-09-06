import { NextRequest, NextResponse } from 'next/server';
import { getSessionUserId } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { toCsv } from '@/lib/csv/engine';
import { logAudit } from '@/lib/audit';
import { DEFAULT_ROSTER_SLOTS, buildSlotLabels } from '@/lib/optimizer/types';

// Exports generated lineups to a CSV the user can review and manually upload
// wherever they enter contests. SlateEdge never uploads, submits, or connects
// to any contest operator itself. The column order is user-configurable via
// `slots` (comma-separated) and `field` (name|id) query params — verify the
// result against your contest operator's current upload template before use.
export async function GET(req: NextRequest) {
  const userId = await getSessionUserId();
  if (!userId) return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 });

  const runId = req.nextUrl.searchParams.get('runId');
  if (!runId) return NextResponse.json({ error: 'runId is required' }, { status: 400 });

  const field = (req.nextUrl.searchParams.get('field') as 'name' | 'id') || 'name';
  const slotsParam = req.nextUrl.searchParams.get('slots');
  const slotLabels = slotsParam ? slotsParam.split(',') : buildSlotLabels(DEFAULT_ROSTER_SLOTS);

  const run = await prisma.lineupRun.findFirst({ where: { id: runId, userId } });
  if (!run) return NextResponse.json({ error: 'Lineup run not found' }, { status: 404 });

  const lineups = await prisma.lineup.findMany({
    where: { runId },
    include: { players: { include: { player: true } } },
    orderBy: { createdAt: 'asc' },
  });

  const rows = lineups.map((lineup) => {
    const bySlot = new Map(lineup.players.map((lp) => [lp.slot, lp.player]));
    return slotLabels.map((slot) => {
      const player = bySlot.get(slot);
      if (!player) return '';
      return field === 'id' ? player.playerId : `${player.playerName} (${player.playerId})`;
    });
  });

  const csv = toCsv(slotLabels, rows);

  await logAudit(userId, 'export.csv', { runId, lineupCount: lineups.length }, { type: 'LineupRun', id: runId });

  return new NextResponse(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="slateedge-lineups-${runId}.csv"`,
    },
  });
}
