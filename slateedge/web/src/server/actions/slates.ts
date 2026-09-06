'use server';

import { z } from 'zod';
import { randomUUID } from 'crypto';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';

export interface SlateFormState {
  error?: string;
  success?: string;
}

const createSlateSchema = z.object({
  slateName: z.string().min(1, 'Slate name is required'),
  sport: z.string().default('NFL'),
  contestDate: z.string().refine((v) => !Number.isNaN(Date.parse(v)), 'Invalid contest date'),
});

export async function createSlateAction(_prev: SlateFormState, formData: FormData): Promise<SlateFormState> {
  const user = await requireUser();
  const parsed = createSlateSchema.safeParse({
    slateName: formData.get('slateName'),
    sport: formData.get('sport') || 'NFL',
    contestDate: formData.get('contestDate'),
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? 'Invalid input' };
  }

  const slate = await prisma.slate.create({
    data: {
      userId: user.id,
      slateId: randomUUID(),
      slateName: parsed.data.slateName,
      sport: parsed.data.sport.toUpperCase(),
      contestDate: new Date(parsed.data.contestDate),
    },
  });

  await logAudit(user.id, 'import.salary', { note: 'slate created manually' }, { type: 'Slate', id: slate.id });
  revalidatePath('/slates');
  redirect(`/slates/${slate.id}`);
}

export async function deleteSlateAction(formData: FormData) {
  const user = await requireUser();
  const slateId = String(formData.get('slateId') ?? '');
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (!slate) return;
  await prisma.slate.delete({ where: { id: slate.id } });
  await logAudit(user.id, 'slate.delete', { slateName: slate.slateName }, { type: 'Slate', id: slate.id });
  revalidatePath('/slates');
  revalidatePath('/dashboard');
}
