'use server';

import { z } from 'zod';
import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';

export interface SettingsFormState {
  error?: string;
  success?: string;
}

const settingsSchema = z.object({
  sessionBudgetCents: z.coerce.number().int().min(0),
  stopLossCents: z.coerce.number().int().min(0),
  chalkThresholdPct: z.coerce.number().min(0).max(100),
  contrarianOwnershipPct: z.coerce.number().min(0).max(100),
  contrarianCeilingPctile: z.coerce.number().min(0).max(100),
  defaultSalaryCap: z.coerce.number().int().min(1000),
});

export async function updateSettingsAction(_prev: SettingsFormState, formData: FormData): Promise<SettingsFormState> {
  const user = await requireUser();
  const parsed = settingsSchema.safeParse({
    sessionBudgetCents: Math.round(Number(formData.get('sessionBudget') ?? 0) * 100),
    stopLossCents: Math.round(Number(formData.get('stopLoss') ?? 0) * 100),
    chalkThresholdPct: formData.get('chalkThresholdPct'),
    contrarianOwnershipPct: formData.get('contrarianOwnershipPct'),
    contrarianCeilingPctile: formData.get('contrarianCeilingPctile'),
    defaultSalaryCap: formData.get('defaultSalaryCap'),
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? 'Invalid settings' };
  }

  await prisma.settings.upsert({
    where: { userId: user.id },
    update: parsed.data,
    create: { userId: user.id, ...parsed.data },
  });

  await logAudit(user.id, 'settings.update', parsed.data);
  revalidatePath('/settings');
  revalidatePath('/dashboard');
  return { success: 'Settings saved.' };
}

export async function deleteAllDataAction(formData: FormData) {
  const user = await requireUser();
  const confirmation = String(formData.get('confirmation') ?? '');
  if (confirmation !== 'DELETE') return;

  await prisma.$transaction([
    prisma.slate.deleteMany({ where: { userId: user.id } }),
    prisma.lineupRun.deleteMany({ where: { userId: user.id } }),
    prisma.simulationRun.deleteMany({ where: { userId: user.id } }),
  ]);

  await logAudit(user.id, 'data.deleteAll');
  revalidatePath('/', 'layout');
}
