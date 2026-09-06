import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { getActiveSlate } from '@/lib/activeSlate';
import { AppShell } from '@/components/app-shell';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const [slates, activeSlate] = await Promise.all([
    prisma.slate.findMany({
      where: { userId: user.id },
      orderBy: { createdAt: 'desc' },
      select: { id: true, slateName: true, contestDate: true, isDemo: true },
    }),
    getActiveSlate(),
  ]);

  return (
    <AppShell
      displayName={user.displayName || user.email}
      slates={slates.map((s) => ({ ...s, contestDate: s.contestDate.toISOString() }))}
      activeSlateId={activeSlate?.id}
    >
      {children}
    </AppShell>
  );
}
