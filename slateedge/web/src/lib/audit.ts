import { prisma } from '@/lib/db';

export type AuditAction =
  | 'import.salary'
  | 'import.projection'
  | 'import.results'
  | 'player.edit'
  | 'player.lock'
  | 'player.exclude'
  | 'projection.adjust'
  | 'optimizer.run'
  | 'simulation.run'
  | 'lineup.edit'
  | 'lineup.delete'
  | 'export.csv'
  | 'slate.delete'
  | 'results.delete'
  | 'results.link'
  | 'data.deleteAll'
  | 'settings.update'
  | 'auth.login'
  | 'auth.register'
  | 'auth.logout';

export async function logAudit(
  userId: string,
  action: AuditAction,
  detail?: Record<string, unknown>,
  entity?: { type: string; id: string }
) {
  await prisma.auditLog.create({
    data: {
      userId,
      action,
      detail: detail ? JSON.parse(JSON.stringify(detail)) : undefined,
      entityType: entity?.type,
      entityId: entity?.id,
    },
  });
}
