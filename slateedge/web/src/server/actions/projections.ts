'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';
import { applyManualAdjustment } from '@/lib/calculations';
import { recomputeProjectionSnapshotsFromSources } from '@/server/actions/imports';
import { recomputeSlateAnalytics } from '@/lib/server/analytics';

export interface ProjectionFormState {
  error?: string;
  success?: string;
}

export async function applyBlendWeightsAction(
  _prev: ProjectionFormState,
  formData: FormData
): Promise<ProjectionFormState> {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return { error: 'Slate not found.' };

  const sources = await prisma.projectionSource.findMany({ where: { slateId } });
  const weights: Record<string, number> = {};
  for (const source of sources) {
    const raw = formData.get(`weight_${source.id}`);
    weights[source.id] = raw ? Number(raw) : 1;
  }

  await recomputeProjectionSnapshotsFromSources(slateId, user.id, weights);
  await logAudit(user.id, 'projection.adjust', { kind: 'blend_weight', weights }, { type: 'Slate', id: slateId });
  revalidatePath('/projections');
  revalidatePath('/players');
  revalidatePath('/ownership');
  return { success: 'Blend weights applied. Base and final projections were recomputed for every player.' };
}

export async function manualAdjustProjectionAction(formData: FormData) {
  const user = await requireUser();
  const playerId = String(formData.get('playerId') ?? '');
  const kind = String(formData.get('kind') ?? 'points') as 'points' | 'percent';
  const delta = Number(formData.get('delta') ?? 0);

  const player = await prisma.player.findFirst({
    where: { id: playerId, slate: { userId: user.id } },
    include: { projection: true },
  });
  if (!player?.projection) return;

  const before = player.projection.finalPoints;
  const after = applyManualAdjustment(before, kind, delta);

  await prisma.projectionSnapshot.update({ where: { playerId }, data: { finalPoints: after } });
  await prisma.projectionAdjustment.create({
    data: {
      playerId,
      editorUserId: user.id,
      kind: kind === 'points' ? 'manual_points' : 'manual_percent',
      beforeValue: before,
      afterValue: after,
      detail: { delta },
    },
  });

  await recomputeSlateAnalytics(player.slateId, user.id);
  await logAudit(user.id, 'projection.adjust', { kind, delta, before, after }, { type: 'Player', id: playerId });
  revalidatePath('/projections');
  revalidatePath('/players');
  revalidatePath('/ownership');
}
