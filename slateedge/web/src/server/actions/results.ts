'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';

// Manually ties an imported result row to a SlateEdge-generated lineup so the
// Results Tracker can break results down by stack construction, salary
// remaining, and ownership range — data that a plain results CSV row (which
// only carries a free-text lineup_id) cannot supply on its own.
export async function linkContestResultToLineupAction(formData: FormData) {
  const user = await requireUser();
  const resultId = String(formData.get('resultId') ?? '');
  const lineupId = String(formData.get('lineupId') ?? '');

  const result = await prisma.contestResult.findFirst({ where: { id: resultId, slate: { userId: user.id } } });
  if (!result) return;

  if (!lineupId) {
    await prisma.contestResult.update({ where: { id: resultId }, data: { linkedLineupId: null } });
    revalidatePath('/results');
    return;
  }

  const lineup = await prisma.lineup.findFirst({
    where: { id: lineupId, run: { slateId: result.slateId, userId: user.id } },
  });
  if (!lineup) return;

  await prisma.contestResult.update({ where: { id: resultId }, data: { linkedLineupId: lineup.id } });
  await logAudit(user.id, 'results.link', { resultId, lineupId }, { type: 'ContestResult', id: resultId });
  revalidatePath('/results');
}

export async function deleteContestResultAction(formData: FormData) {
  const user = await requireUser();
  const resultId = String(formData.get('resultId') ?? '');
  const result = await prisma.contestResult.findFirst({
    where: { id: resultId, slate: { userId: user.id } },
  });
  if (!result) return;
  await prisma.contestResult.delete({ where: { id: resultId } });
  await logAudit(user.id, 'results.delete', { contestName: result.contestName }, { type: 'ContestResult', id: resultId });
  revalidatePath('/results');
  revalidatePath('/dashboard');
}
