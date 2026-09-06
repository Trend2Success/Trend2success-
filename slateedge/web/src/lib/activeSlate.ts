'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { prisma } from '@/lib/db';
import { requireUser } from '@/lib/auth';

const ACTIVE_SLATE_COOKIE = 'se_active_slate';

export async function getActiveSlate() {
  const user = await requireUser();
  const cookieId = cookies().get(ACTIVE_SLATE_COOKIE)?.value;

  if (cookieId) {
    const slate = await prisma.slate.findFirst({ where: { id: cookieId, userId: user.id } });
    if (slate) return slate;
  }

  const latest = await prisma.slate.findFirst({
    where: { userId: user.id },
    orderBy: { createdAt: 'desc' },
  });
  return latest;
}

export async function setActiveSlateAction(formData: FormData) {
  const slateId = String(formData.get('slateId') ?? '');
  const user = await requireUser();
  const slate = await prisma.slate.findFirst({ where: { id: slateId, userId: user.id } });
  if (slate) {
    cookies().set(ACTIVE_SLATE_COOKIE, slateId, { path: '/', maxAge: 60 * 60 * 24 * 365 });
  }
  const redirectTo = String(formData.get('redirectTo') ?? '/dashboard');
  redirect(redirectTo);
}
