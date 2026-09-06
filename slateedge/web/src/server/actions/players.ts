'use server';

import { z } from 'zod';
import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';

export async function togglePlayerFlagAction(formData: FormData) {
  const user = await requireUser();
  const playerId = String(formData.get('playerId') ?? '');
  const flag = String(formData.get('flag') ?? '') as 'locked' | 'excluded';
  const value = formData.get('value') === 'true';

  const player = await prisma.player.findFirst({
    where: { id: playerId, slate: { userId: user.id } },
  });
  if (!player) return;

  if (flag === 'locked' && value && player.excluded) {
    await prisma.player.update({ where: { id: playerId }, data: { excluded: false } });
  }
  if (flag === 'excluded' && value && player.locked) {
    await prisma.player.update({ where: { id: playerId }, data: { locked: false } });
  }

  await prisma.player.update({ where: { id: playerId }, data: { [flag]: value } });
  await logAudit(user.id, flag === 'locked' ? 'player.lock' : 'player.exclude', { value }, { type: 'Player', id: playerId });
  revalidatePath('/players');
  revalidatePath('/lineups');
}

const notesSchema = z.object({ playerId: z.string().min(1), notes: z.string().max(2000) });

export async function updatePlayerNotesAction(formData: FormData) {
  const user = await requireUser();
  const parsed = notesSchema.safeParse({ playerId: formData.get('playerId'), notes: formData.get('notes') ?? '' });
  if (!parsed.success) return;

  const player = await prisma.player.findFirst({ where: { id: parsed.data.playerId, slate: { userId: user.id } } });
  if (!player) return;

  await prisma.player.update({ where: { id: player.id }, data: { notes: parsed.data.notes } });
  await logAudit(user.id, 'player.edit', { field: 'notes' }, { type: 'Player', id: player.id });
  revalidatePath('/players');
}

const TAGS = ['CORE', 'STRONG_PLAY', 'TOURNAMENT_PIVOT', 'VALUE', 'FADE', 'INJURY_WATCH', 'CUSTOM'] as const;

export async function togglePlayerTagAction(formData: FormData) {
  const user = await requireUser();
  const playerId = String(formData.get('playerId') ?? '');
  const tag = String(formData.get('tag') ?? '');
  const label = formData.get('label') ? String(formData.get('label')) : '';
  const add = formData.get('add') === 'true';

  if (!(TAGS as readonly string[]).includes(tag)) return;
  const player = await prisma.player.findFirst({ where: { id: playerId, slate: { userId: user.id } } });
  if (!player) return;

  if (add) {
    await prisma.playerTag.upsert({
      where: { playerId_tag_label: { playerId, tag: tag as (typeof TAGS)[number], label } },
      update: {},
      create: { playerId, tag: tag as (typeof TAGS)[number], label },
    });
  } else {
    await prisma.playerTag.deleteMany({ where: { playerId, tag: tag as (typeof TAGS)[number], label } });
  }

  await logAudit(user.id, 'player.edit', { field: 'tag', tag, add }, { type: 'Player', id: playerId });
  revalidatePath('/players');
}
