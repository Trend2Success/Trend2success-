'use server';

import { z } from 'zod';
import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';
import { logAudit } from '@/lib/audit';

export interface PresetFormState {
  error?: string;
  success?: string;
}

const saveSchema = z.object({
  name: z.string().min(1, 'Name your preset').max(80),
  settingsJson: z.string().min(1),
});

// Saves the current Lineup Builder form state as a named, reusable preset for
// this user. Explicitly a starting point the user can reload and keep
// editing — never described as a proven strategy.
export async function saveLineupPresetAction(_prev: PresetFormState, formData: FormData): Promise<PresetFormState> {
  const user = await requireUser();
  const parsed = saveSchema.safeParse({
    name: formData.get('name'),
    settingsJson: formData.get('settingsJson'),
  });
  if (!parsed.success) return { error: parsed.error.issues[0]?.message ?? 'Invalid preset' };

  let settings: unknown;
  try {
    settings = JSON.parse(parsed.data.settingsJson);
  } catch {
    return { error: 'Could not read the current form settings.' };
  }

  await prisma.lineupPreset.upsert({
    where: { userId_name: { userId: user.id, name: parsed.data.name } },
    update: { settingsJson: settings as object },
    create: { userId: user.id, name: parsed.data.name, settingsJson: settings as object },
  });

  await logAudit(user.id, 'settings.update', { scope: 'lineup_preset', name: parsed.data.name });
  revalidatePath('/lineups');
  return { success: `Saved preset "${parsed.data.name}". Presets are starting points — keep reviewing and editing them as you learn.` };
}

export async function deleteLineupPresetAction(formData: FormData) {
  const user = await requireUser();
  const presetId = String(formData.get('presetId') ?? '');
  const preset = await prisma.lineupPreset.findFirst({ where: { id: presetId, userId: user.id } });
  if (!preset) return;
  await prisma.lineupPreset.delete({ where: { id: preset.id } });
  await logAudit(user.id, 'settings.update', { scope: 'lineup_preset', action: 'delete', name: preset.name });
  revalidatePath('/lineups');
}
