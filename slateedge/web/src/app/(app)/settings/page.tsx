import { requireUser } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Callout } from '@/components/ui/callout';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { SettingsForm } from './settings-form';
import { DeleteAllDataButton } from './danger-zone';

const PLANNED_FEATURES = [
  'Cloud/OAuth authentication (v1 uses local accounts only)',
  'Authorized third-party projection API connectors',
  'Multi-user shared workspaces',
  'Native mobile app',
];

export default async function SettingsPage() {
  const user = await requireUser();
  const [settings, auditLogs] = await Promise.all([
    prisma.settings.findUnique({ where: { userId: user.id } }),
    prisma.auditLog.findMany({ where: { userId: user.id }, orderBy: { createdAt: 'desc' }, take: 50 }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Settings & Responsible Play</h1>
        <p className="text-sm text-ink-400">{user.email}</p>
      </div>

      <Callout variant="warning" title="Responsible play">
        DFS involves financial risk. Use a fixed entertainment budget. Model outputs are estimates and do not
        guarantee results. Review your session budget and stop-loss below before every session — never chase losses
        or raise stakes because of a prior result.
      </Callout>

      <Card>
        <CardHeader>
          <CardTitle>Budget, thresholds & defaults</CardTitle>
        </CardHeader>
        <CardContent>
          <SettingsForm
            defaults={{
              sessionBudget: (settings?.sessionBudgetCents ?? 10000) / 100,
              stopLoss: (settings?.stopLossCents ?? 5000) / 100,
              chalkThresholdPct: settings?.chalkThresholdPct ?? 25,
              contrarianOwnershipPct: settings?.contrarianOwnershipPct ?? 8,
              contrarianCeilingPctile: settings?.contrarianCeilingPctile ?? 70,
              defaultSalaryCap: settings?.defaultSalaryCap ?? 50000,
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Planned features</CardTitle>
          <CardDescription>Not implemented in this version — shown here for transparency, not active in the product.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {PLANNED_FEATURES.map((f) => (
            <div key={f} className="flex items-center gap-2 text-xs text-ink-400">
              <Badge variant="outline">Planned</Badge>
              {f}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audit log</CardTitle>
          <CardDescription>Every import, edit, optimizer run, and export is logged here.</CardDescription>
        </CardHeader>
        <CardContent>
          {auditLogs.length === 0 ? (
            <p className="text-xs text-ink-400">No activity yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{new Date(log.createdAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-ink-400">
                      {log.entityType ? `${log.entityType} · ${log.entityId}` : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Danger zone</CardTitle>
          <CardDescription>Permanently delete every slate, player, projection, lineup, and simulation you've stored.</CardDescription>
        </CardHeader>
        <CardContent>
          <DeleteAllDataButton />
        </CardContent>
      </Card>
    </div>
  );
}
